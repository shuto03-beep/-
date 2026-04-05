from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, TimeField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional


class SchoolBlockForm(FlaskForm):
    school_id = SelectField('学校', coerce=int, validators=[DataRequired(message='学校を選択してください')])
    facility_id = SelectField('施設（全施設の場合は空欄）', coerce=int, validators=[Optional()])
    date = DateField('日付', validators=[DataRequired(message='日付を選択してください')])
    start_time = TimeField('開始時間（終日の場合は空欄）', validators=[Optional()])
    end_time = TimeField('終了時間（終日の場合は空欄）', validators=[Optional()])
    reason = TextAreaField('理由', validators=[DataRequired(message='理由を入力してください')])
    submit = SubmitField('ブロックする')
