"""初期データ投入スクリプト"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.organization import Organization
from app.models.school import School
from app.models.facility import Facility


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        # 既存データチェック
        if School.query.first():
            print('データは既に存在します。スキップします。')
            return

        # 学校データ
        inami = School(
            name='稲美中学校',
            code='inami',
            address='兵庫県加古郡稲美町',
        )
        inami_kita = School(
            name='稲美北中学校',
            code='inami_kita',
            address='兵庫県加古郡稲美町',
        )
        db.session.add_all([inami, inami_kita])
        db.session.flush()

        # 施設データ（各学校に6施設ずつ）
        facility_defs = [
            ('グラウンド', 'outdoor', '校庭グラウンド'),
            ('テニスコート', 'outdoor', 'テニスコート'),
            ('体育館', 'indoor', '体育館'),
            ('卓球場', 'indoor', '卓球場'),
            ('武道場', 'indoor', '武道場（柔道・剣道）'),
            ('特別教室棟', 'indoor', '特別教室（音楽室・美術室等）'),
        ]

        for school in [inami, inami_kita]:
            for name, ftype, desc in facility_defs:
                facility = Facility(
                    school_id=school.id,
                    name=name,
                    facility_type=ftype,
                    description=desc,
                    is_active=True,
                )
                db.session.add(facility)

        # 管理者ユーザー（事務局）
        admin = User(
            username='admin',
            email='admin@inachalle.jp',
            display_name='事務局管理者',
            role=User.ROLE_ADMIN,
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # サンプル学校ユーザー
        school_user = User(
            username='school_inami',
            email='school@inami.jp',
            display_name='稲美中学校担当',
            role=User.ROLE_SCHOOL,
        )
        school_user.set_password('school123')
        db.session.add(school_user)

        # サンプル団体
        org = Organization(
            name='いなみサッカークラブ',
            representative='田中太郎',
            contact_email='soccer@inami.jp',
            contact_phone='079-xxx-xxxx',
            registration_number='INA-001',
            is_approved=True,
        )
        db.session.add(org)
        db.session.flush()

        # 団体責任者ユーザー
        org_leader = User(
            username='tanaka',
            email='tanaka@example.com',
            display_name='田中太郎',
            role=User.ROLE_ORG_LEADER,
            organization_id=org.id,
        )
        org_leader.set_password('tanaka123')
        db.session.add(org_leader)

        # 一般住民ユーザー
        resident = User(
            username='yamada',
            email='yamada@example.com',
            display_name='山田花子',
            role=User.ROLE_RESIDENT,
        )
        resident.set_password('yamada123')
        db.session.add(resident)

        db.session.commit()
        print('初期データを投入しました！')
        print()
        print('=== ログイン情報 ===')
        print('事務局管理者: admin / admin123')
        print('学校担当: school_inami / school123')
        print('団体責任者: tanaka / tanaka123')
        print('一般住民: yamada / yamada123')


if __name__ == '__main__':
    seed()
