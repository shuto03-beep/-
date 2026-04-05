from datetime import datetime
from app.extensions import db


class SchoolBlock(db.Model):
    __tablename__ = 'school_blocks'

    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=True)  # NULL = 終日ブロック
    end_time = db.Column(db.Time, nullable=True)
    reason = db.Column(db.Text, nullable=False)
    blocked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    school = db.relationship('School', backref=db.backref('blocks', lazy='dynamic'))
    user = db.relationship('User', backref='blocks_created')

    @property
    def is_all_day(self):
        return self.start_time is None

    @property
    def facility_name(self):
        if self.facility:
            return self.facility.name
        return '全施設'

    def __repr__(self):
        return f'<SchoolBlock {self.school.name} {self.date} {self.reason}>'
