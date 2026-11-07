"""Offline Live2D inspection and explicit BongoCatMC conversion adapters (Python 3)."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILE = Path(__file__).with_name('live2d_profiles.json')
IGNORE = shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', '*.zip')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root):
    root = Path(root)
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError('Symbolic links are not supported: ' + str(p))
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc', '.pyo'):
            result[p.relative_to(root).as_posix()] = digest(p)
    return result


def fingerprint(root):
    return hashlib.sha256(json.dumps(inventory(root), sort_keys=True).encode()).hexdigest()


def safe_path(root, name):
    name = str(name).replace('\\', '/')
    rel = PurePosixPath(name)
    if rel.is_absolute() or '..' in rel.parts or ':' in name:
        raise ValueError('Unsafe relative path: ' + name)
    root = Path(root).resolve()
    target = root.joinpath(*rel.parts).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Path escapes model folder: ' + name)
    return target


@contextmanager
def source_model(source, selector=None):
    source = Path(source).resolve()
    with tempfile.TemporaryDirectory(prefix='live2d-inspect-') as temp:
        if source.suffix.lower() == '.zip':
            root = Path(temp)
            with zipfile.ZipFile(source) as archive:
                entries = archive.infolist()
                if sum(i.file_size for i in entries) > 2 * 1024**3:
                    raise ValueError('Archive exceeds 2 GiB inspection limit; extract and inspect a folder.')
                targets = set()
                for item in entries:
                    target = safe_path(root, item.filename)
                    key = str(target).casefold()
                    if key in targets or stat.S_ISLNK(item.external_attr >> 16):
                        raise ValueError('Duplicate path or symbolic link in archive: ' + item.filename)
                    targets.add(key)
                for item in entries:
                    target = safe_path(root, item.filename)
                    if item.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(item) as src, target.open('wb') as dst:
                            shutil.copyfileobj(src, dst)
        else:
            root = source if source.is_dir() else source.parent
        if selector:
            candidates = [safe_path(root, selector)]
        elif source.name.endswith('.model3.json'):
            candidates = [source]
        else:
            candidates = sorted(root.rglob('*.model3.json'))
        if len(candidates) != 1:
            raise ValueError('Select one model using --model. Candidates: ' + ', '.join(str(p.relative_to(root)) for p in candidates))
        model = candidates[0]
        if not model.name.endswith('.model3.json') or not model.is_file():
            raise ValueError('Missing .model3.json: ' + str(model))
        yield model


def inspect_model(model):
    from PIL import Image
    cfg = read(model)
    refs = cfg.get('FileReferences', {})
    dependencies = []

    def add(kind, name):
        path = safe_path(model.parent, name)
        entry = {'kind': kind, 'file': name, 'exists': path.is_file()}
        if path.is_file():
            entry.update(bytes=path.stat().st_size, sha256=digest(path))
            if kind == 'texture':
                with Image.open(path) as im:
                    entry.update(size=list(im.size), mode=im.mode)
        dependencies.append(entry)

    for key in ('Moc', 'Physics', 'Pose', 'DisplayInfo', 'UserData'):
        if refs.get(key):
            add(key.lower(), refs[key])
    if not refs.get('Moc'):
        raise ValueError('Model has no FileReferences.Moc')
    for name in refs.get('Textures', []):
        add('texture', name)
    expressions = []
    for entry in refs.get('Expressions', []):
        add('expression', entry['File'])
        path = safe_path(model.parent, entry['File'])
        expressions.append(dict(entry, parameters=read(path).get('Parameters', []) if path.exists() else []))
    motions = refs.get('Motions', {})
    for entries in motions.values():
        for entry in entries:
            add('motion', entry['File'])
            if entry.get('Sound'):
                add('sound', entry['Sound'])
    physics = {}
    if refs.get('Physics'):
        path = safe_path(model.parent, refs['Physics'])
        if path.exists():
            settings = read(path).get('PhysicsSettings', [])
            physics = {'rigs': len(settings), 'particles': sum(len(s.get('Vertices', [])) for s in settings)}
    signature = fingerprint(model.parent)
    matches = [name for name, p in read(PROFILE_FILE).items() if p['source_sha256'] == signature]
    return {'schema': 1, 'model': model.name, 'source_sha256': signature,
            'supported_adapters': matches, 'dependencies': dependencies,
            'missing': [d['file'] for d in dependencies if not d['exists']],
            'expressions': expressions, 'motion_groups': motions, 'physics': physics,
            'keyboard_images': len(list((model.parent / 'resources/left-keys').glob('*.png'))),
            'scope': 'Dependency inspection; no universal Cubism-to-MC conversion is implied.'}


def run_stage(root, name, command):
    log = root / 'pipeline-logs' / (name + '.log')
    log.parent.mkdir(exist_ok=True)
    print('Running ' + name, file=sys.stderr, flush=True)
    with log.open('w', encoding='utf-8') as stream:
        result = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError('Stage failed: %s; see %s' % (name, log))
    return {'name': name, 'command': command, 'log': log.relative_to(root).as_posix()}


def convert(args):
    profiles = read(PROFILE_FILE)
    profile = profiles[args.profile]
    source = args.source or str(ROOT / profile['source'])
    output = Path(args.output).resolve()
    # All legacy builders run in a copied workspace; never repoint them at the live addon.
    if output.exists() or ROOT.is_relative_to(output):
        raise ValueError('Output must be a NEW directory, outside existing runtime/source folders.')
    for protected in ('addon', 'assets', 'tools', 'skills'):
        if output.is_relative_to(ROOT / protected):
            raise ValueError('Output overlaps protected project content.')
    if output.is_relative_to(Path(source).resolve()):
        raise ValueError('Output overlaps source.')
    with source_model(source, args.model) as model:
        report = inspect_model(model)
        if report['missing'] or args.profile not in report['supported_adapters']:
            raise ValueError('Source differs from this adapter\'s pinned model package. Inspect and implement/validate an adapter first. Output was not created.')
        if not shutil.which('node'):
            raise ValueError('Node.js is required.')
        import numpy, PIL, soundfile  # noqa: F401; fail before creating output
        output.mkdir(parents=True)
        for folder in ('tools', 'assets/source'):
            shutil.copytree(ROOT / folder, output / folder, ignore=IGNORE)
        # Builders propagate legal notices; include their source documents in isolation.
        for folder in ('licenses', 'docs'):
            shutil.copytree(ROOT / folder, output / folder, ignore=IGNORE)
        for name in ('LICENSE', 'COPYRIGHT.md', 'THIRD_PARTY_NOTICES.md', 'requirements-build.txt'):
            shutil.copy2(ROOT / name, output / name)
        for pack in ('behavior_pack', 'resource_pack'):
            shutil.copytree(ROOT / 'addon' / pack, output / 'addon' / pack, ignore=IGNORE)
        # A matching external package is accepted; pinning proves copied canonical content is identical.
        write(output / 'source-inspection.json', report)
    record = {'schema': 1, 'status': 'building', 'profile': args.profile,
              'source': str(Path(source).resolve()), 'source_sha256': report['source_sha256'],
              'kind': 'bongocatmc-runtime-snapshot',
              'scope': 'Rebuilds selected known model; retains the other model and existing HUD/runtime. Not a standalone model subpack.',
              'tool_sha256': inventory(output / 'tools'), 'stages': []}
    write(output / 'conversion.json', record)
    try:
        record['stages'].append(run_stage(output, 'sample', ['node', profile['sampler']]))
        command = [sys.executable, '-c', 'import sys; sys.path.insert(0,"tools"); from build_cat import build_assets; build_assets()'] if args.profile == 'default' else [sys.executable, 'tools/build_deepseek.py']
        record['stages'].append(run_stage(output, 'build', command))
        for test in profile['tests']:
            record['stages'].append(run_stage(output, Path(test).stem, [sys.executable, test]))
        record.update(status='complete', runtime_sha256=inventory(output / 'addon'))
        write(output / 'conversion.json', record)
        result = validate(output)
        write(output / 'validation.json', result)
    except Exception:
        record['status'] = 'failed'
        write(output / 'conversion.json', record)
        raise
    return {'output': str(output), 'profile': args.profile, 'validation': result}


def validate(output):
    import math
    from PIL import Image
    output = Path(output).resolve()
    record = read(output / 'conversion.json')
    if record.get('status') != 'complete':
        raise ValueError('Conversion did not complete.')
    if inventory(output / 'addon') != record['runtime_sha256']:
        raise ValueError('Runtime changed after conversion; rebuild before exporting.')
    rp = output / 'addon/resource_pack'
    registry = read(rp / 'models/netease_models.json')
    checked = []
    for name, item in registry.items():
        mesh_path = safe_path(rp / 'models', item['mesh'])
        safe_path(rp / 'models', item['skeleton']).read_bytes()
        for mesh in read(mesh_path)['mesh']:
            count = len(mesh['vertices'])
            if not all(isinstance(i, int) and 0 <= i < count for triangle in mesh['indices'] for i in triangle):
                raise ValueError('Invalid triangle indices: ' + name)
            for vertex in mesh['vertices']:
                if not all(math.isfinite(v) for field in ('pos', 'normal', 'uvcoord') for v in vertex[field]):
                    raise ValueError('Non-finite vertex: ' + name)
        for texture in item['texture'].values():
            with Image.open(safe_path(rp / 'textures/models', texture + '.png')) as im:
                im.verify()
        checked.append(name)
    for pack in ('behavior_pack', 'resource_pack'):
        read(output / 'addon' / pack / 'manifest.json')
    return {'ok': True, 'models': checked, 'runtime_files': len(record['runtime_sha256']),
            'checks': ['build-time Core comparisons', 'adapter regression tests', 'runtime hashes', 'mesh indices and finite vertices', 'registry dependencies and PNG integrity'],
            'limitation': 'Offline validation only; no MC or mobile-device certification.'}


def export(output, destination):
    output, destination = Path(output).resolve(), Path(destination).resolve()
    result = validate(output)
    if destination.exists() or destination.is_relative_to(output):
        raise ValueError('Destination must be a new file outside the conversion directory.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    record = read(output / 'conversion.json')
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(record['runtime_sha256']):
            archive.write(safe_path(output / 'addon', name), name)
        archive.writestr('conversion-report.json', json.dumps({'profile': record['profile'], 'source_sha256': record['source_sha256'], 'kind': record['kind'], 'scope': record['scope'], 'validation': result}, ensure_ascii=False, indent=2))
    return {'archive': str(destination), 'sha256': digest(destination), 'kind': record['kind'],
            'note': 'Runtime snapshot for development, not a NetEase audited/encrypted submission package.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inspect = sub.add_parser('inspect', help='Inspect folder, model3.json or ZIP without running source code')
    inspect.add_argument('source'); inspect.add_argument('--model'); inspect.add_argument('--report')
    conv = sub.add_parser('convert', help='Rebuild a pinned adapter in a new isolated workspace')
    conv.add_argument('--profile', choices=sorted(read(PROFILE_FILE)), required=True)
    conv.add_argument('--source'); conv.add_argument('--model'); conv.add_argument('--output', required=True)
    val = sub.add_parser('validate'); val.add_argument('output')
    exp = sub.add_parser('export'); exp.add_argument('output'); exp.add_argument('--destination', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'inspect':
            with source_model(args.source, args.model) as model:
                result = inspect_model(model)
            if args.report:
                path = Path(args.report)
                if path.exists():
                    raise ValueError('Report already exists.')
                write(path, result)
        elif args.command == 'convert':
            result = convert(args)
        elif args.command == 'validate':
            result = validate(args.output)
        else:
            result = export(args.output, args.destination)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('missing') else 0
    except (ValueError, OSError, KeyError, ImportError, zipfile.BadZipFile) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
