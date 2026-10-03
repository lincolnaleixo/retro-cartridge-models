#!/usr/bin/env python3
"""Exercise export failures that otherwise reach the runtime model loader."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest

from inspect_glb import ValidationError, inspect


def fixture():
    # Deliberately interleave XYZ + UV: reading this as tightly packed geometry
    # produces plausible but wrong bounds and must never pass unnoticed.
    binary = b"".join(struct.pack("<5f", *row) for row in (
        (-2, 0, 0, 0, 0), (2, 0, 0, 1, 0), (0, 3, 0, 0.5, 1)))
    binary += struct.pack("<3H", 0, 1, 2)
    document = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 60, "byteStride": 20},
            {"buffer": 0, "byteOffset": 60, "byteLength": 6},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3",
             "min": [-2, 0, 0], "max": [2, 3, 0]},
            {"bufferView": 0, "byteOffset": 12, "componentType": 5126,
             "count": 3, "type": "VEC2"},
            {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"},
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "TEXCOORD_0": 1},
                                    "indices": 2, "material": 0}]}],
        "materials": [{"name": "BlankLabel"}],
        "nodes": [{"name": "FrontLabel", "mesh": 0}, {"name": "RearLabel", "mesh": 0}],
        "scenes": [{"nodes": [0, 1]}], "scene": 0,
    }
    return document, binary


def encode(document, binary):
    text = json.dumps(document, separators=(",", ":")).encode("utf-8")
    text += b" " * (-len(text) % 4)
    binary += b"\0" * (-len(binary) % 4)
    return (struct.pack("<4sII", b"glTF", 2, 28 + len(text) + len(binary))
            + struct.pack("<I4s", len(text), b"JSON") + text
            + struct.pack("<I4s", len(binary), b"BIN\0") + binary)


class ExportContractTests(unittest.TestCase):
    def inspect_bytes(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.glb"
            path.write_bytes(data)
            return inspect(path)

    def check_invalid(self, document, binary, message):
        with self.assertRaisesRegex(ValidationError, message):
            self.inspect_bytes(encode(document, binary))

    def test_interleaved_geometry_and_labels(self):
        report = self.inspect_bytes(encode(*fixture()))
        self.assertEqual(report["positionBounds"]["min"], [-2, 0, 0])
        self.assertEqual(report["positionBounds"]["max"], [2, 3, 0])
        self.assertEqual(report["triangles"], 1)
        self.assertEqual(report["labels"], {"front": ["FrontLabel"], "rear": ["RearLabel"]})

    def test_legacy_snes_label_names(self):
        document, binary = fixture()
        document["nodes"][0]["name"] = "Front printed paper label"
        document["nodes"][1]["name"] = "Rear printed information"
        self.assertEqual(self.inspect_bytes(encode(document, binary))["status"], "passed")

    def test_truncated_or_corrupted_container(self):
        data = encode(*fixture())
        for broken in (data[:8], data[:-1], b"NOPE" + data[4:],
                       data[:12] + struct.pack("<I", 0xFFFFFFFC) + data[16:]):
            with self.subTest(length=len(broken)):
                with self.assertRaises(ValidationError):
                    self.inspect_bytes(broken)

    def test_external_buffer_and_images(self):
        for kind in ("buffer", "image"):
            for uri in ("https://example.org/resource.bin", "../resource.bin"):
                document, binary = fixture()
                if kind == "buffer":
                    document["buffers"][0]["uri"] = uri
                else:
                    document["images"] = [{"uri": uri}]
                with self.subTest(kind=kind, uri=uri):
                    self.check_invalid(document, binary, "embedded")

    def test_missing_label_or_label_uv(self):
        document, binary = fixture()
        document["nodes"][1]["name"] = "AnonymousPlane"
        self.check_invalid(document, binary, "missing rear label")
        document, binary = fixture()
        del document["meshes"][0]["primitives"][0]["attributes"]["TEXCOORD_0"]
        self.check_invalid(document, binary, "label missing TEXCOORD_0")

    def test_non_finite_geometry_and_inaccurate_bounds(self):
        for value in (float("nan"), float("inf")):
            document, binary = fixture()
            self.check_invalid(document, struct.pack("<f", value) + binary[4:], "non-finite")
        document, binary = fixture()
        document["accessors"][0]["max"] = [2, 30, 0]
        self.check_invalid(document, binary, "does not match binary data")

    def test_out_of_range_geometry_data(self):
        document, binary = fixture()
        self.check_invalid(document, binary[:-2] + struct.pack("<H", 99), "vertex index out of range")
        document, binary = fixture()
        document["accessors"][0]["count"] = 4
        self.check_invalid(document, binary, "exceeds its bufferView")

    def test_no_exported_camera_or_light(self):
        document, binary = fixture()
        document["nodes"][0]["camera"] = 0
        self.check_invalid(document, binary, "cameras must not")
        document, binary = fixture()
        document["extensions"] = {"KHR_lights_punctual": {"lights": [{"type": "point"}]}}
        self.check_invalid(document, binary, "lights must not")

    def test_sparse_position_update_is_used_for_bounds(self):
        document, binary = fixture()
        # A sparse replacement moves the last vertex from y=3 to y=5.
        binary += b"\0\0" + struct.pack("<I3f", 2, 0, 5, 0)
        document["buffers"][0]["byteLength"] = len(binary)
        document["bufferViews"] += [
            {"buffer": 0, "byteOffset": 68, "byteLength": 4},
            {"buffer": 0, "byteOffset": 72, "byteLength": 12},
        ]
        document["accessors"][0]["sparse"] = {
            "count": 1, "indices": {"bufferView": 2, "componentType": 5125},
            "values": {"bufferView": 3},
        }
        stale_bounds = copy.deepcopy(document)
        document["accessors"][0]["max"] = [2, 5, 0]
        self.assertEqual(self.inspect_bytes(encode(document, binary))["positionBounds"]["max"], [2, 5, 0])
        self.check_invalid(stale_bounds, binary, "does not match binary data")


if __name__ == "__main__":
    unittest.main()
