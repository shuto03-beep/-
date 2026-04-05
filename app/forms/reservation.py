from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, HiddenField, TextAreaField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange


class ReservationForm(FlaskForm):
    facility_id = SelectField('施設', coerce=int, validate_choice=False, validators=[DataRequired(message='施設を選択してください')])
    date = DateField('利用日', validators=[DataRequired(message='利用日を選択してください')])
    time_slot = SelectField('時間枠', validate_choice=False, validators=[DataRequired(message='時間枠を選択してください')])
    purpose = TextAreaField('利用目的', validators=[DataRequired(message='利用目的を入力してください')])
    expected_participants = IntegerField('予定参加人数', validators=[
        Optional(),
        NumberRange(min=1, message='1人以上を入力してください')
    ])
    notes = TextAreaField('備考', validators=[Optional()])
    submit = SubmitField('予約する')


class EditReservationForm(FlaskForm):
    facility_id = SelectField('施設', coerce=int, validate_choice=False, validators=[DataRequired(message='施設を選択してください')])
    date = DateField('利用日', validators=[DataRequired(message='利用日を選択してください')])
    time_slot = SelectField('時間枠', validate_choice=False, validators=[DataRequired(message='時間枠を選択してください')])
    purpose = TextAreaField('利用目的', validators=[DataRequired(message='利用目的を入力してください')])
    expected_participants = IntegerField('予定参加人数', validators=[
        Optional(),
        NumberRange(min=1, message='1人以上を入力してください')
    ])
    notes = TextAreaField('備考', validators=[Optional()])
    submit = SubmitField('変更を保存する')


class CancelReservationForm(FlaskForm):
    cancellation_reason = TextAreaField('キャンセル理由', validators=[
        DataRequired(message='キャンセル理由を入力してください')
    ])
    submit = SubmitField('キャンセルする')
