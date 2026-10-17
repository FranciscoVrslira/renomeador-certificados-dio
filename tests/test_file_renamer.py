import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from modules.file_renamer import Renamer, filename, normalize_title, units


class RenameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.renamer = Renamer(self.folder)

    def make(self, name="original.pdf"):
        path = self.folder / name
        path.write_bytes(b"unchanged certificate bytes")
        return path

    def test_normalization(self):
        self.assertEqual(normalize_title('Introdução: C# / IA?'), 'Introdução_ C# _ IA_')
        self.assertEqual(normalize_title('A<>:"/\\|?*\x01'), 'A__________')
        self.assertEqual(normalize_title('Curso.  '), 'Curso')
        self.assertEqual(normalize_title('CON.txt'), '_CON.txt')
        self.assertEqual(normalize_title('LPT¹'), '_LPT¹')
        with self.assertRaises(ValueError):
            normalize_title('...')

    def test_rename_preserves_bytes(self):
        source = self.make()
        before = hashlib.sha256(source.read_bytes()).digest()
        status, final = self.renamer.rename(source, 'Introdução à IA')
        self.assertEqual(status, 'RENOMEADO')
        self.assertEqual(final.name, 'Introdução à IA.pdf')
        self.assertEqual(hashlib.sha256(final.read_bytes()).digest(), before)

    def test_duplicates_case_and_idempotence(self):
        self.make('PYTHON.pdf')
        self.make('Python (2).pdf')
        status, target = self.renamer.rename(self.make(), 'Python')
        self.assertEqual(target.name, 'Python (3).pdf')
        self.assertEqual(self.renamer.rename(target, 'Python')[0], 'JA_PROCESSADO')
        self.assertEqual(self.renamer.rename(self.folder / 'PYTHON.pdf', 'Python')[0], 'JA_PROCESSADO')
        self.assertEqual((self.folder / 'PYTHON.pdf').read_bytes(), b'unchanged certificate bytes')

    def test_suffix_without_base_is_still_processed(self):
        self.assertEqual(self.renamer.rename(self.make('Python (12).pdf'), 'Python')[0], 'JA_PROCESSADO')

    def test_dry_run_reserves_names(self):
        renamer = Renamer(self.folder, dry_run=True)
        a, b = self.make('a.pdf'), self.make('b.pdf')
        self.assertEqual(renamer.rename(a, 'Python')[1].name, 'Python.pdf')
        self.assertEqual(renamer.rename(b, 'Python')[1].name, 'Python (2).pdf')
        self.assertTrue(a.exists() and b.exists())
        self.assertFalse((self.folder / 'Python.pdf').exists())

    def test_permission_and_invalid(self):
        path = self.make()
        with patch('modules.file_renamer.os.rename', side_effect=PermissionError('arquivo em uso')):
            with self.assertRaises(PermissionError):
                self.renamer.rename(path, 'Python')
        self.assertTrue(path.exists())
        with self.assertRaises(ValueError):
            self.renamer.rename(self.folder / 'missing.pdf', 'Python')

    def test_race_never_overwrites(self):
        original_rename = os.rename
        def race(source, target):
            if target.name == 'Python.pdf':
                target.write_bytes(b'existing')
                raise FileExistsError()
            original_rename(source, target)
        with patch('modules.file_renamer.os.rename', side_effect=race):
            self.assertEqual(self.renamer.rename(self.make(), 'Python')[1].name, 'Python (2).pdf')
        self.assertEqual((self.folder / 'Python.pdf').read_bytes(), b'existing')

    def test_long_unicode_and_truncated_suffix(self):
        title = 'Acentuação 😀 ' * 40
        self.make(filename(title, self.folder, 90))
        renamer = Renamer(self.folder, 90)
        _, target = renamer.rename(self.make(), title)
        self.assertLessEqual(units(target.name), 90)
        self.assertTrue(target.name.endswith(' (2).pdf'))
        self.assertEqual(renamer.rename(target, title)[0], 'JA_PROCESSADO')
