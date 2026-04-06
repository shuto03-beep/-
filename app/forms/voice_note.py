"""音声ノート関連フォーム"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, DateField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Optional
from datetime import date


class VoiceNoteUploadForm(FlaskForm):
    title = StringField('タイトル', validators=[DataRequired(message='タイトルを入力してください')])
    recorded_date = DateField('録音日', default=date.today, validators=[DataRequired()])
    file = FileField('テキストファイル', validators=[
        FileRequired(message='ファイルを選択してください'),
        FileAllowed(['txt'], 'テキストファイル(.txt)のみアップロード可能です')
    ])


class VoiceNoteTextForm(FlaskForm):
    title = StringField('タイトル', validators=[DataRequired(message='タイトルを入力してください')])
    recorded_date = DateField('録音日', default=date.today, validators=[DataRequired()])
    content = TextAreaField('テキスト内容', validators=[DataRequired(message='テキストを入力してください')])


class TaskStatusForm(FlaskForm):
    status = SelectField('ステータス', choices=[
        ('pending', '未着手'),
        ('in_progress', '進行中'),
        ('completed', '完了'),
        ('cancelled', 'キャンセル'),
    ], validators=[DataRequired()])
