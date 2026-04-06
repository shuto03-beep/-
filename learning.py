"""自己学習エンジン - パラメータ自動最適化"""
import json
import numpy as np
from datetime import datetime, timedelta
from config import LEARNING_FILE, DEFAULT_WEIGHTS


def load_learning_state() -> dict:
    """learning.jsonから学習状態を読み込む"""
    try:
        with open(LEARNING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "weights": DEFAULT_WEIGHTS.copy(),
            "parameters": {
                "stop_loss_pct": -0.03,
                "take_profit_pct": 0.08,
                "buy_threshold": 60,
            },
            "version": 1,
            "last_optimization": None,
            "performance_history": [],
        }


class _NumpyEncoder(json.JSONEncoder):
    """numpy型をPython型に変換するエンコーダー"""
    def default(self, obj):
        if hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        return super().default(obj)


def save_learning_state(learning_data: dict):
    """learning.jsonに保存"""
    LEARNING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEARNING_FILE, "w", encoding="utf-8") as f:
        json.dump(learning_data, f, ensure_ascii=False, indent=2, cls=_NumpyEncoder)


def should_run_optimization(state: dict) -> bool:
    """最適化を実行すべきか判定"""
    learning = load_learning_state()
    last_opt = learning.get("last_optimization")

    # 週次チェック
    if last_opt:
        last_date = datetime.fromisoformat(last_opt)
        if datetime.now() - last_date < timedelta(days=7):
            return False

    # クローズ済みトレードが5件以上あるか（A戦略を基準に判定）
    strategies = state.get("strategies", {})
    first_key = next(iter(strategies), None)
    if not first_key:
        return False
    closed = strategies[first_key].get("closed_trades", [])
    return len(closed) >= 5


def analyze_trade_history(state: dict) -> dict:
    """直近トレードの成績を分析"""
    # マルチ戦略対応: 全戦略のトレードを集約
    all_closed = []
    for s in state.get("strategies", {}).values():
        all_closed.extend(s.get("closed_trades", []))
    closed = all_closed
    if not closed:
        return {"total": 0, "wins": 0, "win_rate": 0, "avg_pnl_pct": 0}

    # 直近50件
    recent = closed[-50:]
    wins = [t for t in recent if t["pnl"] > 0]
    losses = [t for t in recent if t["pnl"] <= 0]

    # 指標別の勝率分析
    indicator_performance = {}
    for trade in recent:
        reasons = trade.get("signal_reasons", [])
        is_win = trade["pnl"] > 0
        for reason in reasons:
            key = _categorize_reason(reason)
            if key:
                if key not in indicator_performance:
                    indicator_performance[key] = {"wins": 0, "total": 0}
                indicator_performance[key]["total"] += 1
                if is_win:
                    indicator_performance[key]["wins"] += 1

    # AI判断の正確性
    ai_trades = [t for t in recent if t.get("ai_confidence", 0) > 0]
    ai_accuracy = 0
    if ai_trades:
        ai_wins = sum(1 for t in ai_trades if t["pnl"] > 0)
        ai_accuracy = ai_wins / len(ai_trades)

    return {
        "total": len(recent),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(recent) if recent else 0,
        "avg_pnl_pct": np.mean([t["pnl_pct"] for t in recent]) if recent else 0,
        "avg_win_pnl": np.mean([t["pnl_pct"] for t in wins]) if wins else 0,
        "avg_loss_pnl": np.mean([t["pnl_pct"] for t in losses]) if losses else 0,
        "indicator_performance": indicator_performance,
        "ai_accuracy": ai_accuracy,
        "ai_trade_count": len(ai_trades),
    }


def _categorize_reason(reason: str) -> str | None:
    """シグナル根拠をカテゴリに分類"""
    mapping = {
        "ゴールデンクロス": "ma_cross", "デッドクロス": "ma_cross",
        "上昇トレンド": "ma_trend", "下降トレンド": "ma_trend",
        "MACD": "macd",
        "RSI": "rsi",
        "ボリンジャー": "bollinger",
        "出来高": "volume",
        "ストキャスティクス": "stochastic",
        "一目均衡表": "ichimoku",
        "類似パターン": "historical",
    }
    for keyword, key in mapping.items():
        if keyword in reason:
            return key
    return None


