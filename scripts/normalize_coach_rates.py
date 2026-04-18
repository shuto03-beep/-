"""既存指導者の時間単価を会計年度ポリシーに合わせて正規化する。

固定単価期間中: 有償 → FIXED_PAID_RATE、無償 → 0
自由期間中: 変更しない（既存値を尊重）

本番環境で `python scripts/normalize_coach_rates.py` として実行。
既存のCoachレコードを更新しコミットします。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.coach import Coach
from app.utils.fiscal import FIXED_PAID_RATE, is_fixed_rate_period, fiscal_period_label


def main():
    app = create_app()
    with app.app_context():
        print(f'現在: {fiscal_period_label()}')
        if not is_fixed_rate_period():
            print('自由期間のため、既存の時間単価は変更しません。')
            return

        changed = 0
        for c in Coach.query.all():
            if c.compensation_type == Coach.COMPENSATION_UNPAID:
                target = 0
            else:
                target = FIXED_PAID_RATE
            if (c.hourly_rate or 0) != target:
                print(f'  {c.full_name}: {c.hourly_rate} → {target}')
                c.hourly_rate = target
                changed += 1

        if changed:
            db.session.commit()
            print(f'✅ {changed}件の指導者の時間単価を正規化しました。')
        else:
            print('正規化の必要はありません。')


if __name__ == '__main__':
    main()
