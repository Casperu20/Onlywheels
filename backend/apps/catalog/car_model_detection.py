import json
import math
import re
import struct
from dataclasses import dataclass
from typing import BinaryIO

_GLB_MAGIC = b"glTF"
_JSON_CHUNK = 0x4E4F534A
_WHEEL_PART = re.compile(r"wheel|tire|tyre|rim|felg|roata|brake|caliper|disc", re.IGNORECASE)


@dataclass(frozen=True)
class DetectionResult:
    anchors: dict | None
    error: str | None


@dataclass(frozen=True)
class _Box:
    minimum: tuple[float, float, float]
    maximum: tuple[float, float, float]

    @property
    def center(self) -> tuple[float, float, float]:
        return tuple((low + high) / 2 for low, high in zip(self.minimum, self.maximum, strict=True))


class _DetectionError(ValueError):
    pass


def detect_wheel_anchors(glb_file: BinaryIO) -> DetectionResult:
    try:
        document = _read_glb_json(glb_file)
        candidates, bounds = _collect_mesh_bounds(document)
        return _infer_anchors(candidates, bounds)
    except (_DetectionError, OSError, UnicodeDecodeError, json.JSONDecodeError, struct.error) as exc:
        return DetectionResult(None, str(exc))
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return DetectionResult(None, "The GLB JSON contains an invalid structure.")


def _read_glb_json(glb_file: BinaryIO) -> dict:
    try:
        glb_file.seek(0)
    except (AttributeError, OSError):
        pass
    data = glb_file.read()
    if not isinstance(data, bytes) or len(data) < 20:
        raise _DetectionError("The uploaded file is not a valid GLB 2.0 file.")
    magic, version, declared_length = struct.unpack_from("<4sII", data)
    if magic != _GLB_MAGIC or version != 2 or declared_length != len(data):
        raise _DetectionError("The uploaded file must be a complete GLB 2.0 file.")

    offset = 12
    document = None
    while offset < len(data):
        if offset + 8 > len(data):
            raise _DetectionError("The GLB contains a truncated chunk header.")
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        if chunk_length % 4:
            raise _DetectionError("The GLB contains a chunk whose length is not four-byte aligned.")
        end = offset + chunk_length
        if end > len(data):
            raise _DetectionError("The GLB contains a truncated chunk.")
        if chunk_type == _JSON_CHUNK:
            if document is not None or offset != 20:
                raise _DetectionError("The GLB must contain one JSON chunk in the first position.")
            try:
                document = json.loads(data[offset:end].decode("utf-8").rstrip(" \0"))
            except json.JSONDecodeError as exc:
                raise _DetectionError("The GLB JSON chunk is invalid.") from exc
        offset = end

    if not isinstance(document, dict):
        raise _DetectionError("The GLB JSON chunk must contain an object.")
    asset = document.get("asset")
    if not isinstance(asset, dict) or asset.get("version") != "2.0":
        raise _DetectionError("The GLB is missing a valid glTF 2.0 JSON chunk.")
    return document


