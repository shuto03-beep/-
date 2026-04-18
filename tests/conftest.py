import os

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('FLASK_ENV', 'testing')

from datetime import date, time

import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models.facility import Facility
from app.models.organization import Organization
from app.models.reservation import Reservation
from app.models.school import School
from app.models.user import User


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    user = User(username='admin', email='admin@test.jp', display_name='管理者', role=User.ROLE_ADMIN)
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def leader_user(app, approved_org):
    user = User(
        username='leader', email='leader@test.jp', display_name='代表', role=User.ROLE_ORG_LEADER,
        organization_id=approved_org.id,
    )
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def school(app):
    s = School(name='稲美中学校', code='INA01')
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def facility(app, school):
    f = Facility(school_id=school.id, name='体育館', facility_type='indoor')
    db.session.add(f)
    db.session.commit()
    return f


@pytest.fixture
def approved_org(app):
    org = Organization(
        name='いなチャレ陸上クラブ', representative='山田',
        is_approved=True, is_inachalle_certified=True,
    )
    db.session.add(org)
    db.session.commit()
    return org


@pytest.fixture
def login_admin(client, admin_user):
    with client.session_transaction() as s:
        s['_user_id'] = str(admin_user.id)
        s['_fresh'] = True
    return admin_user


def make_reservation(facility, org, user, status=Reservation.STATUS_CONFIRMED, at=time(16, 45)):
    r = Reservation(
        facility_id=facility.id, organization_id=org.id, reserved_by=user.id,
        date=date.today(), start_time=at,
        end_time=time((at.hour + 1) % 24, at.minute),
        status=status,
    )
    db.session.add(r)
    db.session.commit()
    return r
