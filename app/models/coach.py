from datetime import datetime

from app.extensions import db


coach_organizations = db.Table(
    'coach_organizations',
    db.Column('coach_id', db.Integer, db.ForeignKey('coaches.id'), primary_key=True),
    db.Column('organization_id', db.Integer, db.ForeignKey('organizations.id'), primary_key=True),
)


class Coach(db.Model):
    __tablename__ = 'coaches'

    COMPENSATION_PAID = 'paid'        # 有償
    COMPENSATION_UNPAID = 'unpaid'    # 無償

    COMPENSATION_LABELS = {
        COMPENSATION_PAID: '有償',
        COMPENSATION_UNPAID: '無償',
    }

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    full_name_kana = db.Column(db.String(200))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    birth_date = db.Column(db.Date)
    qualification = db.Column(db.String(200))
    compensation_type = db.Column(db.String(20), nullable=False, default=COMPENSATION_UNPAID)
    hourly_rate = db.Column(db.Integer, default=0)  # 円/時間
    is_teacher_dual_role = db.Column(db.Boolean, default=False)  # 教職員兼職兼業
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('coach_profile', uselist=False))

    organizations = db.relationship(
        'Organization',
        secondary=coach_organizations,
        backref=db.backref('coaches', lazy='dynamic'),
    )

    __table_args__ = (
        db.UniqueConstraint('full_name', 'birth_date', name='uq_coach_fullname_birth'),
    )

    @property
    def compensation_label(self):
        return self.COMPENSATION_LABELS.get(self.compensation_type, self.compensation_type)

    @property
    def organization_count(self):
        return len(self.organizations)

    @property
    def is_multi_affiliated(self):
        """複数の団体に所属している（ダブルカウントリスク）"""
        return self.organization_count > 1

    def __repr__(self):
        return f'<Coach {self.full_name}>'
