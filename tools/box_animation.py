"""Append an explicit, portable hinge animation to a closed packaging GLB."""
import json
import math
import struct
from pathlib import Path


def read_glb(path):
    raw = Path(path).read_bytes()
    magic, version, length = struct.unpack_from('<III', raw)
    if magic != 0x46546C67 or version != 2 or length != len(raw):
        raise ValueError('Invalid GLB header')
    offset, document, binary = 12, None, None
    while offset < len(raw):
        size, kind = struct.unpack_from('<II', raw, offset)
        body = raw[offset + 8:offset + 8 + size]
        if len(body) != size:
            raise ValueError('Truncated GLB chunk')
        if kind == 0x4E4F534A:
            document = json.loads(body)
        elif kind == 0x004E4942:
            binary = body
        else:
            raise ValueError('Unexpected GLB chunk')
        offset += 8 + size
    if document is None or binary is None:
        raise ValueError('Expected JSON and embedded binary chunks')
    return document, binary


def write_glb(path, document, binary):
    data = json.dumps(document, separators=(',', ':'), ensure_ascii=False).encode()
    data += b' ' * (-len(data) % 4)
    binary += b'\0' * (-len(binary) % 4)
    total = 12 + 8 + len(data) + 8 + len(binary)
    Path(path).write_bytes(struct.pack('<III', 0x46546C67, 2, total)
                          + struct.pack('<II', len(data), 0x4E4F534A) + data
                          + struct.pack('<II', len(binary), 0x004E4942) + binary)


def append_open_animation(path, hinges, duration=2.0):
    """Use recorded local XYZW endpoints; never transform any model vertices."""
    document, original = read_glb(path)
    if document.get('animations'):
        raise ValueError('Expected a static closed export')
    if len(document.get('buffers', [])) != 1 or document['buffers'][0].get('uri'):
        raise ValueError('Expected one embedded buffer')
    if not hinges or not math.isfinite(duration) or duration <= 0:
        raise ValueError('Animation needs hinges and a positive duration')
    by_name = {}
    for index, node in enumerate(document['nodes']):
        by_name.setdefault(node.get('name'), []).append(index)
    binary = bytearray(original)
    accessors = document.setdefault('accessors', [])
    views = document.setdefault('bufferViews', [])
    animation = {'name': 'Open', 'channels': [], 'samplers': [],
                 'extras': {'description': 'Closed at 0 seconds; fully open at 2 seconds. Reverse to close.'}}

    def accessor(values, kind, count, minimum=None, maximum=None):
        binary.extend(b'\0' * (-len(binary) % 4))
        offset = len(binary)
        payload = struct.pack('<' + 'f' * len(values), *values)
        binary.extend(payload)
        views.append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(payload)})
        record = {'bufferView': len(views) - 1, 'componentType': 5126,
                  'count': count, 'type': kind}
        if minimum is not None:
            record.update(min=minimum, max=maximum)
        accessors.append(record)
        return len(accessors) - 1

    seen = set()
    for hinge in hinges:
        name = hinge['name']
        if name in seen or len(by_name.get(name, [])) != 1:
            raise ValueError(f'Missing, duplicate or ambiguous hinge: {name}')
        seen.add(name)
        node_index = by_name[name][0]
        node = document['nodes'][node_index]
        if 'matrix' in node:
            raise ValueError(f'Animated hinge has a matrix instead of TRS: {name}')
        quaternions = [hinge['closedQuaternion'], hinge['openQuaternion']]
        for q in quaternions:
            if len(q) != 4 or not all(math.isfinite(x) for x in q):
                raise ValueError('Invalid rotation quaternion')
            if abs(sum(x * x for x in q) - 1) > 1e-5:
                raise ValueError('Rotation quaternion must be normalized')
        actual = node.get('rotation', [0, 0, 0, 1])
        dot = abs(sum(a * b for a, b in zip(actual, quaternions[0])))
        if abs(dot - 1) > 1e-5:
            raise ValueError(f'Closed hinge pose differs from exported node: {name}')
        phase = float(hinge.get('animationPhase', 0))
        if not 0 <= phase < 0.9:
            raise ValueError('Animation phase must be in [0, 0.9)')
        times = [0, duration] if phase == 0 else [0, phase * duration, duration]
        values = quaternions if phase == 0 else [quaternions[0], *quaternions]
        input_index = accessor(times, 'SCALAR', len(times), [0], [duration])
        output_index = accessor([v for q in values for v in q], 'VEC4', len(values))
        sampler = len(animation['samplers'])
        animation['samplers'].append({'input': input_index, 'output': output_index,
                                      'interpolation': 'LINEAR'})
        animation['channels'].append({'sampler': sampler,
                                      'target': {'node': node_index, 'path': 'rotation'}})
    document['animations'] = [animation]
    document['buffers'][0]['byteLength'] = len(binary)
    write_glb(path, document, bytes(binary))
    return {'name': 'Open', 'durationSeconds': duration, 'hinges': len(hinges),
            'originalBinaryBytesPreserved': len(original)}
