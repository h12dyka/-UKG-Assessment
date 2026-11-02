from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import func
from app.models.teacher import Teacher
from app.models.submission import Submission
from app.models.material import UKGMaterial
from app.models.rubric import Rubric

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # 1. Statistik Ringkasan Utama (Real Database Supabase)
    total_teachers = Teacher.query.filter_by(is_active=True).count()
    total_submissions = Submission.query.count()
    
    under_review = Submission.query.filter(Submission.status.in_(['under_ai_review', 'queued'])).count()
    passed_count = Submission.query.filter_by(status='passed').count()
    not_passed_count = Submission.query.filter_by(status='not_passed').count()
    pending_admin = Submission.query.filter_by(status='pending_admin_review').count()

    # 2. Distribusi Guru Berdasarkan Jenjang Sekolah
    grade_distribution = (
        Teacher.query.with_entities(Teacher.grade_level, func.count(Teacher.id))
        .group_by(Teacher.grade_level)
        .all()
    )
    grade_labels = [g[0] for g in grade_distribution]
    grade_counts = [g[1] for g in grade_distribution]

    # Distribusi Hasil Penilaian
    result_labels = ['Lulus', 'Belum Lulus', 'Perlu Ditinjau Admin', 'Sedang Diproses']
    result_counts = [passed_count, not_passed_count, pending_admin, under_review]

    # 3. Filter & Pencarian Tabel Proyek Terbaru
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip()
    material_filter = request.args.get('material', '').strip()
    semester_filter = request.args.get('semester', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Submission.query.join(Teacher).join(UKGMaterial)

    if search_query:
        query = query.filter(
            (Teacher.name.ilike(f'%{search_query}%')) |
            (Submission.project_title.ilike(f'%{search_query}%')) |
            (Teacher.nip.ilike(f'%{search_query}%'))
        )
    if status_filter:
        query = query.filter(Submission.status == status_filter)
    if material_filter:
        query = query.filter(Submission.material_id == int(material_filter))
    if semester_filter:
        query = query.filter(UKGMaterial.semester == semester_filter)

    pagination = query.order_by(Submission.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    recent_submissions = pagination.items

    materials = UKGMaterial.query.filter_by(is_active=True).order_by(UKGMaterial.title).all()

    # Hitung total submission per semester
    semester_1_count = Submission.query.join(UKGMaterial).filter(UKGMaterial.semester == 'Semester 1').count()
    semester_2_count = Submission.query.join(UKGMaterial).filter(UKGMaterial.semester == 'Semester 2').count()

    return render_template(
        'dashboard/index.html',
        total_teachers=total_teachers,
        total_submissions=total_submissions,
        under_review=under_review,
        passed_count=passed_count,
        not_passed_count=not_passed_count,
        pending_admin=pending_admin,
        grade_labels=grade_labels,
        grade_counts=grade_counts,
        result_labels=result_labels,
        result_counts=result_counts,
        semester_1_count=semester_1_count,
        semester_2_count=semester_2_count,
        submissions=recent_submissions,
        pagination=pagination,
        search_query=search_query,
        status_filter=status_filter,
        material_filter=material_filter,
        semester_filter=semester_filter,
        materials=materials
    )
