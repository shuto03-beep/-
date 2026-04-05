from datetime import datetime
from app.extensions import db


class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    reserved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='confirmed')
    purpose = db.Column(db.Text)
    expected_participants = db.Column(db.Integer)
    notes = db.Column(db.Text)
    cancelled_at = db.Column(db.DateTime)
    cancelled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    cancellation_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[reserved_by], backref='reservations')
    canceller = db.relationship('User', foreign_keys=[cancelled_by])

    STATUS_CONFIRMED = 'confirmed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_LABELS = {
        'confirmed': '確定',
        'cancelled': 'キャンセル済み',
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    @property
    def is_active(self):
        return self.status == self.STATUS_CONFIRMED

    @property
    def time_range(self):
        return f'{self.start_time.strftime("%H:%M")}〜{self.end_time.strftime("%H:%M")}'

    def __repr__(self):
        return f'<Reservation {self.id} {self.date} {self.time_range}>'
