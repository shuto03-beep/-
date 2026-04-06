"""音声ノート分析 - データモデル"""
import json
from datetime import datetime, date
from app.extensions import db


class VoiceNote(db.Model):
    __tablename__ = 'voice_notes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    source_file = db.Column(db.String(300))
    recorded_date = db.Column(db.Date, nullable=False, default=date.today)
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship('Task', backref='voice_note', lazy='dynamic', cascade='all, delete-orphan')
    analyses = db.relationship('Analysis', backref='voice_note', lazy='dynamic', cascade='all, delete-orphan')
    thinking_patterns = db.relationship('ThinkingPattern', backref='voice_note', lazy='dynamic', cascade='all, delete-orphan')
    improvements = db.relationship('Improvement', backref='voice_note', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<VoiceNote {self.id} {self.title}>'


class Task(db.Model):
    __tablename__ = 'voice_tasks'

    id = db.Column(db.Integer, primary_key=True)
    voice_note_id = db.Column(db.Integer, db.ForeignKey('voice_notes.id'), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    urgency = db.Column(db.Integer, nullable=False, default=3)       # 1-5
    importance = db.Column(db.Integer, nullable=False, default=3)    # 1-5
    quadrant = db.Column(db.String(20), nullable=False, default='schedule')
    deadline = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default='pending')
    priority_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    QUADRANT_DO_FIRST = 'do_first'
    QUADRANT_SCHEDULE = 'schedule'
    QUADRANT_DELEGATE = 'delegate'
    QUADRANT_ELIMINATE = 'eliminate'

    QUADRANT_LABELS = {
        'do_first': '今すぐやる',
        'schedule': '計画する',
        'delegate': '任せる',
        'eliminate': '排除する',
    }

    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_LABELS = {
        'pending': '未着手',
        'in_progress': '進行中',
        'completed': '完了',
        'cancelled': 'キャンセル',
    }

    @property
    def quadrant_label(self):
        return self.QUADRANT_LABELS.get(self.quadrant, self.quadrant)

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    @property
    def is_overdue(self):
        if self.deadline and self.status not in ('completed', 'cancelled'):
            return self.deadline < date.today()
        return False

    def calculate_priority(self):
        score = (self.urgency * 2 + self.importance * 3) / 5.0
        if self.deadline:
            days_left = (self.deadline - date.today()).days
            if days_left <= 0:
                score += 3.0
            elif days_left <= 3:
                score += 2.0
            elif days_left <= 7:
                score += 1.0
        self.priority_score = round(score, 2)
        return self.priority_score

    @staticmethod
    def determine_quadrant(urgency, importance):
        if urgency >= 4 and importance >= 4:
            return 'do_first'
        elif urgency < 4 and importance >= 4:
            return 'schedule'
        elif urgency >= 4 and importance < 4:
            return 'delegate'
        else:
            return 'eliminate'

    def __repr__(self):
        return f'<Task {self.id} {self.title[:30]}>'


class Analysis(db.Model):
    __tablename__ = 'voice_analyses'

    id = db.Column(db.Integer, primary_key=True)
    voice_note_id = db.Column(db.Integer, db.ForeignKey('voice_notes.id'), nullable=False)
    role = db.Column(db.String(30), nullable=False)
    content = db.Column(db.Text, nullable=False)  # JSON string
    score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ROLE_TASK_EXTRACTOR = 'task_extractor'
    ROLE_LIFE_COACH = 'life_coach'
    ROLE_PSYCHOLOGIST = 'psychologist'
    ROLE_STRATEGIST = 'strategist'
    ROLE_CRITIC = 'critic'

    ROLE_LABELS = {
        'task_extractor': 'タスク抽出',
        'life_coach': 'ライフコーチ',
        'psychologist': '心理分析',
        'strategist': '戦略プランナー',
        'critic': '批評家',
    }

    @property
    def role_label(self):
        return self.ROLE_LABELS.get(self.role, self.role)

    @property
    def parsed_content(self):
        try:
            return json.loads(self.content)
        except (json.JSONDecodeError, TypeError):
            return {}

    def __repr__(self):
        return f'<Analysis {self.id} {self.role}>'


class ThinkingPattern(db.Model):
    __tablename__ = 'thinking_patterns'

    id = db.Column(db.Integer, primary_key=True)
    voice_note_id = db.Column(db.Integer, db.ForeignKey('voice_notes.id'), nullable=False)
    pattern_type = db.Column(db.String(30), nullable=False)  # cognitive_bias, habit, strength, weakness
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    frequency = db.Column(db.Integer, default=1)
    first_detected = db.Column(db.Date, default=date.today)
    last_detected = db.Column(db.Date, default=date.today)

    TYPE_LABELS = {
        'cognitive_bias': '認知バイアス',
        'habit': '習慣',
        'strength': '強み',
        'weakness': '課題',
    }

    @property
    def type_label(self):
        return self.TYPE_LABELS.get(self.pattern_type, self.pattern_type)

    def __repr__(self):
        return f'<ThinkingPattern {self.id} {self.name}>'


class Improvement(db.Model):
    __tablename__ = 'improvements'

    id = db.Column(db.Integer, primary_key=True)
    voice_note_id = db.Column(db.Integer, db.ForeignKey('voice_notes.id'), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    current_state = db.Column(db.Text)
    target_state = db.Column(db.Text)
    steps = db.Column(db.Text)  # JSON array
    progress = db.Column(db.Integer, default=0)  # 0-100
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    CATEGORY_LABELS = {
        'health': '健康',
        'career': 'キャリア',
        'relationship': '人間関係',
        'mindset': 'マインドセット',
        'skill': 'スキル',
        'finance': '経済',
        'lifestyle': 'ライフスタイル',
    }

    @property
    def category_label(self):
        return self.CATEGORY_LABELS.get(self.category, self.category)

    @property
    def parsed_steps(self):
        try:
            return json.loads(self.steps) if self.steps else []
        except (json.JSONDecodeError, TypeError):
            return []

    def __repr__(self):
        return f'<Improvement {self.id} {self.title[:30]}>'
