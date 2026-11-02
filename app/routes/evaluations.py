import io
from flask import send_file
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.submission import Submission
from app.models.evaluation import AIEvaluation, FinalAssessmentDecision
from app.models.material import UKGMaterial, TeacherCompetency
from app.models.teacher import Teacher
from app.models.audit_log import AuditLog
from app.services.ai_evaluator import AIEvaluatorService
from app.services.scoring_engine import ScoringEngine
from app.services.audit_service import AuditService

evaluations_bp = Blueprint('evaluations', __name__, url_prefix='/evaluations')

@evaluations_bp.route('/<int:submission_id>')
@login_required
def detail(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    evaluation = submission.ai_evaluation
    decision = submission.final_decision
    rubric_version = submission.rubric_version

    return render_template(
        'evaluations/detail.html',
        submission=submission,
        evaluation=evaluation,
        decision=decision,
        rubric_version=rubric_version
    )

@evaluations_bp.route('/<int:submission_id>/run', methods=['POST'])
@login_required
def run_evaluation(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    active_version = submission.rubric_version

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
        flash("Penilaian AI Evaluator berhasil diperbarui.", 'success')
    else:
        submission.status = 'failed_processing'
        db.session.commit()
        flash(f"Gagal memproses evaluasi: {eval_res.get('error', 'Terjadi kesalahan teknis.')}", 'danger')

    return redirect(url_for('evaluations.detail', submission_id=submission.id))

@evaluations_bp.route('/<int:submission_id>/approve', methods=['POST'])
@login_required
def approve(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    decision = submission.final_decision
    if not decision:
        flash("Belum ada keputusan evaluasi yang dapat disetujui.", 'warning')
        return redirect(url_for('evaluations.detail', submission_id=submission.id))

    decision.decided_by_id = current_user.id
    decision.decided_at = datetime.utcnow()

    # Sinkronisasi status TeacherCompetency
    teacher_comp = TeacherCompetency.query.filter_by(
        teacher_id=submission.teacher_id,
        material_id=submission.material_id
    ).first()
    if teacher_comp:
        teacher_comp.status = decision.decision_status
        teacher_comp.latest_score = decision.final_score
        teacher_comp.last_evaluated_at = datetime.utcnow()

    db.session.commit()
    AuditService.log('ADMIN_APPROVAL', 'FinalAssessmentDecision', decision.id, {
        'status': decision.decision_status,
        'final_score': decision.final_score
    })
    flash("Hasil penilaian resmi berhasil disetujui oleh Admin.", 'success')
    return redirect(url_for('evaluations.detail', submission_id=submission.id))

@evaluations_bp.route('/<int:submission_id>/override', methods=['POST'])
@login_required
def override(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    decision = submission.final_decision

    if not decision:
        flash("Belum ada keputusan evaluasi yang dapat diubah.", 'warning')
        return redirect(url_for('evaluations.detail', submission_id=submission.id))

    new_status = request.form.get('decision_status') or request.form.get('passing_status')
    new_score = request.form.get('final_score', type=float)
    admin_notes = (request.form.get('admin_notes') or request.form.get('reason') or '').strip()
    feedback = request.form.get('feedback', '').strip()
    if feedback:
        admin_notes = f"{admin_notes} | Catatan Guru: {feedback}" if admin_notes else feedback

    if not new_status or new_score is None:
        flash("Status keputusan dan nilai akhir wajib diisi.", 'warning')
        return redirect(url_for('evaluations.detail', submission_id=submission.id))

    orig_score = decision.final_score
    orig_status = decision.decision_status

    decision.decision_status = new_status
    decision.final_score = new_score
    decision.admin_notes = admin_notes
    decision.is_overridden = True
    decision.decided_by_id = current_user.id
    decision.decided_at = datetime.utcnow()

    submission.status = new_status
    submission.final_score = new_score

    # Sinkronisasi status TeacherCompetency
    teacher_comp = TeacherCompetency.query.filter_by(
        teacher_id=submission.teacher_id,
        material_id=submission.material_id
    ).first()
    if teacher_comp:
        teacher_comp.status = new_status
        teacher_comp.latest_score = new_score
        teacher_comp.last_evaluated_at = datetime.utcnow()

    db.session.commit()

    AuditService.log('ADMIN_OVERRIDE', 'FinalAssessmentDecision', decision.id, {
        'old_score': orig_score,
        'new_score': new_score,
        'old_status': orig_status,
        'new_status': new_status,
        'admin_notes': admin_notes
    })

    flash("Keputusan akhir penilaian berhasil disetujui / diperbarui oleh Admin.", 'success')
    return redirect(url_for('evaluations.detail', submission_id=submission.id))

override_decision = override

@evaluations_bp.route('/<int:submission_id>/report')
@login_required
def report(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    evaluation = submission.ai_evaluation
    decision = submission.final_decision

    return render_template(
        'evaluations/report.html',
        submission=submission,
        evaluation=evaluation,
        decision=decision
    )

print_report = report

@evaluations_bp.route('/rekap')
@login_required
def rekap():
    materials = UKGMaterial.query.order_by(UKGMaterial.code).all()
    teachers = Teacher.query.order_by(Teacher.name).all()

    teacher_data = []
    for t in teachers:
        comps = TeacherCompetency.query.filter_by(teacher_id=t.id).all()
        mat_map = {c.material_id: c for c in comps}

        passed_count = sum(1 for c in comps if c.status == 'passed')
        total_mats = len(materials)

        if total_mats > 0 and passed_count == total_mats:
            summary = {
                'label': f'Kompeten Penuh ({passed_count}/{total_mats})',
                'badge_class': 'bg-emerald-100 text-emerald-800 border-emerald-300'
            }
        elif passed_count > 0:
            summary = {
                'label': f'Kompeten Sebagian ({passed_count}/{total_mats})',
                'badge_class': 'bg-amber-100 text-amber-800 border-amber-300'
            }
        else:
            summary = {
                'label': f'Belum Kompeten ({passed_count}/{total_mats})',
                'badge_class': 'bg-slate-100 text-slate-700 border-slate-300'
            }

        teacher_data.append({
            'teacher': t,
            'summary': summary,
            'mat_map': mat_map
        })

    return render_template('evaluations/rekap.html', materials=materials, teacher_data=teacher_data)

@evaluations_bp.route('/audit-logs')
@login_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '').strip()

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)

    pagination = query.paginate(page=page, per_page=20, error_out=False)
    logs = pagination.items

    return render_template(
        'evaluations/audit_logs.html',
        logs=logs,
        pagination=pagination,
        action_filter=action_filter
    )

@evaluations_bp.route('/rekap/export-excel')
@login_required
def export_rekap_excel():
    """
    Export Matriks Rekapitulasi Kompetensi Guru ke format Excel (.xlsx)
    Lengkap dengan styling warna status kelulusan modular.
    """
    
    materials = UKGMaterial.query.order_by(UKGMaterial.code).all()
    teachers = Teacher.query.order_by(Teacher.name).all()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekap Kompetensi UKG"
    ws.views.sheetView[0].showGridLines = True
    
    # Styling Palet Warna
    header_fill = PatternFill(start_color="312E81", end_color="312E81", fill_type="solid") # Indigo gelap
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    passed_fill = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid") # Hijau lembut
    passed_font = Font(name="Calibri", size=10, bold=True, color="065F46")
    
    failed_fill = PatternFill(start_color="FFE4E6", end_color="FFE4E6", fill_type="solid") # Merah lembut
    failed_font = Font(name="Calibri", size=10, bold=True, color="9F1239")
    
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    
    # 1. Judul Laporan
    ws.merge_cells("A1:H1")
    ws["A1"] = "REKAPITULASI KOMPETENSI GURU - UJI KOMPETENSI GURU (UKG)"
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    
    ws["A2"] = f"Waktu Unduh: {datetime.now().strftime('%d %B %Y, %H:%M WIB')} | Diunduh oleh: {current_user.name}"
    ws["A2"].font = Font(name="Calibri", size=9, italic=True, color="64748B")
    # 2. Header Tabel (Mulai Baris 4)
    headers = ["No", "Nama Guru", "NIP", "Asal Sekolah", "Jenjang / Unit", "Status Keseluruhan"]
    for m in materials:
        headers.append(f"{m.code}\n({m.title})")
    row_num = 4
    for col_idx, header_text in enumerate(headers, 1):
        cell = ws.cell(row=row_num, column=col_idx, value=header_text)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[row_num].height = 32
    # 3. Baris Data Guru
    row_num = 5
    for idx, t in enumerate(teachers, 1):
        comps = TeacherCompetency.query.filter_by(teacher_id=t.id).all()
        mat_map = {c.material_id: c for c in comps}
        passed_count = sum(1 for c in comps if c.status == 'passed')
        total_mats = len(materials)
        if total_mats > 0 and passed_count == total_mats:
            overall_status = f"Kompeten Penuh ({passed_count}/{total_mats})"
        elif passed_count > 0:
            overall_status = f"Kompeten Sebagian ({passed_count}/{total_mats})"
        else:
            overall_status = f"Belum Kompeten ({passed_count}/{total_mats})"
        # Kolom Data Identitas
        row_data = [
            idx,
            t.name,
            t.nip or "-",
            t.school_origin or "-",
            t.grade_level or "-",
            overall_status
        ]
        # Tulis identitas
        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_idx, value=val)
            cell.alignment = center_align if col_idx in [1, 3, 5, 6] else left_align
            cell.font = Font(name="Calibri", size=10)
            cell.border = thin_border
        # Kolom Nilai Modular per Materi
        for m_idx, m in enumerate(materials, start=len(row_data) + 1):
            cell = ws.cell(row=row_num, column=m_idx)
            cell.alignment = center_align
            cell.border = thin_border
            
            if m.id in mat_map:
                comp = mat_map[m.id]
                score_str = f"{comp.latest_score:.1f}" if comp.latest_score is not None else "-"
                
                if comp.status == 'passed':
                    cell.value = f"LULUS ({score_str})"
                    cell.fill = passed_fill
                    cell.font = passed_font
                elif comp.status == 'not_passed':
                    cell.value = f"GAGAL ({score_str})"
                    cell.fill = failed_fill
                    cell.font = failed_font
                elif comp.status == 'in_progress':
                    cell.value = "PROSES"
                    cell.font = Font(name="Calibri", size=10, italic=True, color="4338CA")
                else:
                    cell.value = "Belum Dinilai"
                    cell.font = Font(name="Calibri", size=10, color="94A3B8")
            else:
                cell.value = "-"
                cell.font = Font(name="Calibri", size=10, color="CBD5E1")
        ws.row_dimensions[row_num].height = 22
        row_num += 1
    # 4. Auto-fit Lebar Kolom
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            # Abaikan baris judul gabungan
            if cell.row < 4:
                continue
            val_str = str(cell.value or "")
            if "\n" in val_str:
                val_str = max(val_str.split("\n"), key=len)
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
    # 5. Kembalikan Berkas Excel ke Browser
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"Rekap_Kompetensi_UKG_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )
    
    
    