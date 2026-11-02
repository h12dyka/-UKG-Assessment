from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.material import UKGMaterial
from app.models.rubric import Rubric, RubricVersion, RubricCriterion
from app.services.audit_service import AuditService

rubrics_bp = Blueprint('rubrics', __name__, url_prefix='/rubrics')

@rubrics_bp.route('/')
@login_required
def index():
    rubrics = Rubric.query.join(UKGMaterial).order_by(UKGMaterial.grade_level, UKGMaterial.class_level, UKGMaterial.semester).all()
    return render_template('rubrics/index.html', rubrics=rubrics)

@rubrics_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    materials = UKGMaterial.query.filter_by(is_active=True).order_by(UKGMaterial.grade_level, UKGMaterial.class_level).all()
    if request.method == 'POST':
        material_id = request.form.get('material_id', type=int)
        title = request.form.get('title', '').strip()
        passing_grade = request.form.get('passing_grade', 75.0, type=float)
        allowed_file_types = request.form.get('allowed_file_types', '.xlsx, .csv').strip()
        competencies_measured = request.form.get('competencies_measured', '').strip()
        project_instructions = request.form.get('project_instructions', '').strip()

        names = request.form.getlist('c_name[]')
        weights = [float(w) for w in request.form.getlist('c_weight[]') if w]
        indicators = request.form.getlist('c_indicator[]')
        descs = request.form.getlist('c_desc[]')
        min_scores = [float(s) if s else 70.0 for s in request.form.getlist('c_min_score[]')]

        total_weight = sum(weights)
        if abs(total_weight - 100.0) > 0.01:
            flash(f"Total bobot kriteria adalah {total_weight:.1f}%. Wajib berjumlah tepat 100%.", 'danger')
            return render_template('rubrics/form.html', materials=materials)

        rubric = Rubric(
            material_id=material_id,
            title=title,
            passing_grade=passing_grade,
            allowed_file_types=allowed_file_types,
            competencies_measured=competencies_measured,
            project_instructions=project_instructions,
            created_by_id=current_user.id
        )
        db.session.add(rubric)
        db.session.flush()

        version = RubricVersion(
            rubric_id=rubric.id,
            version_number=1,
            version_label='v1.0',
            status='active',
            effective_date=date.today(),
            change_notes='Versi inisial rubrik standar UKG',
            approved_by_id=current_user.id,
            approved_at=datetime.utcnow()
        )
        db.session.add(version)
        db.session.flush()

        for idx, name in enumerate(names):
            is_mand = bool(request.form.get(f'c_mandatory[{idx}]'))
            crit = RubricCriterion(
                version_id=version.id,
                name=name,
                description=descs[idx] if idx < len(descs) else '',
                weight=weights[idx] if idx < len(weights) else 0.0,
                scale_min=0.0,
                scale_max=100.0,
                is_mandatory=is_mand,
                mandatory_min_score=min_scores[idx] if idx < len(min_scores) else 70.0,
                evidence_indicators=indicators[idx] if idx < len(indicators) else '',
                sort_order=idx + 1
            )
            db.session.add(crit)

        db.session.commit()
        AuditService.log('CREATE_RUBRIC', 'Rubric', rubric.id, {'title': rubric.title})
        flash(f"Rubrik standar '{rubric.title}' berhasil dibuat dengan versi aktif v1.0.", 'success')
        return redirect(url_for('rubrics.detail', rubric_id=rubric.id))

    return render_template('rubrics/form.html', materials=materials)

@rubrics_bp.route('/<int:rubric_id>/new-version', methods=['GET', 'POST'])
@login_required
def new_version(rubric_id):
    rubric = Rubric.query.get_or_404(rubric_id)
    latest_v = rubric.active_version or (rubric.versions[0] if rubric.versions else None)

    if request.method == 'POST':
        change_notes = request.form.get('change_notes', '').strip()
        activate_immediately = bool(request.form.get('activate_immediately'))

        names = request.form.getlist('c_name[]')
        weights = [float(w) for w in request.form.getlist('c_weight[]') if w]
        indicators = request.form.getlist('c_indicator[]')
        descs = request.form.getlist('c_desc[]')
        min_scores = [float(s) if s else 70.0 for s in request.form.getlist('c_min_score[]')]

        total_weight = sum(weights)
        if abs(total_weight - 100.0) > 0.01:
            flash(f"Total bobot kriteria adalah {total_weight:.1f}%. Wajib berjumlah tepat 100%.", 'danger')
            return render_template('rubrics/version_form.html', rubric=rubric, latest_v=latest_v)

        next_num = len(rubric.versions) + 1
        new_label = f"v1.{next_num - 1}" if next_num > 1 else "v1.0"

        if activate_immediately:
            for v in rubric.versions:
                if v.status == 'active':
                    v.status = 'archived'

        status = 'active' if activate_immediately else 'draft'
        new_v = RubricVersion(
            rubric_id=rubric.id,
            version_number=next_num,
            version_label=new_label,
            status=status,
            effective_date=date.today(),
            change_notes=change_notes,
            approved_by_id=current_user.id if activate_immediately else None,
            approved_at=datetime.utcnow() if activate_immediately else None
        )
        db.session.add(new_v)
        db.session.flush()

        for idx, name in enumerate(names):
            is_mand = bool(request.form.get(f'c_mandatory[{idx}]'))
            crit = RubricCriterion(
                version_id=new_v.id,
                name=name,
                description=descs[idx] if idx < len(descs) else '',
                weight=weights[idx] if idx < len(weights) else 0.0,
                scale_min=0.0,
                scale_max=100.0,
                is_mandatory=is_mand,
                mandatory_min_score=min_scores[idx] if idx < len(min_scores) else 70.0,
                evidence_indicators=indicators[idx] if idx < len(indicators) else '',
                sort_order=idx + 1
            )
            db.session.add(crit)

        db.session.commit()
        AuditService.log('CREATE_RUBRIC_VERSION', 'RubricVersion', new_v.id, {'version_label': new_label, 'status': status})
        flash(f"Versi rubrik baru {new_label} berhasil disimpan ({'Aktif' if activate_immediately else 'Draft'}).", 'success')
        return redirect(url_for('rubrics.detail', rubric_id=rubric.id, v=new_v.id))

    return render_template('rubrics/version_form.html', rubric=rubric, latest_v=latest_v)

