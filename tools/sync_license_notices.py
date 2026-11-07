"""Copy license notices into both packs; --check never writes or launches MC."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    'LICENSE': 'LICENSE',
    'COPYRIGHT.md': 'COPYRIGHT.md',
    'THIRD_PARTY_NOTICES.md': 'THIRD_PARTY_NOTICES.md',
    'licenses/BongoCatMC-additional-permission.txt': 'licenses/BongoCatMC-additional-permission.txt',
    'licenses/BongoCat-assets-MIT.txt': 'licenses/BongoCat-assets-MIT.txt',
    'licenses/Live2D-Framework-NOTICE.md': 'licenses/Live2D-Framework-NOTICE.md',
    'docs/deepseek-permission.md': 'docs/deepseek-permission.md',
    'docs/source-distribution.md': 'docs/source-distribution.md',
}


def sync(root=ROOT, check=False):
    root = Path(root)
    # Fail before partial copying if a source notice is absent.
    payloads = [(name, target, (root / name).read_bytes()) for name, target in FILES.items()]
    stale = []
    for pack in ('behavior_pack', 'resource_pack'):
        for name, target, data in payloads:
            dest = root / 'addon' / pack / 'legal' / target
            if not dest.is_file() or dest.read_bytes() != data:
                stale.append(str(dest.relative_to(root)))
                if not check:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
    legacy = root / 'addon/resource_pack/BONGOCAT_ASSET_LICENSE.txt'
    expected = (root / 'licenses/BongoCat-assets-MIT.txt').read_bytes()
    if not legacy.is_file() or legacy.read_bytes() != expected:
        stale.append(str(legacy.relative_to(root)))
        if not check:
            legacy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / 'licenses/BongoCat-assets-MIT.txt', legacy)
    if check and stale:
        raise ValueError('Missing/stale notices: ' + ', '.join(stale))
    return len(stale)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    count = sync(check=args.check)
    print('Notices verified.' if args.check else 'Updated %d notice files.' % count)
