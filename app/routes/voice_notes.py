"""音声ノート分析 - ルート定義"""
import json
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.voice_note import VoiceNote, Task, Analysis, ThinkingPattern, Improvement
from app.forms.voice_note import VoiceNoteUploadForm, VoiceNoteTextForm, TaskStatusForm
from app.services.voice_ai_service import run_full_analysis
from app.services.voice_notification_service import notify_analysis_complete
from app.services.notification_service import get_unread_count

voice_notes_bp = Blueprint('voice_notes', __name__, url_prefix='/voice-notes')


@voice_notes_bp.before_request
@login_required
def require_login():
    pass


@voice_notes_bp.context_processor
def inject_unread_count():
    if current_user.is_authenticated:
        return {'unread_count': get_unread_count(current_user.id)}
    return {}


# --- ダッシュボード ---
@voice_notes_bp.route('/')
def dashboard():
    recent_notes = VoiceNote.query.order_by(VoiceNote.created_at.desc()).limit(5).all()

    urgent_tasks = Task.query.filter(
        Task.status.in_(['pending', 'in_progress']),
        Task.quadrant == 'do_first'
    ).order_by(Task.priority_score.desc()).limit(10).all()

    overdue_tasks = Task.query.filter(
        Task.status.in_(['pending', 'in_progress']),
        Task.deadline < date.today(),
        Task.deadline.isnot(None)
    ).all()

    total_tasks = Task.query.filter(Task.status.in_(['pending', 'in_progress'])).count()
    completed_tasks = Task.query.filter(Task.status == 'completed').count()
    total_notes = VoiceNote.query.count()
    patterns_count = db.session.query(ThinkingPattern.name).distinct().count()

    return render_template('voice_notes/dashboard.html',
                           recent_notes=recent_notes,
                           urgent_tasks=urgent_tasks,
                           overdue_tasks=overdue_tasks,
                           total_tasks=total_tasks,
                           completed_tasks=completed_tasks,
                           total_notes=total_notes,
                           patterns_count=patterns_count)


# --- アップロード ---
@voice_notes_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    file_form = VoiceNoteUploadForm()
    text_form = VoiceNoteTextForm()

    if request.method == 'POST':
        upload_mode = request.form.get('upload_mode', 'file')

        if upload_mode == 'file' and file_form.validate_on_submit():
            file = file_form.file.data
            content = file.read().decode('utf-8', errors='replace')
            title = file_form.title.data
            recorded_date = file_form.recorded_date.data
            source_file = file.filename
        elif upload_mode == 'text' and text_form.validate_on_submit():
            content = text_form.content.data
            title = text_form.title.data
            recorded_date = text_form.recorded_date.data
            source_file = None
        else:
            flash('入力内容を確認してください。', 'danger')
            return render_template('voice_notes/upload.html',
                                   file_form=file_form, text_form=text_form)

        # VoiceNote保存
        voice_note = VoiceNote(
            title=title,
            content=content,
            source_file=source_file,
            recorded_date=recorded_date,
        )
        db.session.add(voice_note)
        db.session.flush()  # IDを取得

        # AI分析実行
        flash('AI分析を実行中です...', 'info')
        try:
            results = run_full_analysis(content, str(recorded_date))
            _save_analysis_results(voice_note, results)
            db.session.commit()

            # Discord通知
            tasks = Task.query.filter_by(voice_note_id=voice_note.id).all()
            analyses = Analysis.query.filter_by(voice_note_id=voice_note.id).all()
            notify_analysis_complete(voice_note, tasks, analyses)

            flash('分析が完了しました！', 'success')
            return redirect(url_for('voice_notes.detail', note_id=voice_note.id))

        except Exception as e:
            db.session.rollback()
            flash(f'分析中にエラーが発生しました: {e}', 'danger')
            return render_template('voice_notes/upload.html',
                                   file_form=file_form, text_form=text_form)

    return render_template('voice_notes/upload.html',
                           file_form=file_form, text_form=text_form)


