from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from app.models.school import School
from app.models.facility import Facility
from app.models.reservation import Reservation
from app.models.school_block import SchoolBlock
from app.extensions import db

calendar_bp = Blueprint('calendar', __name__)

# 施設ごとのカラーマップ
FACILITY_COLORS = {
    'グラウンド':    {'bg': '#2e7d32', 'border': '#1b5e20'},
    'テニスコート':  {'bg': '#00838f', 'border': '#006064'},
    '体育館':        {'bg': '#1565c0', 'border': '#0d47a1'},
    '卓球場':        {'bg': '#6a1b9a', 'border': '#4a148c'},
    '武道場':        {'bg': '#bf360c', 'border': '#8d1e04'},
    '特別教室棟':    {'bg': '#f57f17', 'border': '#e65100'},
}
DEFAULT_COLOR = {'bg': '#455a64', 'border': '#37474f'}


def get_facility_color(facility_name):
    return FACILITY_COLORS.get(facility_name, DEFAULT_COLOR)


@calendar_bp.route('/calendar')
@login_required
def index():
    schools = School.query.all()
    facilities = Facility.query.filter_by(is_active=True).all()
    return render_template('calendar/index.html',
                           schools=schools,
                           facilities=facilities,
                           facility_colors=FACILITY_COLORS)


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
        color = get_facility_color(r.facility.name)
        is_certified = r.organization.is_inachalle_certified

        events.append({
            'id': f'r_{r.id}',
            'title': f'{r.facility.name}: {r.organization.name}',
            'start': f'{r.date.isoformat()}T{r.start_time.strftime("%H:%M:%S")}',
            'end': f'{r.date.isoformat()}T{r.end_time.strftime("%H:%M:%S")}',
            'color': color['bg'],
            'borderColor': color['border'],
            'extendedProps': {
                'type': 'reservation',
                'facility': r.facility.name,
                'facilityType': r.facility.type_label,
                'school': r.facility.school.name,
                'organization': r.organization.name,
                'purpose': r.purpose or '',
                'participants': r.expected_participants or 0,
                'isCertified': is_certified,
                'timeRange': r.time_range,
            }
        })

    # 学校ブロックイベント
    block_query = SchoolBlock.query.filter(
        SchoolBlock.date >= start_date,
        SchoolBlock.date <= end_date,
    )
    if facility_id:
        facility = db.session.get(Facility, facility_id)
        if facility:
            block_query = block_query.filter(
                SchoolBlock.school_id == facility.school_id,
                db.or_(
                    SchoolBlock.facility_id.is_(None),
                    SchoolBlock.facility_id == facility_id,
                ),
            )
    elif school_id:
        block_query = block_query.filter(SchoolBlock.school_id == school_id)

    for b in block_query.all():
        event_data = {
            'id': f'b_{b.id}',
            'title': f'【{b.school.name}】{b.reason}',
            'color': '#c0392b',
            'borderColor': '#922b21',
            'display': 'block',
            'extendedProps': {
                'type': 'block',
                'reason': b.reason,
                'facility': b.facility_name,
                'school': b.school.name,
            }
        }

        if b.is_all_day:
            event_data['start'] = b.date.isoformat()
            event_data['allDay'] = True
        else:
            event_data['start'] = f'{b.date.isoformat()}T{b.start_time.strftime("%H:%M:%S")}'
            event_data['end'] = f'{b.date.isoformat()}T{b.end_time.strftime("%H:%M:%S")}'

        events.append(event_data)

    return jsonify(events)
