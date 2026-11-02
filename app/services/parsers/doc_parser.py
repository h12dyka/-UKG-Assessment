import os
from pathlib import Path
from typing import Dict, Any
import docx
import pypdf
from pptx import Presentation
from app.services.parsers.base_parser import BaseParser

class DocumentParser(BaseParser):
    def parse(self, file_path: str) -> Dict[str, Any]:
        ext = Path(file_path).suffix.lower()

        if ext in ['.pptx', '.ppt']:
            return self._parse_pptx(file_path)
        elif ext in ['.docx', '.doc']:
            return self._parse_docx(file_path)
        elif ext == '.pdf':
            return self._parse_pdf(file_path)
        else:
            return {
                'success': False,
                'summary': f"Format dokumen '{ext}' tidak dikenali oleh DocumentParser.",
                'extracted_content': '',
                'metadata': {},
                'error': f"Format tidak didukung: {ext}"
            }

    def _parse_pptx(self, file_path: str) -> Dict[str, Any]:
        try:
            prs = Presentation(file_path)
            slide_count = len(prs.slides)
            extracted_slides = []
            total_shapes = 0
            has_media = False

            # Cek rasio aspek slide (16:9 vs 4:3)
            slide_width = prs.slide_width
            slide_height = prs.slide_height
            ratio_val = slide_width / slide_height if slide_height else 1.33
            aspect_ratio_str = "16:9 (Widescreen)" if abs(ratio_val - 1.777) < 0.15 else "4:3 (Standar)"

            for idx, slide in enumerate(prs.slides, start=1):
                slide_texts = []
                shapes_count = len(slide.shapes)
                total_shapes += shapes_count

                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for paragraph in shape.text_frame.paragraphs:
                            txt = paragraph.text.strip()
                            if txt:
                                slide_texts.append(txt)
                    # Cek keberadaan tabel
                    if shape.has_table:
                        for row in shape.table.rows:
                            row_txt = [c.text.strip() for c in row.cells if c.text.strip()]
                            if row_txt:
                                slide_texts.append(" | ".join(row_txt))
                    # Cek media / movie / audio
                    if shape.shape_type in [16, 14]: # media / placeholder
                        has_media = True

                slide_content = f"--- SLIDE {idx} (Shapes: {shapes_count}) ---\n"
                if slide_texts:
                    slide_content += "\n".join(slide_texts)
                else:
                    slide_content += "[Slide ini memuat elemen grafis/gambar tanpa teks eksplisit]"
                extracted_slides.append(slide_content)

            summary = (
                f"Presentasi PowerPoint berisi {slide_count} slide dengan format rasio {aspect_ratio_str}. "
                f"Memuat {total_shapes} elemen bentuk/grafis visual."
            )

            full_extracted = "\n\n".join(extracted_slides)

            return {
                'success': True,
                'summary': summary,
                'extracted_content': full_extracted,
                'metadata': {
                    'type': 'pptx',
                    'total_slides': slide_count,
                    'total_shapes': total_shapes,
                    'aspect_ratio': aspect_ratio_str,
                    'has_multimedia_hints': has_media
                },
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'summary': f"Gagal membaca presentasi PPTX: {str(e)}",
                'extracted_content': '',
                'metadata': {'type': 'pptx', 'error': str(e)},
                'error': str(e)
            }

    def _parse_docx(self, file_path: str) -> Dict[str, Any]:
        try:
            doc = docx.Document(file_path)
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            
            # Ekstrak teks tabel jika ada
            table_texts = []
            for t in doc.tables:
                for row in t.rows:
                    row_txt = [c.text.strip() for c in row.cells if c.text.strip()]
                    if row_txt:
                        table_texts.append(" | ".join(row_txt))

            full_text = "\n\n".join(paragraphs)
            if table_texts:
                full_text += "\n\n--- TABEL DOKUMEN ---\n" + "\n".join(table_texts)

            word_count = len(full_text.split())
            summary = f"Dokumen Word memuat {len(paragraphs)} paragraf dan {len(doc.tables)} tabel (~{word_count} kata)."

            return {
                'success': True,
                'summary': summary,
                'extracted_content': full_text,
                'metadata': {
                    'type': 'docx',
                    'paragraphs_count': len(paragraphs),
                    'tables_count': len(doc.tables),
                    'word_count': word_count
                },
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'summary': f"Gagal membaca berkas DOCX: {str(e)}",
                'extracted_content': '',
                'metadata': {'type': 'docx'},
                'error': str(e)
            }

    def _parse_pdf(self, file_path: str) -> Dict[str, Any]:
        try:
            reader = pypdf.PdfReader(file_path)
            page_count = len(reader.pages)
            extracted_pages = []

            for idx, page in enumerate(reader.pages, start=1):
                txt = page.extract_text() or ''
                extracted_pages.append(f"--- HALAMAN {idx} ---\n{txt.strip()}")

            full_text = "\n\n".join(extracted_pages)
            word_count = len(full_text.split())
            summary = f"Dokumen PDF memuat {page_count} halaman (~{word_count} kata)."

            return {
                'success': True,
                'summary': summary,
                'extracted_content': full_text,
                'metadata': {
                    'type': 'pdf',
                    'pages_count': page_count,
                    'word_count': word_count
                },
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'summary': f"Gagal membaca PDF: {str(e)}",
                'extracted_content': '',
                'metadata': {'type': 'pdf'},
                'error': str(e)
            }
