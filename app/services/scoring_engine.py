from typing import Dict, Any, Tuple
from app.extensions import db
from app.models.evaluation import AIEvaluation, EvaluationCriteriaResult, FinalAssessmentDecision
from app.models.material import TeacherCompetency
from app.models.submission import Submission

class ScoringEngine:
    @staticmethod
    def calculate_evaluation_result(
        submission: Submission,
        ai_result_data,
        raw_response: str,
        ai_model: str
    ) -> AIEvaluation:
        """
        Menghitung nilai akhir secara deterministik di backend berdasarkan
        rumus bobot rubrik resmi dan menerapkan aturan kelulusan.
        """
        rubric_version = submission.rubric_version
        rubric = rubric_version.rubric
        criteria_map = {c.id: c for c in rubric_version.criteria}

        total_calculated_score = 0.0
        mandatory_failed = False
        mandatory_fail_reasons = []

        # 1. Hitung skor terbobot per kriteria
        criteria_result_objects = []
        for eval_item in ai_result_data.criteria_evaluations:
            criterion = criteria_map.get(eval_item.criterion_id)
            if not criterion:
                continue

            score = float(eval_item.score)
            weight = float(criterion.weight)
            weighted_score = round(score * (weight / 100.0), 2)
            total_calculated_score += weighted_score

            # Cek syarat kriteria wajib (Gatekeeper)
            if criterion.is_mandatory:
                min_req = float(criterion.mandatory_min_score)
                if score < min_req:
                    mandatory_failed = True
                    mandatory_fail_reasons.append(
                        f"Kriteria wajib '{criterion.name}' memperoleh skor {score:.1f} (di bawah batas minimal {min_req:.1f})."
                    )

            criteria_result_objects.append(
                EvaluationCriteriaResult(
                    criterion_id=criterion.id,
                    criterion_name=criterion.name,
                    weight=weight,
                    score=score,
                    weighted_score=weighted_score,
                    evidence_found=eval_item.evidence_found,
                    rationale=eval_item.rationale,
                    shortcomings=eval_item.shortcomings or "-",
                    recommendations=eval_item.recommendations or "-",
                    is_sufficient=eval_item.is_sufficient
                )
            )

        final_calculated_score = round(total_calculated_score, 2)

        # 2. Tentukan status kelulusan berdasarkan aturan backend
        passing_grade = float(rubric.passing_grade)
        has_sufficient = ai_result_data.has_sufficient_evidence
        is_valid_project = getattr(ai_result_data, 'is_valid_project', True)

        # Cek jika berkas didiskualifikasi oleh Gatekeeper (Bukan Proyek / Nilai 0)
        if not is_valid_project or final_calculated_score == 0.0:
            status = 'not_passed'
            rejection = getattr(ai_result_data, 'rejection_reason', '') or "Berkas yang diunggah tidak teridentifikasi sebagai proyek yang sesuai (Bukan Proyek / Tidak Relevan)."
            status_reason = f"DISKUALIFIKASI (BELUM LULUS): {rejection}"
        elif not has_sufficient:
            status = 'pending_admin_review'
            status_reason = "Bukti dalam berkas proyek dinilai belum memadai atau tidak sesuai spesifikasi penugasan."
        elif mandatory_failed:
            status = 'not_passed'
            status_reason = f"Tidak memenuhi syarat kelulusan wajib: {'; '.join(mandatory_fail_reasons)}"
        elif final_calculated_score >= passing_grade:
            status = 'passed'
            status_reason = f"LULUS. Nilai akhir {final_calculated_score:.2f} melampaui passing grade ({passing_grade:.2f}) dan seluruh kriteria wajib terpenuhi."
        else:
            status = 'not_passed'
            status_reason = f"BELUM LULUS. Nilai akhir {final_calculated_score:.2f} belum mencapai passing grade ({passing_grade:.2f})."

        # 3. Simpan entitas AIEvaluation        # 3. Bersihkan evaluasi lama jika sudah ada (agar bisa dinilai ulang)
        existing_eval = AIEvaluation.query.filter_by(submission_id=submission.id).first()
        if existing_eval:
            db.session.delete(existing_eval)
            db.session.flush()

        evaluation = AIEvaluation(
            submission_id=submission.id,
            rubric_version_id=rubric_version.id,
            ai_model=ai_model,
            raw_ai_response=raw_response,
            has_sufficient_evidence=has_sufficient,
            confidence_score=ai_result_data.confidence_score,
            overall_summary=ai_result_data.overall_summary,
            calculated_ai_score=final_calculated_score,
            calculated_status=status,
            status_reason=status_reason,
            criteria_results=criteria_result_objects
        )
        db.session.add(evaluation)
        db.session.flush()

        # 4. Inisialisasi FinalAssessmentDecision (menunggu persetujuan / koreksi Admin)
        decision = FinalAssessmentDecision.query.filter_by(submission_id=submission.id).first()
        if not decision:
            decision = FinalAssessmentDecision(
                submission_id=submission.id,
                evaluation_id=evaluation.id,
                decision_status=status,
                final_score=final_calculated_score,
                admin_notes="Nilai awal dihasilkan otomatis oleh Evaluator sesuai konfigurasi rubrik resmi.",
                is_overridden=False,
                original_ai_score=final_calculated_score,
                decided_by_id=None
            )
            db.session.add(decision)
        else:
            decision.evaluation_id = evaluation.id
            if not decision.is_overridden:
                decision.decision_status = status
                decision.final_score = final_calculated_score
                decision.original_ai_score = final_calculated_score

        # 5. Sinkronisasi status Submission
        submission.final_score = decision.final_score
        submission.status = decision.decision_status

        # 6. Perbarui status TeacherCompetency untuk materi ini secara terisolasi
        teacher_comp = TeacherCompetency.query.filter_by(
            teacher_id=submission.teacher_id,
            material_id=submission.material_id
        ).first()

        if teacher_comp:
            teacher_comp.status = decision.decision_status
            teacher_comp.latest_score = decision.final_score
            teacher_comp.last_evaluated_at = evaluation.evaluated_at

        db.session.commit()
        return evaluation
