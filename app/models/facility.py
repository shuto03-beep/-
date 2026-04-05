from app.extensions import db


class Facility(db.Model):
    __tablename__ = 'facilities'

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    facility_type = db.Column(db.String(10), nullable=False)  # 'outdoor' or 'indoor'
    capacity = db.Column(db.Integer)
    description = db.Column(db.Text)
    usage_rules = db.Column(db.Text)       # 利用ルール・注意事項
    equipment = db.Column(db.Text)         # 設備情報
    is_active = db.Column(db.Boolean, default=True)

    reservations = db.relationship('Reservation', backref='facility', lazy='dynamic')
    blocks = db.relationship('SchoolBlock', backref='facility', lazy='dynamic')
    time_settings = db.relationship('FacilityTimeSlot', backref='facility',
                                   lazy='dynamic', cascade='all, delete-orphan')

    TYPE_OUTDOOR = 'outdoor'
    TYPE_INDOOR = 'indoor'

    TYPE_LABELS = {
        'outdoor': '室外',
        'indoor': '室内',
    }

    @property
    def type_label(self):
        return self.TYPE_LABELS.get(self.facility_type, self.facility_type)

    @property
    def full_name(self):
        return f'{self.school.name} - {self.name}'

    def get_time_slots_for_date(self, target_date):
        """指定日の利用可能時間枠を返す。施設別設定があればそれを、なければデフォルトを使用。"""
        from datetime import time
        weekday = target_date.weekday()

        # 施設別の時間設定を検索
        custom_slots = FacilityTimeSlot.query.filter(
            FacilityTimeSlot.facility_id == self.id,
            FacilityTimeSlot.day_of_week == weekday,
            FacilityTimeSlot.is_available == True,
        ).order_by(FacilityTimeSlot.start_time).all()

        if custom_slots:
            return [(s.start_time, s.end_time) for s in custom_slots]

        # デフォルト: 平日16:00-21:00、土日8:00-21:00
        slots = []
        if weekday < 5:  # 平日
            for hour in range(16, 21):
                slots.append((time(hour, 0), time(hour + 1, 0)))
        else:  # 土日
            for hour in range(8, 12):
                slots.append((time(hour, 0), time(hour + 1, 0)))
            for hour in range(13, 21):
                slots.append((time(hour, 0), time(hour + 1, 0)))
        return slots

    def __repr__(self):
        return f'<Facility {self.full_name}>'


class FacilityTimeSlot(db.Model):
    """施設ごとの利用可能時間枠の設定"""
    __tablename__ = 'facility_time_slots'

    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=月, 1=火, ..., 6=日
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True)

    DAY_LABELS = ['月', '火', '水', '木', '金', '土', '日']

    @property
    def day_label(self):
        return self.DAY_LABELS[self.day_of_week] if 0 <= self.day_of_week <= 6 else '?'

    @property
    def time_label(self):
        return f'{self.start_time.strftime("%H:%M")}〜{self.end_time.strftime("%H:%M")}'

    def __repr__(self):
        return f'<FacilityTimeSlot {self.day_label} {self.time_label}>'
