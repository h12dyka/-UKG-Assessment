from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.teacher import Teacher
from app.models.material import UKGMaterial, TeacherCompetency
from app.services.audit_service import AuditService

teachers_bp = Blueprint('teachers', __name__, url_prefix='/teachers')

@teachers_bp.route('/')
@login_required
def index():
    search = request.args.get('q', '').strip()
    grade = request.args.get('grade', '').strip()
    school = request.args.get('school', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Teacher.query

    if search:
        query = query.filter(
            (Teacher.name.ilike(f'%{search}%')) |
            (Teacher.nip.ilike(f'%{search}%')) |
            (Teacher.school_origin.ilike(f'%{search}%'))
        )
    if grade:
        query = query.filter(Teacher.grade_level == grade)
    if school:
        query = query.filter(Teacher.school_origin.ilike(f'%{school}%'))

    pagination = query.order_by(Teacher.name.asc()).paginate(page=page, per_page=15, error_out=False)
    teachers = pagination.items

    schools = db.session.query(Teacher.school_origin).distinct().order_by(Teacher.school_origin).all()
    schools = [s[0] for s in schools if s[0]]

    return render_template(
        'teachers/index.html',
        teachers=teachers,
        pagination=pagination,
        search=search,
        grade=grade,
        school=school,
        schools=schools
    )

@teachers_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    materials = UKGMaterial.query.filter_by(is_active=True).order_by(UKGMaterial.grade_level, UKGMaterial.class_level, UKGMaterial.semester, UKGMaterial.title).all()

    if request.method == 'POST':
        nip = request.form.get('nip', '').strip()
        name = request.form.get('name', '').strip()
        school_origin = request.form.get('school_origin', '').strip()
        grade_level = request.form.get('grade_level', '').strip()
        classes_taught = request.form.get('classes_taught', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        selected_materials = request.form.getlist('materials') # list of material_id strings

        # Validasi NIP duplikat
        if Teacher.query.filter_by(nip=nip).first():
            flash(f"Nomor Identitas / NIP '{nip}' sudah terdaftar pada sistem.", 'danger')
            return render_template('teachers/form.html', materials=materials, teacher=None, form_data=request.form)

        if not name or not nip or not school_origin:
            flash("Nama guru, NIP, dan asal sekolah wajib diisi.", 'warning')
            return render_template('teachers/form.html', materials=materials, teacher=None, form_data=request.form)

        teacher = Teacher(
            nip=nip,
            name=name,
            school_origin=school_origin,
            grade_level=grade_level or 'SD',
            classes_taught=classes_taught or '-',
            email=email or None,
            phone=phone or None,
            is_active=True
        )
        db.session.add(teacher)
        db.session.flush()

        # Petakan materi UKG yang diwajibkan
        for mat_id in selected_materials:
            try:
                comp = TeacherCompetency(
                    teacher_id=teacher.id,
                    material_id=int(mat_id),
                    is_required=True,
                    status='not_started'
                )
                db.session.add(comp)
            except Exception:
                pass

        db.session.commit()
        AuditService.log('CREATE_TEACHER', 'Teacher', teacher.id, {'nip': nip, 'name': name})
        flash(f"Guru '{name}' berhasil didaftarkan beserta pemetaan materi UKG.", 'success')
        return redirect(url_for('teachers.detail', teacher_id=teacher.id))

    return render_template('teachers/form.html', materials=materials, teacher=None, form_data={})

@teachers_bp.route('/<int:teacher_id>')
@login_required
def detail(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    summary = teacher.get_competency_summary()
    return render_template('teachers/detail.html', teacher=teacher, summary=summary)

@teachers_bp.route('/<int:teacher_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    materials = UKGMaterial.query.filter_by(is_active=True).order_by(UKGMaterial.grade_level, UKGMaterial.class_level, UKGMaterial.semester, UKGMaterial.title).all()
    current_mat_ids = [c.material_id for c in teacher.required_competencies]

    if request.method == 'POST':
        nip = request.form.get('nip', '').strip()
        name = request.form.get('name', '').strip()
        school_origin = request.form.get('school_origin', '').strip()
        grade_level = request.form.get('grade_level', '').strip()
        classes_taught = request.form.get('classes_taught', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        is_active = bool(request.form.get('is_active'))
        selected_materials = [int(m) for m in request.form.getlist('materials')]

        # Cek duplikasi NIP jika diubah
        existing = Teacher.query.filter(Teacher.nip == nip, Teacher.id != teacher.id).first()
        if existing:
            flash(f"Nomor Identitas '{nip}' sudah digunakan oleh guru lain.", 'danger')
            return render_template('teachers/form.html', materials=materials, teacher=teacher, current_mat_ids=current_mat_ids)

        teacher.nip = nip
        teacher.name = name
        teacher.school_origin = school_origin
        teacher.grade_level = grade_level
        teacher.classes_taught = classes_taught
        teacher.email = email or None
        teacher.phone = phone or None
        teacher.is_active = is_active

        # Update materi kompetensi
        for comp in list(teacher.required_competencies):
            if comp.material_id not in selected_materials:
                db.session.delete(comp)

        existing_ids = [c.material_id for c in teacher.required_competencies]
        for m_id in selected_materials:
            if m_id not in existing_ids:
                new_comp = TeacherCompetency(
                    teacher_id=teacher.id,
                    material_id=m_id,
                    is_required=True,
                    status='not_started'
                )
                db.session.add(new_comp)

        db.session.commit()
        AuditService.log('UPDATE_TEACHER', 'Teacher', teacher.id, {'nip': nip, 'name': name})
        flash(f"Data guru '{name}' berhasil diperbarui.", 'success')
        return redirect(url_for('teachers.detail', teacher_id=teacher.id))

    return render_template('teachers/form.html', materials=materials, teacher=teacher, current_mat_ids=current_mat_ids)

@teachers_bp.route('/<int:teacher_id>/delete', methods=['POST'])
@login_required
def delete(teacher_id):
    teacher = Teacher.query.get_or_404(teacher_id)
    name = teacher.name
    db.session.delete(teacher)
    db.session.commit()
    AuditService.log('DELETE_TEACHER', 'Teacher', teacher_id, {'name': name})
    flash(f"Data guru '{name}' telah dihapus dari sistem.", 'info')
    return redirect(url_for('teachers.index'))
