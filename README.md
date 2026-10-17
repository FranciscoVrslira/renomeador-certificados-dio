# Renomeador Automático de Certificados DIO

Automação local para Windows e Python 3.14. Lê somente a primeira página dos
PDFs diretamente na pasta configurada e renomeia cada documento com o título
identificado. Não altera os bytes do PDF, não percorre subpastas e não usa APIs.

## Instalação e primeiro uso

1. Extraia o ZIP para uma pasta local com permissão de escrita.
2. Instale [Python 3.14 para Windows](https://www.python.org/downloads/windows/),
   incluindo o launcher `py`.
3. Execute `instalar.bat`. Ele cria `.venv`, instala as dependências Python,
   cria `.env` a partir do exemplo se necessário e verifica o OCR.
4. Edite `.env` e configure, por exemplo:

   ```env
   PASTA_CERTIFICADOS=C:\Certificados\DIO
   TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

   Use caminhos sem aspas ou com aspas simples. As variáveis do ambiente têm
   precedência sobre `.env`. Caminhos relativos partem da pasta do projeto,
   independentemente do diretório do terminal. A configuração padrão aponta
   para a subpasta vazia `certificados`.
5. Para revisar uma primeira execução, use `executar.bat --dry-run` no terminal.
6. Execute `executar.bat` para renomear. `DRY_RUN=false` é o padrão.

Também é possível executar diretamente:

```powershell
& '.\.venv\Scripts\python.exe' Main.py --dry-run
& '.\.venv\Scripts\python.exe' Main.py
& '.\.venv\Scripts\python.exe' -m unittest discover -s tests -v
```

Os scripts não exigem ativação manual do ambiente virtual. O instalador não
recria silenciosamente um ambiente existente que use outra versão do Python.

## Tesseract e português

O pacote `pytesseract` é uma interface; o executável Tesseract é instalado
separadamente. Siga a seção Windows da
[documentação do Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html),
que aponta para os instaladores mantidos pela UB Mannheim. Na instalação,
inclua os dados de português (`por.traineddata`). O projeto não baixa nem instala
Tesseract automaticamente e não solicita privilégios administrativos.

Se o executável não estiver no PATH, defina `TESSERACT_PATH` no `.env`.
Confira os idiomas com:

```powershell
& 'C:\Program Files\Tesseract-OCR\tesseract.exe' --list-langs
& '.\.venv\Scripts\python.exe' check_environment.py
```

A lista deve conter `por`. `OCR_LANGUAGE=por+eng` exige ambos os idiomas.
Se faltarem dados, consulte os
[arquivos oficiais de idiomas](https://github.com/tesseract-ocr/tessdata_fast)
e coloque `por.traineddata` na pasta `tessdata` da instalação, respeitando suas
permissões. Se houver instalações múltiplas, confira também `TESSDATA_PREFIX`.

Sem Tesseract, a extração nativa continua funcionando. Arquivos que dependerem
de OCR ficam com o nome original e motivo registrado. `OCR_ENABLED=false`
desativa as tentativas. O instalador retorna código 1 se o OCR estiver incompleto,
mesmo que as dependências Python tenham sido instaladas corretamente.

## Como o título é identificado

A leitura nativa usa `PyMuPDF`, preservando o texto e as posições das linhas.
O extrator exige uma abertura explícita (`concluiu com sucesso o curso`,
`concluiu com sucesso`, `Curso:`, `Nome do curso:` e variantes implementadas)
e um fechamento (`carga horária`, `com duração`, `com N horas` ou
`realizado em`). Ele aceita títulos distribuídos em até seis linhas próximas,
rejeita metadados comuns e resultados ambíguos, e não usa o nome original como
fonte do título. Quebras de linha e espaços repetidos viram um espaço; aspas
externas pareadas são consideradas delimitadores. Acentos, capitalização e
pontuação interna são preservados.

Exemplo reconhecido:

```text
Certificamos que Maria da Silva
concluiu com sucesso o curso
Introdução à Engenharia de Prompts
com carga horária de 2 horas
```

Se faltar contexto suficiente, o título não é adivinhado. O OCR tenta a primeira
página a 300 DPI, com `pytesseract.image_to_data`, incluindo posições e confiança.
Uma região configurada é tentada primeiro com margem para capturar o contexto;
em seguida, a página inteira. Escala de cinza e ajuste de contraste só são
tentados após falha da imagem original. Há timeout por chamada e limite de
40 milhões de pixels por página. O PDF é fechado antes da renomeação.

**Referência fornecida:** o PDF `2LR9QCGT.pdf` foi inspecionado visualmente e
contém o título **Tipos de Operadores com Python**. Ele não contém texto nativo
extraível: exige OCR. O layout tem a abertura `concluiu o curso` e o fechamento
`com carga horária de 2 horas.`, já cobertos pelas regras. Foi adicionado um teste
de regressão com transcrição manual e posições aproximadas da imagem, com o nome
do aluno anonimizado. Isso valida o parser, mas não equivale a executar OCR real.
O Tesseract continua pendente de instalação. Layouts sem os delimitadores
documentados são mantidos intactos. Confiança heurística e confiança do OCR não
são garantia estatística de correção; revise a simulação em seus certificados.

## Configuração da identificação

| Variável | Padrão | Significado |
| --- | --- | --- |
| `TITLE_MIN_CONFIDENCE` | `0.90` | Limiar heurístico entre 0,90 e 1; conclusão recebe 0,98, rótulo recebe 0,94 |
| `TITLE_REGION` | vazio | Restrição espacial opcional `x0,y0,x1,y1`, números entre 0 e 1 |
| `MAX_TITLE_CHARS` | `240` | Máximo de caracteres do título antes da normalização |
| `OCR_MIN_CONFIDENCE` | `85` | Confiança mínima de cada palavra das linhas selecionadas, escala 0–100 |
| `OCR_DPI` | `300` | Resolução de renderização entre 150 e 600 |
| `OCR_TIMEOUT` | `45` | Timeout em segundos de cada chamada ao Tesseract |
| `MAX_FILENAME_UNITS` | `240` | Limite do nome completo, em unidades UTF-16, máximo 255 |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` ou `ERROR` |
| `DRY_RUN` | `false` | Simula e reserva os nomes propostos durante o lote |

Para o modelo visual de `2LR9QCGT.pdf`, a região aproximada do título é
`TITLE_REGION=0.15,0.47,0.75,0.55`. Ela foi conferida visualmente, mas ainda
precisa de validação com as caixas reais retornadas pelo Tesseract. O padrão
continua vazio para aceitar outros layouts. A origem é o canto superior esquerdo
da página sem rotação: x é a fração da largura e y a fração da altura.
Todos os centros das linhas selecionadas devem cair dentro da região.
Linhas que compartilhem título e contexto também precisam caber. A região
restringe os candidatos; não autoriza aceitar texto sem contexto. Mantenha-a
vazia até conhecer o layout. As regras de linguagem estão em
`modules/title_extractor.py`; um novo modelo deve ganhar testes antes de ampliar
essas regras.

## Segurança e duplicidades

Caracteres proibidos pelo Windows (`<>:"/\|?*` e controles ASCII) viram `_`.
Espaços/pontos finais são retirados e nomes reservados recebem `_` no início.
Unicode válido é mantido. O nome é truncado somente quando necessário para
respeitar o limite configurado e um caminho completo de até 259 unidades UTF-16,
compatível com aplicações Windows sem suporte a caminhos longos. Pastas longas
demais produzem falha explícita, sem mover o documento.

Colisões ignoram diferenças de caixa e incluem arquivos e diretórios. O primeiro
nome disponível é usado: `Curso.pdf`, `Curso (2).pdf`, `Curso (3).pdf` etc.
Um nome já correspondente, inclusive um sufixo numérico anteriormente aplicado,
é mantido, mesmo que o arquivo sem sufixo já não exista. Isso também considera
títulos truncados. Arquivos de conteúdo duplicado não são apagados nem deduplicados.

A operação final usa `os.rename` no Windows, que falha se o destino já existir;
uma colisão surgida entre a verificação e a operação provoca nova tentativa com
o próximo número. Não há `replace`, cópia sobre destino ou exclusão de PDFs.
A renomeação real é recusada em outros sistemas operacionais. Execute um lote
por vez e evite editar os certificados durante o processamento. Links simbólicos
são recusados.

## Logs e resumo

Há um arquivo UTF-8 por execução em `logs/`, além do console. Cada registro de
resultado contém data/hora, nome original, título, método, tentativa de OCR,
nome final, status e motivo. `DEBUG` acrescenta diagnóstico e rastros de erro.
Os logs contêm os nomes dos cursos e arquivos; armazene-os conforme sua política.

| Status | Efeito |
| --- | --- |
| `RENOMEADO` | Renomeação realizada |
| `JA_PROCESSADO` | Nome válido já aplicado |
| `SIMULADO` | Nome proposto; nenhuma alteração |
| `TITULO_NAO_IDENTIFICADO` | Original preservado; veja motivo e `ocr_tentado` |
| `ERRO_LEITURA` | Documento inválido, protegido, inacessível ou falha de leitura |
| `ERRO_RENOMEACAO` | Falha de permissão, arquivo em uso ou nome/caminho inválido |

O resumo é construído a partir dos status reais. Simulações são contadas
separadamente. Níveis WARNING/ERROR ocultam andamento e resumo INFO; use INFO
para o acompanhamento completo. Saída do programa: 0 para lote sem falhas,
1 para falhas individuais e 2 para falha geral/configuração.

## Estrutura

```text
Main.py                    Coordenação e resumo
config.py                  Leitura e validação do .env
check_environment.py       Diagnóstico do Python e OCR
modules/pdf_reader.py      Leitura nativa e coordenadas
modules/title_extractor.py  Regras de identificação
modules/ocr_service.py      Renderização, OCR e pré-processamento
modules/file_renamer.py     Nomes Windows e renomeação segura
modules/logger_config.py    Logs
tests/                     Testes unitários e integração sintética
logs/                      Logs por execução
certificados/              Pasta padrão de entrada
requirements.txt           Faixas compatíveis das dependências
requirements-lock.txt      Versões exatas usadas na validação
instalar.bat / executar.bat Instalação e execução no Windows
```

## Compatibilidade e dependências

O projeto foi desenvolvido para CPython 3.14, Windows x64. O
[PyMuPDF documenta testes com Python 3.14](https://pymupdf.readthedocs.io/en/latest/installation.html),
o [Pillow documenta suporte](https://pillow.readthedocs.io/en/stable/installation/python-support.html)
e o [python-dotenv declara suporte](https://pypi.org/project/python-dotenv/).
O [pytesseract 0.3.13](https://pypi.org/project/pytesseract/) é uma interface Python
para o executável externo; seu metadata não declara especificamente 3.14.
Sua instalação, importação e integração com respostas simuladas foram verificadas
em 3.14 neste projeto. Não foi necessário substituir nenhuma biblioteca.

Para reproduzir exatamente as versões da validação:

```powershell
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-lock.txt
```

## Problemas comuns

- **Pasta inexistente:** confira `PASTA_CERTIFICADOS`. A aplicação não cria uma
  pasta digitada incorretamente; o lote é encerrado com mensagem de erro.
- **Permissão/arquivo em uso:** feche leitores de PDF, confira as permissões da
  pasta e tente novamente. Os demais documentos continuam sendo processados.
- **PDF protegido ou corrompido:** o original permanece. Providencie uma cópia
  válida ou sem senha, obtida legitimamente, e processe novamente.
- **Título não identificado:** consulte `DEBUG`, confira os delimitadores e a
  região. Uma região isolada não basta para identificar um título com segurança.
- **OCR ausente/idioma indisponível:** rode `check_environment.py`, configure o
  caminho e confira `--list-langs`. O fallback não instala componentes.
- **OCR lento:** reduza DPI ou aumente o timeout dentro dos limites; cada página
  pode exigir várias tentativas. O processamento é sequencial.
- **Caminho muito longo:** mova a pasta para mais perto da raiz do disco.
- **Logs indisponíveis:** confira permissão de escrita na pasta do projeto.

## Validação

Veja `VALIDACAO.md` para resultados executados e limitações. Os testes usam
`unittest`, arquivos temporários e mocks para falhas de permissão, corrida de
colisões e OCR. Nenhum certificado pessoal é incluído na distribuição.
