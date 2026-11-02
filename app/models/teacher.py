from datetime import datetime
from app.extensions import db

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    nip = db.Column(db.String(50), unique=True, nullable=False, index=True) # Nomor Identitas Guru
    name = db.Column(db.String(150), nullable=False, index=True)
    school_origin = db.Column(db.String(200), nullable=False) # Asal Sekolah / Unit
    grade_level = db.Column(db.String(50), nullable=False) # SD, SMP, SMA, SMK
    classes_taught = db.Column(db.String(100), nullable=False) # Contoh: Kelas 1, Kelas 2
    email = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # relasi
    submissions = db.relationship('Submission', back_populates='teacher', cascade='all, delete-orphan')
    required_competencies = db.relationship('TeacherCompetency', back_populates='teacher', cascade='all, delete-orphan')
    
    def get_competency_summary(self):
        total = len(self.required_competencies)
        passed = sum(1 for c in self.required_competencies if c.status == 'passed')
        not_passed = sum(1 for c in self.required_competencies if c.status == 'not_passed')
        pending = total - (passed + not_passed)
        
        if total == 0:
            badge = "bg-slate-100 text-slate-700"
            label = "Belum Ada Materi"
        elif passed == total:
            badge = "bg-emerald-100 text-emerald-800"
            label = "Lulus Semua Materi"
        elif not_passed > 0:
            badge = "bg-rose-100 text-rose-800"
            label = f"{passed}/{total} Lulus (Perlu Remedial)"
        else:
            badge = "bg-amber-100 text-amber-800"
            label = f"{passed}/{total} Selesai"
            
        return {
            'total': total,
            'passed': passed,
            'not_passed': not_passed,
            'pending': pending,
            'badge_class': badge,
            'label': label
        }
        
    def __repr__(self):
        return f'<Teacher {self.nip} - {self.name}>'
