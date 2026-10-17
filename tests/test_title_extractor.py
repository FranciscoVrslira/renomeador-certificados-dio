from dataclasses import replace
from pathlib import Path
import unittest

from config import Config
from modules.pdf_reader import TextLine
from modules.title_extractor import extract_title


def lines(*texts, confidence=100):
    return [TextLine(t, (.1, .2 + i * .04, .9, .23 + i * .04), confidence)
            for i, t in enumerate(texts)]


class TitleTests(unittest.TestCase):
    def setUp(self):
        self.config = Config(Path("."))

    def test_accents_and_multiline(self):
        result = extract_title(lines("Certificamos que Maria da Silva", "concluiu com sucesso o curso",
                                     "Introdução à Engenharia", "de Prompts", "com carga horária de 2 horas"), self.config)
        self.assertEqual(result.title, "Introdução à Engenharia de Prompts")

    def test_inline(self):
        self.assertEqual(extract_title(lines("concluiu o curso C#: Coleções, com carga horária de 4 horas"),
                                       self.config).title, "C#: Coleções")

    def test_quoted_and_label(self):
        self.assertEqual(extract_title(lines('Curso: “Python e IA”', 'Carga horária: 8 horas'),
                                       self.config).title, "Python e IA")

    def test_no_course_word(self):
        self.assertEqual(extract_title(lines("concluiu com sucesso", "Introdução ao Python", "com duração de 3 horas"),
                                       self.config).title, "Introdução ao Python")

    def test_no_guess(self):
        for sample in ((), ("Maria da Silva", "Certificado", "DIO", "2 horas"),
                       ("Curso: Python",), ("concluiu o curso Certificado de Maria com carga horária de 2 horas",)):
            with self.subTest(sample=sample):
                self.assertIsNone(extract_title(lines(*sample), self.config).title)

    def test_ambiguity(self):
        self.assertIsNone(extract_title(lines("Curso: Python com carga horária de 2 horas",
                                             "Curso: Java com carga horária de 2 horas"), self.config).title)

    def test_ocr_low_confidence(self):
        self.assertIsNone(extract_title(lines("Curso: Python carga horária: 3 horas", confidence=60),
                                       self.config, ocr=True).title)

    def test_ocr_high_confidence(self):
        self.assertEqual(extract_title(lines("Curso: Python carga horária: 3 horas", confidence=97),
                                       self.config, ocr=True).title, "Python")

    def test_region_and_threshold(self):
        sample = lines("Curso: Python carga horária: 3 horas")
        self.assertIsNone(extract_title(sample, replace(self.config, title_region=(0, .7, 1, .9))).title)
        self.assertIsNone(extract_title(sample, replace(self.config, min_confidence=.99)).title)

    def test_distant_blocks(self):
        sample = [TextLine("concluiu o curso", (.1, .1, .9, .15)),
                  TextLine("Python", (.1, .7, .9, .75)),
                  TextLine("carga horária 2 horas", (.1, .8, .9, .85))]
        # With one title line distant from its anchor, reject the disconnected layout.
        self.assertIsNone(extract_title(sample, self.config).title)

    def test_dio_reference_layout(self):
        # Manual transcription of the supplied image, NOT actual OCR output.
        # Student identity is anonymized; coordinates are visual approximations.
        sample = [
            TextLine('Certificamos que', (.178, .33, .32, .36)),
            TextLine('Pessoa de Exemplo', (.178, .38, .57, .42)),
            TextLine('em 07 de Outubro de 2025, concluiu o curso', (.178, .435, .55, .465)),
            TextLine('Tipos de Operadores com Python', (.178, .49, .71, .535)),
            TextLine('com carga horária de 2 horas.', (.178, .56, .43, .59)),
        ]
        config = replace(self.config, title_region=(.15, .47, .75, .55))
        for ocr in (False, True):
            with self.subTest(ocr=ocr):
                self.assertEqual(extract_title(sample, config, ocr=ocr).title,
                                 'Tipos de Operadores com Python')

    def test_reference_title_is_not_hardcoded(self):
        sample = lines('em 07 de Outubro de 2025, concluiu o curso',
                       'Estruturas de Dados em Python', 'com carga horária de 2 horas.')
        self.assertEqual(extract_title(sample, self.config).title, 'Estruturas de Dados em Python')
        self.assertIsNone(extract_title([], self.config, ocr=True).title)
