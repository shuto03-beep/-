from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models.user import User


class LoginForm(FlaskForm):
    username = StringField('ユーザー名', validators=[DataRequired(message='ユーザー名を入力してください')])
    password = PasswordField('パスワード', validators=[DataRequired(message='パスワードを入力してください')])
    submit = SubmitField('ログイン')


class RegistrationForm(FlaskForm):
    username = StringField('ユーザー名', validators=[
        DataRequired(message='ユーザー名を入力してください'),
        Length(min=3, max=80, message='ユーザー名は3〜80文字で入力してください')
    ])
    email = StringField('メールアドレス', validators=[
        DataRequired(message='メールアドレスを入力してください'),
        Email(message='正しいメールアドレスを入力してください')
    ])
    display_name = StringField('表示名', validators=[
        DataRequired(message='表示名を入力してください'),
        Length(max=100)
    ])
    phone = StringField('電話番号')
    password = PasswordField('パスワード', validators=[
        DataRequired(message='パスワードを入力してください'),
        Length(min=6, message='パスワードは6文字以上で入力してください')
    ])
    password_confirm = PasswordField('パスワード（確認）', validators=[
        DataRequired(message='確認用パスワードを入力してください'),
        EqualTo('password', message='パスワードが一致しません')
    ])
    submit = SubmitField('登録')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('このユーザー名は既に使用されています')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('このメールアドレスは既に登録されています')
