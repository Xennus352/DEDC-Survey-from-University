"""Inspect question structure without exporting filled-in survey answers.

Usage: uv run python scripts/inspect_survey_workbook.py /path/to/workbook.xlsx
This is an audit tool, not the administrator import endpoint.
"""

import hashlib
import json
from pathlib import Path
import posixpath
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

S = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'


def inspect_workbook(path):
    raw = Path(path).read_bytes()
    result = {'sha256': hashlib.sha256(raw).hexdigest(), 'sheets': []}
    with ZipFile(path) as archive:
        if sum(info.file_size for info in archive.infolist()) > 50_000_000:
            raise ValueError('Workbook exceeds the audit size limit.')

        def xml(name):
            content = archive.read(name)
            if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
                raise ValueError('XML declarations with entities are unsupported.')
            return ET.fromstring(content)

        shared = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            shared = [''.join(t.text or '' for t in item.findall('.//s:t', S))
                      for item in xml('xl/sharedStrings.xml').findall('s:si', S)]
        relations = {item.get('Id'): item.get('Target')
                     for item in xml('xl/_rels/workbook.xml.rels')
                     if item.get('TargetMode') != 'External'}
        for sheet in xml('xl/workbook.xml').findall('s:sheets/s:sheet', S):
            target = relations[sheet.get(R)]
            name = posixpath.normpath(posixpath.join('xl', target))
            if target.startswith('/'):
                name = target.lstrip('/')
            if not name.startswith('xl/worksheets/'):
                raise ValueError('Unexpected worksheet relationship.')
            root = xml(name)
            rows = {}
            for row in root.findall('s:sheetData/s:row', S):
                values = {}
                for cell in row.findall('s:c', S):
                    value = cell.find('s:v', S)
                    text = value.text if value is not None else ''.join(t.text or '' for t in cell.findall('.//s:t', S))
                    if cell.get('t') == 's':
                        text = shared[int(text)]
                    if text:
                        values[cell.get('r')] = {'text': text, 'style': cell.get('s', '0')}
                rows[int(row.get('r'))] = values
            sections, questions = [], []
            for number, cells in rows.items():
                identifier = cells.get(f'A{number}', {}).get('text', '')
                label = cells.get(f'B{number}', {}).get('text')
                if identifier.isdigit() and label:
                    questions.append({'number': identifier, 'label': label, 'cell': f'B{number}',
                                      'style': cells[f'B{number}']['style'],
                                      'section': len(sections)})
                elif number > 4 and identifier:
                    sections.append({'label': identifier, 'cell': f'A{number}'})
            result['sheets'].append({
                'name': sheet.get('name'), 'dimension': root.find('s:dimension', S).get('ref'),
                'headers': {cell: value['text'] for cell, value in rows.get(4, {}).items()},
                'sections': sections, 'questions': questions,
                'merged_ranges': [m.get('ref') for m in root.findall('s:mergeCells/s:mergeCell', S)],
                'validation_count': len(root.findall('s:dataValidations/s:dataValidation', S)),
                'formula_count': len(root.findall('.//s:f', S)),
                'table_count': len(root.findall('s:tableParts/s:tablePart', S)),
            })
    return result


if __name__ == '__main__':
    print(json.dumps(inspect_workbook(sys.argv[1]), ensure_ascii=False, indent=2))
