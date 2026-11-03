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
        elif ext in ['sb3', 'sb2', 'sb']:
            res = self.scratch_parser.parse(file_path)
        elif ext == 'aia':
            res = self._parse_app_inventor_aia(file_path)
        elif ext == 'apk':
            # Parser Khusus Paket Aplikasi Android
            res = self._parse_android_apk(file_path)
        elif ext in ['blend', 'blend1', 'blend2']:
            # Parser Khusus Blender 3D Project & Backup
            res = self._parse_blender_project(file_path)
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
    def _parse_app_inventor_aia(self, file_path: str) -> Dict[str, Any]:
        """
        Membedah berkas proyek MIT App Inventor (.aia)
        """
        try:
            if not zipfile.is_zipfile(file_path):
                return {'success': False, 'summary': "Berkas .aia bukan arsip App Inventor valid.", 'extracted_content': '', 'metadata': {'type': 'aia'}, 'error': 'Bukan zip valid'}

            with zipfile.ZipFile(file_path, 'r') as zf:
                namelist = zf.namelist()
                screens = [Path(n).stem for n in namelist if n.endswith('.scm')]
                block_files = [n for n in namelist if n.endswith('.bky')]
                assets = [n for n in namelist if '/assets/' in n and not n.endswith('/')]

            total_screens = len(screens)
            total_blocks = len(block_files)

            content = (
                f"=== PROYEK MIT APP INVENTOR (.AIA) ===\n"
                f"Nama Berkas: {Path(file_path).name}\n"
                f"Jumlah Layar (Screens): {total_screens} ({', '.join(screens) if screens else 'Tidak ada'})\n"
                f"Jumlah Modul Blok Logika: {total_blocks}\n"
                f"Jumlah Aset Media: {len(assets)}\n"
                f"Status: Proyek aplikasi mobile berhasil diverifikasi."
            )

            return {
                'success': True,
                'summary': f"Proyek App Inventor: {total_screens} Layar, {total_blocks} Modul Blok, {len(assets)} Aset.",
                'extracted_content': content,
                'metadata': {
                    'type': 'app_inventor',
                    'extension': 'aia',
                    'total_screens': total_screens,
                    'screens': screens,
                    'total_blocks': total_blocks,
                    'total_assets': len(assets)
                },
                'error': None
            }
        except Exception as e:
            return {'success': False, 'summary': f"Gagal membaca .aia: {str(e)}", 'extracted_content': '', 'metadata': {'type': 'aia'}, 'error': str(e)}

    def _parse_blender_project(self, file_path: str) -> Dict[str, Any]:
        """Membaca header dan validasi proyek Blender 3D (.blend)"""
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            with open(file_path, 'rb') as f:
                header = f.read(12)

            # Validasi Magic Header Blender resmi (BLENDER_v... atau BLENDER-v...)
            is_valid_blend = header.startswith(b'BLENDER')
            version_str = "Tidak diketahui"
            if is_valid_blend and len(header) >= 12:
                version_raw = header[9:12].decode('ascii', errors='ignore')
                version_str = f"v{version_raw[0]}.{version_raw[1:]}" if len(version_raw) == 3 else "Standar"

            content = (
                f"=== BERKAS PROYEK BLENDER 3D (.BLEND) ===\n"
                f"Nama Berkas: {Path(file_path).name}\n"
                f"Validasi Format: {'Resmi Blender Binary File' if is_valid_blend else 'Header Tidak Valid'}\n"
                f"Versi Blender: {version_str}\n"
                f"Ukuran Berkas: {size_mb:.2f} MB\n"
                f"Status: Proyek 3D Modeling/Animasi terverifikasi."
            )

            return {
                'success': True,
                'summary': f"Proyek Blender 3D ({version_str}), Ukuran: {size_mb:.2f} MB.",
                'extracted_content': content,
                'metadata': {
                    'type': 'blender_3d',
                    'extension': Path(file_path).suffix.lower().replace('.', ''),
                    'is_valid_header': is_valid_blend,
                    'blender_version': version_str,
                    'size_mb': round(size_mb, 2)
                },
                'error': None
            }
        except Exception as e:
            return {'success': False, 'summary': f"Gagal membaca file Blender: {str(e)}", 'extracted_content': '', 'metadata': {'type': 'blender_3d'}, 'error': str(e)}

    def _parse_android_apk(self, file_path: str) -> Dict[str, Any]:
        """Membaca validasi paket aplikasi Android (.apk)"""
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            is_valid_apk = False
            has_dex = False

            if zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zf:
                    namelist = zf.namelist()
                    is_valid_apk = 'AndroidManifest.xml' in namelist
                    has_dex = any(n.endswith('.dex') for n in namelist)

            content = (
                f"=== PAKET APLIKASI ANDROID (.APK) ===\n"
                f"Nama Berkas: {Path(file_path).name}\n"
                f"Validasi Paket: {'Paket Android APK Sah (AndroidManifest terdeteksi)' if is_valid_apk else 'Arsip APK Tidak Utuh'}\n"
                f"Kode Terkompilasi: {'Tersedia (.dex aktif)' if has_dex else 'Tidak ditemukan'}\n"
                f"Ukuran Berkas: {size_mb:.2f} MB"
            )

            return {
                'success': True,
                'summary': f"Aplikasi Android (.apk), Ukuran: {size_mb:.2f} MB, Valid: {is_valid_apk}.",
                'extracted_content': content,
                'metadata': {
                    'type': 'android_apk',
                    'extension': 'apk',
                    'is_valid_apk': is_valid_apk,
                    'has_dex': has_dex,
                    'size_mb': round(size_mb, 2)
                },
                'error': None
            }
        except Exception as e:
            return {'success': False, 'summary': f"Gagal membaca APK: {str(e)}", 'extracted_content': '', 'metadata': {'type': 'android_apk'}, 'error': str(e)}
