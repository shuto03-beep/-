from app.extensions import db


class School(db.Model):
    __tablename__ = 'schools'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(200))
    contact_phone = db.Column(db.String(20))

    facilities = db.relationship('Facility', backref='school', lazy='dynamic')

    def __repr__(self):
        return f'<School {self.name}>'
