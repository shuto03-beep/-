from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, Email


class OrganizationRegistrationForm(FlaskForm):
    name = StringField('団体名', validators=[DataRequired(message='団体名を入力してください')])
    representative = StringField('代表者名', validators=[DataRequired(message='代表者名を入力してください')])
    contact_email = StringField('連絡先メールアドレス', validators=[
        Optional(), Email(message='正しいメールアドレスを入力してください')
    ])
    contact_phone = StringField('連絡先電話番号', validators=[Optional()])
    registration_number = StringField('いなチャレ登録番号', validators=[Optional()])
    notes = TextAreaField('備考', validators=[Optional()])
    submit = SubmitField('登録申請')


class UserEditForm(FlaskForm):
    role = SelectField('ロール', choices=[
        ('admin', '事務局'),
        ('school', '学校'),
        ('org_leader', '団体責任者'),
        ('org_member', '団体メンバー'),
        ('resident', '一般住民'),
    ], validators=[DataRequired()])
    is_active = BooleanField('有効')
    submit = SubmitField('更新')
