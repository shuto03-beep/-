from datetime import datetime, date, time
from app.extensions import db
from app.models.reservation import Reservation
from app.models.school_block import SchoolBlock
from app.utils.helpers import get_available_time_slots


class ReservationConflictError(Exception):
    pass


class SchoolBlockedError(Exception):
    pass


def get_available_slots(facility_id, target_date):
    """指定施設・日付の利用可能な時間枠を返す"""
    all_slots = get_available_time_slots(target_date)

    existing = Reservation.query.filter(
        Reservation.facility_id == facility_id,
        Reservation.date == target_date,
        Reservation.status == Reservation.STATUS_CONFIRMED,
    ).all()
    booked_times = {(r.start_time, r.end_time) for r in existing}

    from app.models.facility import Facility
    facility = db.session.get(Facility, facility_id)
    if not facility:
        return []

    blocks = SchoolBlock.query.filter(
        SchoolBlock.school_id == facility.school_id,
        SchoolBlock.date == target_date,
        db.or_(
            SchoolBlock.facility_id.is_(None),
            SchoolBlock.facility_id == facility_id,
        )
    ).all()

    available = []
    for start, end in all_slots:
        if (start, end) in booked_times:
            continue

        blocked = False
        for block in blocks:
            if block.is_all_day:
                blocked = True
                break
            if block.start_time and block.end_time:
                if start < block.end_time and end > block.start_time:
                    blocked = True
                    break
        if not blocked:
            available.append((start, end))

    return available


def create_reservation(facility_id, organization_id, user_id, target_date, start_time, end_time, purpose, expected_participants=None, notes=None):
    """予約を作成する（重複チェック付き）"""
    existing = Reservation.query.filter(
        Reservation.facility_id == facility_id,
        Reservation.date == target_date,
        Reservation.start_time == start_time,
        Reservation.status == Reservation.STATUS_CONFIRMED,
    ).first()

    if existing:
        raise ReservationConflictError('この時間帯は既に予約されています')

    from app.models.facility import Facility
    facility = db.session.get(Facility, facility_id)
    blocks = SchoolBlock.query.filter(
        SchoolBlock.school_id == facility.school_id,
        SchoolBlock.date == target_date,
        db.or_(
            SchoolBlock.facility_id.is_(None),
            SchoolBlock.facility_id == facility_id,
        )
    ).all()

    for block in blocks:
        if block.is_all_day:
            raise SchoolBlockedError(f'学校行事のため利用できません（{block.reason}）')
        if block.start_time and block.end_time:
            if start_time < block.end_time and end_time > block.start_time:
                raise SchoolBlockedError(f'学校行事のため利用できません（{block.reason}）')

    reservation = Reservation(
        facility_id=facility_id,
        organization_id=organization_id,
        reserved_by=user_id,
        date=target_date,
        start_time=start_time,
        end_time=end_time,
        status=Reservation.STATUS_CONFIRMED,
        purpose=purpose,
        expected_participants=expected_participants,
        notes=notes,
    )
    db.session.add(reservation)
    db.session.commit()
    return reservation


def cancel_reservation(reservation_id, user_id, reason):
    """予約をキャンセルする"""
    reservation = db.session.get(Reservation, reservation_id)
    if not reservation:
        raise ValueError('予約が見つかりません')

    reservation.status = Reservation.STATUS_CANCELLED
    reservation.cancelled_at = datetime.utcnow()
    reservation.cancelled_by = user_id
    reservation.cancellation_reason = reason
    db.session.commit()
    return reservation
