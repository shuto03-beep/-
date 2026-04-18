from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.school import School
from app.models.facility import Facility
from app.models.school_block import SchoolBlock
from app.models.reservation import Reservation
from app.forms.block import SchoolBlockForm
from app.services.notification_service import queue_notifications, send_queued_emails
from app.services.activity_log_service import log_activity
from app.utils.decorators import role_required

blocks_bp = Blueprint('blocks', __name__)


@blocks_bp.route('/blocks')
@login_required
@role_required('admin', 'school')
def list_blocks():
    query = SchoolBlock.query.order_by(SchoolBlock.date.desc())
    blocks = query.all()
    return render_template('blocks/list.html', blocks=blocks)


@blocks_bp.route('/blocks/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'school')
def new_block():
    form = SchoolBlockForm()
    schools = School.query.all()
    form.school_id.choices = [(s.id, s.name) for s in schools]

    facilities = Facility.query.filter_by(is_active=True).all()
    form.facility_id.choices = [(0, '全施設')] + [(f.id, f'{f.school.name} - {f.name}') for f in facilities]

    if form.validate_on_submit():
        block = SchoolBlock(
            school_id=form.school_id.data,
            facility_id=form.facility_id.data if form.facility_id.data != 0 else None,
            date=form.date.data,
            start_time=form.start_time.data if form.start_time.data else None,
            end_time=form.end_time.data if form.end_time.data else None,
            reason=form.reason.data,
            blocked_by=current_user.id,
        )
        db.session.add(block)

        # ブロックと競合する既存予約を自動キャンセル
        conflict_query = Reservation.query.filter(
            Reservation.date == form.date.data,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        )

        if block.facility_id:
            conflict_query = conflict_query.filter(Reservation.facility_id == block.facility_id)
        else:
            conflict_query = conflict_query.join(Facility).filter(Facility.school_id == block.school_id)

        if not block.is_all_day and block.start_time and block.end_time:
            conflict_query = conflict_query.filter(
                Reservation.start_time < block.end_time,
                Reservation.end_time > block.start_time,
            )

        conflicts = conflict_query.all()
        notifications = []
        for r in conflicts:
            r.status = Reservation.STATUS_CANCELLED
            r.cancellation_reason = f'学校行事のため自動キャンセル: {block.reason}'
            notifications.append({
                'user_id': r.reserved_by,
                'title': '予約が自動キャンセルされました',
                'message': f'{r.facility.full_name}の{r.date}の予約が学校行事（{block.reason}）のためキャンセルされました。',
                'link': url_for('reservations.detail', id=r.id),
            })
        queue_notifications(notifications)

        db.session.flush()
        log_activity(
            'create_school_block',
            target_type='school_block', target_id=block.id,
            details=f'date={form.date.data} reason={form.reason.data} auto_cancelled={len(conflicts)}',
        )

        db.session.commit()
        send_queued_emails(notifications)

        if conflicts:
            flash(f'ブロックを設定し、{len(conflicts)}件の予約を自動キャンセルしました。', 'warning')
        else:
            flash('ブロックを設定しました。', 'success')

        return redirect(url_for('blocks.list_blocks'))

    return render_template('blocks/new.html', form=form)


@blocks_bp.route('/blocks/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'school')
def delete_block(id):
    block = db.session.get(SchoolBlock, id)
    if not block:
        flash('ブロックが見つかりません。', 'danger')
        return redirect(url_for('blocks.list_blocks'))

    db.session.delete(block)
    db.session.commit()
    flash('ブロックを解除しました。', 'info')
    return redirect(url_for('blocks.list_blocks'))
