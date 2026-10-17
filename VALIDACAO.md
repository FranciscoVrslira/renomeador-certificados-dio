# Validação executada

Data: 16/10/2026. Ambiente: Windows x64, CPython 3.14.4.

## Resultados

- `python -m unittest discover -s tests -v`: **30 testes passaram** na atualização com a referência.
- `python -m pip check`: nenhuma dependência incompatível detectada.
- `python -m compileall -q Main.py config.py check_environment.py modules tests`:
  compilação concluída sem erros.
- `instalar.bat`: criou o ambiente virtual Python 3.14 e instalou as dependências.
  Detectou corretamente Tesseract ausente e retornou 1, indicando OCR incompleto.
- `executar.bat --dry-run`, chamado de fora da pasta do projeto: código 0,
  configuração relativa resolvida e resumo exibido para a pasta padrão vazia.

Os testes cobrem extração multilinha, acentos, pontuação, ambiguidade, confiança,
região configurada e separação espacial; normalização Windows e nomes reservados;
colisões por caixa, sequenciamento, reexecução e simulação; truncamento Unicode;
preservação de bytes por SHA-256; corrida de criação do destino; falha de permissão;
PDFs sintéticos reais, arquivos corrompidos, protegidos e vazios; isolamento de
subpastas; continuidade do lote; fallback, timeout, ausência do OCR, idioma ausente,
conversão de coordenadas OCR e nova tentativa com pré-processamento.

As renomeações dos testes foram reais, dentro de diretórios temporários. As falhas
de permissão/corrida e as respostas do reconhecedor OCR foram simuladas com mocks.
A renderização PyMuPDF e o pré-processamento Pillow foram executados realmente.

## Dependências instaladas

```text
PyMuPDF 1.28.2
pytesseract 0.3.13
Pillow 13.0.0
python-dotenv 1.2.4
packaging 26.3
```

## Limitações pendentes

O Tesseract não estava disponível no PATH nem nos caminhos usuais verificados.
Não houve instalação automática do motor. Assim, não se afirma validação real de
reconhecimento OCR com português; ela exige Tesseract e os dados `por` instalados.

## Referência DIO recebida

O arquivo `2LR9QCGT.pdf` foi aberto e renderizado para inspeção visual. O título
confirmado é `Tipos de Operadores com Python`. A primeira página não retornou
texto nem blocos de texto pelo PyMuPDF, portanto precisa de OCR.

Foi acrescentado um teste de parser usando uma transcrição manual do contexto
e coordenadas aproximadas, com o nome do aluno anonimizado. Outro teste garante
que o nome do curso não é fixado no código. A região visual proposta é
`0.15,0.47,0.75,0.55`, opcional; as regras existentes já cobrem os delimitadores
do certificado. O PDF pessoal não integra o ZIP.

A validação ponta a ponta do OCR nessa amostra permanece pendente do Tesseract.
O original foi preservado. Execute a simulação após instalar o motor e confira
o nome proposto antes de usar a renomeação real.
