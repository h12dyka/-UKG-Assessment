from datetime import datetime
from app.extensions import db

class Rubric(db.Model):
    __tablename__ = 'rubrics'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('ukg_materials.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    project_instructions = db.Column(db.Text, nullable=False)
    competencies_measured = db.Column(db.Text, nullable=False)
    passing_grade = db.Column(db.Float, default=75.0, nullable=False)
    allowed_file_types = db.Column(db.String(255), default='.jpeg, .jpg, .png', nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    material = db.relationship('UKGMaterial', back_populates='rubrics')
    versions = db.relationship('RubricVersion', back_populates='rubric', cascade='all, delete-orphan', order_by='desc(RubricVersion.version_number)')
    creator = db.relationship('User')
    
    @property
    def active_version(self):
        for v in self.versions:
            if v.status == 'active':
                return v
        return None

    def __repr__(self):
        return f'<Rubric {self.title}>'


class RubricVersion(db.Model):
    __tablename__ = 'rubric_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    rubric_id = db.Column(db.Integer, db.ForeignKey('rubrics.id', ondelete='CASCADE'), nullable=False, index=True)
    version_number = db.Column(db.Integer, default=1, nullable=False) 
    version_label = db.Column(db.String(50), default='v1.0', nullable=False)
    status = db.Column(db.String(50), default='draft', nullable=False) # draft, pending_approval, active, archived
    effective_date = db.Column(db.Date, nullable=True)
    change_notes = db.Column(db.Text, nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    rubric = db.relationship('Rubric', back_populates='versions')
    criteria = db.relationship('RubricCriterion', back_populates='version', cascade='all, delete-orphan', order_by='RubricCriterion.sort_order')
    submissions = db.relationship('Submission', back_populates='rubric_version')

    @property
    def total_weight(self):
        return sum(c.weight for c in self.criteria) if self.criteria else 0.0


class RubricCriterion(db.Model):
    __tablename__ = 'rubric_criteria'
    
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey('rubric_versions.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False) # e.g. Ide / Kreatifitas / Tehnik (70%)
    description = db.Column(db.Text, nullable=True)
    weight = db.Column(db.Float, nullable=False) # Bobot persentase
    scale_min = db.Column(db.Float, default=0.0, nullable=False)
    scale_max = db.Column(db.Float, default=100.0, nullable=False)
    is_mandatory = db.Column(db.Boolean, default=False, nullable=False)
    mandatory_min_score = db.Column(db.Float, default=70.0, nullable=True)
    evidence_indicators = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    version = db.relationship('RubricVersion', back_populates='criteria')
