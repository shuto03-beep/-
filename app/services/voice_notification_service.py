"""音声ノート分析結果のDiscord通知"""
import os
import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def _send_discord(message: str):
    """Discordにメッセージを送信"""
    if not DISCORD_WEBHOOK_URL:
        print(f"[VOICE-DISCORD] Webhook未設定 → コンソール出力:\n{message}")
        return

    url = DISCORD_WEBHOOK_URL.replace("https://discordapp.com/", "https://discord.com/")
    chunks = [message[i:i + 1990] for i in range(0, len(message), 1990)]
    for chunk in chunks:
        try:
            resp = requests.post(url, json={"content": chunk}, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[VOICE-DISCORD] 送信エラー: {e}")


def notify_analysis_complete(voice_note, tasks, analyses):
    """分析完了通知をDiscordに送信"""
    # タスクをquadrantごとにグループ化
    quadrants = {
        'do_first': [],
        'schedule': [],
        'delegate': [],
        'eliminate': [],
    }
    for task in tasks:
        quadrants.get(task.quadrant, []).append(task)

    msg = f"""🎙️ **音声ノート分析完了**
━━━━━━━━━━━━━━━━━━━
📝 **{voice_note.title}** ({voice_note.recorded_date})

📋 **要約**: {voice_note.summary[:200] if voice_note.summary else '(なし)'}...

"""

    # アイゼンハワーマトリクス
    msg += "🎯 **アイゼンハワーマトリクス**\n"

    if quadrants['do_first']:
        msg += "\n🔴 **今すぐやる（緊急×重要）**\n"
        for t in quadrants['do_first']:
            deadline = f" 期限:{t.deadline}" if t.deadline else ""
            msg += f"  • {t.title}{deadline}\n"

    if quadrants['schedule']:
        msg += "\n🟡 **計画する（重要）**\n"
        for t in quadrants['schedule']:
            deadline = f" 期限:{t.deadline}" if t.deadline else ""
            msg += f"  • {t.title}{deadline}\n"

    if quadrants['delegate']:
        msg += "\n🟠 **任せる（緊急）**\n"
        for t in quadrants['delegate']:
            msg += f"  • {t.title}\n"

    if quadrants['eliminate']:
        msg += "\n⚪ **排除する**\n"
        for t in quadrants['eliminate']:
            msg += f"  • {t.title}\n"

    # 分析ハイライト
    for analysis in analyses:
        if analysis.role == 'life_coach':
            parsed = analysis.parsed_content
            if parsed.get('encouragement'):
                msg += f"\n💪 **コーチからのメッセージ**: {parsed['encouragement']}\n"
        elif analysis.role == 'critic':
            parsed = analysis.parsed_content
            score = parsed.get('quality_score', '-')
            msg += f"\n📊 **分析品質スコア**: {score}/10\n"

    msg += f"\n🔗 ダッシュボードで詳細を確認してください"

    _send_discord(msg)


def notify_daily_summary(pending_tasks, overdue_tasks, patterns_count):
    """日次サマリー通知"""
    msg = f"""☀️ **日次ライフアナリティクス**
━━━━━━━━━━━━━━━━━━━
📋 未完了タスク: {len(pending_tasks)}件
⚠️ 期限超過: {len(overdue_tasks)}件
🧠 検出パターン: {patterns_count}種類
"""

    if overdue_tasks:
        msg += "\n🚨 **期限超過タスク**\n"
        for t in overdue_tasks[:5]:
            msg += f"  • {t.title} (期限: {t.deadline})\n"

    urgent = [t for t in pending_tasks if t.quadrant == 'do_first']
    if urgent:
        msg += "\n🔴 **今すぐやるべきタスク**\n"
        for t in urgent[:5]:
            msg += f"  • {t.title}\n"

    _send_discord(msg)
