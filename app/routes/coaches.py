from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.forms.coach import CoachForm
from app.models.coach import Coach
from app.models.organization import Organization
from app.services.activity_log_service import log_activity
from app.utils.decorators import admin_required

coaches_bp = Blueprint('coaches', __name__)


def _set_org_choices(form):
    form.organization_ids.choices = [
        (o.id, o.name)
        for o in Organization.query.filter_by(is_approved=True).order_by(Organization.name).all()
    ]


@coaches_bp.route('/admin/coaches')
@login_required
@admin_required
def list_coaches():
    only_multi = request.args.get('multi') == '1'
    query = Coach.query.options(joinedload(Coach.organizations)).order_by(Coach.full_name)
    coaches = query.all()
    if only_multi:
        coaches = [c for c in coaches if c.is_multi_affiliated]
    total = len(coaches)
    multi_count = sum(1 for c in Coach.query.options(joinedload(Coach.organizations)).all() if c.is_multi_affiliated)
    return render_template(
        'admin/coaches.html',
        coaches=coaches, total=total, multi_count=multi_count, only_multi=only_multi,
    )


@coaches_bp.route('/admin/coaches/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_coach():
    form = CoachForm()
    _set_org_choices(form)

    if form.validate_on_submit():
        coach = Coach(
            full_name=form.full_name.data.strip(),
            full_name_kana=form.full_name_kana.data or None,
            email=form.email.data or None,
            phone=form.phone.data or None,
            birth_date=form.birth_date.data,
            qualification=form.qualification.data or None,
            compensation_type=form.compensation_type.data,
            hourly_rate=form.hourly_rate.data or 0,
            is_teacher_dual_role=form.is_teacher_dual_role.data,
            is_active=form.is_active.data,
            notes=form.notes.data or None,
        )
        selected_orgs = Organization.query.filter(Organization.id.in_(form.organization_ids.data)).all()
        coach.organizations = selected_orgs
        db.session.add(coach)
        db.session.flush()
        log_activity(
            'register_coach',
            target_type='coach', target_id=coach.id,
            details=f'name={coach.full_name} orgs={len(selected_orgs)}',
        )
        db.session.commit()

        if coach.is_multi_affiliated:
            flash(
                f'指導者「{coach.full_name}」を登録しました。'
                f'複数団体（{coach.organization_count}団体）に所属しているため、'
                '謝金計算時のダブルカウントに注意してください。',
                'warning',
            )
        else:
            flash(f'指導者「{coach.full_name}」を登録しました。', 'success')
        return redirect(url_for('coaches.list_coaches'))

    return render_template('admin/coach_form.html', form=form, coach=None)


@coaches_bp.route('/admin/coaches/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_coach(id):
    coach = db.session.get(Coach, id)
    if not coach:
        flash('指導者が見つかりません。', 'danger')
        return redirect(url_for('coaches.list_coaches'))

    form = CoachForm(obj=coach)
    _set_org_choices(form)
    if request.method == 'GET':
        form.organization_ids.data = [o.id for o in coach.organizations]

    if form.validate_on_submit():
        coach.full_name = form.full_name.data.strip()
        coach.full_name_kana = form.full_name_kana.data or None
        coach.email = form.email.data or None
        coach.phone = form.phone.data or None
        coach.birth_date = form.birth_date.data
        coach.qualification = form.qualification.data or None
        coach.compensation_type = form.compensation_type.data
        coach.hourly_rate = form.hourly_rate.data or 0
        coach.is_teacher_dual_role = form.is_teacher_dual_role.data
        coach.is_active = form.is_active.data
        coach.notes = form.notes.data or None
        coach.organizations = Organization.query.filter(
            Organization.id.in_(form.organization_ids.data),
        ).all()
        log_activity(
            'update_coach',
            target_type='coach', target_id=coach.id,
            details=f'name={coach.full_name}',
        )
        db.session.commit()
        flash(f'指導者「{coach.full_name}」を更新しました。', 'success')
        return redirect(url_for('coaches.list_coaches'))

    return render_template('admin/coach_form.html', form=form, coach=coach)
