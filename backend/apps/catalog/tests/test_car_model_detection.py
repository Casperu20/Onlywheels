import json
import struct
from io import BytesIO
from types import SimpleNamespace

import pytest
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.catalog.car_model_detection import detect_wheel_anchors
from apps.catalog.models import CarModel3D

pytestmark = pytest.mark.django_db


def glb_bytes(
    *,
    nested=False,
    matrix_node=False,
    brakes=False,
    spare=False,
    missing_bounds=False,
    unnamed_wheels=False,
    translation=(0, 0, 0),
):
    tx, ty, tz = translation
    accessors = [
        {"min": [-2, 0, -0.9], "max": [2, 1.5, 0.9]},
        {"min": [-0.25, -0.25, -0.1], "max": [0.25, 0.25, 0.1]},
    ]
    if missing_bounds:
        accessors[1] = {}

    nodes = [{"name": "body", "mesh": 0, "translation": [tx, ty, tz]}]
    meshes = [{"name": "body shell", "primitives": [{"attributes": {"POSITION": 0}}]}]
    roots = [0]
    points = [
        (-1.2, 0.3, -0.7),
        (1.2, 0.3, -0.7),
        (-1.2, 0.3, 0.7),
        (1.2, 0.3, 0.7),
    ]
    for index, (x, y, z) in enumerate(points):
        mesh_index = len(meshes)
        node_index = len(nodes)
        mesh_name = "alloy mesh" if unnamed_wheels else "alloy wheel mesh"
        meshes.append({"name": mesh_name, "primitives": [{"attributes": {"POSITION": 1}}]})
        if nested and index == 0:
            nodes.append({"name": "front axle", "translation": [1 + tx, ty, tz], "children": [node_index + 1]})
            node_name = "object nested" if unnamed_wheels else "wheel nested"
            nodes.append({"name": node_name, "translation": [x - 1, y, z], "mesh": mesh_index})
            roots.append(node_index)
        elif matrix_node and index == 1:
            matrix = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x + tx, y + ty, z + tz, 1]
            node_name = "object matrix" if unnamed_wheels else "wheel matrix"
            nodes.append({"name": node_name, "matrix": matrix, "mesh": mesh_index})
        else:
            node_name = f"object {index}" if unnamed_wheels else f"wheel {index}"
            nodes.append({"name": node_name, "translation": [x + tx, y + ty, z + tz], "mesh": mesh_index})
        if not (nested and index == 0):
            roots.append(node_index)

    if brakes:
        mesh_index = len(meshes)
        node_index = len(nodes)
        meshes.append(
            {
                "name": "brake disc",
                "primitives": [{"attributes": {"POSITION": 1}}],
            }
        )
        nodes.append({"name": "disc", "translation": list(points[0]), "mesh": mesh_index})
        roots.append(node_index)
    if spare:
        mesh_index = len(meshes)
        node_index = len(nodes)
        meshes.append({"name": "spare tire", "primitives": [{"attributes": {"POSITION": 1}}]})
        nodes.append({"name": "boot spare", "translation": [1.4, 1.2, 0], "mesh": mesh_index})
        roots.append(node_index)

    document = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": roots}],
        "nodes": nodes,
        "meshes": meshes,
        "accessors": accessors,
    }
    payload = json.dumps(document, separators=(",", ":")).encode()
    payload += b" " * (-len(payload) % 4)
    chunk = struct.pack("<II", len(payload), 0x4E4F534A) + payload
    return struct.pack("<4sII", b"glTF", 2, 12 + len(chunk)) + chunk


def malformed_glb(chunk_length, chunk_type, payload):
    chunk = struct.pack("<II", chunk_length, chunk_type) + payload
    return struct.pack("<4sII", b"glTF", 2, 20 + len(payload)) + chunk


def glb_with_truncated_trailing_chunk():
    valid = glb_bytes()
    trailing = struct.pack("<II", 16, 0x004E4942) + b"\0" * 4
    return valid[:8] + struct.pack("<I", len(valid) + len(trailing)) + valid[12:] + trailing


