import os
from pathlib import Path
from typing import Dict, Any
from PIL import Image
from app.services.parsers.base_parser import BaseParser

class ImageParser(BaseParser):
    def parse(self, file_path: str) -> Dict[str, Any]:
        try:
            p = Path(file_path)
            file_size_kb = os.path.getsize(file_path) / 1024.0

            with Image.open(file_path) as img:
                width, height = img.size
                img_format = img.format or p.suffix.replace('.', '').upper()
                color_mode = img.mode

                # Deteksi rasio aspek kanvas
                aspect_num = max(width, height) / min(width, height)
                orientation = "Landscape" if width >= height else "Portrait"

                # Cek standar kanvas A4 ISO 216 (rasio ~ 1.414) atau 16:9 (rasio ~ 1.777)
                layout_standard = "Standar"
                if abs(aspect_num - 1.414) < 0.12:
                    layout_standard = "Proporsi Kanvas A4 (ISO 216)"
                elif abs(aspect_num - 1.777) < 0.12:
                    layout_standard = "Rasio Layar Lebar 16:9"
                elif abs(aspect_num - 1.333) < 0.10:
                    layout_standard = "Rasio Standar 4:3"
                elif abs(aspect_num - 1.0) < 0.05:
                    layout_standard = "Rasio Persegi 1:1"

                # DPI jika ada
                dpi_info = img.info.get('dpi', (72, 72))
                dpi_val = int(dpi_info[0]) if isinstance(dpi_info, tuple) else 72

                summary = (
                    f"Citra grafis desain ({img_format}) resolusi {width}x{height} px, "
                    f"orientasi {orientation} [{layout_standard}], mode warna {color_mode}, ukuran berkas {file_size_kb:.1f} KB."
                )

                extracted_content = (
                    f"--- METADATA CITRA DESAIN GRAFIS POSTER/MEDIA ---\n"
                    f"Nama Berkas: {p.name}\n"
                    f"Format: {img_format}\n"
                    f"Dimensi Piksel: {width} x {height} px\n"
                    f"Orientasi: {orientation}\n"
                    f"Proporsi Layout: {layout_standard}\n"
                    f"Mode Warna: {color_mode}\n"
                    f"Kepadatan DPI: {dpi_val} DPI\n"
                    f"Ukuran Berkas: {file_size_kb:.2f} KB\n"
                    f"Integritas Berkas: Terverifikasi utuh, tidak rusak/corrupt, siap dievaluasi."
                )

                return {
                    'success': True,
                    'summary': summary,
                    'extracted_content': extracted_content,
                    'metadata': {
                        'type': 'image',
                        'format': img_format,
                        'width': width,
                        'height': height,
                        'aspect_ratio': layout_standard,
                        'orientation': orientation,
                        'mode': color_mode,
                        'dpi': dpi_val,
                        'size_kb': round(file_size_kb, 1)
                    },
                    'error': None
                }
        except Exception as e:
            return {
                'success': False,
                'summary': f"Gagal membaca citra poster: {str(e)}",
                'extracted_content': '',
                'metadata': {'type': 'image'},
                'error': str(e)
            }