def _collect_mesh_bounds(document: dict) -> tuple[list[_Box], _Box]:
    nodes = document.get("nodes", [])
    meshes = document.get("meshes", [])
    accessors = document.get("accessors", [])
    materials = document.get("materials", [])
    scenes = document.get("scenes", [])
    if not isinstance(nodes, list) or not nodes or not isinstance(meshes, list) or not isinstance(accessors, list):
        raise _DetectionError("The GLB has no usable nodes, meshes, or accessors.")

    scene_index = document.get("scene", 0)
    if not isinstance(scene_index, int) or scene_index < 0 or scene_index >= len(scenes):
        raise _DetectionError("The GLB has no valid default scene.")
    roots = scenes[scene_index].get("nodes", [])
    all_boxes: list[_Box] = []
    wheel_boxes: list[_Box] = []
    visited: set[int] = set()

    def visit(node_index: int, parent: list[list[float]], ancestors: tuple[str, ...], stack: frozenset[int]) -> None:
        if not isinstance(node_index, int) or node_index < 0 or node_index >= len(nodes) or node_index in stack:
            raise _DetectionError("The GLB contains an invalid or cyclic node hierarchy.")
        node = nodes[node_index]
        if not isinstance(node, dict):
            raise _DetectionError("The GLB contains an invalid node.")
        local = _node_matrix(node)
        world = _multiply(parent, local)
        node_name = str(node.get("name", ""))
        names = (*ancestors, node_name)
        if node.get("mesh") is not None:
            mesh_index = node["mesh"]
            if not isinstance(mesh_index, int) or mesh_index < 0 or mesh_index >= len(meshes):
                raise _DetectionError("The GLB references an invalid mesh.")
            mesh = meshes[mesh_index]
            mesh_name = str(mesh.get("name", ""))
            primitives = mesh.get("primitives", [])
            if not isinstance(primitives, list) or not primitives:
                raise _DetectionError("A GLB mesh has no primitives.")
            for primitive in primitives:
                position_index = primitive.get("attributes", {}).get("POSITION")
                if not isinstance(position_index, int) or position_index < 0 or position_index >= len(accessors):
                    raise _DetectionError("A GLB mesh is missing a POSITION accessor.")
                accessor = accessors[position_index]
                local_box = _accessor_box(accessor)
                world_box = _transform_box(local_box, world)
                all_boxes.append(world_box)

                material_index = primitive.get("material")
                material_name = ""
                if isinstance(material_index, int) and 0 <= material_index < len(materials):
                    material_name = str(materials[material_index].get("name", ""))
                if any(_WHEEL_PART.search(name) for name in (*names, mesh_name, material_name) if name):
                    wheel_boxes.append(world_box)
        visited.add(node_index)
        children = node.get("children", [])
        if not isinstance(children, list):
            raise _DetectionError("The GLB contains an invalid node children list.")
        for child in children:
            visit(child, world, names, stack | {node_index})

    if not isinstance(roots, list) or not roots:
        raise _DetectionError("The GLB default scene has no root nodes.")
    identity = _identity()
    for root in roots:
        visit(root, identity, (), frozenset())
    if not all_boxes:
        raise _DetectionError("The GLB has no bounded POSITION geometry.")
    overall = _merge_boxes(all_boxes)
    if not wheel_boxes:
        raise _DetectionError("No wheel-named or brake-named parts were found; enter wheel positions manually.")
    return wheel_boxes, overall


def _accessor_box(accessor: dict) -> _Box:
    if not isinstance(accessor, dict):
        raise _DetectionError("A POSITION accessor is invalid.")
    minimum = accessor.get("min")
    maximum = accessor.get("max")
    if not (
        isinstance(minimum, list)
        and isinstance(maximum, list)
        and len(minimum) == len(maximum) == 3
        and all(_finite_number(value) for value in (*minimum, *maximum))
    ):
        raise _DetectionError("POSITION bounds (min/max) are missing; enter wheel positions manually.")
    low = tuple(float(value) for value in minimum)
    high = tuple(float(value) for value in maximum)
    if any(a > b for a, b in zip(low, high, strict=True)):
        raise _DetectionError("POSITION bounds (min/max) are invalid.")
    return _Box(low, high)


