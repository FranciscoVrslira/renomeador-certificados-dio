from dataclasses import replace
import logging
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import pymupdf
from PIL import Image

from config import Config, load_config
from Main import run_batch
from modules.ocr_service import OCRService
from modules.pdf_reader import TextLine
from modules.title_extractor import TitleResult


def certificate(path, *, encrypted=False, empty=False):
    with pymupdf.open() as doc:
        page = doc.new_page(width=842, height=595)
        if not empty:
            page.insert_text((80, 130), 'Certificamos que Maria da Silva', fontsize=16)
            page.insert_text((80, 180), 'concluiu com sucesso o curso', fontsize=14)
            page.insert_text((80, 220), 'Introdução à Engenharia de Prompts', fontsize=18)
            page.insert_text((80, 260), 'com carga horária de 2 horas', fontsize=14)
        options = dict(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw='owner', user_pw='secret') if encrypted else {}
        doc.save(path, **options)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.config = Config(self.folder, ocr_enabled=False)
        self.logger = logging.getLogger('test-dio')
        self.logger.addHandler(logging.NullHandler())
        self.logger.propagate = False

    def test_batch_continues_and_second_run(self):
        certificate(self.folder / 'a.pdf')
        certificate(self.folder / 'b.PDF')
        (self.folder / 'corrupt.pdf').write_bytes(b'not a PDF')
        certificate(self.folder / 'protected.pdf', encrypted=True)
        certificate(self.folder / 'blank.pdf', empty=True)
        nested = self.folder / 'nested'
        nested.mkdir()
        certificate(nested / 'ignore.pdf')
        counts = run_batch(self.config, self.logger)
        self.assertEqual(counts['RENOMEADO'], 2)
        self.assertEqual(counts['ERRO_LEITURA'], 2)
        self.assertEqual(counts['TITULO_NAO_IDENTIFICADO'], 1)
        self.assertTrue((nested / 'ignore.pdf').exists())
        counts = run_batch(self.config, self.logger)
        self.assertEqual(counts['JA_PROCESSADO'], 2)
        self.assertEqual(counts['RENOMEADO'], 0)

    def test_missing_folder(self):
        with self.assertRaises(NotADirectoryError):
            run_batch(replace(self.config, folder=self.folder / 'missing'), self.logger)

    def test_ocr_fallback(self):
        certificate(self.folder / 'image.pdf', empty=True)
        with patch.object(OCRService, 'extract', return_value=TitleResult('Curso OCR', .98, 'mock')) as extract:
            counts = run_batch(replace(self.config, ocr_enabled=True), self.logger)
            self.assertEqual(extract.call_count, 1)
        self.assertEqual(counts['RENOMEADO'], 1)

    def test_ocr_missing_preserves_original(self):
        certificate(self.folder / 'image.pdf', empty=True)
        with patch('modules.ocr_service.subprocess.run', side_effect=FileNotFoundError('tesseract')):
            counts = run_batch(replace(self.config, ocr_enabled=True), self.logger)
        self.assertEqual(counts['TITULO_NAO_IDENTIFICADO'], 1)
        self.assertTrue((self.folder / 'image.pdf').exists())

    def test_language_missing(self):
        service = OCRService(self.config)
        with patch('modules.ocr_service.subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'eng\n', '')):
            with self.assertRaisesRegex(RuntimeError, 'por'):
                service.check()

    def test_ocr_render_and_preprocess_retry(self):
        path = self.folder / 'image.pdf'
        certificate(path, empty=True)
        service = OCRService(self.config)
        good = [TextLine('Curso: Python carga horária: 2 horas', (.1, .3, .9, .4), 99)]
        with pymupdf.open(path) as doc:
            with patch.object(service, 'check'), patch.object(service, 'lines', side_effect=[[], good]) as read:
                result = service.extract(doc[0], self.logger)
                self.assertEqual(result.title, 'Python')
                self.assertEqual(read.call_count, 2)

    def test_rename_failure_continues(self):
        certificate(self.folder / 'a.pdf')
        certificate(self.folder / 'b.pdf')
        with patch('modules.file_renamer.os.rename', side_effect=PermissionError('bloqueado')):
            counts = run_batch(self.config, self.logger)
        self.assertEqual(counts['ERRO_RENOMEACAO'], 2)
        self.assertTrue((self.folder / 'a.pdf').exists())

    def test_ocr_timeout(self):
        certificate(self.folder / 'image.pdf', empty=True)
        with patch.object(OCRService, 'extract', side_effect=RuntimeError('Tesseract process timeout')):
            counts = run_batch(replace(self.config, ocr_enabled=True), self.logger)
        self.assertEqual(counts['TITULO_NAO_IDENTIFICADO'], 1)

    def test_ocr_coordinates_and_minimum_word_confidence(self):
        data = dict(text=['Curso:', 'Python', 'carga', 'horária'], block_num=[1]*4,
                    par_num=[1]*4, line_num=[1]*4, left=[0, 20, 40, 60], top=[10]*4,
                    width=[10]*4, height=[10]*4, conf=[99, 40, 98, 98])
        with Image.new('RGB', (100, 100)) as image:
            with patch('modules.ocr_service.pytesseract.image_to_data', return_value=data):
                result = OCRService(self.config).lines(image, (0, 0, 1, 1), 6)
        self.assertEqual(result[0].confidence, 40)
        self.assertEqual(result[0].bbox, (0, .1, .7, .2))

    def test_env_relative_and_validation(self):
        env = self.folder / '.env'
        env.write_text('PASTA_CERTIFICADOS=entrada\nDRY_RUN=true\n', encoding='utf-8-sig')
        with patch.dict('os.environ', {}, clear=True):
            config = load_config(self.folder)
            self.assertEqual(config.folder, self.folder / 'entrada')
            self.assertTrue(config.dry_run)
            env.write_text('TITLE_REGION=0,0,nan,1', encoding='utf-8')
            with self.assertRaises(ValueError):
                load_config(self.folder)
