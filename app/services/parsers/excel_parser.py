import csv
from pathlib import Path
from typing import Dict, Any, List
import openpyxl
from app.services.parsers.base_parser import BaseParser

class ExcelParser(BaseParser):
    def parse(self, file_path: str) -> Dict[str, Any]:
        p = Path(file_path)
        ext = p.suffix.lower()

        if ext == '.csv':
            return self._parse_csv(file_path)
        else:
            return self._parse_openpyxl(file_path)

    def _parse_openpyxl(self, file_path: str) -> Dict[str, Any]:
        try:
            # Buka workbook tanpa data_only agar formula asli terbaca
            wb = openpyxl.load_workbook(file_path, data_only=False)
            sheet_names = wb.sheetnames

            all_formulas = []
            formula_types = set()
            sheet_summaries = []
            extracted_text_blocks = []

            total_non_empty_cells = 0

            for sheet_name in sheet_names:
                ws = wb[sheet_name]
                sheet_formulas = []
                row_count = 0
                sample_rows = []

                for row_idx, row in enumerate(ws.iter_rows(values_only=False), start=1):
                    row_values = []
                    has_val = False
                    for col_idx, cell in enumerate(row, start=1):
                        val = cell.value
                        if val is not None:
                            has_val = True
                            total_non_empty_cells += 1
                            val_str = str(val).strip()

                            # Deteksi Formula Excel (dimulai dengan '=')
                            if val_str.startswith('='):
                                formula_clean = val_str.upper()
                                sheet_formulas.append({
                                    'cell': cell.coordinate,
                                    'formula': val_str
                                })
                                all_formulas.append(f"{sheet_name}!{cell.coordinate}: {val_str}")
                                
                                # Deteksi jenis fungsi (SUM, IF, VLOOKUP, AVERAGE, dll)
                                for func in ['VLOOKUP', 'HLOOKUP', 'INDEX', 'MATCH', 'XLOOKUP', 'IF', 'SUM', 'AVERAGE', 'COUNT', 'COUNTA', 'MAX', 'MIN', 'CONCATENATE', 'LEFT', 'RIGHT', 'MID']:
                                    if func in formula_clean:
                                        formula_types.add(func)

                            row_values.append(val_str)
                        else:
                            row_values.append('')

                    if has_val:
                        row_count += 1
                        if len(sample_rows) < 15: # Ambil sampel 15 baris pertama per sheet
                            sample_rows.append(f"Baris {row_idx}: " + " | ".join([v for v in row_values if v][:8]))

                sheet_summaries.append(
                    f"Sheet '{sheet_name}': {row_count} baris aktif, {len(sheet_formulas)} formula terdeteksi."
                )

                block_content = f"=== LEMBAR KERJA: {sheet_name} ===\n"
                if sheet_formulas:
                    block_content += "Daftar Formula Digunakan:\n"
                    for sf in sheet_formulas[:25]:
                        block_content += f" - Sel {sf['cell']}: {sf['formula']}\n"
                    if len(sheet_formulas) > 25:
                        block_content += f" - ... dan {len(sheet_formulas) - 25} formula lainnya.\n"
                else:
                    block_content += "Tidak ditemukan formula '=' pada sheet ini.\n"

                block_content += "\nContoh Sampel Data Baris:\n"
                block_content += "\n".join(sample_rows[:10])
                extracted_text_blocks.append(block_content)

            summary = (
                f"Workbook Excel berisi {len(sheet_names)} sheet ({', '.join(sheet_names)}). "
                f"Ditemukan total {len(all_formulas)} sel formula aktif dengan fungsi: {', '.join(sorted(list(formula_types))) or 'Dasar'}."
            )

            full_extracted = "\n\n".join(extracted_text_blocks)

            return {
                'success': True,
                'summary': summary,
                'extracted_content': full_extracted,
                'metadata': {
                    'type': 'xlsx',
                    'sheets_count': len(sheet_names),
                    'sheet_names': sheet_names,
                    'total_formulas': len(all_formulas),
                    'detected_functions': list(formula_types),
                    'total_cells_filled': total_non_empty_cells
                },
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'summary': f"Gagal membaca berkas Excel: {str(e)}",
                'extracted_content': '',
                'metadata': {'type': 'xlsx', 'error': str(e)},
                'error': str(e)
            }

    def _parse_csv(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, mode='r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.reader(f)
                rows = list(reader)

            row_count = len(rows)
            col_count = len(rows[0]) if rows else 0
            sample = [" | ".join(r[:8]) for r in rows[:15]]

            summary = f"Berkas CSV dengan {row_count} baris dan {col_count} kolom data."
            extracted = f"=== BERKAS CSV ===\nTotal Baris: {row_count}\n\nSampel Data:\n" + "\n".join(sample)

            return {
                'success': True,
                'summary': summary,
                'extracted_content': extracted,
                'metadata': {
                    'type': 'csv',
                    'rows_count': row_count,
                    'columns_count': col_count
                },
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'summary': f"Gagal membaca CSV: {str(e)}",
                'extracted_content': '',
                'metadata': {'type': 'csv'},
                'error': str(e)
            }
