#!/usr/bin/env python3
"""Inspect the repository's self-contained, uncompressed glTF 2.0 exports.

Checks container/buffer integrity, geometry, embedded resources and label UVs.
This is an export-contract check, not a replacement for the Khronos validator
or an engine import/render review. Bounds are mesh-local, before node transforms.
"""
import argparse
import json
import math
from pathlib import Path
import struct
import sys


LABEL_NAMES = {
    "front": {"FrontLabel", "Front printed paper label"},
    "rear": {"RearLabel", "Rear printed information"},
}
COMPONENTS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
              5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
          "MAT2": 4, "MAT3": 9, "MAT4": 16}


class ValidationError(ValueError):
    """An export cannot satisfy the repository's import contract."""


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def integer(value, context, minimum=0):
    require(type(value) is int and value >= minimum,
            f"{context}: expected integer >= {minimum}")
    return value


def reference(items, index, context):
    integer(index, context)
    require(index < len(items), f"{context}: index {index} out of range")
    return items[index]


def finite(values, context):
    require(all(type(v) in (int, float) and math.isfinite(v) for v in values),
            f"{context}: non-finite or non-numeric value")


def read_glb(path):
    data = Path(path).read_bytes()
    require(len(data) >= 20, "truncated GLB header")
    magic, version, length = struct.unpack_from("<4sII", data)
    require(magic == b"glTF" and version == 2, "expected GLB version 2")
    require(length == len(data), "GLB declared length differs from file size")
    chunks = []
    cursor = 12
    while cursor < len(data):
        require(cursor + 8 <= len(data), "truncated GLB chunk header")
        size, kind = struct.unpack_from("<II", data, cursor)
        cursor += 8
        require(size % 4 == 0, "GLB chunk length must be aligned to four bytes")
        require(cursor + size <= len(data), "truncated GLB chunk payload")
        chunks.append((kind, data[cursor:cursor + size]))
        cursor += size
    require([kind for kind, _ in chunks] == [0x4E4F534A, 0x004E4942],
            "expected one JSON chunk followed by one BIN chunk")
    try:
        document = json.loads(chunks[0][1].decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        raise ValidationError(f"invalid GLB JSON: {error}") from error
    require(isinstance(document, dict), "GLB JSON must be an object")
    require(document.get("asset", {}).get("version") == "2.0", "expected glTF 2.0 asset")
    return document, chunks[1][1], len(data)


class Accessors:
    """Decode typed accessors, including interleaving, matrix padding and sparse data."""

    def __init__(self, document, binary):
        self.document = document
        self.binary = binary
        self.views = document.get("bufferViews", [])
        self.items = document.get("accessors", [])
        self.cache = {}
        buffers = document.get("buffers", [])
        require(len(buffers) == 1, "expected one embedded buffer")
        require("uri" not in buffers[0], "buffer must use embedded BIN data, without a URI")
        size = integer(buffers[0].get("byteLength"), "buffer.byteLength", 1)
        require(size <= len(binary) <= size + 3, "BIN length differs from buffer.byteLength")
        for index, view in enumerate(self.views):
            require(view.get("buffer") == 0, f"bufferView {index}: invalid buffer")
            start = integer(view.get("byteOffset", 0), f"bufferView {index}.byteOffset")
            length = integer(view.get("byteLength"), f"bufferView {index}.byteLength", 1)
            require(start + length <= size, f"bufferView {index}: exceeds embedded buffer")
            if "byteStride" in view:
                stride = integer(view["byteStride"], f"bufferView {index}.byteStride", 4)
                require(stride <= 252 and stride % 4 == 0,
                        f"bufferView {index}: invalid byteStride")

    def layout(self, item, context):
        component = item.get("componentType")
        shape = item.get("type")
        require(component in COMPONENTS and shape in WIDTHS,
                f"{context}: invalid componentType/type")
        code, size = COMPONENTS[component]
        width = WIDTHS[shape]
        if shape.startswith("MAT"):
            rows = int(shape[-1])
            column_size = (rows * size + 3) // 4 * 4
            offsets = [column * column_size + row * size
                       for column in range(rows) for row in range(rows)]
            element_size = rows * column_size
        else:
            offsets = [n * size for n in range(width)]
            element_size = width * size
        return code, size, offsets, element_size

    def unpack(self, view_index, offset, count, layout, context, packed=False):
        view = reference(self.views, view_index, context + ".bufferView")
        code, size, offsets, element_size = layout
        offset = integer(offset, context + ".byteOffset")
        stride = element_size if packed else view.get("byteStride", element_size)
        require(not packed or "byteStride" not in view,
                f"{context}: sparse bufferView cannot have byteStride")
        require(stride >= element_size and stride % size == 0,
                f"{context}: byteStride smaller than element or misaligned")
        start = view.get("byteOffset", 0) + offset
        require(offset % size == 0 and start % size == 0, f"{context}: misaligned accessor")
        require(offset + (count - 1) * stride + element_size <= view["byteLength"],
                f"{context}: accessor exceeds its bufferView")
        scalar = struct.Struct("<" + code)
        return [tuple(scalar.unpack_from(self.binary, start + n * stride + shift)[0]
                      for shift in offsets) for n in range(count)]

    def read(self, index):
        item = reference(self.items, index, "accessor")
        if index in self.cache:
            return self.cache[index]
        context = f"accessor {index}"
        count = integer(item.get("count"), context + ".count", 1)
        layout = self.layout(item, context)
        if "bufferView" in item:
            values = self.unpack(item["bufferView"], item.get("byteOffset", 0), count, layout, context)
        else:
            require(item.get("byteOffset", 0) == 0, f"{context}: byteOffset without bufferView")
            values = [(0,) * WIDTHS[item["type"]] for _ in range(count)]
        sparse = item.get("sparse")
        if sparse:
            sparse_count = integer(sparse.get("count"), context + ".sparse.count", 1)
            require(sparse_count <= count, f"{context}: sparse count exceeds accessor count")
            indices = sparse["indices"]
            require(indices.get("componentType") in (5121, 5123, 5125),
                    f"{context}: invalid sparse index componentType")
            index_layout = self.layout({**indices, "type": "SCALAR"}, context)
            targets = [v[0] for v in self.unpack(indices["bufferView"], indices.get("byteOffset", 0),
                       sparse_count, index_layout, context + ".sparse.indices", packed=True)]
            require(all(0 <= target < count for target in targets)
                    and all(a < b for a, b in zip(targets, targets[1:])),
                    f"{context}: sparse indices must be increasing and in range")
            source = sparse["values"]
            updates = self.unpack(source["bufferView"], source.get("byteOffset", 0), sparse_count,
                                  layout, context + ".sparse.values", packed=True)
            for target, value in zip(targets, updates):
                values[target] = value
        if item.get("normalized"):
            kind = item["componentType"]
            require(kind in (5120, 5121, 5122, 5123), f"{context}: invalid normalized componentType")
            scale = {5120: 127, 5121: 255, 5122: 32767, 5123: 65535}[kind]
            values = [tuple(max(value / scale, -1) for value in row) for row in values]
        for value in values:
            finite(value, context)
        self.cache[index] = values
        return values


def inspect(path):
    document, binary, file_size = read_glb(path)
    nodes = document.get("nodes", [])
    meshes = document.get("meshes", [])
    materials = document.get("materials", [])
    require(meshes, "no meshes")
    require(not document.get("cameras") and not any("camera" in n for n in nodes),
            "cameras must not be exported")
    require("KHR_lights_punctual" not in document.get("extensions", {})
            and not any("KHR_lights_punctual" in n.get("extensions", {}) for n in nodes),
            "lights must not be exported")
    reader = Accessors(document, binary)
    for index in range(len(reader.items)):
        reader.read(index)
    for index, item in enumerate(document.get("images", [])):
        require("uri" not in item, f"image {index}: use embedded bufferView, without a URI")
        reference(reader.views, item.get("bufferView"), f"image {index}.bufferView")
        require(item.get("mimeType") in ("image/png", "image/jpeg", "image/webp", "image/ktx2"),
                f"image {index}: missing or unsupported MIME type")
    mesh_names = [{mesh.get("name", "")} for mesh in meshes]
    for index, node in enumerate(nodes):
        if "mesh" in node:
            reference(meshes, node["mesh"], f"node {index}.mesh")
            mesh_names[node["mesh"]].add(node.get("name", ""))
        for key, size in (("translation", 3), ("rotation", 4), ("scale", 3), ("matrix", 16)):
            if key in node:
                require(len(node[key]) == size, f"node {index}: invalid {key}")
                finite(node[key], f"node {index}.{key}")
        for child in node.get("children", []):
            reference(nodes, child, f"node {index}.children")
    labels = {side: [] for side in LABEL_NAMES}
    low, high = [math.inf] * 3, [-math.inf] * 3
    primitives = triangles = vertices = 0
    for mesh_index, mesh in enumerate(meshes):
        label_sides = [side for side, names in LABEL_NAMES.items() if mesh_names[mesh_index] & names]
        for side in label_sides:
            labels[side].extend(sorted(mesh_names[mesh_index] & LABEL_NAMES[side]))
        require(mesh.get("primitives"), f"mesh {mesh_index}: no primitives")
        for primitive_index, primitive in enumerate(mesh["primitives"]):
            context = f"mesh {mesh_index} primitive {primitive_index}"
            primitives += 1
            attributes = primitive.get("attributes", {})
            require("POSITION" in attributes, f"{context}: missing POSITION")
            positions = reader.read(attributes["POSITION"])
            position_item = reader.items[attributes["POSITION"]]
            require(position_item["type"] == "VEC3" and position_item["componentType"] == 5126,
                    f"{context}: POSITION must be floating-point VEC3")
            actual_low = [min(row[axis] for row in positions) for axis in range(3)]
            actual_high = [max(row[axis] for row in positions) for axis in range(3)]
            for key, actual in (("min", actual_low), ("max", actual_high)):
                bounds = position_item.get(key, [])
                require(len(bounds) == 3, f"{context}: POSITION requires min/max bounds")
                finite(bounds, context + ".POSITION." + key)
                require(all(math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-7)
                            for a, b in zip(bounds, actual)),
                        f"{context}: POSITION {key} does not match binary data")
            low = [min(a, b) for a, b in zip(low, actual_low)]
            high = [max(a, b) for a, b in zip(high, actual_high)]
            vertices += len(positions)
            for semantic, accessor in attributes.items():
                values = reader.read(accessor)
                require(len(values) == len(positions), f"{context}: {semantic} count differs from POSITION")
            if label_sides:
                require("TEXCOORD_0" in attributes, f"{context}: label missing TEXCOORD_0")
                require(reader.items[attributes["TEXCOORD_0"]]["type"] == "VEC2",
                        f"{context}: label TEXCOORD_0 must be VEC2")
            if "material" in primitive:
                reference(materials, primitive["material"], context + ".material")
            count = len(positions)
            if "indices" in primitive:
                indices = reader.read(primitive["indices"])
                item = reader.items[primitive["indices"]]
                require(item["type"] == "SCALAR" and item["componentType"] in (5121, 5123, 5125)
                        and not item.get("normalized"), f"{context}: invalid indices accessor")
                require(all(row[0] < len(positions) for row in indices), f"{context}: vertex index out of range")
                count = len(indices)
            mode = primitive.get("mode", 4)
            require(mode in (4, 5, 6), f"{context}: expected triangle geometry")
            require(count >= 3 and (mode != 4 or count % 3 == 0), f"{context}: incomplete triangles")
            triangles += count // 3 if mode == 4 else count - 2
    for side, names in labels.items():
        if side == 'rear' and any(n.get('extras', {}).get('mediaType') == 'optical-disc' for n in nodes):
            require(not names, 'optical disc must not expose its reading side as rear artwork')
            continue
        require(names, f"missing {side} label; expected one of {sorted(LABEL_NAMES[side])}")
    return {
        "file": Path(path).name,
        "status": "passed",
        "bytes": file_size,
        "meshes": len(meshes),
        "primitives": primitives,
        "vertices": vertices,
        "triangles": triangles,
        "materials": len(materials),
        "images": len(document.get("images", [])),
        "labels": labels,
        "positionBounds": {"space": "mesh-local", "min": low, "max": high},
        "selfContained": True,
        "cameras": 0,
        "lights": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, help="also save the JSON report to this file")
    args = parser.parse_args(argv)
    reports = []
    for path in args.files:
        try:
            reports.append(inspect(path))
        except (ValidationError, OSError, KeyError, TypeError, struct.error) as error:
            reports.append({"file": path.name, "status": "failed", "error": str(error)})
    result = {"status": "passed" if all(r["status"] == "passed" for r in reports) else "failed",
              "assets": reports}
    output = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
