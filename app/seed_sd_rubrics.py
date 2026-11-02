import sys
from pathlib import Path
from datetime import datetime, date

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.teacher import Teacher
from app.models.material import UKGMaterial, TeacherCompetency
from app.models.rubric import Rubric, RubricVersion, RubricCriterion

def seed_sd_rubrics():
    print("=" * 65)
    print("MEMPERBARUI STANDAR PENILAIAN & RUBRIK UKG SD SOKRATES (SEMESTER 1)")
    print("=" * 65)

    app = create_app()
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        admin_id = admin.id if admin else None

        sd_modules = [
            {
                'code': 'UKG-SD-01',
                'title': 'Komputer Dasar: Desain Poster Gemar Membaca (TuxPaint)',
                'grade_level': 'SD',
                'class_level': 'Kelas 1',
                'semester': 'Semester 1',
                'academic_year': '2025/2026',
                'subject': 'Komputer Dasar',
                'description': 'Proyek guru membuat poster promosi membiasakan kegiatan gemar membaca sejak dini menggunakan TuxPaint.',
                'theme': 'Membiasakan Kegiatan Gemar Membaca Sejak Dini',
                'app_name': 'TuxPaint atau aplikasi alternatifnya',
                'allowed_files': '.jpeg, .jpg, .png',
                'passing_grade': 75.0,
                'instructions': (
                    "1. Proyek dikerjakan secara individu dengan membuat media promosi poster bertema 'Membiasakan Kegiatan Gemar Membaca Sejak Dini'.\n"
                    "2. Menggunakan aplikasi TuxPaint (atau alternatifnya) yang menghasilkan berkas gambar (JPEG/PNG).\n"
                    "3. Menggunakan teks dan gambar berupa hasil desain poster yang menarik untuk siswa kelas 1 SD.\n"
                    "4. Gambar harus sopan, tidak ada unsur pornografi, SARA, ataupun sindiran, serta tidak melanggar hak cipta.\n"
                    "5. Format nama berkas: Nama Peserta_SD_Nama Sekolah_TuxPaint."
                ),
                'competencies': "Profesional (Tehnikal): Pemahaman kurikulum komputer dasar kelas 1 SD, penguasaan tools menggambar TuxPaint, pemilihan warna, dan pembuatan poster edukatif."
            },
            {
                'code': 'UKG-SD-02',
                'title': 'Komputer Dasar: Poster Duta Kelas Hemat Energi (Ms.Paint)',
                'grade_level': 'SD',
                'class_level': 'Kelas 2',
                'semester': 'Semester 1',
                'academic_year': '2025/2026',
                'subject': 'Komputer Dasar',
                'description': 'Proyek guru membuat poster ukuran A4 tema Menjadi Duta Kelas Hemat Energi menggunakan Ms.Paint.',
                'theme': 'Menjadi Duta Kelas dengan tema “Hemat Energi”',
                'app_name': 'Ms.Paint atau aplikasi alternatifnya',
                'allowed_files': '.jpeg, .jpg, .png',
                'passing_grade': 75.0,
                'instructions': (
                    "1. Proyek dikerjakan secara individu dengan membuat media poster promosi kegiatan bertema 'Menjadi Duta Kelas dengan tema Hemat Energi'.\n"
                    "2. Menggunakan aplikasi Ms.Paint atau alternatifnya dengan ukuran media A4 dan format gambar JPEG/PNG.\n"
                    "3. Memadukan elemen teks ajakan hemat energi dan gambar ilustrasi digital yang dibuat secara mandiri.\n"
                    "4. Bebas dari unsur SARA, pornografi, dan tidak melanggar hak cipta.\n"
                    "5. Format penamaan berkas: Nama Peserta_SD_Nama Sekolah_MsPaint."
                ),
                'competencies': "Profesional (Tehnikal): Penguasaan teknik menggambar digital Ms.Paint, pengaturan kanvas ukuran A4, penyusunan tipografi, dan pesan kampanye hemat energi."
            },
            {
                'code': 'UKG-SD-03',
                'title': 'Komputer Dasar: Desain Poster Damai Itu Indah Stop Bullying (Photoscape)',
                'grade_level': 'SD',
                'class_level': 'Kelas 3',
                'semester': 'Semester 1',
                'academic_year': '2025/2026',
                'subject': 'Komputer Dasar',
                'description': 'Proyek guru membuat poster edukasi pencegahan perundungan menggunakan aplikasi Photoscape.',
                'theme': 'Damai Itu Indah: Stop Bullying',
                'app_name': 'Photoscape atau aplikasi alternatifnya',
                'allowed_files': '.jpeg, .jpg, .png',
                'passing_grade': 75.0,
                'instructions': (
                    "1. Proyek dikerjakan secara individu dengan membuat desain poster mengenai informasi bagaimana cara menghindari bullying di lingkungan sekolah.\n"
                    "2. Menggunakan aplikasi Photoscape atau alternatifnya, memadukan teks pesan perdamaian dan olah gambar grafis/foto.\n"
                    "3. Format gambar keluaran: JPEG/PNG dengan layout proporsional dan estetis.\n"
                    "4. Tidak mengandung unsur SARA atau sindiran negatif, tidak melanggar hak cipta.\n"
                    "5. Format nama berkas: Nama Peserta_SD_Nama Sekolah_Photoscape."
                ),
                'competencies': "Profesional (Tehnikal): Penguasaan manipulasi grafis Photoscape, penataan tata letak visual pesan sosial, filter warna, dan komposisi teks informatif."
            },
            {
                'code': 'UKG-SD-04',
                'title': 'Komputer Dasar: Desain Mading Menjaga Bumi Kita (Word & Excel)',
                'grade_level': 'SD',
                'class_level': 'Kelas 4',
                'semester': 'Semester 1',
                'academic_year': '2025/2026',
                'subject': 'Komputer Dasar',
                'description': 'Proyek guru membuat mading ukuran A4 tema Menjaga Bumi Kita memadukan rencana Word, tabel Excel, dan foto prakarya.',
                'theme': 'Gerakan Mengajak Bersama-sama Menjaga Bumi Kita',
                'app_name': 'Ms.Word dan Ms.Excel atau aplikasi alternatifnya',
                'allowed_files': '.docx, .xlsx, .pdf, .zip',
                'passing_grade': 75.0,
                'instructions': (
                    "1. Membuat rencana kegiatan projek menggunakan Ms.Word.\n"
                    "2. Membuat tabel jadwal periodik kapan dan bagaimana projek dilakukan menggunakan Ms.Excel.\n"
                    "3. Membuat sebuah prakarya atau kerajinan tangan fisik yang berhubungan dengan tema menjaga bumi.\n"
                    "4. Membuat desain mading ukuran A4 menggunakan Ms.Word dengan memasukkan keterangan projek, tabel jadwal dari Excel, dan foto dokumentasi prakarya.\n"
                    "5. Format berkas: .docx dan .xlsx (atau dibundel dalam 1 ZIP/PDF).\n"
                    "6. Format folder: Nama Peserta_SD_Nama Sekolah_Mading."
                ),
                'competencies': "Profesional (Tehnikal): Integrasi multi-aplikasi pengolah kata (Word) dan lembar sebar (Excel), perancangan layout majalah dinding, dan dokumentasi prakarya."
            },
            {
                'code': 'UKG-SD-05',
                'title': 'Komputer Dasar: Slide Presentasi & Media Budaya Nusantara (PowerPoint & Video)',
                'grade_level': 'SD',
                'class_level': 'Kelas 5',
                'semester': 'Semester 1',
                'academic_year': '2025/2026',
                'subject': 'Komputer Dasar',
                'description': 'Proyek presentasi 16:9 PowerPoint mengenal dan mencintai budaya nusantara dilengkapi video rekaman mandiri dan foto kerajinan.',
                'theme': 'Gerakan Mengenal dan Mencintai Budaya Nusantara Indonesia',
                'app_name': 'Ms.PowerPoint atau aplikasi alternatifnya',
                'allowed_files': '.pptx, .ppt, .pdf, .zip',
                'passing_grade': 75.0,
                'instructions': (
                    "1. Membuat slide presentasi 16:9 berisikan informasi salah satu kebudayaan daerah (alat musik, tarian, baju adat, dsb).\n"
                    "2. Video rekaman peserta memainkan alat musik daerah / menyanyi lagu daerah / tarian / tutorial memasak makanan khas (wajib diperankan sendiri, dilarang comot internet).\n"
                    "3. Foto kerajinan tangan / prakarya khas daerah yang dibuat sendiri oleh guru.\n"
                    "4. Mencantumkan foto dan profil pembuat slide, serta wajib memasukkan logo sekolah dan Binus Center.\n"
                    "5. Format keluaran: .pptx (dan file pendukung dalam ZIP)."
                ),
                'competencies': "Profesional (Tehnikal): Penguasaan pembuatan media presentasi interaktif rasio 16:9 Ms.PowerPoint, integrasi multimedia audio-video, dan penyampaian konten budaya."
            },
            {
                'code': 'UKG-SD-06',
                'title': 'Komputer Dasar: Cerita Animasi / Game Bangga Indonesia (Scratch & PPT)',
                'grade_level': 'SD',
                'class_level': 'Kelas 6',
                'semester': 'Semester 1',
                'academic_year': '2025/2026',
                'subject': 'Komputer Dasar',
                'description': 'Proyek membuat animasi atau game Scratch bertema Bangga Indonesia disertai laporan presentasi PowerPoint.',
                'theme': 'Bangga Indonesia',
                'app_name': 'Scratch dan Ms.PowerPoint',
                'allowed_files': '.sb3, .sb, .pptx, .zip',
                'passing_grade': 75.0,
                'instructions': (
                    "1. Membuat cerita animasi atau game sederhana menggunakan aplikasi Scratch bertema 'Bangga Indonesia'.\n"
                    "2. Membuat laporan PowerPoint yang menjelaskan: mengapa bangga sebagai WNI, daftar sprite & background, alur cerita/game, screen capture bukti upload ke komunitas https://scratch.mit.edu/, foto profil, serta logo sekolah dan Binus Center.\n"
                    "3. Format berkas: .sb3 (projek Scratch) dan .pptx (laporan presentasi).\n"
                    "4. Format folder pengumpulan: Nama Peserta_SD_Nama Sekolah_Scratch."
                ),
                'competencies': "Profesional (Tehnikal): Computational thinking, pemrograman blok Scratch (event, control loop, conditional if-else, variabel), dan pembuatan presentasi laporan."
            }
        ]

        # Tiga Kriteria Standar Sokrates:
        # a. Ide / Kreatifitas / Tehnik (70%)
        # b. Kerapihan (20%)
        # c. Tema (10%)
        # Total = 100%

        for m_data in sd_modules:
            # 1. Pastikan Materi UKG Terdaftar
            mat = UKGMaterial.query.filter_by(code=m_data['code']).first()
            if not mat:
                mat = UKGMaterial(
                    code=m_data['code'],
                    title=m_data['title'],
                    grade_level=m_data['grade_level'],
                    class_level=m_data['class_level'],
                    semester=m_data['semester'],
                    academic_year=m_data['academic_year'],
                    subject=m_data['subject'],
                    description=m_data['description']
                )
                db.session.add(mat)
                db.session.flush()
            else:
                mat.title = m_data['title']
                mat.description = m_data['description']
                mat.semester = m_data['semester']
                mat.academic_year = m_data['academic_year']
                db.session.flush()

            # 2. Pastikan Rubrik Terdaftar
            rubric = Rubric.query.filter_by(material_id=mat.id).first()
            if not rubric:
                rubric = Rubric(
                    material_id=mat.id,
                    title=f"Rubrik Penilaian UKG SD {mat.class_level}: {m_data['theme']}",
                    description=f"Standar penilaian resmi UKG Sokrates untuk jenjang SD {mat.class_level} ({m_data['app_name']}).",
                    project_instructions=m_data['instructions'],
                    competencies_measured=m_data['competencies'],
                    passing_grade=m_data['passing_grade'],
                    allowed_file_types=m_data['allowed_files'],
                    created_by_id=admin_id
                )
                db.session.add(rubric)
                db.session.flush()
            else:
                rubric.title = f"Rubrik Penilaian UKG SD {mat.class_level}: {m_data['theme']}"
                rubric.project_instructions = m_data['instructions']
                rubric.competencies_measured = m_data['competencies']
                rubric.allowed_file_types = m_data['allowed_files']
                db.session.flush()

            # 3. Buat Versi Aktif Rubrik
            for v in rubric.versions:
                v.status = 'archived'

            version_label = f"v1.{len(rubric.versions) + 1}" if rubric.versions else "v1.0"
            new_version = RubricVersion(
                rubric_id=rubric.id,
                version_number=len(rubric.versions) + 1,
                version_label=version_label,
                status='active', # Aktif resmi
                effective_date=date(2025, 7, 1),
                change_notes="Standar Penilaian Resmi Kurikulum Komputer Dasar SD Sokrates (Bobot 70/20/10).",
                approved_by_id=admin_id,
                approved_at=datetime.utcnow()
            )
            db.session.add(new_version)
            db.session.flush()

            # 4. Tambahkan 3 Kriteria Resmi
            c1 = RubricCriterion(
                version_id=new_version.id,
                name="Ide / Kreatifitas / Tehnik (70%)",
                description=(
                    f"Kesesuaian penggunaan tools perangkat lunak ({m_data['app_name']}), kedalaman ide karya, "
                    f"kreativitas eksplorasi fitur media, dan orisinalitas pengerjaan proyek guru."
                ),
                weight=70.0,
                scale_min=0.0,
                scale_max=100.0,
                is_mandatory=True,
                mandatory_min_score=70.0,
                evidence_indicators=(
                    f"Penguasaan aplikasi {m_data['app_name']}, keaslian karya mandiri, variasi elemen grafis/logika, "
                    f"ketepatan format berkas ({m_data['allowed_files']}), dan pemenuhan teknis penugasan."
                ),
                sort_order=1
            )

            c2 = RubricCriterion(
                version_id=new_version.id,
                name="Kerapihan (20%)",
                description=(
                    "Keteraturan tata letak visual (layout), keterbacaan teks/font, proporsi gambar dan kanvas, "
                    "harmonisasi warna, dan kerapihan struktur berkas proyek."
                ),
                weight=20.0,
                scale_min=0.0,
                scale_max=100.0,
                is_mandatory=False,
                mandatory_min_score=None,
                evidence_indicators=(
                    "Keseimbangan komposisi (alignment), keterbacaan tipografi (font legible), proporsi elemen desain, "
                    "estetika visual, dan kerapihan penyusunan berkas tugas."
                ),
                sort_order=2
            )

            c3 = RubricCriterion(
                version_id=new_version.id,
                name="Tema (10%)",
                description=(
                    f"Kesesuaian seluruh materi proyek dengan tema penugasan resmi: '{m_data['theme']}', "
                    f"kesantunan konten (bebas SARA/pornografi), dan nilai edukasi bagi siswa SD."
                ),
                weight=10.0,
                scale_min=0.0,
                scale_max=100.0,
                is_mandatory=True,
                mandatory_min_score=60.0,
                evidence_indicators=(
                    f"Relevansi langsung dengan tema '{m_data['theme']}', pesan kampanye edukatif, "
                    "kesopanan visual dan bahasa, kepatuhan etika tanpa pelanggaran hak cipta."
                ),
                sort_order=3
            )

            db.session.add_all([c1, c2, c3])
            print(f"  [OK] Materi {m_data['code']} ({m_data['class_level']}) - Rubrik {version_label} AKTIF (Bobot: 70% + 20% + 10% = 100%).")

        # 5. Seed Data Guru Contoh (SD)
        sample_teachers = [
            {
                'nip': '198705122010012001',
                'name': 'Amelia Paramma, S.Pd.',
                'school_origin': 'SDK Frateran 1 Surabaya',
                'grade_level': 'SD',
                'classes_taught': 'Kelas 1, Kelas 2',
                'email': 'amelia.paramma@frateran.sch.id',
                'phone': '081234567890',
                'materials': ['UKG-SD-01', 'UKG-SD-02']
            },
            {
                'nip': '198908222014021003',
                'name': 'Bambang Supriyanto, S.Kom.',
                'school_origin': 'SDK Santo Yusup Malang',
                'grade_level': 'SD',
                'classes_taught': 'Kelas 3, Kelas 4',
                'email': 'bambang.supriyanto@yusup.sch.id',
                'phone': '081398765432',
                'materials': ['UKG-SD-03', 'UKG-SD-04']
            },
            {
                'nip': '199203152018032005',
                'name': 'Yohanes Hendri, S.Pd.',
                'school_origin': 'SDK Indra Siswa Bondowoso',
                'grade_level': 'SD',
                'classes_taught': 'Kelas 5, Kelas 6',
                'email': 'yohanes.hendri@indrasiswa.sch.id',
                'phone': '082187654321',
                'materials': ['UKG-SD-05', 'UKG-SD-06']
            }
        ]

        for t_data in sample_teachers:
            t = Teacher.query.filter_by(nip=t_data['nip']).first()
            if not t:
                t = Teacher(
                    nip=t_data['nip'],
                    name=t_data['name'],
                    school_origin=t_data['school_origin'],
                    grade_level=t_data['grade_level'],
                    classes_taught=t_data['classes_taught'],
                    email=t_data['email'],
                    phone=t_data['phone'],
                    is_active=True
                )
                db.session.add(t)
                db.session.flush()

                # Petakan materi wajib
                for m_code in t_data['materials']:
                    m_obj = UKGMaterial.query.filter_by(code=m_code).first()
                    if m_obj:
                        comp = TeacherCompetency(
                            teacher_id=t.id,
                            material_id=m_obj.id,
                            is_required=True,
                            status='not_started'
                        )
                        db.session.add(comp)
                print(f"  [OK] Guru Contoh '{t.name}' terdaftar dan dipetakan materinya.")

        db.session.commit()
        print("\n" + "=" * 65)
        print("PENYELARASAN RUBRIK UKG SD SOKRATES & DATA GURU SELESAI (SUKSES 100%)")
        print("=" * 65)

if __name__ == '__main__':
    seed_sd_rubrics()
