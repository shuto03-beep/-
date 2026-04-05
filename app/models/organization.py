from datetime import datetime, date, timedelta
from app.extensions import db

# 予約可能期間の設定
INACHALLE_ADVANCE_DAYS = 90   # いなチャレ認定団体: 3ヶ月（90日）先まで予約可能
GENERAL_ADVANCE_DAYS = 30     # 一般団体: 1ヶ月（30日）先まで予約可能


class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    representative = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    registration_number = db.Column(db.String(50), unique=True)
    is_approved = db.Column(db.Boolean, default=False)
    is_inachalle_certified = db.Column(db.Boolean, default=False)  # いなチャレ認定団体
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reservations = db.relationship('Reservation', backref='organization', lazy='dynamic')

    @property
    def status_label(self):
        if not self.is_approved:
            return '承認待ち'
        return 'いなチャレ認定' if self.is_inachalle_certified else '一般承認済み'

    @property
    def advance_days(self):
        """この団体が何日先まで予約できるか"""
        return INACHALLE_ADVANCE_DAYS if self.is_inachalle_certified else GENERAL_ADVANCE_DAYS

    @property
    def earliest_bookable_date(self):
        """予約可能な最も早い日（明日以降）"""
        tomorrow = date.today() + timedelta(days=1)
        return tomorrow

    @property
    def latest_bookable_date(self):
        """予約可能な最も遅い日"""
        return date.today() + timedelta(days=self.advance_days)

    def can_book_date(self, target_date):
        """指定日に予約できるかどうか"""
        return self.earliest_bookable_date <= target_date <= self.latest_bookable_date

    def __repr__(self):
        return f'<Organization {self.name}>'
