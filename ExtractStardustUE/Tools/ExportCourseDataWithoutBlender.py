import argparse
import json
import struct
import sys
import types
from pathlib import Path


class RecordingKDTree:
    def __init__(self, capacity):
        self.points = []

    def insert(self, point, index):
        self.points.append((point, index))

    def balance(self):
        pass


def install_blender_import_stubs():
    blender = types.ModuleType("bpy")
    mathutils = types.ModuleType("mathutils")
    mathutils.kdtree = types.SimpleNamespace(KDTree=RecordingKDTree)
    sys.modules.setdefault("bpy", blender)
    sys.modules.setdefault("mathutils", mathutils)


def write_stations(output, path):
    for index, row in enumerate(path.rows):
        flags = (1 if row["gap"] else 0) | (2 if row["cave"] else 0)
        output.write(struct.pack("<f3f3f3f3f", row["dist"], *path.P[index], *path.T[index], *path.R[index], *path.U[index]))
        output.write(struct.pack("<fffiiiff", row["width"], row["bank"], row["slope"], flags, row["seg"], row["surf"], path.ride[index, 0], path.ride[index, 1]))
        output.write(path.Wr[index].astype("<f4").tobytes())


def write_names(output, names):
    output.write(struct.pack("<i", len(names)))
    for name in names:
        encoded = name.encode("utf-8")
        output.write(struct.pack("<i", len(encoded)))
        output.write(encoded)


def write_course_data(path, output_dir, spec):
    course_path = output_dir / f"{spec['name']}_course.bytes"
    graph_path = output_dir / f"{spec['name']}_graph.bytes"
    with course_path.open("wb") as output:
        output.write(b"RDDC")
        output.write(struct.pack("<iiif", 1, path.S, path.N, path.step))
        write_stations(output, path)
        write_names(output, path.names)
    with graph_path.open("wb") as output:
        output.write(b"RDDG")
        output.write(struct.pack("<ii", 2, 1))
        encoded_id = path.id.encode("utf-8")
        output.write(struct.pack("<i", len(encoded_id)))
        output.write(encoded_id)
        output.write(struct.pack("<ifff", -1, 0.0, float(path.dist[-1]), float(path.dist[-1])))
        output.write(struct.pack("<iif", path.S, path.N, path.step))
        write_stations(output, path)
        write_names(output, path.names)
    return course_path, graph_path


def main():
    repository = Path(__file__).resolve().parents[2]
    blender_tools = repository / "ExtractStardustRDD" / "Art" / "Blender"
    parser = argparse.ArgumentParser(description="Gera o RDDC/RDDG da rota principal sem iniciar o Blender.")
    parser.add_argument("--spec", type=Path, default=repository / "ExtractStardustRDD" / "Art" / "Courses" / "red_dust_divide.json")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parents[1] / "Saved" / "GeneratedCourse" / "red_dust_divide")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    spec_path = args.spec.resolve()
    output_dir = args.out_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    install_blender_import_stubs()
    sys.path.insert(0, str(blender_tools))
    sys.argv = [str(blender_tools / "rdd_build_route.py"), "--", str(spec_path), str(output_dir)]

    import rdd_build_route as builder

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    builder.OPEN_FIELDS.clear()
    builder.plateau = lambda x, z, col, course_dist, seed: builder.np.full(builder.np.shape(x), 318.0)
    seed = int(spec.get("seed", 1))
    rows, step = builder.integrate(spec)
    geology = builder.geo.Column(seed)
    path = builder.build_path("main", rows, step, geology, seed, [segment["id"] for segment in spec["segments"]], seed + 100, seed)
    path.parent = None
    path.from_d = 0.0
    path.to_d = float(path.dist[-1])
    path.length = float(path.dist[-1])
    course_path, graph_path = write_course_data(path, output_dir, spec)

    if args.install:
        tracks_dir = Path(__file__).resolve().parents[1] / "Content" / "Tracks"
        tracks_dir.mkdir(parents=True, exist_ok=True)
        (tracks_dir / "sandbox_course.bytes").write_bytes(course_path.read_bytes())
        (tracks_dir / "sandbox_graph.bytes").write_bytes(graph_path.read_bytes())

    result = {
        "course": str(course_path),
        "graph": str(graph_path),
        "stations": path.S,
        "ring_points": path.N,
        "length_km": round(float(path.dist[-1]) / 1000.0, 3),
        "paths": [path.id],
        "branches_included": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