@rubrics_bp.route('/<int:rubric_id>')
@login_required
def detail(rubric_id):
    rubric = Rubric.query.get_or_404(rubric_id)
    version_id = request.args.get('v', type=int)

    if version_id:
        version = RubricVersion.query.filter_by(id=version_id, rubric_id=rubric.id).first_or_404()
    else:
        version = rubric.active_version or (rubric.versions[0] if rubric.versions else None)

    total_weight = sum(c.weight for c in version.criteria) if version else 0.0

    return render_template('rubrics/detail.html', rubric=rubric, version=version, total_weight=total_weight)

@rubrics_bp.route('/<int:rubric_id>/versions/<int:version_id>/activate', methods=['POST'])
@login_required
def activate_version(rubric_id, version_id):
    rubric = Rubric.query.get_or_404(rubric_id)
    version = RubricVersion.query.filter_by(id=version_id, rubric_id=rubric.id).first_or_404()

    # Validasi total bobot harus 100%
    total_weight = sum(c.weight for c in version.criteria)
    if abs(total_weight - 100.0) > 0.01:
        flash(f"Versi ini belum dapat diaktifkan! Total bobot kriteria adalah {total_weight:.1f}%. Wajib berjumlah tepat 100%.", 'danger')
        return redirect(url_for('rubrics.detail', rubric_id=rubric.id, v=version.id))

    # Arsipkan versi lain
    for v in rubric.versions:
        if v.status == 'active':
            v.status = 'archived'

    version.status = 'active'
    version.approved_by_id = current_user.id
    version.approved_at = datetime.utcnow()
    db.session.commit()

    AuditService.log('ACTIVATE_RUBRIC_VERSION', 'RubricVersion', version.id, {'rubric_id': rubric.id, 'version': version.version_label})
    flash(f"Versi rubrik {version.version_label} berhasil diaktifkan sebagai acuan resmi UKG.", 'success')
    return redirect(url_for('rubrics.detail', rubric_id=rubric.id, v=version.id))

@rubrics_bp.route('/<int:rubric_id>/versions/create', methods=['POST'])
@login_required
def create_version(rubric_id):
    rubric = Rubric.query.get_or_404(rubric_id)
    base_version_id = request.form.get('base_version_id', type=int)

    base_version = RubricVersion.query.filter_by(id=base_version_id, rubric_id=rubric.id).first() if base_version_id else rubric.active_version

    next_num = len(rubric.versions) + 1
    new_label = f"v1.{next_num - 1}" if next_num > 1 else "v1.0"
    notes = request.form.get('change_notes', f"Dibuat dari {base_version.version_label if base_version else 'awal'}").strip()

    new_v = RubricVersion(
        rubric_id=rubric.id,
        version_number=next_num,
        version_label=new_label,
        status='draft',
        effective_date=date.today(),
        change_notes=notes,
        approved_by_id=None
    )
    db.session.add(new_v)
    db.session.flush()

    # Salin kriteria dari versi acuan
    if base_version:
        for c in base_version.criteria:
            new_c = RubricCriterion(
                version_id=new_v.id,
                name=c.name,
                description=c.description,
                weight=c.weight,
                scale_min=c.scale_min,
                scale_max=c.scale_max,
                is_mandatory=c.is_mandatory,
                mandatory_min_score=c.mandatory_min_score,
                evidence_indicators=c.evidence_indicators,
                sort_order=c.sort_order
            )
            db.session.add(new_c)

    db.session.commit()
    AuditService.log('CREATE_RUBRIC_VERSION', 'RubricVersion', new_v.id, {'version_label': new_label})
    flash(f"Draft versi baru {new_label} berhasil dibuat. Silakan sesuaikan kriteria dan bobot.", 'success')
    return redirect(url_for('rubrics.detail', rubric_id=rubric.id, v=new_v.id))


@rubrics_bp.route('/<int:rubric_id>/delete', methods=['POST'])
@login_required
def delete(rubric_id):
    rubric = Rubric.query.get_or_404(rubric_id)
    title = rubric.title
    
    has_submissions = any(v.submissions for v in rubric.versions)
    if has_submissions:
        flash(f"Rubrik '{title}' tidak dapat dihapus karena sudah memiliki riwayat pengumpulan guru. Gunakan fitur arsip versi sebagai gantinya.", 'danger')
        return redirect(url_for('rubrics.index'))
    
    try:
        db.session.delete(rubric)
        db.session.commit()
        AuditService.log('DELETE_RUBRIC', 'Rubric', rubric_id, {'title': title})
        flash(f"Rubrik Penilaian '{title}' Berhasil dihapus.", 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f"Gagal manghapus rubrik: {str(e)}", 'danger')
        
    return redirect(url_for('rubrics.index'))
