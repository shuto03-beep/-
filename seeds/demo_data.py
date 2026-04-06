"""デモデータ投入スクリプト（予約・ブロック・通知・活動ログ）"""
import random
from datetime import date, time, timedelta, datetime

from app.extensions import db
from app.models.reservation import Reservation
from app.models.school_block import SchoolBlock
from app.models.notification import Notification
from app.models.activity_log import ActivityLog
from app.models.facility import Facility
from app.models.organization import Organization
from app.models.user import User
from app.models.school import School


def create_demo_data():
    # 既にデモデータがあればスキップ
    if Reservation.query.count() > 0:
        print('デモデータは既に存在します。スキップします。')
        return

    random.seed(42)
    today = date.today()

    # 既存データの取得
    inami = School.query.filter_by(code='inami').first()
    inami_kita = School.query.filter_by(code='inami_kita').first()
    if not inami or not inami_kita:
        print('学校データが見つかりません。先にseed_dataを実行してください。')
        return

    soccer_org = Organization.query.filter_by(registration_number='INA-001').first()
    tennis_org = Organization.query.filter_by(registration_number='GEN-001').first()

    tanaka = User.query.filter_by(username='tanaka').first()
    suzuki = User.query.filter_by(username='suzuki').first()
    admin = User.query.filter_by(username='admin').first()
    school_user = User.query.filter_by(username='school_inami').first()
    yamada = User.query.filter_by(username='yamada').first()

    inami_facilities = Facility.query.filter_by(school_id=inami.id).all()
    kita_facilities = Facility.query.filter_by(school_id=inami_kita.id).all()
    all_facilities = inami_facilities + kita_facilities

    # 施設名→施設オブジェクトのマッピング（学校ごと）
    def get_facility(school_facilities, name):
        for f in school_facilities:
            if f.name == name:
                return f
        return None

    # --- 予約データ（25件） ---
    purposes = [
        'サッカー練習',
        'テニス練習',
        'バレーボール練習',
        '卓球練習',
        '剣道練習',
        '吹奏楽練習',
        'ダンス練習',
        'バスケットボール練習',
    ]

    # 施設と目的の相性マッピング
    facility_purposes = {
        'グラウンド': ['サッカー練習', 'サッカー練習'],
        'テニスコート': ['テニス練習', 'テニス練習'],
        '体育館': ['バレーボール練習', 'バスケットボール練習', 'ダンス練習'],
        '卓球場': ['卓球練習', '卓球練習'],
        '武道場': ['剣道練習', '剣道練習'],
        '特別教室棟': ['吹奏楽練習', 'ダンス練習'],
    }

    # 団体と利用者のペア
    org_user_pairs = [
        (soccer_org, tanaka),
        (tennis_org, suzuki),
    ]

    reservations = []
    used_slots = set()  # (facility_id, date, start_time) の重複防止

    for i in range(25):
        # 日付: 今日から14日間でランダム
        day_offset = random.randint(1, 14)
        res_date = today + timedelta(days=day_offset)
        weekday = res_date.weekday()  # 0=月 6=日

        # 時間帯: 平日16-21, 週末8-21
        if weekday < 5:
            start_hour = random.choice([16, 17, 18, 19, 20])
        else:
            start_hour = random.choice([8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20])

        start_t = time(start_hour, 0)
        end_t = time(start_hour + 1, 0)

        # 施設をランダム選択
        facility = random.choice(all_facilities)

        # 重複スロットを回避（最大5回リトライ）
        slot_key = (facility.id, res_date, start_hour)
        retries = 0
        while slot_key in used_slots and retries < 5:
            facility = random.choice(all_facilities)
            day_offset = random.randint(1, 14)
            res_date = today + timedelta(days=day_offset)
            weekday = res_date.weekday()
            if weekday < 5:
                start_hour = random.choice([16, 17, 18, 19, 20])
            else:
                start_hour = random.choice([8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20])
            start_t = time(start_hour, 0)
            end_t = time(start_hour + 1, 0)
            slot_key = (facility.id, res_date, start_hour)
            retries += 1

        used_slots.add(slot_key)

        # 目的は施設に合った内容を選択
        possible_purposes = facility_purposes.get(facility.name, purposes)
        purpose = random.choice(possible_purposes)

        # 団体・ユーザー選択
        org, user = random.choice(org_user_pairs)

        # 参加人数
        participants = random.randint(10, 40)

        # 一部をキャンセル済みにする（最後の2件）
        if i >= 23:
            status = 'cancelled'
            cancelled_at = datetime.utcnow() - timedelta(days=random.randint(0, 3))
            cancellation_reason = random.choice([
                '雨天のため中止',
                '参加者不足のため',
                '日程変更のため',
            ])
        else:
            status = 'confirmed'
            cancelled_at = None
            cancellation_reason = None

        reservation = Reservation(
            facility_id=facility.id,
            organization_id=org.id,
            reserved_by=user.id,
            date=res_date,
            start_time=start_t,
            end_time=end_t,
            status=status,
            purpose=purpose,
            expected_participants=participants,
            notes=None,
            cancelled_at=cancelled_at,
            cancelled_by=user.id if cancelled_at else None,
            cancellation_reason=cancellation_reason,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 7)),
        )
        reservations.append(reservation)
        db.session.add(reservation)

    db.session.flush()
    print(f'  予約データ: {len(reservations)}件作成')

    # --- 学校ブロックデータ（4件） ---
    blocks = []

    # 1. 体育大会（終日・全施設）- 稲美中学校
    block_date_1 = today + timedelta(days=random.choice([5, 6, 7, 8, 9, 10]))
    # 土日に寄せる
    while block_date_1.weekday() < 5:
        block_date_1 += timedelta(days=1)

    block1 = SchoolBlock(
        facility_id=None,  # 全施設
        school_id=inami.id,
        date=block_date_1,
        start_time=None,  # 終日
        end_time=None,
        reason='体育大会',
        blocked_by=school_user.id,
        created_at=datetime.utcnow() - timedelta(days=5),
    )
    blocks.append(block1)
    db.session.add(block1)

    # 2. 授業参観（午後・体育館）- 稲美中学校
    block_date_2 = today + timedelta(days=random.choice([3, 4, 5, 6]))
    # 平日に寄せる
    while block_date_2.weekday() >= 5:
        block_date_2 += timedelta(days=1)

    gym = get_facility(inami_facilities, '体育館')
    block2 = SchoolBlock(
        facility_id=gym.id if gym else None,
        school_id=inami.id,
        date=block_date_2,
        start_time=time(13, 0),
        end_time=time(17, 0),
        reason='授業参観',
        blocked_by=school_user.id,
        created_at=datetime.utcnow() - timedelta(days=3),
    )
    blocks.append(block2)
    db.session.add(block2)

    # 3. 施設点検（特定時間・グラウンド）- 稲美北中学校
    block_date_3 = today + timedelta(days=random.choice([2, 3, 4]))
    while block_date_3.weekday() >= 5:
        block_date_3 += timedelta(days=1)

    kita_ground = get_facility(kita_facilities, 'グラウンド')
    block3 = SchoolBlock(
        facility_id=kita_ground.id if kita_ground else None,
        school_id=inami_kita.id,
        date=block_date_3,
        start_time=time(9, 0),
        end_time=time(12, 0),
        reason='施設点検',
        blocked_by=admin.id,
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    blocks.append(block3)
    db.session.add(block3)

    # 4. 卒業式準備（終日・体育館）- 稲美北中学校
    block_date_4 = today + timedelta(days=12)
    while block_date_4.weekday() >= 5:
        block_date_4 += timedelta(days=1)

    kita_gym = get_facility(kita_facilities, '体育館')
    block4 = SchoolBlock(
        facility_id=kita_gym.id if kita_gym else None,
        school_id=inami_kita.id,
        date=block_date_4,
        start_time=None,
        end_time=None,
        reason='卒業式準備',
        blocked_by=admin.id,
        created_at=datetime.utcnow() - timedelta(days=1),
    )
    blocks.append(block4)
    db.session.add(block4)

    print(f'  学校ブロック: {len(blocks)}件作成')

    # --- 活動ログデータ（8件） ---
    logs = []
    now = datetime.utcnow()

    log_entries = [
        (admin.id, 'create_reservation', 'Reservation', reservations[0].id,
         f'{reservations[0].date}の予約を代理作成しました'),
        (tanaka.id, 'create_reservation', 'Reservation', reservations[1].id,
         'サッカー練習の予約を作成しました'),
        (suzuki.id, 'create_reservation', 'Reservation', reservations[2].id,
         'テニス練習の予約を作成しました'),
        (school_user.id, 'create_block', 'SchoolBlock', blocks[0].id,
         '体育大会のため施設をブロックしました'),
        (admin.id, 'approve_organization', 'Organization', soccer_org.id,
         'いなみサッカークラブを承認しました'),
        (tanaka.id, 'cancel_reservation', 'Reservation', reservations[-1].id,
         '予約をキャンセルしました（雨天のため）'),
        (admin.id, 'create_block', 'SchoolBlock', blocks[2].id,
         '施設点検のためブロックを設定しました'),
        (suzuki.id, 'login', None, None,
         'ログインしました'),
    ]

    for idx, (user_id, action, target_type, target_id, details) in enumerate(log_entries):
        log = ActivityLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            created_at=now - timedelta(hours=idx * 6 + random.randint(0, 3)),
        )
        logs.append(log)
        db.session.add(log)

    print(f'  活動ログ: {len(logs)}件作成')

    # --- 通知データ（5件） ---
    notifications = []

    notif_entries = [
        (tanaka.id, '予約が確定しました',
         f'{reservations[1].date}のサッカー練習の予約が確定されました。',
         '/reservations', False),
        (suzuki.id, '予約が確定しました',
         f'{reservations[2].date}のテニス練習の予約が確定されました。',
         '/reservations', True),
        (tanaka.id, '施設ブロックのお知らせ',
         f'{block_date_1}は体育大会のため稲美中学校の全施設が利用できません。',
         '/calendar', False),
        (suzuki.id, '施設ブロックのお知らせ',
         f'{block_date_3}は施設点検のため稲美北中学校グラウンドが利用できません。',
         '/calendar', True),
        (yamada.id, 'システムメンテナンスのお知らせ',
         '4月中旬にシステムメンテナンスを予定しています。詳細は追ってご連絡します。',
         None, False),
    ]

    for user_id, title, message, link, is_read in notif_entries:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            is_read=is_read,
            link=link,
            created_at=now - timedelta(hours=random.randint(1, 48)),
        )
        notifications.append(notif)
        db.session.add(notif)

    print(f'  通知: {len(notifications)}件作成')

    db.session.commit()
    print('デモデータの投入が完了しました！')


if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from app import create_app
    app = create_app()
    with app.app_context():
        create_demo_data()
