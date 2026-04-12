"""Plaud JSON エントリを Obsidian 用 Markdown に変換するスクリプト"""
import json
import os
import re
import glob

ENTRIES_DIR = "data/plaud/entries"
OUTPUT_DIR = "knowledge-base/raw/articles"

def slugify(title):
    """日本語タイトルをファイル名用に変換（kebab-case）"""
    # 日付プレフィックスがあればそのまま使う
    s = title.strip()
    # スペース・全角スペースをハイフンに
    s = re.sub(r'[\s　]+', '-', s)
    # ファイル名に使えない文字を除去
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    # 連続ハイフンを1つに
    s = re.sub(r'-+', '-', s)
    s = s.strip('-')
    return s.lower() if s.isascii() else s

def extract_transcript(raw):
    """raw.transcript からテキストを抽出"""
    transcript = raw.get("transcript", "")
    if not transcript:
        return ""

    # API同期エントリ: JSON文字列の中に ai_content がある場合
    try:
        parsed = json.loads(transcript)
        if isinstance(parsed, dict) and "ai_content" in parsed:
            content = parsed["ai_content"]
            # 画像リンクを除去 (Plaud独自のパス)
            content = re.sub(r'!\[.*?\]\(permanent/.*?\)', '', content)
            return content.strip()
    except (json.JSONDecodeError, TypeError):
        pass

    return transcript

def convert_entry(filepath):
    """1件のエントリを Markdown に変換"""
    with open(filepath, "r", encoding="utf-8") as f:
        entry = json.load(f)

    entry_id = entry.get("id", "unknown")
    title = entry.get("title", entry_id)
    recorded = entry.get("recorded_at", "")[:10]

    # lifelog情報
    lifelog = entry.get("lifelog", {})
    tags = lifelog.get("tags", [])
    narrative = lifelog.get("narrative", "")
    mood = lifelog.get("mood", "")
    people = lifelog.get("people", [])

    # raw情報
    raw = entry.get("raw", {})
    transcript = extract_transcript(raw)
    summary = raw.get("summary", "")

    # タスク
    tasks = entry.get("tasks", [])

    # メモ
    notes = entry.get("notes", [])

    # Markdown 組み立て
    lines = []
    lines.append(f"# {title}")
    lines.append(f"<!-- recorded: {recorded} -->")
    lines.append(f"<!-- source: plaud -->")
    if tags:
        lines.append(f"<!-- tags: {', '.join(tags)} -->")
    if mood:
        lines.append(f"<!-- mood: {mood} -->")
    lines.append("")

    # 要約/ナラティブ
    if summary or narrative:
        lines.append("## 概要")
        if summary:
            lines.append(summary)
        elif narrative:
            lines.append(narrative)
        lines.append("")

    # トランスクリプト/AI生成コンテンツ
    if transcript:
        # ai_content の場合はすでにセクション構造を持っているので、
        # 見出しレベルを調整（# → ## に）
        if transcript.startswith("#"):
            # 最初の見出し行（タイトル重複）を除去
            content_lines = transcript.split("\n")
            filtered = []
            skip_first_heading = True
            for line in content_lines:
                if skip_first_heading and line.startswith("# "):
                    skip_first_heading = False
                    continue
                filtered.append(line)
            transcript = "\n".join(filtered).strip()

        if transcript:
            lines.append("## 内容")
            lines.append(transcript)
            lines.append("")

    # タスク
    if tasks:
        lines.append("## タスク")
        for t in tasks:
            check = "x" if t.get("status") == "done" else " "
            priority = t.get("priority", "")
            due = t.get("due", "")
            task_line = f"- [{check}] {t.get('title', '')}"
            meta = []
            if priority:
                meta.append(f"優先度:{priority}")
            if due:
                meta.append(f"期限:{due}")
            if meta:
                task_line += f" ({', '.join(meta)})"
            lines.append(task_line)
        lines.append("")

    # 人物
    if people:
        lines.append("## 関連人物")
        for p in people:
            lines.append(f"- {p}")
        lines.append("")

    # メモ
    if notes:
        lines.append("## メモ")
        for n in notes:
            lines.append(f"- {n.get('text', '')}")
        lines.append("")

    return "\n".join(lines), entry_id

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    json_files = glob.glob(os.path.join(ENTRIES_DIR, "*.json"))
    count = 0

    for filepath in sorted(json_files):
        try:
            md_content, entry_id = convert_entry(filepath)
            # ファイル名: エントリIDをそのまま使う（既にkebab-case的）
            filename = slugify(entry_id) + ".md"
            outpath = os.path.join(OUTPUT_DIR, filename)
            with open(outpath, "w", encoding="utf-8") as f:
                f.write(md_content)
            count += 1
        except Exception as e:
            print(f"ERROR: {filepath}: {e}")

    print(f"変換完了: {count} 件のエントリを {OUTPUT_DIR}/ に出力しました")

if __name__ == "__main__":
    main()
