from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='resident')
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    child_organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = db.relationship(
        'Organization', foreign_keys=[organization_id],
        backref=db.backref('members', lazy='dynamic'),
    )
    child_organization = db.relationship(
        'Organization', foreign_keys=[child_organization_id],
        backref=db.backref('parent_watchers', lazy='dynamic'),
    )

    ROLE_ADMIN = 'admin'
    ROLE_SCHOOL = 'school'
    ROLE_ORG_LEADER = 'org_leader'
    ROLE_ORG_MEMBER = 'org_member'
    ROLE_RESIDENT = 'resident'
    ROLE_COACH = 'coach'
    ROLE_PARENT = 'parent'

    ROLE_LABELS = {
        'admin': '事務局',
        'school': '学校',
        'org_leader': '団体責任者',
        'org_member': '団体メンバー',
        'resident': '一般住民',
        'coach': '指導者',
        'parent': '保護者',
    }

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def role_label(self):
        return self.ROLE_LABELS.get(self.role, self.role)

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_school(self):
        return self.role == self.ROLE_SCHOOL

    @property
    def is_org_leader(self):
        return self.role == self.ROLE_ORG_LEADER

    @property
    def is_coach(self):
        return self.role == self.ROLE_COACH

    @property
    def is_parent(self):
        return self.role == self.ROLE_PARENT

    @property
    def can_make_reservation(self):
        return self.role in (self.ROLE_ADMIN, self.ROLE_ORG_LEADER)

    def __repr__(self):
        return f'<User {self.username}>'
