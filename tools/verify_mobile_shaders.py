"""Compile/link BongoCatMC shaders against engine headers.

Adapted from the local Balatro project; desktop-driver checks are not phone QA.
Includes the actual NETEASE_SKINNING material path.
"""
import argparse
import json
import re
from pathlib import Path
import moderngl

ROOT = Path(__file__).resolve().parents[1]
RP = ROOT / "addon/resource_pack"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headers", action="append", type=Path, required=True,
                        help="Engine GLSL include directory; repeat in precedence order")
    parser.add_argument("--versions", nargs="+", default=["120", "330 core", "300 es", "310 es"])
    parser.add_argument("--output", type=Path,
                        default=ROOT / "diagnostics/mobile-shaders/compile.json")
    args = parser.parse_args()
    roots = [RP / "shaders/glsl"] + args.headers
    used = set()

    def resolve(name):
        for root in roots:
            path = root / name
            if path.is_file():
                return path
        raise FileNotFoundError("Missing engine shader: " + name)

    def expand(path, stack=()):
        if path in stack:
            raise ValueError("Recursive include: " + str(path))
        used.add(str(path.resolve()))
        return re.sub(r'#include\s+"([^\"]+)"',
                      lambda m: expand(resolve(m[1]), stack + (path,)),
                      path.read_text(encoding="utf-8-sig"))

    materials = json.loads((RP / "materials/entity.material").read_text(encoding="utf8"))["materials"]
    ctx = moderngl.create_standalone_context(require=330)
    rows = []
    for version in args.versions:
        for name, data in materials.items():
            if not isinstance(data, dict):
                continue
            # Resolve explicit project shader files and retain engine includes.
            vertex = resolve(Path(data.get("vertexShader", "entity.vertex")).name)
            fragment = resolve(Path(data["fragmentShader"]).name)
            for msaa in (False, True):
                for large in (False, True):
                    defines = ["USE_SKINNING", "NETEASE_SKINNING", "USE_UV_ANIM"] + data.get("defines", [])
                    if large:
                        defines.append("LARGE_VERTEX_SHADER_UNIFORMS")
                    if msaa:
                        defines.append("MSAA_FRAMEBUFFER_ENABLED")
                    prefix = "#version " + version + "\n"
                    # Match the engine's stage defaults without patching shader bodies.
                    if version.endswith("es") or version == "100":
                        prefix += "precision highp float;\nprecision highp int;\n"
                    elif int(version.split()[0]) < 130:
                        prefix += "#define highp\n#define mediump\n#define lowp\n"
                    prefix += "#define POS4 vec4\n#define MAT4 mat4\n"
                    prefix += "".join("#define " + d + "\n" for d in defines)
                    row = dict(material=name, version=version, msaa=msaa, large_uniforms=large)
                    try:
                        program = ctx.program(vertex_shader=prefix + expand(vertex),
                                              fragment_shader=prefix + expand(fragment))
                    except moderngl.Error as error:
                        row.update(status="failed", error=str(error))
                    else:
                        program.release()
                        row["status"] = "passed"
                    rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(renderer=ctx.info["GL_RENDERER"], headers=[str(p) for p in args.headers],
                  files=sorted(used), results=rows,
                  limitation="Desktop compiler/linker only; not Android/iOS runtime validation")
    args.output.write_text(json.dumps(report, indent=2), encoding="utf8")
    ctx.release()
    failed = [r for r in rows if r["status"] == "failed"]
    print("Passed %d/%d shader variants" % (len(rows)-len(failed), len(rows)))
    for row in failed[:4]:
        print(row["material"], row["version"], row["error"])
    return bool(failed)


if __name__ == "__main__":
    raise SystemExit(main())