def _save_analysis_results(voice_note: VoiceNote, results: dict):
    """分析結果をDBに保存"""
    # 要約
    voice_note.summary = results.get('summary', '')

    # 各ロールの分析結果を保存
    for role in ['task_extractor', 'life_coach', 'psychologist', 'strategist', 'critic']:
        if role in results:
            analysis = Analysis(
                voice_note_id=voice_note.id,
                role=role,
                content=json.dumps(results[role], ensure_ascii=False),
                score=results.get('critic', {}).get('quality_score', 0) if role == 'critic' else 0,
            )
            db.session.add(analysis)

    # タスク抽出結果からTaskレコードを作成
    task_data = results.get('task_extractor', {})
    for t in task_data.get('tasks', []):
        urgency = min(5, max(1, int(t.get('urgency', 3))))
        importance = min(5, max(1, int(t.get('importance', 3))))
        quadrant = Task.determine_quadrant(urgency, importance)

        deadline = None
        if t.get('deadline'):
            try:
                deadline = datetime.strptime(t['deadline'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass

        task = Task(
            voice_note_id=voice_note.id,
            title=t.get('title', '無題のタスク'),
            description=t.get('description', ''),
            urgency=urgency,
            importance=importance,
            quadrant=quadrant,
            deadline=deadline,
        )
        task.calculate_priority()
        db.session.add(task)

    # 思考パターン
    psych_data = results.get('psychologist', {})
    for p in psych_data.get('thinking_patterns', []):
        pattern = ThinkingPattern(
            voice_note_id=voice_note.id,
            pattern_type=p.get('type', 'habit'),
            name=p.get('name', '不明なパターン'),
            description=p.get('description', ''),
        )
        db.session.add(pattern)

    # 改善プラン
    strat_data = results.get('strategist', {})
    for imp in strat_data.get('improvements', []):
        steps = imp.get('steps', [])
        improvement = Improvement(
            voice_note_id=voice_note.id,
            category=imp.get('category', 'lifestyle'),
            title=imp.get('title', '無題の改善プラン'),
            current_state=imp.get('current_state', ''),
            target_state=imp.get('target_state', ''),
            steps=json.dumps(steps, ensure_ascii=False),
        )
        db.session.add(improvement)


# --- 詳細表示 ---
@voice_notes_bp.route('/<int:note_id>')
def detail(note_id):
    voice_note = VoiceNote.query.get_or_404(note_id)
    analyses = Analysis.query.filter_by(voice_note_id=note_id).all()
    tasks = Task.query.filter_by(voice_note_id=note_id).order_by(Task.priority_score.desc()).all()
    patterns = ThinkingPattern.query.filter_by(voice_note_id=note_id).all()
    improvements = Improvement.query.filter_by(voice_note_id=note_id).all()

    analyses_dict = {a.role: a for a in analyses}

    return render_template('voice_notes/detail.html',
                           note=voice_note,
                           analyses=analyses_dict,
                           tasks=tasks,
                           patterns=patterns,
                           improvements=improvements)


# --- タスク一覧（アイゼンハワーマトリクス） ---
@voice_notes_bp.route('/tasks')
def tasks():
    status_filter = request.args.get('status', 'active')
    if status_filter == 'active':
        task_list = Task.query.filter(Task.status.in_(['pending', 'in_progress']))
    elif status_filter == 'all':
        task_list = Task.query
    else:
        task_list = Task.query.filter_by(status=status_filter)

    task_list = task_list.order_by(Task.priority_score.desc()).all()

    quadrants = {
        'do_first': [t for t in task_list if t.quadrant == 'do_first'],
        'schedule': [t for t in task_list if t.quadrant == 'schedule'],
        'delegate': [t for t in task_list if t.quadrant == 'delegate'],
        'eliminate': [t for t in task_list if t.quadrant == 'eliminate'],
    }

    status_form = TaskStatusForm()
    return render_template('voice_notes/tasks.html',
                           quadrants=quadrants,
                           tasks=task_list,
                           status_filter=status_filter,
                           status_form=status_form)


# --- タスクステータス更新 ---
@voice_notes_bp.route('/tasks/<int:task_id>/status', methods=['POST'])
def update_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    new_status = request.form.get('status')

    if new_status in Task.STATUS_LABELS:
        task.status = new_status
        if new_status == 'completed':
            task.completed_at = datetime.utcnow()
        db.session.commit()
        flash(f'タスク「{task.title}」を「{task.status_label}」に更新しました。', 'success')
    else:
        flash('無効なステータスです。', 'danger')

    return redirect(request.referrer or url_for('voice_notes.tasks'))


# --- インサイト（思考パターン & 改善プラン） ---
@voice_notes_bp.route('/insights')
def insights():
    patterns = ThinkingPattern.query.order_by(ThinkingPattern.last_detected.desc()).all()
    improvements = Improvement.query.filter_by(status='active').order_by(Improvement.created_at.desc()).all()

    # パターンタイプ別に集約
    pattern_summary = {}
    for p in patterns:
        if p.name not in pattern_summary:
            pattern_summary[p.name] = {
                'name': p.name,
                'type': p.pattern_type,
                'type_label': p.type_label,
                'description': p.description,
                'count': 0,
                'first_detected': p.first_detected,
                'last_detected': p.last_detected,
            }
        pattern_summary[p.name]['count'] += 1
        if p.last_detected and p.last_detected > pattern_summary[p.name]['last_detected']:
            pattern_summary[p.name]['last_detected'] = p.last_detected

    sorted_patterns = sorted(pattern_summary.values(), key=lambda x: x['count'], reverse=True)

    # カテゴリ別改善プラン
    improvement_categories = {}
    for imp in improvements:
        cat = imp.category
        if cat not in improvement_categories:
            improvement_categories[cat] = {
                'label': imp.category_label,
                'items': [],
                'avg_progress': 0,
            }
        improvement_categories[cat]['items'].append(imp)

    for cat in improvement_categories.values():
        if cat['items']:
            cat['avg_progress'] = sum(i.progress for i in cat['items']) // len(cat['items'])

    return render_template('voice_notes/insights.html',
                           patterns=sorted_patterns,
                           improvements=improvements,
                           improvement_categories=improvement_categories)


# --- API: マトリクスデータ ---
@voice_notes_bp.route('/api/matrix-data')
def api_matrix_data():
    tasks = Task.query.filter(Task.status.in_(['pending', 'in_progress'])).all()
    data = [{
        'id': t.id,
        'title': t.title,
        'urgency': t.urgency,
        'importance': t.importance,
        'quadrant': t.quadrant,
        'deadline': str(t.deadline) if t.deadline else None,
        'status': t.status,
        'is_overdue': t.is_overdue,
    } for t in tasks]
    return jsonify(data)


# --- API: パターンデータ ---
@voice_notes_bp.route('/api/pattern-data')
def api_pattern_data():
    patterns = ThinkingPattern.query.order_by(ThinkingPattern.last_detected).all()
    type_counts = {}
    for p in patterns:
        t = p.pattern_type
        type_counts[t] = type_counts.get(t, 0) + 1

    return jsonify({
        'type_counts': type_counts,
        'patterns': [{
            'name': p.name,
            'type': p.pattern_type,
            'date': str(p.last_detected),
        } for p in patterns]
    })


# --- API: 改善進捗データ ---
@voice_notes_bp.route('/api/improvement-data')
def api_improvement_data():
    improvements = Improvement.query.filter_by(status='active').all()
    categories = {}
    for imp in improvements:
        cat = imp.category
        if cat not in categories:
            categories[cat] = {'label': imp.category_label, 'total': 0, 'count': 0}
        categories[cat]['total'] += imp.progress
        categories[cat]['count'] += 1

    return jsonify({
        'categories': {
            k: {'label': v['label'], 'avg_progress': v['total'] // v['count'] if v['count'] else 0}
            for k, v in categories.items()
        }
    })
