from datetime import datetime
from app.extensions import db

class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id', ondelete='CASCADE'), nullable=False, index=True)
    material_id = db.Column(db.Integer, db.ForeignKey('ukg_materials.id', ondelete='CASCADE'), nullable=False, index=True)
    rubric_version_id = db.Column(db.Integer, db.ForeignKey('rubric_versions.id', ondelete='RESTRICT'), nullable=False, index=True)
    
    project_title = db.Column(db.String(250), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    attempt_number = db.Column(db.Integer, default=1, nullable=False)
    
    # Status: 'uploaded', 'queued', 'under_ai_review', 'pending_admin_review', 'passed', 'not_passed', 'failed_processing'
    status = db.Column(db.String(40), default='uploaded', nullable=False, index=True)
    final_score = db.Column(db.Float, nullable=True)
    
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relasi
    teacher = db.relationship('Teacher', back_populates='submissions')
    material = db.relationship('UKGMaterial', back_populates='submissions')
    rubric_version = db.relationship('RubricVersion', back_populates='submissions')
    files = db.relationship('ProjectFile', back_populates='submission', cascade='all, delete-orphan')
    ai_evaluation = db.relationship('AIEvaluation', back_populates='submission', uselist=False, cascade='all, delete-orphan')
    final_decision = db.relationship('FinalAssessmentDecision', back_populates='submission', uselist=False, cascade='all, delete-orphan')

    @property
    def status_label_id(self):
        labels = {
            'uploaded': 'Berkas Terunggah',
            'queued': 'Antrean Analisis',
            'under_ai_review': 'Sedang Dinilai AI',
            'pending_admin_review': 'Perlu Ditinjau Admin',
            'passed': 'Lulus',
            'not_passed': 'Belum Lulus',
            'failed_processing': 'Gagal Teknis'
        }
        return labels.get(self.status, self.status)

    @property
    def status_badge_class(self):
        classes = {
            'passed': 'bg-emerald-100 text-emerald-800 border-emerald-300',
            'not_passed': 'bg-rose-100 text-rose-800 border-rose-300',
            'pending_admin_review': 'bg-amber-100 text-amber-800 border-amber-300',
            'under_ai_review': 'bg-indigo-100 text-indigo-800 border-indigo-300 animate-pulse',
            'queued': 'bg-blue-100 text-blue-800 border-blue-300',
            'uploaded': 'bg-slate-100 text-slate-800 border-slate-300',
            'failed_processing': 'bg-red-100 text-red-900 border-red-300'
        }
        return classes.get(self.status, 'bg-slate-100 text-slate-700')


class ProjectFile(db.Model):
    __tablename__ = 'project_files'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id', ondelete='CASCADE'), nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False) # image, docx, pptx, xlsx, scratch, code, zip
    file_size = db.Column(db.BigInteger, nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    
    extracted_text = db.Column(db.Text, nullable=True)
    parser_metadata = db.Column(db.Text, nullable=True) # JSON serialisasi temuan parser
    parse_status = db.Column(db.String(30), default='success', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submission = db.relationship('Submission', back_populates='files')

    @property
    def human_size(self):
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"