def optimize_weights(analysis: dict) -> dict:
    """指標の重みを成績に基づき調整"""
    learning = load_learning_state()
    current_weights = learning.get("weights", DEFAULT_WEIGHTS.copy())
    ind_perf = analysis.get("indicator_performance", {})

    if analysis["total"] < 20:
        print("  [LEARNING] サンプル不足（20件未満）、重み調整スキップ")
        return current_weights

    new_weights = current_weights.copy()
    for key, perf in ind_perf.items():
        if perf["total"] < 5:
            continue
        win_rate = perf["wins"] / perf["total"]
        default = DEFAULT_WEIGHTS.get(key, 10)

        # 勝率60%以上: +5%、40%以下: -5%
        if win_rate >= 0.60:
            adjustment = int(current_weights[key] * 0.05)
            new_weights[key] = min(current_weights[key] + max(adjustment, 1), default * 2)
        elif win_rate <= 0.40:
            adjustment = int(current_weights[key] * 0.05)
            new_weights[key] = max(current_weights[key] - max(adjustment, 1), default // 2)

    # 合計が100になるように正規化
    total = sum(new_weights.values())
    if total > 0:
        scale = 100 / total
        new_weights = {k: max(1, int(v * scale)) for k, v in new_weights.items()}
        # 端数を最大ウェイトの項目に加算して合計100を保証
        diff = 100 - sum(new_weights.values())
        if diff != 0:
            max_key = max(new_weights, key=new_weights.get)
            new_weights[max_key] += diff

    return new_weights


def optimize_parameters(analysis: dict, state: dict) -> dict:
    """ストップロス/利確/閾値を最適化"""
    learning = load_learning_state()
    params = learning.get("parameters", {}).copy()
    # マルチ戦略対応: 全戦略のトレードを集約
    all_closed = []
    for s in state.get("strategies", {}).values():
        all_closed.extend(s.get("closed_trades", []))
    closed = all_closed

    if len(closed) < 20:
        return params

    recent = closed[-50:]

    # ストップロスの最適化: ストップロスで決済されたトレードの損失率を分析
    sl_trades = [t for t in recent if t.get("reason") == "STOP_LOSS"]
    if len(sl_trades) >= 5:
        avg_sl_loss = np.mean([t["pnl_pct"] for t in sl_trades])
        # 損失が平均-5%以上なら少し緩める、-2%以下ならもう少し厳しく
        if avg_sl_loss < -0.05:
            params["stop_loss_pct"] = max(params["stop_loss_pct"] * 0.95, -0.05)
        elif avg_sl_loss > -0.02:
            params["stop_loss_pct"] = min(params["stop_loss_pct"] * 1.05, -0.02)

    # 利確の最適化: 利確で決済されたトレードの利益率を分析
    tp_trades = [t for t in recent if t.get("reason") == "TAKE_PROFIT"]
    if len(tp_trades) >= 5:
        avg_tp_profit = np.mean([t["pnl_pct"] for t in tp_trades])
        if avg_tp_profit > 0.10:
            params["take_profit_pct"] = min(params["take_profit_pct"] * 1.05, 0.15)
        elif avg_tp_profit < 0.05:
            params["take_profit_pct"] = max(params["take_profit_pct"] * 0.95, 0.05)

    return params


def run_learning_cycle(state: dict) -> dict:
    """学習サイクルのメインエントリポイント"""
    print("[LEARNING] 学習サイクル開始...")
    learning = load_learning_state()

    # トレード分析
    analysis = analyze_trade_history(state)
    print(f"  勝率: {analysis['win_rate']:.0%}, 平均損益: {analysis['avg_pnl_pct']:.1%}")

    # 重み最適化
    new_weights = optimize_weights(analysis)
    learning["weights"] = new_weights

    # パラメータ最適化
    new_params = optimize_parameters(analysis, state)
    learning["parameters"] = new_params

    # バージョンアップ
    learning["version"] = learning.get("version", 0) + 1
    learning["last_optimization"] = datetime.now().isoformat()

    # パフォーマンス履歴追加
    perf_entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "version": learning["version"],
        "win_rate": analysis["win_rate"],
        "avg_pnl_pct": analysis["avg_pnl_pct"],
        "total_trades": analysis["total"],
    }
    learning.setdefault("performance_history", []).append(perf_entry)

    # 2週連続で成績悪化ならリセット
    perf_hist = learning["performance_history"]
    if len(perf_hist) >= 3:
        last_three = perf_hist[-3:]
        if all(p["win_rate"] < 0.40 for p in last_three):
            print("  [LEARNING] 3週連続勝率40%未満 → デフォルトにリセット")
            learning["weights"] = DEFAULT_WEIGHTS.copy()
            learning["parameters"] = {
                "stop_loss_pct": -0.03,
                "take_profit_pct": 0.08,
                "buy_threshold": 60,
            }

    save_learning_state(learning)
    print(f"  [LEARNING] v{learning['version']} 保存完了")
    return analysis


def generate_performance_report(state: dict) -> str:
    """週次パフォーマンスレポート生成"""
    analysis = analyze_trade_history(state)
    learning = load_learning_state()
    summary = []

    summary.append("📊 週次パフォーマンスレポート")
    summary.append("━" * 30)
    summary.append(f"学習バージョン: v{learning.get('version', 1)}")
    summary.append(f"総トレード数: {analysis['total']}")
    summary.append(f"勝率: {analysis['win_rate']:.0%}")
    summary.append(f"平均損益: {analysis['avg_pnl_pct']:.1%}")
    if analysis['wins'] > 0:
        summary.append(f"平均勝ち幅: +{analysis['avg_win_pnl']:.1%}")
    if analysis['losses'] > 0:
        summary.append(f"平均負け幅: {analysis['avg_loss_pnl']:.1%}")

    # AI精度
    if analysis["ai_trade_count"] > 0:
        summary.append(f"\n🤖 AI判断精度: {analysis['ai_accuracy']:.0%} ({analysis['ai_trade_count']}件)")

    # 指標別パフォーマンス
    ind_perf = analysis.get("indicator_performance", {})
    if ind_perf:
        summary.append("\n📈 指標別勝率:")
        for key, perf in sorted(ind_perf.items(), key=lambda x: x[1].get("wins", 0) / max(x[1].get("total", 1), 1), reverse=True):
            if perf["total"] >= 3:
                wr = perf["wins"] / perf["total"]
                summary.append(f"  {key}: {wr:.0%} ({perf['total']}件)")

    return "\n".join(summary)
