import os
import zipfile
from pathlib import Path
from typing import Dict, Any
from app.services.parsers.excel_parser import ExcelParser
from app.services.parsers.doc_parser import DocumentParser
from app.services.parsers.scratch_parser import ScratchParser
from app.services.parsers.code_parser import CodeParser
from app.services.parsers.image_parser import ImageParser

class FileParserManager:
    def __init__(self):
        self.excel_parser = ExcelParser()
        self.doc_parser = DocumentParser()
        self.scratch_parser = ScratchParser()
        self.code_parser = CodeParser()
        self.image_parser = ImageParser()

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Mendeteksi ekstensi dan mendelegasikan ke parser yang sesuai.
        Mendukung ZIP yang berisi materi multi-berkas.
        """
        p = Path(file_path)
        ext = p.suffix.lower().replace('.', '')

        if ext in ['xlsx', 'xls', 'csv', 'xlsm']:
            res = self.excel_parser.parse(file_path)
        elif ext in ['pdf', 'docx', 'doc', 'pptx', 'ppt']:
            res = self.doc_parser.parse(file_path)
        elif ext in ['sb3', 'sb']:
            res = self.scratch_parser.parse(file_path)
        elif ext in ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'svg']:
            res = self.image_parser.parse(file_path)
        elif ext in ['cpp', 'c', 'pas', 'py', 'java', 'js', 'html', 'css', 'txt', 'sql', 'json', 'xml']:
            res = self.code_parser.parse(file_path)
        elif ext in ['zip', 'rar', '7z', 'tar', 'gz']:
            res = self._parse_zip_archive(file_path) if ext == 'zip' else {
                'success': True,
                'summary': f"Berkas arsip proyek kompresi (.{ext}).",
                'extracted_content': f"=== ARSIP PROYEK GURU: {p.name} ===\nTipe: Arsip {ext.upper()}\nUkuran: {os.path.getsize(file_path) / (1024*1024):.2f} MB",
                'metadata': {'type': 'archive', 'extension': ext},
                'error': None
            }
        elif ext in ['mp4', 'avi', 'mov', 'mkv', 'webm', 'wmv', 'flv']:
            # Penanganan khusus berkas video proyek rekaman desktop (Scratch/Presentasi)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            res = {
                'success': True,
                'summary': f"Berkas Video Rekaman Proyek (.{ext}), Ukuran: {size_mb:.2f} MB.",
                'extracted_content': (
                    f"=== BERKAS VIDEO REKAMAN PROYEK GURU ===\n"
                    f"Nama Berkas: {p.name}\n"
                    f"Format: Video .{ext.upper()}\n"
                    f"Ukuran Berkas: {size_mb:.2f} MB\n"
                    f"Status: Berkas video berhasil diunggah dan tersimpan siap untuk verifikasi dan penilaian asesor."
                ),
                'metadata': {'type': 'video', 'extension': ext, 'size_mb': round(size_mb, 2)},
                'error': None
            }
        else:
            # Fallback otomatis untuk semua format berkas lainnya
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            res = {
                'success': True,
                'summary': f"Berkas proyek (.{ext}), Ukuran: {size_mb:.2f} MB.",
                'extracted_content': (
                    f"=== BERKAS PROYEK GURU: {p.name} ===\n"
                    f"Ekstensi Berkas: .{ext}\n"
                    f"Ukuran Berkas: {size_mb:.2f} MB\n"
                    f"Status: Berkas terunggah dan tersimpan aman di server penyimpanan."
                ),
                'metadata': {'type': 'generic_file', 'extension': ext, 'size_mb': round(size_mb, 2)},
                'error': None
            }

        if isinstance(res, dict) and 'metadata' in res and isinstance(res['metadata'], dict):
            res['metadata']['extension'] = ext
            res['metadata']['filename'] = p.name

        return res

    def _parse_zip_archive(self, file_path: str) -> Dict[str, Any]:
        try:
            if not zipfile.is_zipfile(file_path):
                return {
                    'success': False,
                    'summary': "Berkas ZIP rusak atau tidak valid.",
                    'extracted_content': '',
                    'metadata': {'type': 'zip'},
                    'error': "Bukan ZIP valid"
                }

            with zipfile.ZipFile(file_path, 'r') as zf:
                namelist = [n for n in zf.namelist() if not n.startswith('__MACOSX') and not n.endswith('/')]
                total_files = len(namelist)
                
                # Cek apakah ini sebenarnya Scratch .sb3 yang dinamai .zip
                if 'project.json' in namelist:
                    res = self.scratch_parser.parse(file_path)
                    res['summary'] = "[Arsip ZIP Scratch] " + res.get('summary', '')
                    return res

                # Daftar ekstensi yang ada di dalam ZIP
                sub_extensions = list(set([Path(n).suffix.lower() for n in namelist]))
                
                extracted_content = (
                    f"=== ARSIP ZIP PROYEK GURU ===\n"
                    f"Total Berkas di dalam Arsip: {total_files}\n"
                    f"Tipe Berkas yang Ditemukan: {', '.join(sub_extensions)}\n\n"
                    f"Daftar Berkas Lengkap:\n"
                )
                for fname in namelist[:20]:
                    extracted_content += f" - {fname}\n"
                if total_files > 20:
                    extracted_content += f" - ... dan {total_files - 20} berkas lainnya.\n"

                summary = (
                    f"Arsip ZIP berisi {total_files} berkas proyek "
                    f"dengan tipe format: {', '.join(sub_extensions[:6])}."
                )

                return {
                    'success': True,
                    'summary': summary,
                    'extracted_content': extracted_content,
                    'metadata': {
                        'type': 'zip',
                        'total_files': total_files,
                        'contained_extensions': sub_extensions,
                        'file_list': namelist[:20]
                    },
                    'error': None
                }
        except Exception as e:
            return {
                'success': False,
                'summary': f"Gagal membaca arsip ZIP: {str(e)}",
                'extracted_content': '',
                'metadata': {'type': 'zip'},
                'error': str(e)
            }
