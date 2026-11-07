"""Boundary and real-output checks for the offline conversion entry point."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import live2d_pipeline as pipeline


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def model(self, folder=None, refs=None):
        folder = folder or self.root
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / 'sample.model3.json'
        pipeline.write(path, {'Version': 3, 'FileReferences': refs or {'Moc': 'sample.moc3'}})
        return path

    def test_missing_resource_is_explicit_and_unknown_is_not_matched(self):
        result = pipeline.inspect_model(self.model())
        self.assertEqual(result['missing'], ['sample.moc3'])
        self.assertEqual(result['supported_adapters'], [])

    def test_unknown_conversion_does_not_create_output(self):
        source = self.model(self.root / 'source')
        output = self.root / 'output'
        args = argparse.Namespace(profile='default', source=str(source), model=None, output=str(output))
        with self.assertRaisesRegex(ValueError, 'Output was not created'):
            pipeline.convert(args)
        self.assertFalse(output.exists())

    def test_reference_cannot_escape_model(self):
        with self.assertRaisesRegex(ValueError, 'Unsafe relative path'):
            pipeline.inspect_model(self.model(refs={'Moc': '../outside.moc3'}))

    def test_archive_traversal_rejected_before_extract(self):
        archive = self.root / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('../escaped.txt', 'bad')
        with self.assertRaisesRegex(ValueError, 'Unsafe relative path'):
            with pipeline.source_model(archive):
                self.fail('unsafe archive yielded a model')
        self.assertFalse((self.root / 'escaped.txt').exists())

    def test_archive_symlink_rejected(self):
        archive = self.root / 'bad.zip'
        entry = zipfile.ZipInfo('link'); entry.create_system = 3
        entry.external_attr = 0o120777 << 16
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr(entry, '../outside')
        with self.assertRaisesRegex(ValueError, 'symbolic link'):
            with pipeline.source_model(archive):
                self.fail('unsafe archive yielded a model')

    def test_archive_selection_and_case_duplicate(self):
        archive = self.root / 'models.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            for name in ('a', 'b'):
                z.writestr(name + '/sample.model3.json', json.dumps({'FileReferences': {'Moc': 'sample.moc3'}}))
                z.writestr(name + '/sample.moc3', b'fixture')
        with self.assertRaisesRegex(ValueError, 'Select one model'):
            with pipeline.source_model(archive):
                pass
        with pipeline.source_model(archive, 'b/sample.model3.json') as model:
            self.assertEqual(pipeline.inspect_model(model)['missing'], [])
        with zipfile.ZipFile(archive, 'a') as z:
            z.writestr('B/SAMPLE.moc3', b'duplicate')
        with self.assertRaisesRegex(ValueError, 'Duplicate path'):
            with pipeline.source_model(archive):
                pass

    def test_existing_output_cannot_be_overwritten(self):
        args = argparse.Namespace(profile='default', source=None, model=None, output=str(self.root))
        sentinel = self.root / 'keep.txt'; sentinel.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'NEW directory'):
            pipeline.convert(args)
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_model_change_invalidates_pin(self):
        self.model()
        first = pipeline.fingerprint(self.root)
        (self.root / 'sample.moc3').write_bytes(b'changed')
        self.assertNotEqual(first, pipeline.fingerprint(self.root))


class BuiltOutputTests(unittest.TestCase):
    def test_both_real_conversions_and_export_exclusions(self):
        # Integration artifacts are optional outside the developer workspace.
        for profile in ('default', 'deepseek'):
            output = pipeline.ROOT / 'build' / ('pipeline-' + profile)
            if not (output / 'conversion.json').exists():
                self.skipTest('Run both isolated conversions first')
            self.assertTrue(pipeline.validate(output)['ok'])
            with tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / 'runtime.zip'
                pipeline.export(output, destination)
                with zipfile.ZipFile(destination) as z:
                    names = z.namelist()
                    self.assertIn('behavior_pack/manifest.json', names)
                    self.assertIn('resource_pack/manifest.json', names)
                    self.assertNotIn('behavior_pack.zip', names)
                    self.assertTrue(all(n.startswith(('behavior_pack/', 'resource_pack/')) or n == 'conversion-report.json' for n in names))
                    self.assertFalse(any('vendor' in n or '__pycache__' in n or n.endswith('.moc3') for n in names))
                with self.assertRaisesRegex(ValueError, 'new file'):
                    pipeline.export(output, destination)

    def test_tampered_output_fails_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); addon = root / 'addon'; addon.mkdir()
            file = addon / 'test.txt'; file.write_text('original')
            pipeline.write(root / 'conversion.json', {'status': 'complete', 'runtime_sha256': pipeline.inventory(addon)})
            file.write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Runtime changed'):
                pipeline.validate(root)


if __name__ == '__main__':
    unittest.main()
