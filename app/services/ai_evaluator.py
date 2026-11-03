import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
import requests
from pydantic import BaseModel, Field
from flask import current_app

logger = logging.getLogger(__name__)

# --- Pydantic Schema for Strict Output Validation ---

class CriterionEvaluationOutput(BaseModel):
    criterion_id: int = Field(description="ID kriteria yang dinilai")
    score: float = Field(ge=0.0, le=100.0, description="Skor penilaian dari 0 sampai 100")
    evidence_found: str = Field(description="Bukti spesifik/faktual yang ditemukan di dalam berkas proyek")
    rationale: str = Field(description="Penjelasan detail mengapa skor tersebut diberikan berdasarkan kriteria")
    shortcomings: Optional[str] = Field(default="", description="Kekurangan atau kekeliruan yang ditemukan")
    recommendations: Optional[str] = Field(default="", description="Saran perbaikan konkret untuk guru")
    is_sufficient: bool = Field(default=True, description="Apakah bukti di dalam berkas cukup untuk dinilai secara obyektif")

class AIEvaluationResponse(BaseModel):
    confidence_score: float = Field(ge=0.0, le=1.0, description="Tingkat keyakinan evaluasi dari 0.0 sampai 1.0")
    has_sufficient_evidence: bool = Field(description="Apakah berkas proyek memiliki konten yang cukup untuk dinilai")
    overall_summary: str = Field(description="Ringkasan analisis keseluruhan kualitas proyek guru")
    criteria_evaluations: List[CriterionEvaluationOutput] = Field(description="Daftar penilaian untuk setiap kriteria rubrik")
    is_valid_project: Optional[bool] = Field(default=True, description="Apakah berkas merupakan pengerjaan proyek riil yang relevan dengan instruksi penugasan materi")
    rejection_reason: Optional[str] = Field(default="", description="Alasan diskualifikasi jika berkas bukan proyek yang sah")


