from app.extensions import db


class Facility(db.Model):
    __tablename__ = 'facilities'

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    facility_type = db.Column(db.String(10), nullable=False)  # 'outdoor' or 'indoor'
    capacity = db.Column(db.Integer)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    reservations = db.relationship('Reservation', backref='facility', lazy='dynamic')
    blocks = db.relationship('SchoolBlock', backref='facility', lazy='dynamic')

    TYPE_OUTDOOR = 'outdoor'
    TYPE_INDOOR = 'indoor'

    TYPE_LABELS = {
        'outdoor': '室外',
        'indoor': '室内',
    }

    @property
    def type_label(self):
        return self.TYPE_LABELS.get(self.facility_type, self.facility_type)

    @property
    def full_name(self):
        return f'{self.school.name} - {self.name}'

    def __repr__(self):
        return f'<Facility {self.full_name}>'
