# Currículo — Markdown para PDF (otimizado para ATS/IA)

Projeto para manter o currículo em Markdown como fonte única da verdade e
gerar automaticamente PDFs otimizados para leitura por ATS (Applicant
Tracking System) e por triagem automatizada via IA.

## Estrutura do projeto

```
curriculo_base_PT.md   # conteúdo do currículo em português (fonte)
curriculo_base_EN.md   # conteúdo do currículo em inglês (fonte)
instructions.md        # regras para um agente de IA adaptar o currículo a uma vaga
gerar_pdf.py           # script que converte os .md acima em PDF
requirements.txt       # dependências Python (reportlab)
Curriculo_PT.pdf       # gerado pelo script (A4)
Curriculo_EN.pdf       # gerado pelo script (Letter)
```

## Como usar

1. Instale as dependências (uma vez, idealmente em um venv):
   ```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Edite `curriculo_base_PT.md` e/ou `curriculo_base_EN.md` com o conteúdo do
   currículo (ver convenções abaixo).

3. Gere os PDFs:
   ```
   python gerar_pdf.py
   ```
   Isso processa `curriculo_base_PT.md` e `curriculo_base_EN.md` (se
   existirem no diretório atual) e cria `Curriculo_PT.pdf` / `Curriculo_EN.pdf`.

   Outros usos:
   ```
   python gerar_pdf.py meu_curriculo.md --out-dir dist --max-pages 1
   ```

## Convenções do Markdown

- `# Nome` — primeira linha do arquivo, único H1.
- Linha solta logo abaixo do nome — vira o subtítulo (ex: cargo desejado).
- **A primeira seção `##` do arquivo é sempre tratada como bloco de
  contato**: deve conter só itens de lista (`- Label: valor`) e é renderizada
  em uma linha só, sem repetir o título da seção.
- Demais seções `##` (Experiência, Formação, Habilidades, Idiomas, Carta de
  Apresentação, etc.) viram seções normais do PDF.
- Dentro de uma seção, `### Cargo/Curso` seguido da linha `**Empresa** |
  Período` forma um item de experiência/formação. Bullets (`-`) abaixo viram
  a lista de responsabilidades.
- Seções sem `###` (como Habilidades/Idiomas) podem ser só uma lista de
  bullets direto abaixo do `##`.

Basta adicionar mais bullets, mais itens `###` ou seções `##` inteiras — o
script se adapta automaticamente, sem precisar editar `gerar_pdf.py`.

## Nome do arquivo de entrada

O script identifica o idioma pelo sufixo do nome do arquivo:

- `..._PT.md` → página A4, rótulo de página "Pagina X".
- `..._EN.md` → página Letter, rótulo de página "Page X".
- Qualquer outro nome → padrão A4/"Pagina X".

## Como adaptar seu Markdown para uma vaga específica

[instructions.md](instructions.md) contém as regras que um agente de IA deve
seguir para adaptar `curriculo_base_PT.md` / `curriculo_base_EN.md` a uma
vaga específica — reordenando e reescrevendo o conteúdo para casar com as
palavras-chave da vaga, melhorando a relevância para ATS, sem nunca inventar
ou alterar fatos (empresas, datas, formações, habilidades, etc.). Também fixa
as convenções estruturais da seção acima, para que o arquivo gerado continue
sendo interpretável pelo `gerar_pdf.py`.

Para usar, forneça a um agente de IA o(s) arquivo(s) Markdown atual(is) do
currículo, o texto da vaga e o `instructions.md`, com um prompt como:

```
Baseado na descrição da vaga abaixo, adapte os arquivos curriculo_base_EN.md
e curriculo_base_PT.md para se adequarem ao que a vaga pede. Siga as regras
estabelecidas em instructions.md. Gere os novos arquivos com o nome atual +
"_adapted.md" (ou seja, curriculo_base_EN_adapted.md e
curriculo_base_PT_adapted.md), sem modificar os arquivos originais.

Descrição da vaga:
<cole aqui a descrição da vaga>
```

Isso produz `curriculo_base_PT_adapted.md` e `curriculo_base_EN_adapted.md`
— versões ajustadas e relevantes para ATS para aquela candidatura específica,
deixando os arquivos-base originais intocados. Gere os PDFs a partir deles
da mesma forma que qualquer outro arquivo de entrada:

```
python gerar_pdf.py curriculo_base_PT_adapted.md curriculo_base_EN_adapted.md
```

## Por que é ATS/IA-friendly

- Coluna única, sem tabelas, caixas de texto ou imagens de texto.
- Fontes padrão do PDF (Helvetica), sempre com texto selecionável/extraível.
- Ordem de leitura estritamente linear, igual à ordem do Markdown.
- Metadados do PDF (título, autor, assunto, palavras-chave) preenchidos
  automaticamente a partir do conteúdo.
- Auto-encaixe de layout: o script tenta várias escalas de espaçamento/fonte
  até o conteúdo caber no limite de páginas configurado (`--max-pages`,
  padrão 2), sem exigir ajuste manual quando novas experiências/habilidades
  são adicionadas.

Mais detalhes de implementação em [CLAUDE.md](CLAUDE.md).
