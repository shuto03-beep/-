import yfinance as yf
import requests
import os
from datetime import datetime

# ▼▼ 設定エリア（ここを自由に編集してください） ▼▼
# DiscordのURL（GitHubのSecretsから読み込みますが、テスト時は直接書いてもOK）
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# 監視リスト：銘柄ごとに「買い目標」「売り目標」を設定できます
WATCH_LIST = [
    {
        "ticker": "9432.T",   # NTT
        "name": "NTT",        # 通知に表示する名前
        "buy_target": 153.0,  # これ以下なら「買い」通知
        "sell_target": 160.0, # これ以上なら「売り」通知
        "check_rsi": True     # RSIも一緒に計算して表示するか
    },
    {
        "ticker": "7203.T",   # トヨタ自動車（例）
        "name": "トヨタ",
        "buy_target": 2500.0,
        "sell_target": 3000.0,
        "check_rsi": True
    },
    # 必要ならここに辞書 {...} をコピーして追加できます
]
# ▲▲ 設定エリア終了 ▲▲

def calculate_rsi(data, period=14):
    """RSIを計算する関数"""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_market():
    print(f"[{datetime.now()}] 市場チェック開始...")
    
    for item in WATCH_LIST:
        ticker = item["ticker"]
        name = item["name"]
        
        try:
            # データ取得（1ヶ月分）
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")
            
            if len(hist) < 15:
                print(f"{name}: データ不足のためスキップ")
                continue

            # 現在価格
            current_price = hist['Close'].iloc[-1]
            
            # RSI計算（オプション）
            rsi_val = 0
            rsi_str = ""
            if item["check_rsi"]:
                hist['RSI'] = calculate_rsi(hist)
                rsi_val = hist['RSI'].iloc[-1]
                rsi_str = f"(RSI: {rsi_val:.2f})"

            print(f"{name} | 現在: {current_price:.1f}円 {rsi_str}")

            # 判定ロジック
            # パターンA：買い目標以下になった（安値圏）
            if current_price <= item["buy_target"]:
                send_discord("buy", name, current_price, item["buy_target"], rsi_val)
            
            # パターンB：売り目標以上になった（高値圏）
            elif current_price >= item["sell_target"]:
                send_discord("sell", name, current_price, item["sell_target"], rsi_val)
                
        except Exception as e:
            print(f"エラー発生 ({name}): {e}")

def send_discord(type, name, current, target, rsi):
    """Discordに通知を送る関数"""
    
    if type == "buy":
        color = "🔵" # 青丸
        title = "買い時の可能性（安値圏）"
        diff_msg = f"目標の **{target}円** を割り込みました！"
    else:
        color = "🔴" # 赤丸
        title = "利確チャンス（高値圏）"
        diff_msg = f"目標の **{target}円** に到達しました！"

    message = (
        f"{color} **{title}**\n"
        f"銘柄: **{name}**\n"
        f"現在価格: **{current:.1f}円** {color}\n"
        f"{diff_msg}\n"
        f"参考RSI: {rsi:.2f}\n"
        f"------------------------"
    )
    
    payload = {"content": message}
    headers = {"Content-Type": "application/json"}
    
    try:
        if DISCORD_WEBHOOK_URL:
            requests.post(DISCORD_WEBHOOK_URL, json=payload, headers=headers)
            print(f"Discordへ通知送信: {name} - {type}")
        else:
            print("Webhook URL未設定")
    except Exception as e:
        print(f"送信エラー: {e}")

if __name__ == "__main__":
    check_market()