def test_detects_four_wheel_centres_and_vehicle_length_axis():
    result = detect_wheel_anchors(BytesIO(glb_bytes()))

    assert result.error is None
    assert result.anchors["axis"] == "x"
    assert len(result.anchors["wheels"]) == 4
    assert {
        (round(point["x"], 2), round(point["y"], 2), round(point["z"], 2)) for point in result.anchors["wheels"]
    } == {
        (-1.2, 0.3, -0.7),
        (1.2, 0.3, -0.7),
        (-1.2, 0.3, 0.7),
        (1.2, 0.3, 0.7),
    }


def test_detects_wheels_when_the_glb_is_offset_from_the_origin():
    result = detect_wheel_anchors(BytesIO(glb_bytes(translation=(0, 0, 2.5))))

    assert result.error is None
    assert result.anchors["axis"] == "x"
    assert {round(point["z"], 2) for point in result.anchors["wheels"]} == {1.8, 3.2}


def test_applies_nested_and_matrix_node_transforms():
    result = detect_wheel_anchors(BytesIO(glb_bytes(nested=True, matrix_node=True)))

    assert result.error is None
    positions = {(round(p["x"], 2), round(p["y"], 2), round(p["z"], 2)) for p in result.anchors["wheels"]}
    assert (-1.2, 0.3, -0.7) in positions
    assert (1.2, 0.3, -0.7) in positions


def test_merges_brake_meshes_and_ignores_boot_spare():
    result = detect_wheel_anchors(BytesIO(glb_bytes(brakes=True, spare=True)))

    assert result.error is None
    assert len(result.anchors["wheels"]) == 4
    assert all(point["y"] == pytest.approx(0.3) for point in result.anchors["wheels"])


def test_missing_accessor_bounds_returns_admin_actionable_failure():
    result = detect_wheel_anchors(BytesIO(glb_bytes(missing_bounds=True)))

    assert result.anchors is None
    assert "bounds" in result.error.lower()


def test_car_with_no_recognized_wheel_parts_requires_manual_positions():
    result = detect_wheel_anchors(BytesIO(glb_bytes(unnamed_wheels=True)))

    assert result.anchors is None
    assert "no wheel-named" in result.error.lower()


def test_admin_save_detects_car_anchors_when_glb_is_uploaded(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    car = CarModel3D(
        name="Generic sedan",
        slug="generic-sedan",
        body_type="sedan",
        glb_file=SimpleUploadedFile("car.glb", glb_bytes()),
        length_m="4.200",
        attribution="Example, CC BY 4.0",
    )
    model_admin = admin.site._registry[CarModel3D]

    model_admin.save_model(
        SimpleNamespace(),
        car,
        SimpleNamespace(changed_data=["glb_file"]),
        False,
    )

    car.refresh_from_db()
    assert car.detection_status == CarModel3D.DetectionStatus.OK
    assert car.detected_anchors["axis"] == "x"
    assert len(car.detected_anchors["wheels"]) == 4


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"not a glb file", "GLB"),
        (malformed_glb(20, 0x4E4F534A, b"{}  "), "chunk"),
        (malformed_glb(4, 0x4E4F534A, b"{   "), "JSON"),
        (malformed_glb(4, 0x4E4F534A, b"[]  "), "JSON"),
        (malformed_glb(16, 0x4E4F534A, b'{"asset":[]}    '), "JSON"),
    ],
)
def test_malformed_glb_returns_detection_failure(data, message):
    result = detect_wheel_anchors(BytesIO(data))

    assert result.anchors is None
    assert message.lower() in result.error.lower()


def test_truncated_binary_chunk_after_json_returns_detection_failure():
    result = detect_wheel_anchors(BytesIO(glb_with_truncated_trailing_chunk()))

    assert result.anchors is None
    assert "chunk" in result.error.lower()
