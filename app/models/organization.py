from datetime import datetime
from app.extensions import db


class Organization(db.Model):
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    representative = db.Column(db.String(100), nullable=False)
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    registration_number = db.Column(db.String(50), unique=True)
    is_approved = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reservations = db.relationship('Reservation', backref='organization', lazy='dynamic')

    @property
    def status_label(self):
        return '承認済み' if self.is_approved else '承認待ち'

    def __repr__(self):
        return f'<Organization {self.name}>'
