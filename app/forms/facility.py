from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, TextAreaField, BooleanField, TimeField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class SchoolForm(FlaskForm):
    name = StringField('学校名', validators=[DataRequired(message='学校名を入力してください')])
    code = StringField('学校コード', validators=[DataRequired(message='学校コードを入力してください')])
    address = StringField('住所', validators=[Optional()])
    contact_phone = StringField('連絡先電話番号', validators=[Optional()])
    submit = SubmitField('保存')


class FacilityForm(FlaskForm):
    school_id = SelectField('学校', coerce=int, validators=[DataRequired()])
    name = StringField('施設名', validators=[DataRequired(message='施設名を入力してください')])
    facility_type = SelectField('種別', choices=[
        ('indoor', '室内'),
        ('outdoor', '室外'),
    ], validators=[DataRequired()])
    capacity = IntegerField('定員（人）', validators=[
        Optional(),
        NumberRange(min=1, message='1人以上を入力してください')
    ])
    description = TextAreaField('施設の説明', validators=[Optional()])
    usage_rules = TextAreaField('利用ルール・注意事項', validators=[Optional()])
    equipment = TextAreaField('設備情報', validators=[Optional()])
    is_active = BooleanField('利用可能（有効）')
    submit = SubmitField('保存')


class TimeSlotForm(FlaskForm):
    start_hour = SelectField('開始時間', coerce=int, choices=[
        (h, f'{h:02d}:00') for h in range(6, 22)
    ], validators=[DataRequired()])
    end_hour = SelectField('終了時間', coerce=int, choices=[
        (h, f'{h:02d}:00') for h in range(7, 23)
    ], validators=[DataRequired()])
    submit = SubmitField('追加')
