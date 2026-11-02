import os
import uuid
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, send_file, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.extensions import db
from app.models.teacher import Teacher
from app.models.material import UKGMaterial
from app.models.rubric import Rubric
from app.models.submission import Submission, ProjectFile
from app.services.parsers import FileParserManager
from app.services.ai_evaluator import AIEvaluatorService
from app.services.scoring_engine import ScoringEngine
from app.services.audit_service import AuditService

submissions_bp = Blueprint('submissions', __name__, url_prefix='/submissions')

@submissions_bp.route('/')
@login_required
def index():
    status = request.args.get('status', '').strip()
    material_id = request.args.get('material_id', type=int)
    teacher_id = request.args.get('teacher_id', type=int)
    semester = request.args.get('semester', '').strip()
    search = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Submission.query.join(Teacher).join(UKGMaterial)

    if status:
        query = query.filter(Submission.status == status)
    if material_id:
        query = query.filter(Submission.material_id == material_id)
    if teacher_id:
        query = query.filter(Submission.teacher_id == teacher_id)
    if semester:
        query = query.filter(UKGMaterial.semester == semester)
    if search:
        query = query.filter(
            (Submission.project_title.ilike(f'%{search}%')) |
            (Teacher.name.ilike(f'%{search}%')) |
            (Teacher.nip.ilike(f'%{search}%'))
        )

    pagination = query.order_by(Submission.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    submissions = pagination.items

    materials = UKGMaterial.query.filter_by(is_active=True).order_by(UKGMaterial.title).all()
    teachers = Teacher.query.filter_by(is_active=True).order_by(Teacher.name).all()

    return render_template(
        'submissions/index.html',
        submissions=submissions,
        pagination=pagination,
        status=status,
        material_id=material_id,
        teacher_id=teacher_id,
        semester=semester,
        search=search,
        materials=materials,
        teachers=teachers
    )

@submissions_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    teachers = Teacher.query.filter_by(is_active=True).order_by(Teacher.name).all()
    materials = UKGMaterial.query.filter_by(is_active=True).order_by(UKGMaterial.grade_level, UKGMaterial.class_level, UKGMaterial.semester).all()
    recent_submissions = Submission.query.order_by(Submission.created_at.desc()).limit(8).all()

    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id', type=int)
        material_id = request.form.get('material_id', type=int)
        project_title = request.form.get('project_title', '').strip()
        notes = request.form.get('notes', '').strip()
        run_ai_now = bool(request.form.get('run_ai_now', True))

        if not teacher_id or not material_id or not project_title:
            flash("Mohon lengkapi Guru, Materi UKG, dan Judul Proyek.", 'warning')
            return render_template('submissions/upload.html', teachers=teachers, materials=materials, recent_submissions=recent_submissions)

        if 'project_file' not in request.files:
            flash("Tidak ada berkas yang dipilih. Silakan pilih berkas proyek.", 'danger')
            return render_template('submissions/upload.html', teachers=teachers, materials=materials, recent_submissions=recent_submissions)

        file = request.files['project_file']
        if file.filename == '':
            flash("Mohon pilih berkas proyek yang akan diunggah.", 'danger')
            return render_template('submissions/upload.html', teachers=teachers, materials=materials, recent_submissions=recent_submissions)

        original_filename = secure_filename(file.filename) or 'project_file'
        ext = Path(original_filename).suffix.lower().replace('.', '')

                # 1. Cari Rubrik Aktif untuk materi ini
        rubric = Rubric.query.filter_by(material_id=material_id).first()
        if not rubric:
            flash("Belum ada Rubrik Standar yang dibuat untuk materi UKG ini. Silakan buat rubrik terlebih dahulu.", 'danger')
            return render_template('submissions/upload.html', teachers=teachers, materials=materials, recent_submissions=recent_submissions)

        active_version = rubric.active_version
        if not active_version:
            flash(f"Rubrik '{rubric.title}' belum memiliki versi AKTIF. Mohon aktifkan salah satu versi rubrik terlebih dahulu.", 'danger')
            return render_template('submissions/upload.html', teachers=teachers, materials=materials, recent_submissions=recent_submissions)

        # Semua format berkas diizinkan terunggah (Informasi kesesuaian dicatat tanpa memblokir upload)
        allowed_rubric_raw = rubric.allowed_file_types or ''
        allowed_rubric_exts = [
            e.strip().lower().replace('.', '')
            for e in allowed_rubric_raw.split(',')
            if e.strip()
        ]

        # 2. Hitung percobaan keberapa (attempt_number)
        prev_attempts = Submission.query.filter_by(
            teacher_id=teacher_id,
            material_id=material_id
        ).count()
        attempt_number = prev_attempts + 1

        # 3. Simpan berkas fisik ke folder privat
        upload_dir = Path(current_app.config['UPLOAD_FOLDER'])
        upload_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4().hex[:12]}_{original_filename}"
        saved_file_path = upload_dir / unique_filename
        file.save(str(saved_file_path))
        file_size = os.path.getsize(str(saved_file_path))

        # 4. Buat entitas Submission
        submission = Submission(
            teacher_id=teacher_id,
            material_id=material_id,
            rubric_version_id=active_version.id,
            project_title=project_title,
            notes=notes or None,
            attempt_number=attempt_number,
            status='uploaded',
            uploaded_by_id=current_user.id
        )
        db.session.add(submission)
        db.session.flush()

        # 5. Jalankan Parser Ekstraksi Berkas
        parser_mgr = FileParserManager()
        parse_result = parser_mgr.parse_file(str(saved_file_path))

        project_file = ProjectFile(
            submission_id=submission.id,
            original_filename=original_filename,
            stored_filename=unique_filename,
            file_path=str(saved_file_path),
            file_type=parse_result.get('metadata', {}).get('type', ext),
            file_size=file_size,
            mime_type=file.content_type,
            extracted_text=parse_result.get('extracted_content', ''),
            parser_metadata=str(parse_result.get('metadata', {})),
            parse_status='success' if parse_result.get('success') else 'error'
        )
        db.session.add(project_file)
        db.session.commit()

        AuditService.log('UPLOAD_SUBMISSION', 'Submission', submission.id, {
            'filename': original_filename,
            'size': file_size,
            'attempt': attempt_number
        })

        flash(f"Berkas proyek '{project_title}' berhasil diunggah (Percobaan ke-{attempt_number}).", 'success')

        # 6. Jalankan AI Evaluator jika diminta
        if run_ai_now:
            submission.status = 'under_ai_review'
            db.session.commit()

            ai_service = AIEvaluatorService()
            eval_res = ai_service.evaluate_submission(
                rubric_version=active_version,
                project_title=project_title,
                extracted_content=parse_result.get('extracted_content', ''),
                file_metadata=parse_result.get('metadata', {})
            )

            if eval_res.get('success'):
                ScoringEngine.calculate_evaluation_result(
                    submission=submission,
                    ai_result_data=eval_res['data'],
                    raw_response=eval_res.get('raw_response', ''),
                    ai_model=eval_res.get('model_used', 'AI Evaluator')
                )
                flash("Analisis AI Evaluator selesai secara terstruktur dan nilai telah dihitung.", 'success')
                return redirect(url_for('evaluations.detail', submission_id=submission.id))
            else:
                submission.status = 'failed_processing'
                db.session.commit()
                flash(f"Peringatan Evaluasi: {eval_res.get('error', 'Terjadi kendala pemrosesan AI.')}", 'warning')
                return redirect(url_for('submissions.upload'))

        return redirect(url_for('submissions.index'))

    return render_template(
        'submissions/upload.html',
        teachers=teachers,
        materials=materials,
        recent_submissions=recent_submissions
    )

