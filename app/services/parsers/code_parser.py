from pathlib import Path
from typing import Dict, Any
from app.services.parsers.base_parser import BaseParser

class CodeParser(BaseParser):
    def parse(self, file_path: str) -> Dict[str, Any]:
        p = Path(file_path)
        ext = p.suffix.lower().replace('.', '')

        try:
            # Baca dengan berbagai fallback encoding
            content = ""
            for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            lines = content.splitlines()
            line_count = len(lines)
            non_empty_lines = len([l for l in lines if l.strip()])

            summary = f"Berkas kode/teks (.{ext}) memuat {line_count} baris kode ({non_empty_lines} baris aktif)."

            formatted_content = (
                f"=== BERKAS KODE PROGRAM: {p.name} ===\n"
                f"Bahasa / Ekstensi: .{ext}\n"
                f"Total Baris: {line_count}\n\n"
                f"{content[:20000]}" # Maksimal 20.000 karakter awal untuk keamanan konteks
            )

            return {
                'success': True,
                'summary': summary,
                'extracted_content': formatted_content,
                'metadata': {
                    'type': 'code',
                    'language': ext,
                    'line_count': line_count,
                    'non_empty_lines': non_empty_lines
                },
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'summary': f"Gagal membaca source code: {str(e)}",
                'extracted_content': '',
                'metadata': {'type': 'code', 'error': str(e)},
                'error': str(e)
            }
