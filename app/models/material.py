from datetime import datetime
from app.extensions import db

class UKGMaterial(db.Model):
    __tablename__ = 'ukg_materials'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    grade_level = db.Column(db.String(50), nullable=False)
    class_level = db.Column(db.String(50), nullable=False)
    semester = db.Column(db.String(30), default='Semester 1', nullable=False)
    academic_year = db.Column(db.String(50), default='2025/2026', nullable=False)
    subject = db.Column(db.String(100), default='Informatika / Komputer', nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relasi
    teacher_assignments = db.relationship('TeacherCompetency', back_populates='material', cascade='all, delete-orphan')
    rubrics = db.relationship('Rubric', back_populates='material', cascade='all, delete-orphan')
    submissions = db.relationship('Submission', back_populates='material', cascade='all, delete-orphan')
    
    @property
    def full_name(self):
        sem_str = f" [{self.semester}]" if self.semester else ""
        return f"[{self.code}] {self.title} - {self.grade_level} ({self.class_level}){sem_str}"

    def __repr__(self):
        return f'<UKGMaterial {self.code} - {self.title}>'


class TeacherCompetency(db.Model):
    """
    Pemetaan materi wajib per guru.
    Kelulusan satu materi terisolasi di sini dan tidak otomatis meluluskan materi lain.
    """
    __tablename__ = 'teacher_competencies'
    
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id', ondelete='CASCADE'), nullable=False, index=True)
    material_id = db.Column(db.Integer, db.ForeignKey('ukg_materials.id', ondelete='CASCADE'), nullable=False, index=True)
    is_required = db.Column(db.Boolean, default=True, nullable=False)
    
    # status kelulusan materi ini: 'not_started', 'in_progress', 'passed', 'not_passed'
    status = db.Column(db.String(50), default='not_started', nullable=False)
    latest_score = db.Column(db.Float, nullable=True)
    last_evaluated_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relasi
    teacher = db.relationship('Teacher', back_populates='required_competencies')
    material = db.relationship('UKGMaterial', back_populates='teacher_assignments')