def _node_matrix(node: dict) -> list[list[float]]:
    if "matrix" in node:
        values = node["matrix"]
        if not isinstance(values, list) or len(values) != 16 or not all(_finite_number(v) for v in values):
            raise _DetectionError("A node has an invalid transform matrix.")
        return [[float(values[column * 4 + row]) for column in range(4)] for row in range(4)]

    translation = node.get("translation", [0, 0, 0])
    scale = node.get("scale", [1, 1, 1])
    rotation = node.get("rotation", [0, 0, 0, 1])
    if not (
        isinstance(translation, list)
        and len(translation) == 3
        and isinstance(scale, list)
        and len(scale) == 3
        and isinstance(rotation, list)
        and len(rotation) == 4
        and all(_finite_number(value) for value in (*translation, *scale, *rotation))
    ):
        raise _DetectionError("A node has an invalid TRS transform.")

    x, y, z, w = (float(value) for value in rotation)
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length <= 0:
        raise _DetectionError("A node has a zero-length rotation.")
    x, y, z, w = (value / length for value in (x, y, z, w))
    sx, sy, sz = (float(value) for value in scale)
    return [
        [(1 - 2 * (y * y + z * z)) * sx, (2 * (x * y - z * w)) * sy, (2 * (x * z + y * w)) * sz, float(translation[0])],
        [(2 * (x * y + z * w)) * sx, (1 - 2 * (x * x + z * z)) * sy, (2 * (y * z - x * w)) * sz, float(translation[1])],
        [(2 * (x * z - y * w)) * sx, (2 * (y * z + x * w)) * sy, (1 - 2 * (x * x + y * y)) * sz, float(translation[2])],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _infer_anchors(candidates: list[_Box], overall: _Box) -> DetectionResult:
    spans = [high - low for low, high in zip(overall.minimum, overall.maximum, strict=True)]
    axis = "x" if spans[0] >= spans[2] else "z"
    length_index = 0 if axis == "x" else 2
    side_index = 2 if axis == "x" else 0
    threshold = max(spans[length_index] * 0.12, 0.08)
    centers = [box.center for box in candidates]
    clusters: list[list[tuple[float, float, float]]] = []
    for center in centers:
        nearest = min(
            ((math.dist(center, _mean(cluster)), cluster) for cluster in clusters),
            key=lambda item: item[0],
            default=(math.inf, None),
        )
        if nearest[0] <= threshold:
            nearest[1].append(center)
        else:
            clusters.append([center])
    points = [_mean(cluster) for cluster in clusters]
    if len(points) < 4:
        return DetectionResult(None, "Fewer than four wheel positions were found; enter wheel positions manually.")

    lowest = sorted(points, key=lambda point: point[1])[:4]
    length_sorted = sorted(lowest, key=lambda point: point[length_index])
    front_pair, rear_pair = length_sorted[:2], length_sorted[2:]
    length_span = spans[length_index]
    side_span = spans[side_index]
    front_mean = sum(point[length_index] for point in front_pair) / 2
    rear_mean = sum(point[length_index] for point in rear_pair) / 2
    center_side = (overall.minimum[side_index] + overall.maximum[side_index]) / 2
    symmetry_tolerance = max(side_span * 0.1, 0.05)
    plausible = (
        abs(front_pair[0][length_index] - front_pair[1][length_index]) <= length_span * 0.12
        and abs(rear_pair[0][length_index] - rear_pair[1][length_index]) <= length_span * 0.12
        and abs(rear_mean - front_mean) >= length_span * 0.2
        and (front_pair[0][side_index] - center_side) * (front_pair[1][side_index] - center_side) < 0
        and (rear_pair[0][side_index] - center_side) * (rear_pair[1][side_index] - center_side) < 0
        and abs(sum(point[side_index] for point in front_pair) / 2 - center_side) <= symmetry_tolerance
        and abs(sum(point[side_index] for point in rear_pair) / 2 - center_side) <= symmetry_tolerance
        and abs(front_pair[0][1] - front_pair[1][1]) <= max(spans[1] * 0.2, 0.05)
        and abs(rear_pair[0][1] - rear_pair[1][1]) <= max(spans[1] * 0.2, 0.05)
    )
    if not plausible or side_span <= 0:
        return DetectionResult(
            None,
            "Wheel parts do not form a plausible four-wheel layout; enter wheel positions manually.",
        )

    wheels = [
        {axis_name: round(point[index], 6) for axis_name, index in (("x", 0), ("y", 1), ("z", 2))}
        for point in sorted(lowest, key=lambda point: (point[length_index], point[side_index]))
    ]
    return DetectionResult({"axis": axis, "wheels": wheels}, None)


def _transform_box(box: _Box, matrix: list[list[float]]) -> _Box:
    points = []
    for x in (box.minimum[0], box.maximum[0]):
        for y in (box.minimum[1], box.maximum[1]):
            for z in (box.minimum[2], box.maximum[2]):
                points.append(
                    tuple(
                        sum(matrix[row][column] * value for column, value in enumerate((x, y, z, 1.0)))
                        for row in range(3)
                    )
                )
    return _Box(
        tuple(min(point[index] for point in points) for index in range(3)),
        tuple(max(point[index] for point in points) for index in range(3)),
    )


def _merge_boxes(boxes: list[_Box]) -> _Box:
    return _Box(
        tuple(min(box.minimum[index] for box in boxes) for index in range(3)),
        tuple(max(box.maximum[index] for box in boxes) for index in range(3)),
    )


def _mean(points: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    return tuple(sum(point[index] for point in points) / len(points) for index in range(3))


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _multiply(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [[sum(left[row][k] * right[k][column] for k in range(4)) for column in range(4)] for row in range(4)]


def _identity() -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
