"""Convert a collection of notebooks to a single PDF, via Latex.

- Combines notebooks into one document
- Inserts Latex labels for each document
- Converts links between notebooks to Latex \\ref{}
- Runs pdflatex to make a PDF (actually, nbconvert does this)

Requirements:
- nbconvert pandocfilters  (pip installable)
- pandoc
- pdflatex
"""
import argparse
import logging
import os
from pathlib import Path
from tempfile import mkdtemp
from typing import Sequence

import nbformat
from nbformat import NotebookNode
from nbformat.v4 import new_notebook, new_markdown_cell
from nbconvert.exporters import PDFExporter, LatexExporter
# To be able to filter particular tags: i.e. "hidden"
from nbconvert.preprocessors import TagRemovePreprocessor
from nbconvert.writers import FilesWriter
from nbconvert.utils.pandoc import pandoc
from traitlets.config import Config

from .filter_links import convert_links


log = logging.getLogger(__name__)


def new_latex_cell(source=''):
    return NotebookNode(
        cell_type='raw',  # noqa
        metadata=NotebookNode(raw_mimetype='text/latex'),  # noqa
        source=source,  # noqa
    )


class NoHeader(Exception):
    pass


def add_sec_label(cell: NotebookNode, nbname) -> Sequence[NotebookNode]:
    """Adds a Latex \\label{} under the chapter heading.

    This takes the first cell of a notebook, and expects it to be a Markdown
    cell starting with a level 1 heading. It inserts a label with the notebook
    name just underneath this heading.
    """
    # Original assert.
    # assert cell.cell_type == 'markdown', cell.cell_type
    # replaced with a critical warning in log.
    if cell.cell_type != 'markdown':
        log.critical('add_sec_label: cell_type should be "markdown"')

    lines = cell.source.splitlines()
    if lines[0].startswith('# '):
        header_lines = 1
    elif len(lines) > 1 and lines[1].startswith('==='):
        header_lines = 2
    else:
        raise NoHeader

    header = '\n'.join(lines[:header_lines])
    intro_remainder = '\n'.join(lines[header_lines:]).strip()
    res = [
        new_markdown_cell(header),
        new_latex_cell('\label{sec:%s}' % nbname)  # noqa
    ]
    res[0].metadata = cell.metadata
    if intro_remainder:
        res.append(new_markdown_cell(intro_remainder))
    return res


def combine_notebooks(notebook_files: Sequence[Path]) -> NotebookNode:
    combined_nb = new_notebook()

    count = 0
    for filename in notebook_files:
        count += 1
        log.debug('Adding notebook: %s', filename)
        nbname = filename.stem
        nb = nbformat.read(str(filename), as_version=4)

        try:
            combined_nb.cells.extend(add_sec_label(nb.cells[0], nbname))
        except NoHeader:
            raise NoHeader(f"Failed to find header in {filename}")

        combined_nb.cells.extend(nb.cells[1:])

        if not combined_nb.metadata:
            combined_nb.metadata = nb.metadata.copy()

    log.info('Combined %d files' % count)
    return combined_nb


mydir = os.path.dirname(os.path.abspath(__file__))
filter_links = os.path.join(mydir, 'filter_links.py')


def pandoc_convert_links(source):
    return pandoc(source,
                  'markdown',
                  'latex',
                  extra_args=[
                      '--filter', filter_links
                  ])


class MyLatexExporter(LatexExporter):
    def default_filters(self):
        yield from super().default_filters()
        yield 'resolve_references', convert_links


class MyLatexPDFExporter(PDFExporter):
    def default_filters(self):
        yield from super().default_filters()
        yield 'resolve_references', convert_links


def add_preamble(extra_preamble_file, exporter):
    if extra_preamble_file is None:
        return

    with extra_preamble_file.open() as f:
        extra_preamble = f.read()

    td = mkdtemp()
    print(td)
    template_path = Path(td, 'with_extra_preamble.tplx')
    with template_path.open('w') as f:
        f.write("((* extends 'article.tplx' *))\n"
                "((* block header *))\n"
                "((( super() )))\n"
                )
        f.write(extra_preamble)
        f.write('((* endblock header *))\n')

    # Not using append, because we need an assignment to trigger trailer change
    exporter.template_path = exporter.template_path + [td]
    exporter.template_file = 'with_extra_preamble'


def export(combined_nb: NotebookNode, output_file: Path, pdf=False,
           template_file=None,
           remove_cell_tags: tuple = ('hidden', 'remove_cell'),
           remove_all_outputs_tags: tuple = ('hidden', 'remove_output'),
           remove_input_tags: tuple = ('hidden', 'remove_input'),):
    resources = dict()
    resources['unique_key'] = 'combined'
    resources['output_files_dir'] = 'combined_files'

    # BY DEFAULT: remove cells with this tag text: "hidden"
    # As:  --TagRemovePreprocessor.remove_cell_tags='{"hide_code"}'
    c = Config()
    c.TagRemovePreprocessor.remove_cell_tags = remove_cell_tags
    c.TagRemovePreprocessor.remove_all_outputs_tags = remove_all_outputs_tags
    c.TagRemovePreprocessor.remove_input_tags = remove_input_tags

    c.PDFExporter.preprocessors = ["nbconvert.preprocessors.TagRemovePreprocessor"]
    # c.PDFExporter.exclude_input_prompt = True
    # c.PDFExporter.exclude_output_prompt = True
    # c.PDFExporter.exclude_input = True

    log.info('Converting to %s', 'pdf' if pdf else 'latex')

    exporter = MyLatexPDFExporter(config=c) if pdf else MyLatexExporter(config=c)
    exporter.register_preprocessor(TagRemovePreprocessor(config=c),
                                   enabled=True)

    if template_file is not None:
        exporter.template_file = str(template_file)

    writer = FilesWriter(build_directory=str(output_file.parent))
    output, resources = exporter.from_notebook_node(combined_nb, resources)
    writer.write(output, resources, notebook_name=output_file.stem)


def combine_and_convert(source_dir: Path,
                        output_file: Path,
                        pdf=False,
                        template_file=None,
                        files_pattern: str = '*-*.ipynb'):
    """
    files_pattern: which files to import (defaults to *-*.ipynb).
    source_dir: Source directory or (".").
    """
    notebook_files = sorted(source_dir.glob(files_pattern))
    combined_nb = combine_notebooks(notebook_files)
    # Can remove cells.
    # remove_cell_tags: tuple = ('hidden', 'remove_cell'),
    # remove_all_outputs_tags: tuple = ('hidden', 'remove_output'),
    # remove_input_tags: tuple = ('hidden', 'remove_input'),):
    export(combined_nb, output_file, pdf=pdf, template_file=template_file)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Convert a set of notebooks to PDF via Latex')
    ap.add_argument('source_dir', nargs='?', type=Path, default='.',
                    help='Directory containing the .ipynb files')
    ap.add_argument('--output-file', type=Path, default='combined',
                    help='Base name of the output file.')
    ap.add_argument('--pdf', action='store_true',
                    help='Run Latex to convert to PDF.')
    ap.add_argument('--template', type=Path,
                    help='Latex template file to use for nbconvert.')
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    combine_and_convert(args.source_dir, args.output_file, args.pdf, args.template)


if __name__ == '__main__':
    main()
