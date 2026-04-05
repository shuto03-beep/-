from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from app.models.school import School
from app.models.facility import Facility
from app.models.reservation import Reservation
from app.models.school_block import SchoolBlock

calendar_bp = Blueprint('calendar', __name__)


@calendar_bp.route('/calendar')
@login_required
def index():
    schools = School.query.all()
    facilities = Facility.query.filter_by(is_active=True).all()
    return render_template('calendar/index.html', schools=schools, facilities=facilities)


@calendar_bp.route('/api/events')
@login_required
def events():
    facility_id = request.args.get('facility_id', type=int)
    school_id = request.args.get('school_id', type=int)
    start = request.args.get('start')
    end = request.args.get('end')

    if not start or not end:
        return jsonify([])

    try:
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00')).date()
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00')).date()
    except (ValueError, AttributeError):
        return jsonify([])

    events = []

    # 予約イベント
    query = Reservation.query.filter(
        Reservation.date >= start_date,
        Reservation.date <= end_date,
        Reservation.status == Reservation.STATUS_CONFIRMED,
    )
    if facility_id:
        query = query.filter(Reservation.facility_id == facility_id)
    elif school_id:
        query = query.join(Facility).filter(Facility.school_id == school_id)

    for r in query.all():
        events.append({
            'id': f'r_{r.id}',
            'title': f'{r.facility.name}: {r.organization.name}',
            'start': f'{r.date.isoformat()}T{r.start_time.strftime("%H:%M:%S")}',
            'end': f'{r.date.isoformat()}T{r.end_time.strftime("%H:%M:%S")}',
            'color': '#0d6efd',
            'extendedProps': {
                'type': 'reservation',
                'facility': r.facility.name,
                'organization': r.organization.name,
                'purpose': r.purpose or '',
            }
        })

    # 学校ブロックイベント
    block_query = SchoolBlock.query.filter(
        SchoolBlock.date >= start_date,
        SchoolBlock.date <= end_date,
    )
    if facility_id:
        facility = Facility.query.get(facility_id)
        if facility:
            block_query = block_query.filter(
                SchoolBlock.school_id == facility.school_id,
                (SchoolBlock.facility_id.is_(None)) | (SchoolBlock.facility_id == facility_id),
            )
    elif school_id:
        block_query = block_query.filter(SchoolBlock.school_id == school_id)

    for b in block_query.all():
        if b.is_all_day:
            events.append({
                'id': f'b_{b.id}',
                'title': f'【学校行事】{b.reason}',
                'start': b.date.isoformat(),
                'allDay': True,
                'color': '#dc3545',
                'extendedProps': {
                    'type': 'block',
                    'reason': b.reason,
                    'facility': b.facility_name,
                }
            })
        else:
            events.append({
                'id': f'b_{b.id}',
                'title': f'【学校行事】{b.reason}',
                'start': f'{b.date.isoformat()}T{b.start_time.strftime("%H:%M:%S")}',
                'end': f'{b.date.isoformat()}T{b.end_time.strftime("%H:%M:%S")}',
                'color': '#dc3545',
                'extendedProps': {
                    'type': 'block',
                    'reason': b.reason,
                    'facility': b.facility_name,
                }
            })

    return jsonify(events)
