"""初期データ投入スクリプト（動作確認用）"""
import sys
import os
from datetime import date, time, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.organization import Organization
from app.models.school import School
from app.models.facility import Facility
from app.models.coach import Coach
from app.models.reservation import Reservation
from app.models.school_block import SchoolBlock
from app.models.notification import Notification


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        if School.query.first():
            print('データは既に存在します。スキップします。')
            return

        # === 学校データ ===
        inami = School(name='稲美中学校', code='inami', address='兵庫県加古郡稲美町')
        inami_kita = School(name='稲美北中学校', code='inami_kita', address='兵庫県加古郡稲美町')
        db.session.add_all([inami, inami_kita])
        db.session.flush()

        # === 施設データ ===
        facility_defs = [
            ('グラウンド', 'outdoor', '校庭グラウンド'),
            ('テニスコート', 'outdoor', 'テニスコート'),
            ('体育館', 'indoor', '体育館'),
            ('卓球場', 'indoor', '卓球場'),
            ('武道場', 'indoor', '武道場（柔道・剣道）'),
            ('特別教室棟', 'indoor', '特別教室（音楽室・美術室等）'),
        ]
        facilities_by_school = {}
        for school in [inami, inami_kita]:
            fac_list = []
            for name, ftype, desc in facility_defs:
                f = Facility(
                    school_id=school.id, name=name, facility_type=ftype,
                    description=desc, is_active=True,
                )
                db.session.add(f)
                fac_list.append(f)
            facilities_by_school[school.id] = fac_list
        db.session.flush()

        # === 管理者・学校ユーザー ===
        admin = User(
            username='admin', email='admin@inachalle.jp',
            display_name='事務局管理者', role=User.ROLE_ADMIN,
        )
        admin.set_password('admin123')

        school_user = User(
            username='school_inami', email='school@inami.jp',
            display_name='稲美中学校担当', role=User.ROLE_SCHOOL,
        )
        school_user.set_password('school123')
        db.session.add_all([admin, school_user])

        # === 団体（いなチャレ認定） ===
        soccer = Organization(
            name='いなみサッカークラブ', representative='田中太郎',
            contact_email='soccer@inami.jp', contact_phone='079-xxx-1111',
            registration_number='INA-001',
            is_approved=True, is_inachalle_certified=True,
        )
        db.session.add(soccer)
        db.session.flush()
        tanaka = User(
            username='tanaka', email='tanaka@example.com',
            display_name='田中太郎', role=User.ROLE_ORG_LEADER,
            organization_id=soccer.id,
        )
        tanaka.set_password('tanaka123')
        db.session.add(tanaka)

        # === 団体（一般） ===
        tennis = Organization(
            name='稲美テニス同好会', representative='鈴木一郎',
            contact_email='tennis@inami.jp', contact_phone='079-xxx-2222',
            registration_number='GEN-001',
            is_approved=True, is_inachalle_certified=False,
        )
        db.session.add(tennis)
        db.session.flush()
        suzuki = User(
            username='suzuki', email='suzuki@example.com',
            display_name='鈴木一郎', role=User.ROLE_ORG_LEADER,
            organization_id=tennis.id,
        )
        suzuki.set_password('suzuki123')
        db.session.add(suzuki)

        # === 一般住民 ===
        yamada = User(
            username='yamada', email='yamada@example.com',
            display_name='山田花子', role=User.ROLE_RESIDENT,
        )
        yamada.set_password('yamada123')
        db.session.add(yamada)

        # === 指導者（Coach）=== Plaud 04-08 対応
        coach_user = User(
            username='coach_ito', email='ito@example.com',
            display_name='伊藤 健一', role=User.ROLE_COACH,
        )
        coach_user.set_password('coach123')
        db.session.add(coach_user)
        db.session.flush()

        from app.utils.fiscal import FIXED_PAID_RATE, is_fixed_rate_period
        default_paid_rate = FIXED_PAID_RATE if is_fixed_rate_period() else 1482

        coach_ito = Coach(
            full_name='伊藤 健一', full_name_kana='イトウ ケンイチ',
            email='ito@example.com', phone='090-xxx-3333',
            qualification='サッカー指導者ライセンスC級',
            compensation_type=Coach.COMPENSATION_PAID, hourly_rate=default_paid_rate,
            is_teacher_dual_role=False,
            user_id=coach_user.id,
        )
        coach_ito.organizations = [soccer]
        db.session.add(coach_ito)

        # 教員兼職の指導者（週19h45m上限チェック対象）
        coach_kobayashi = Coach(
            full_name='小林 美和', full_name_kana='コバヤシ ミワ',
            email='kobayashi@example.com', phone='090-xxx-4444',
            qualification='中学校教員（保健体育）',
            compensation_type=Coach.COMPENSATION_UNPAID, hourly_rate=0,
            is_teacher_dual_role=True,
        )
        coach_kobayashi.organizations = [soccer, tennis]  # ダブルカウント候補
        db.session.add(coach_kobayashi)

        # === 保護者 === Plaud 04-15 対応
        parent_user = User(
            username='parent_sato', email='sato@example.com',
            display_name='佐藤 由美', role=User.ROLE_PARENT,
            child_organization_id=soccer.id,
        )
        parent_user.set_password('parent123')
        db.session.add(parent_user)

        db.session.commit()

        # === 予約サンプル（今週・来週） ===
        today = date.today()
        for i, h in enumerate([16, 18]):
            r = Reservation(
                facility_id=facilities_by_school[inami.id][2].id,  # 体育館
                organization_id=soccer.id, reserved_by=tanaka.id,
                date=today + timedelta(days=i + 1),
                start_time=time(h, 0), end_time=time(h + 1, 0),
                purpose='通常練習', expected_participants=18,
                status=Reservation.STATUS_CONFIRMED,
            )
            db.session.add(r)
        for i in range(3):
            r = Reservation(
                facility_id=facilities_by_school[inami.id][1].id,  # テニスコート
                organization_id=tennis.id, reserved_by=suzuki.id,
                date=today + timedelta(days=i + 2),
                start_time=time(17, 0), end_time=time(18, 30),
                purpose='練習試合', expected_participants=8,
                status=Reservation.STATUS_CONFIRMED,
            )
            db.session.add(r)

        # === 学校ブロック（運動会準備） ===
        next_sat = today + timedelta(days=(5 - today.weekday()) % 7 or 7)
        db.session.add(SchoolBlock(
            school_id=inami.id, date=next_sat, reason='運動会準備のため終日ブロック',
            start_time=None, end_time=None, blocked_by=school_user.id,
        ))

        # === 通知サンプル ===
        db.session.add(Notification(
            user_id=parent_user.id,
            title='今週末の練習について',
            message='土曜の練習は運動会準備のため中止となります。',
        ))
        db.session.add(Notification(
            user_id=coach_user.id,
            title='謝金明細が更新されました',
            message='今月分の活動時間が反映されています。マイページでご確認ください。',
        ))

        db.session.commit()

        print('✅ 初期データを投入しました！\n')
        print('=== ログイン情報 ===')
        print('事務局管理者:       admin         / admin123')
        print('学校担当:           school_inami  / school123')
        print('認定団体代表:       tanaka        / tanaka123  （3ヶ月先まで予約可）')
        print('一般団体代表:       suzuki        / suzuki123  （1ヶ月先まで予約可）')
        print('一般住民:           yamada        / yamada123')
        print('指導者:             coach_ito     / coach123   （/my/dashboard）')
        print('保護者:             parent_sato   / parent123  （/family/dashboard）')
        print()
        print('=== サンプルデータ ===')
        print('・2校 × 6施設 = 12施設')
        print('・2団体（認定1・一般1）、指導者2名（1名は教員兼職・複数所属）')
        print('・今週～来週の予約5件、学校ブロック1件、通知2件')


if __name__ == '__main__':
    seed()
