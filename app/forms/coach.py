from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, DateField, IntegerField, SelectField, SelectMultipleField,
    StringField, SubmitField, TextAreaField,
)
from wtforms.validators import DataRequired, Email, NumberRange, Optional

from app.models.coach import Coach


class CoachForm(FlaskForm):
    full_name = StringField('氏名', validators=[DataRequired(message='氏名を入力してください')])
    full_name_kana = StringField('氏名（カナ）', validators=[Optional()])
    email = StringField('メールアドレス', validators=[
        Optional(), Email(message='正しいメールアドレスを入力してください'),
    ])
    phone = StringField('電話番号', validators=[Optional()])
    birth_date = DateField('生年月日', validators=[Optional()])
    qualification = StringField('資格・指導経歴', validators=[Optional()])
    compensation_type = SelectField('報酬区分', choices=[
        (Coach.COMPENSATION_UNPAID, '無償'),
        (Coach.COMPENSATION_PAID, '有償'),
    ], validators=[DataRequired()])
    hourly_rate = IntegerField('時間単価（円）', validators=[
        Optional(), NumberRange(min=0, max=100000, message='0〜100,000円で指定してください'),
    ], default=0)
    is_teacher_dual_role = BooleanField('教職員兼職兼業として登録')
    organization_ids = SelectMultipleField('所属団体（複数選択可）', coerce=int, validators=[Optional()])
    user_id = SelectField('ログインアカウント（マイページ連携）', coerce=int, validators=[Optional()])
    is_active = BooleanField('有効', default=True)
    notes = TextAreaField('備考', validators=[Optional()])
    submit = SubmitField('保存')
