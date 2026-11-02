from datetime import datetime
from app.extensions import db

class AIEvaluation(db.Model):
    __tablename__ = 'ai_evaluations'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id', ondelete='CASCADE'), nullable=False, unique=True)
    rubric_version_id = db.Column(db.Integer, db.ForeignKey('rubric_versions.id', ondelete='RESTRICT'), nullable=False)
    ai_model = db.Column(db.String(80), nullable=False) # e.g. gemini-2.0-flash
    raw_ai_response = db.Column(db.Text, nullable=True)
    has_sufficient_evidence = db.Column(db.Boolean, default=True, nullable=False)
    confidence_score = db.Column(db.Float, nullable=True)
    overall_summary = db.Column(db.Text, nullable=True)
    calculated_ai_score = db.Column(db.Float, nullable=False) # Nilai matematis backend
    calculated_status = db.Column(db.String(40), nullable=False)
    status_reason = db.Column(db.Text, nullable=True)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)

    submission = db.relationship('Submission', back_populates='ai_evaluation')
    criteria_results = db.relationship('EvaluationCriteriaResult', back_populates='evaluation', cascade='all, delete-orphan')


class EvaluationCriteriaResult(db.Model):
    __tablename__ = 'evaluation_criteria_results'

    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('ai_evaluations.id', ondelete='CASCADE'), nullable=False, index=True)
    criterion_id = db.Column(db.Integer, db.ForeignKey('rubric_criteria.id', ondelete='RESTRICT'), nullable=False)
    criterion_name = db.Column(db.String(150), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    score = db.Column(db.Float, nullable=False) # 0 - 100
    weighted_score = db.Column(db.Float, nullable=False)
    evidence_found = db.Column(db.Text, nullable=False)
    rationale = db.Column(db.Text, nullable=False)
    shortcomings = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)
    is_sufficient = db.Column(db.Boolean, default=True, nullable=False)

    evaluation = db.relationship('AIEvaluation', back_populates='criteria_results')
    criterion = db.relationship('RubricCriterion')


class FinalAssessmentDecision(db.Model):
    __tablename__ = 'final_assessment_decisions'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id', ondelete='CASCADE'), nullable=False, unique=True)
    evaluation_id = db.Column(db.Integer, db.ForeignKey('ai_evaluations.id', ondelete='SET NULL'), nullable=True)
    decision_status = db.Column(db.String(40), nullable=False) # passed, not_passed, revised, pending_review
    final_score = db.Column(db.Float, nullable=False)
    admin_notes = db.Column(db.Text, nullable=True)
    is_overridden = db.Column(db.Boolean, default=False, nullable=False) # True jika Admin mengubah nilai AI
    original_ai_score = db.Column(db.Float, nullable=True)
    decided_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    decided_at = db.Column(db.DateTime, default=datetime.utcnow)

    submission = db.relationship('Submission', back_populates='final_decision')
    decided_by = db.relationship('User')

    @property
    def is_approved_by_admin(self):
        return self.decided_by_id is not None

    @property
    def admin_override_reason(self):
        return self.admin_notes