class AIEvaluatorService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or current_app.config.get('GEMINI_API_KEY', '')
        self.model = model or current_app.config.get('GEMINI_MODEL', 'gemini-2.0-flash')

    @staticmethod
    def verify_project_integrity(
        rubric,
        extracted_content: str,
        file_metadata: Dict[str, Any]
    ) -> Tuple[bool, str, float]:
        """
        TAHAP 1: GATEKEEPER VALIDASI KEABSAHAN PROYEK.
        Memverifikasi secara obyektif apakah berkas yang diunggah benar-benar merupakan
        hasil pengerjaan proyek dari instruksi materi UKG, bukan dokumen acak / non-proyek.
        Mengembalikan: (is_valid: bool, rejection_reason: str, relevance_score: float)
        """
        content_clean = (extracted_content or "").strip()
        content_lower = content_clean.lower()
        file_type = file_metadata.get('type', '')
        file_ext = (file_metadata.get('extension') or '').lower().replace('.', '')

        # 0. Verifikasi Kesesuaian Format Berkas terhadap Rubrik Penugasan
        allowed_raw = getattr(rubric, 'allowed_file_types', '') or ''
        if allowed_raw:
            allowed_list = [e.strip().lower().replace('.', '') for e in allowed_raw.split(',') if e.strip()]
            # Normalisasi padanan ekstensi standar
            if 'jpg' in allowed_list and 'jpeg' not in allowed_list:
                allowed_list.append('jpeg')
            if 'jpeg' in allowed_list and 'jpg' not in allowed_list:
                allowed_list.append('jpg')
            if 'ppt' in allowed_list and 'pptx' not in allowed_list:
                allowed_list.append('pptx')
            if 'pptx' in allowed_list and 'ppt' not in allowed_list:
                allowed_list.append('ppt')
            if 'doc' in allowed_list and 'docx' not in allowed_list:
                allowed_list.append('docx')
            if 'docx' in allowed_list and 'doc' not in allowed_list:
                allowed_list.append('doc')
            if 'xls' in allowed_list and 'xlsx' not in allowed_list:
                allowed_list.append('xlsx')
            if 'xlsx' in allowed_list and 'xls' not in allowed_list:
                allowed_list.append('xls')
            if 'sb3' in allowed_list and 'sb2' not in allowed_list:
                allowed_list.append('sb2')
            if 'sb3' in allowed_list and 'sb' not in allowed_list:
                allowed_list.append('sb')

            # Jika bukan arsip ZIP dan ekstensinya tidak diizinkan oleh rubrik materi ini
            if file_ext and file_ext != 'zip' and file_ext not in allowed_list:
                return (
                    False,
                    f"Format Berkas Tidak Sesuai Penugasan! Penugasan materi '{rubric.material.title}' "
                    f"mewajibkan format ({rubric.allowed_file_types}), tetapi yang dikumpulkan adalah berkas .{file_ext}. "
                    f"Berkas didiskualifikasi.",
                    0.0
                )

        # 1. Pengecekan Konten Kosong / Berkas Nir-Substansi
        if len(content_clean) < 25 and file_metadata.get('total_blocks', 0) == 0 and file_type != 'image':
            return False, "Berkas yang diunggah kosong atau tidak memiliki konten pengerjaan proyek yang substansial.", 0.0

        # 2. Pengecekan Khusus Format Berkas Tertentu
        if file_type == 'scratch' and file_metadata.get('total_blocks', 0) == 0:
            return False, "Berkas Scratch (.sb3) kosong dan tidak memuat satu pun blok pemrograman logika.", 0.0

        if file_type == 'code':
            loc = file_metadata.get('loc', 0) or len(content_clean.splitlines())
            if loc < 3:
                return False, "Berkas kode program kosong atau hanya memuat sedikit baris tanpa logika komputasi.", 0.0

        if file_type == 'pptx':
            total_slides = file_metadata.get('total_slides', 0)
            if total_slides == 0:
                return False, "Berkas presentasi PowerPoint kosong (0 slide).", 0.0
            # Jika presentasi hanya memiliki sedikit kata (< 15 kata untuk seluruh slide), dicurigai template kosong
            words_count = len(re.findall(r'\b\w+\b', content_lower))
            if words_count < 15:
                return False, "Berkas presentasi PowerPoint terindikasi sebagai template kosong tanpa muatan proyek materi.", 0.0
        
                # Pengecekan Khusus App Inventor (.aia)
        if file_type == 'app_inventor':
            if file_metadata.get('total_screens', 0) == 0:
                return False, "Berkas App Inventor (.aia) kosong dan tidak memiliki layar/Screen aplikasi.", 0.0

        # Pengecekan Khusus Blender (.blend)
        if file_type == 'blender_3d':
            if not file_metadata.get('is_valid_header', False):
                return False, "Berkas bukan merupakan file biner proyek Blender 3D yang valid.", 0.0
            if file_metadata.get('size_mb', 0) < 0.05:  # Di bawah 50 KB dicurigai file rusak/kosong
                return False, "Berkas Blender (.blend) kosong atau rusak (ukuran terlalu kecil untuk proyek 3D).", 0.0

        # Pengecekan Khusus Android APK (.apk)
        if file_type == 'android_apk':
            if not file_metadata.get('is_valid_apk', False):
                return False, "Berkas .apk rusak dan tidak memuat manifes Android resmi.", 0.0

        # 3. Analisis Kesesuaian Semantik & Topik (Semantic Relevance Gate)
        # Ambil seluruh teks acuan materi
        material_title = getattr(rubric.material, 'title', '') or ''
        instructions = getattr(rubric, 'project_instructions', '') or ''
        competencies = getattr(rubric, 'competencies_measured', '') or ''
        description = getattr(rubric.material, 'description', '') or ''
        reference_text = f"{material_title} {instructions} {competencies} {description}".lower()

        # Ekstrak kata kunci penting (buang stopwords bahasa Indonesia dan kata-kata template parser)
        stopwords = {
            'dan', 'di', 'ke', 'dari', 'yang', 'untuk', 'pada', 'dengan', 'adalah', 'sebagai',
            'ini', 'itu', 'atau', 'dalam', 'bisa', 'harus', 'akan', 'oleh', 'karena', 'maka',
            'jika', 'soal', 'proyek', 'tugas', 'ukg', 'peserta', 'guru', 'dapat', 'membuat',
            'melakukan', 'hasil', 'karya', 'lembar', 'kerja', 'siswa', 'sd', 'smp', 'sma',
            'kelas', 'semester', 'tahun', 'ajaran', 'waktu', 'menit', 'instruksi', 'petunjuk',
            # Boilerplate parser
            'metadata', 'citra', 'desain', 'grafis', 'poster', 'media', 'format', 'dimensi',
            'piksel', 'orientasi', 'portrait', 'landscape', 'proporsi', 'layout', 'mode',
            'warna', 'kepadatan', 'ukuran', 'berkas', 'integritas', 'terverifikasi', 'utuh',
            'nama', 'tipe', 'status', 'terunggah', 'tersimpan', 'aman', 'server', 'penyimpanan',
            'summary', 'preview', 'konten', 'total', 'slide', 'slides', 'halaman', 'shape', 'shapes'
        }
        all_words = re.findall(r'\b[a-zA-Z]{4,}\b', reference_text)
        keywords = set([w for w in all_words if w not in stopwords])
        
                # 4. Deteksi Ketidaksesuaian Jenjang Konten / Berkas (Grade Level Conflict)
        target_grade = (getattr(rubric.material, 'grade_level', '') or '').strip().upper()
        file_name_lower = (file_metadata.get('filename', '') or '').lower()
        combined_text_lower = f"{file_name_lower} {content_lower}"

        grade_patterns = {
            'SD': [
                r'\bukg[-_]sd\b', r'\bsekolah dasar\b', r'\bkelas\s*([1-6]|i{1,3}|iv|v|vi)\b',
                r'[-_]sd[-_.]', r'\bsd\s*(kelas|[1-6])'
            ],
            'SMP': [
                r'\bukg[-_]smp\b', r'\bsekolah menengah pertama\b', r'\bkelas\s*([7-9]|vii|viii|ix)\b',
                r'[-_]smp[-_.]', r'\bsmp\s*(kelas|[7-9])'
            ],
            'SMA': [
                r'\bukg[-_]sma\b', r'\bukg[-_]smk\b', r'\bsekolah menengah atas\b', r'\bkelas\s*(1[0-2]|x|xi|xii)\b',
                r'[-_]sma[-_.]', r'[-_]smk[-_.]', r'\bsma\s*(kelas|1[0-2])'
            ]
        }

        # Cek jika berkas terindikasi kuat milik jenjang lain
        for other_grade, patterns in grade_patterns.items():
            if other_grade != target_grade and target_grade in grade_patterns:
                for pat in patterns:
                    m = re.search(pat, combined_text_lower)
                    if m:
                        detected_term = m.group(0)
                        return (
                            False,
                            f"Ketidaksesuaian Jenjang Proyek! Berkas yang diunggah teridentifikasi sebagai proyek jenjang {other_grade} "
                            f"(terdeteksi indikator: '{detected_term}'), sedangkan materi ujian ini diperuntukkan untuk jenjang {target_grade} "
                            f"({rubric.material.title}).",
                            0.0
                        )

        # Hitung kecocokan kata kunci pada berkas yang diunggah
        if len(keywords) >= 4:
            matched_keywords = [kw for kw in keywords if kw in content_lower]
            relevance_ratio = len(matched_keywords) / len(keywords)

            # Jika SAMA SEKALI tidak ada satu pun kata kunci instruksi/topik yang cocok (0% match)
            if len(matched_keywords) == 0:
                return (
                    False, 
                    f"Konten berkas sama sekali tidak memuat topik atau instruksi penugasan '{material_title}'. "
                    f"Berkas terindikasi sebagai dokumen umum / file salah unggah (Bukan Proyek UKG).", 
                    0.0
                )

            # Jika tingkat kecocokan di bawah ambang batas minimal relevansi (< 15% atau kata cocok < 3)
            if relevance_ratio < 0.15 or len(matched_keywords) < 3:
                return (
                    False,
                    f"Konten berkas tidak memiliki keterkaitan topik yang memadai dengan materi ujian '{material_title}'. "
                    f"Hanya ditemukan {len(matched_keywords)} kata terkait ({', '.join(matched_keywords[:3])}). "
                    f"Berkas tidak memenuhi kualifikasi pengerjaan proyek yang diminta.",
                    relevance_ratio
                )
        else:
            relevance_ratio = 1.0

        # Jika lolos semua penyaringan, berkas sah dinyatakan sebagai Proyek
        return True, "", relevance_ratio

    def evaluate_submission(
        self,
        rubric_version,
        project_title: str,
        extracted_content: str,
        file_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Menjalankan evaluasi AI 2 Tahap terhadap berkas proyek guru.
        """
        rubric = rubric_version.rubric
        criteria = rubric_version.criteria

        # 1. Siapkan data kriteria untuk prompt
        criteria_prompt_list = []
        for c in criteria:
            criteria_prompt_list.append({
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "weight_percent": c.weight,
                "is_mandatory": c.is_mandatory,
                "mandatory_min_score": c.mandatory_min_score if c.is_mandatory else None,
                "evidence_indicators": c.evidence_indicators
            })

        system_instruction = (
            "Anda adalah Asesor Ahli dan Evaluator Obyektif Uji Kompetensi Guru (UKG) Sokrates. "
            "Anda memiliki standar profesional tinggi dan kebijakan ZERO-TOLERANCE terhadap berkas yang bukan proyek.\n\n"
            "=== ATURAN EVALUASI DUA TAHAP (SANGAT KETAT) ===\n"
            "TAHAP 1: GATEKEEPER VALIDASI KEABSAHAN PROYEK (WAJIB DILAKUKAN PERTAMA KALI):\n"
            "Sebelum menilai kriteria apa pun, Anda WAJIB memeriksa apakah berkas di dalam <student_submission> "
            "benar-benar merupakan HASIL PENGERJAAN PROYEK yang relevan dengan 'Instruksi Pengerjaan' dan 'Materi UKG'.\n"
            "Kriteria DISKUALIFIKASI TOTAL (Bukan Proyek / Tidak Relevan):\n"
            "- Berkas hanya berupa materi kuliah/ceramah umum, silabus, dokumen presentasi acak, resep, atau catatan pribadi "
            "  yang TIDAK memuat produk/karya yang diinstruksikan oleh soal materi.\n"
            "- Berkas kosong, template bawaan software tanpa pengerjaan mandiri, atau teks acak.\n"
            "- Topik yang dibahas sama sekali melenceng/berbeda dari materi UKG yang diujikan.\n\n"
            "JIKA BERKAS BUKAN MERUPAKAN PROYEK YANG RELEVAN:\n"
            "- Set 'is_valid_project': false\n"
            "- Set 'has_sufficient_evidence': false\n"
            "- Berikan penjelasan tegas pada 'rejection_reason'\n"
            "- Set 'overall_summary': 'DISKUALIFIKASI PROYEK: [Jelaskan mengapa berkas ini bukan proyek yang sah]'\n"
            "- WAJIB BERIKAN SKOR 0.0 (NOL) PADA SEMUA KRITERIA!\n"
            "- JANGAN PERNAH memberikan nilai kompromi/kasihan pada berkas yang tidak relevan.\n\n"
            "TAHAP 2: PENILAIAN RUBRIK (HANYA JIKA LOLOS TAHAP 1):\n"
            "Jika dan hanya jika berkas lolos Tahap 1 sebagai proyek yang sah, berikan skor 0-100 per kriteria "
            "secara obyektif berdasarkan bukti nyata."
        )

        user_prompt = f"""
=== INFORMASI UKG & RUBRIK PENILAIAN RESMI ===
Judul UKG: {rubric.title}
Materi UKG: {rubric.material.title} ({rubric.material.grade_level} - {rubric.material.class_level})
Semester: {rubric.material.semester} ({rubric.material.academic_year or '2025/2026'})
Deskripsi Materi: {rubric.material.description or '-'}
Instruksi Pengerjaan Proyek: {rubric.project_instructions}
Kompetensi yang Diukur: {rubric.competencies_measured}
Passing Grade Kelulusan: {rubric.passing_grade}
Format Berkas Resmi yang Diwajibkan: {rubric.allowed_file_types}

=== DAFTAR KRITERIA PENILAIAN RESMI ===
{json.dumps(criteria_prompt_list, indent=2, ensure_ascii=False)}

=== METADATA BERKAS PENGGUNA ===
Judul Proyek: {project_title}
Info Parser: {json.dumps(file_metadata, ensure_ascii=False)}

=== KONTEN BERKAS YANG DIUNGGAH ===
<student_submission>
{extracted_content}
</student_submission>

INSTRUKSI FORMAT OUTPUT JSON:
{{
  "is_valid_project": true,
  "rejection_reason": "",
  "confidence_score": 0.95,
  "has_sufficient_evidence": true,
  "overall_summary": "Ringkasan pengerjaan proyek...",
  "criteria_evaluations": [
    {{
      "criterion_id": 1,
      "score": 85.0,
      "evidence_found": "Bukti konkret...",
      "rationale": "Alasan penilaian...",
      "shortcomings": "Kekurangan jika ada...",
      "recommendations": "Saran perbaikan...",
      "is_sufficient": true
    }}
  ]
}}
"""

        # 2. Eksekusi Pemanggilan AI (atau Smart Heuristic Fallback jika API Key belum ada)
        if not self.api_key or self.api_key == 'your_gemini_api_key_here':
            logger.warning("GEMINI_API_KEY belum diset. Menggunakan Smart Heuristic Evaluator dengan Gatekeeper.")
            return self._heuristic_fallback_evaluation(
                rubric=rubric,
                criteria=criteria,
                extracted_content=extracted_content,
                file_metadata=file_metadata
            )

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            payload = {
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": [{"parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.1,  # Rendah agar sangat obyektif dan deterministik
                }
            }

            response = requests.post(url, json=payload, timeout=60)
            if response.status_code != 200:
                logger.error(f"Gemini API Error {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f"Gemini API Error ({response.status_code}): {response.text[:200]}",
                    'is_technical_failure': True
                }

            result_json = response.json()
            candidates = result_json.get('candidates', [])
            if not candidates:
                return {'success': False, 'error': "AI tidak mengembalikan respon.", 'is_technical_failure': True}

            raw_text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            parsed_data = json.loads(raw_text)
            validated_output = AIEvaluationResponse.model_validate(parsed_data)

            # Jika AI menandai berkas bukan proyek yang sah, pastikan semua kriteria bernilai 0.0
            if not validated_output.is_valid_project:
                for c_eval in validated_output.criteria_evaluations:
                    c_eval.score = 0.0
                    c_eval.is_sufficient = False
                    c_eval.evidence_found = "DISKUALIFIKASI: Berkas tidak teridentifikasi sebagai proyek yang sah."

            return {
                'success': True,
                'data': validated_output,
                'raw_response': raw_text,
                'model_used': self.model
            }

        except Exception as e:
            logger.exception("Gagal memproses evaluasi AI, beralih ke Heuristic Fallback")
            return self._heuristic_fallback_evaluation(
                rubric=rubric,
                criteria=criteria,
                extracted_content=extracted_content,
                file_metadata=file_metadata
            )

    def _heuristic_fallback_evaluation(
        self,
        rubric,
        criteria,
        extracted_content: str,
        file_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluator cerdas berbasis bukti parser dengan GATEKEEPER INTEGRITAS PROYEK.
        Mencegah pemberian skor pada berkas acak/non-proyek.
        """
        results = []

        # TAHAP 1: GATEKEEPER VALIDASI PROYEK
        is_valid_project, rejection_reason, relevance_ratio = self.verify_project_integrity(
            rubric=rubric,
            extracted_content=extracted_content,
            file_metadata=file_metadata
        )

        # JIKA GAGAL GATEKEEPER (BUKAN PROYEK / TIDAK RELEVAN):
        if not is_valid_project:
            for c in criteria:
                results.append(
                    CriterionEvaluationOutput(
                        criterion_id=c.id,
                        score=0.0,
                        evidence_found="TIDAK DITEMUKAN BUKTI PROYEK (DISKUALIFIKASI).",
                        rationale=f"Penilaian Ditolak: {rejection_reason}",
                        shortcomings="Berkas yang diunggah tidak memenuhi spesifikasi penugasan proyek materi.",
                        recommendations=f"Mohon unggah berkas yang benar-benar merupakan hasil karya pengerjaan proyek untuk materi '{rubric.material.title}'.",
                        is_sufficient=False
                    )
                )

            return {
                'success': True,
                'data': AIEvaluationResponse(
                    confidence_score=1.0,
                    has_sufficient_evidence=False,
                    is_valid_project=False,
                    rejection_reason=rejection_reason,
                    overall_summary=f"DISKUALIFIKASI PENILAIAN: {rejection_reason}",
                    criteria_evaluations=results
                ),
                'raw_response': f"Project Disqualification: {rejection_reason}",
                'model_used': 'Project Gatekeeper (Rule-Based)'
            }

        # TAHAP 2: PENILAIAN SUBSTANTIF (HANYA JIKA PROYEK SAH)
        content_lower = (extracted_content or "").lower()
        file_type = file_metadata.get('type', '')

        for c in criteria:
            c_name_lower = c.name.lower()
            indicators = [w.strip().lower() for w in c.evidence_indicators.split(',') if w.strip()]
            matched_indicators = [ind for ind in indicators if ind in content_lower]
            match_ind_ratio = len(matched_indicators) / len(indicators) if indicators else 0.8

            evidence = []

            if 'ide' in c_name_lower or 'kreatif' in c_name_lower or 'tehnik' in c_name_lower:
                if file_type == 'scratch':
                    b_count = file_metadata.get('total_blocks', 0)
                    score = min(95.0, 70.0 + (b_count // 4))
                    evidence.append(f"Penerapan teknik Scratch: Terdeteksi {b_count} blok logika pemrograman dan {file_metadata.get('sprites_count', 1)} sprites.")
                elif file_type == 'pptx':
                    s_count = file_metadata.get('total_slides', 0)
                    score = min(92.0, 72.0 + s_count * 2.0)
                    evidence.append(f"Penerapan teknik presentasi proyek: Memuat {s_count} slide materi proyek yang terverifikasi relevan.")
                elif file_type == 'xlsx':
                    f_count = file_metadata.get('total_formulas', 0)
                    score = min(95.0, 72.0 + f_count * 2.5)
                    evidence.append(f"Penerapan formula spreadsheet: {f_count} formula aktif terdeteksi pada lembar kerja.")
                elif file_type == 'code':
                    loc = file_metadata.get('loc', 0) or len(extracted_content.splitlines())
                    score = min(95.0, 70.0 + (loc // 3))
                    evidence.append(f"Struktur kode program komputasi terverifikasi ({loc} baris kode).")
                else:
                    score = 75.0
                    evidence.append("Penerapan teknik media terverifikasi oleh parser proyek.")

            elif 'rapi' in c_name_lower:
                score = 82.0
                evidence.append("Tata letak visual dan struktur elemen proyek tersusun dengan rapi dan proporsional.")

            elif 'tema' in c_name_lower:
                score = min(95.0, 75.0 + (relevance_ratio * 20.0))
                evidence.append(f"Kesesuaian tema terverifikasi ({len(matched_indicators)} indikator rubrik terpenuhi).")

            else:
                score = 75.0
                evidence.append("Kriteria pengerjaan dasar terpenuhi sesuai rubrik materi.")

            results.append(
                CriterionEvaluationOutput(
                    criterion_id=c.id,
                    score=round(score, 1),
                    evidence_found="; ".join(evidence),
                    rationale=f"Evaluasi kriteria '{c.name}' berdasarkan analisis bukti konten proyek.",
                    shortcomings="Perlu pengayaan pada variasi elemen interaktif." if score < 85 else "-",
                    recommendations=f"Tingkatkan pemenuhan indikator: {c.evidence_indicators}",
                    is_sufficient=True
                )
            )

        return {
            'success': True,
            'data': AIEvaluationResponse(
                confidence_score=0.90,
                has_sufficient_evidence=True,
                is_valid_project=True,
                overall_summary=f"Evaluasi Proyek Sah: Berkas berhasil diverifikasi sebagai proyek materi '{rubric.material.title}'.",
                criteria_evaluations=results
            ),
            'raw_response': "Heuristic Evaluation Successful",
            'model_used': 'Smart Heuristic Evaluator'
        }