@submissions_bp.route('/api/teacher-materials/<int:teacher_id>')
@login_required
def get_teacher_materials(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    comps = teacher.required_competencies

    materials_data = []
    for c in comps:
        mat = c.material
        rubric = Rubric.query.filter_by(material_id=mat.id).first()
        has_active_rubric = bool(rubric and rubric.active_version)

        materials_data.append({
            'id': mat.id,
            'code': mat.code,
            'title': mat.title,
            'grade_level': mat.grade_level,
            'class_level': mat.class_level,
            'semester': getattr(mat, 'semester', 'Semester 1') or 'Semester 1',
            'academic_year': getattr(mat, 'academic_year', '2025/2026') or '2025/2026',
            'current_status': c.status,
            'latest_score': c.latest_score,
            'has_active_rubric': has_active_rubric,
            'rubric_title': rubric.title if rubric else None,
            'allowed_file_types': rubric.allowed_file_types if rubric else ''
        })

    teacher_subs = Submission.query.filter_by(teacher_id=teacher.id).order_by(Submission.created_at.desc()).all()
    existing_submissions = []
    for s in teacher_subs:
        f = s.files[0] if s.files else None
        existing_submissions.append({
            'id': s.id,
            'project_title': s.project_title,
            'material_title': s.material.title,
            'material_code': s.material.code,
            'semester': getattr(s.material, 'semester', 'Semester 1') or 'Semester 1',
            'attempt_number': s.attempt_number,
            'status': s.status,
            'status_label': s.status_label_id,
            'status_badge_class': s.status_badge_class,
            'final_score': round(s.final_score, 2) if s.final_score is not None else None,
            'created_at': s.created_at.strftime('%d %b %Y %H:%M') if s.created_at else '-',
            'filename': f.original_filename if f else None,
            'filesize': f.human_size if f else None,
            'file_id': f.id if f else None,
            'detail_url': url_for('evaluations.detail', submission_id=s.id)
        })

    return jsonify({
        'teacher_id': teacher.id,
        'teacher_name': teacher.name,
        'materials': materials_data,
        'existing_submissions': existing_submissions
    })

@submissions_bp.route('/files/download/<int:file_id>')
@login_required
def download_file(file_id):
    proj_file = ProjectFile.query.get_or_404(file_id)
    if not os.path.exists(proj_file.file_path):
        abort(404, description="Berkas fisik tidak ditemukan di server penyimpanan.")

    return send_file(
        proj_file.file_path,
        as_attachment=True,
        download_name=proj_file.original_filename
    )

@submissions_bp.route('/<int:submission_id>/trigger-ai')
@login_required
def trigger_ai(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    active_version = submission.rubric_version or (submission.material.rubrics[0].active_version if submission.material.rubrics else None)

    if not submission.files:
        flash("Tidak ada berkas proyek yang dapat dianalisis.", 'danger')
        return redirect(url_for('evaluations.detail', submission_id=submission.id))

    proj_file = submission.files[0]
    submission.status = 'under_ai_review'
    db.session.commit()

    ai_service = AIEvaluatorService()
    eval_res = ai_service.evaluate_submission(
        rubric_version=active_version,
        project_title=submission.project_title,
        extracted_content=proj_file.extracted_text or '',
        file_metadata={'type': proj_file.file_type, 'extension': proj_file.original_filename.split('.')[-1].lower()}
    )

    if eval_res.get('success'):
        ScoringEngine.calculate_evaluation_result(
            submission=submission,
            ai_result_data=eval_res['data'],
            raw_response=eval_res.get('raw_response', ''),
            ai_model=eval_res.get('model_used', 'AI Evaluator')
        )
        AuditService.log('RUN_AI_EVALUATION', 'Submission', submission.id, {'status': submission.status})
        flash("Evaluasi AI Evaluator berhasil dijalankan ulang.", 'success')
    else:
        submission.status = 'failed_processing'
        db.session.commit()
        flash(f"Gagal memproses evaluasi AI: {eval_res.get('error', 'Terjadi kesalahan teknis.')}", 'danger')

    return redirect(url_for('evaluations.detail', submission_id=submission.id))

