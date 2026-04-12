"""Plaud データから Wiki ページ（sources / concepts / entities）を一括生成する"""
import json
import os
import re
import glob
from datetime import datetime

BASE = "knowledge-base"
ENTRIES_DIR = "data/plaud/entries"
WIKI = f"{BASE}/wiki"
TODAY = datetime.now().strftime("%Y-%m-%d")


def write_page(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def extract_ai_content(raw):
    transcript = raw.get("transcript", "")
    if not transcript:
        return ""
    try:
        parsed = json.loads(transcript)
        if isinstance(parsed, dict) and "ai_content" in parsed:
            content = parsed["ai_content"]
            content = re.sub(r'!\[.*?\]\(permanent/.*?\)', '', content)
            return content.strip()
    except (json.JSONDecodeError, TypeError):
        pass
    return transcript


# ── ソース要約を生成 ──
def generate_sources():
    files = sorted(glob.glob(os.path.join(ENTRIES_DIR, "*.json")))
    sources = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                entry = json.load(f)
        except Exception:
            continue

        eid = entry.get("id", "")
        title = entry.get("title", eid)
        recorded = entry.get("recorded_at", "")[:10]
        lifelog = entry.get("lifelog", {})
        tags = lifelog.get("tags", [])
        narrative = lifelog.get("narrative", "")
        raw = entry.get("raw", {})
        summary = raw.get("summary", "")
        ai_content = extract_ai_content(raw)
        tasks = entry.get("tasks", [])

        # 要約テキスト: narrative > summary > ai_content の最初の段落
        synopsis = narrative or summary
        if not synopsis and ai_content:
            paragraphs = [p.strip() for p in ai_content.split("\n\n") if p.strip() and not p.strip().startswith("#")]
            synopsis = paragraphs[0] if paragraphs else ""

        if not synopsis:
            synopsis = f"{title} の記録。"

        # 概念抽出用にキーワードも保存
        tag_str = ", ".join(tags) if tags else "plaud"

        slug = re.sub(r'[\s　]+', '-', eid.strip())
        slug = re.sub(r'[<>:"/\\|?*]', '', slug)

        md = f"""# {title}
<!-- tags: {tag_str} -->
<!-- updated: {TODAY} -->
<!-- recorded: {recorded} -->
<!-- source-entry: {eid} -->

## 概要
{synopsis}
"""
        if tasks:
            md += "\n## 抽出タスク\n"
            for t in tasks:
                check = "x" if t.get("status") == "done" else " "
                md += f"- [{check}] {t.get('title', '')}\n"

        md += f"""
## 関連概念
<!-- Ingest で自動リンク -->

## 元データ
- [[{slug}|raw/articles/{slug}]]
"""
        outpath = os.path.join(WIKI, "sources", f"{slug}.md")
        write_page(outpath, md)
        sources.append({
            "id": eid, "slug": slug, "title": title,
            "recorded": recorded, "tags": tags, "synopsis": synopsis
        })
    return sources


# ── 概念ページ ──
CONCEPTS = {
    "部活動の地域展開": {
        "tags": "教育, 行政, いなチャレ",
        "summary": "学校の部活動を地域団体へ移行する取り組み。稲美町では「いなチャレ」として令和7〜10年度にかけて段階的に実施。教員の負担軽減と地域スポーツ振興の両立が目的。",
        "details": "教職員の兼職兼業の扱い、指導者登録制度、施設の共有ルール、予算（補助金・交付金）の管理、保護者説明会の運営など多岐にわたる課題を含む。南中学校・北中学校を対象とした先行実施が進行中。",
        "related": ["教育委員会運営", "施設管理", "予算管理"],
    },
    "教育委員会運営": {
        "tags": "教育, 行政, 組織",
        "summary": "稲美町教育委員会における組織運営、人事異動、事務手続き全般。生涯学習課と教育課の連携が主要テーマ。",
        "details": "年度替わりの引継ぎ、新規採用職員のオンボーディング、押印フローの見直し、ファイルサーバーのアクセス権限管理、文書管理のデジタル化推進などを含む。",
        "related": ["部活動の地域展開", "予算管理", "施設管理"],
    },
    "施設管理": {
        "tags": "行政, 設備, セキュリティ",
        "summary": "学校施設・社会体育施設の管理運営。スマートキー（キーズボックス）導入、夜間利用、照明設備、セキュリティなど。",
        "details": "テニスコートや体育館の夜間利用ルール、利用団体への鍵の受け渡しフロー、減免カードの運用、グラウンドライト設置計画などが議論されている。",
        "related": ["教育委員会運営", "部活動の地域展開"],
    },
    "予算管理": {
        "tags": "行政, 財務, 補助金",
        "summary": "行政における予算執行・決算管理。繰越処理、補助金申請、負担行為、決裁フローなど。",
        "details": "年度末の繰越手続き、補正予算の編成、所得税源泉徴収、通勤手当の計算、謝金の支払い処理など、地方自治体の財務実務を幅広くカバー。",
        "related": ["教育委員会運営", "部活動の地域展開"],
    },
    "人権研修": {
        "tags": "教育, 研修, 対話",
        "summary": "職場における人権研修の設計と実施。ハラスメント、アンコンシャス・バイアス、マイクロアグレッションなどを対話形式で学ぶ。",
        "details": "法的線引きではなく「差別を生みやすい社会構造」と「個人の無自覚な偏見」に焦点。参加者の当事者性を引き出すアクティブラーニング手法を採用し、対話文化の醸成を目指す。まつお先生による指導。",
        "related": ["教育委員会運営", "自己分析と成長"],
    },
    "家庭菜園": {
        "tags": "家庭, 趣味, 農業",
        "summary": "スイカ・トマト・きゅうり・なす・ピーマンなどの家庭菜園活動。コンパニオンプランツ、連作障害対策、害虫管理などの技術も含む。",
        "details": "家族（子どもたち）と一緒に植物の観察・収穫を行う。マリーゴールドによる害虫防除、バジルとトマトのコンパニオンプランツ、スズメバチの巣への対処、水仙とネギの見分け方なども記録。",
        "related": ["家族の日常"],
    },
    "家族の日常": {
        "tags": "家庭, 子育て, 日常",
        "summary": "春馬・カナタ・アオトの3人の子どもとの日常生活の記録。ゲーム管理、学習支援、食事計画、外出・娯楽など。",
        "details": "Nintendo Switchの時間管理（15分ルール）、漢字学習、宿題の見守り、映画鑑賞（コナン・ドラえもん）、外食の段取り、洗濯物たたみなどの家事分担を含む。失敗を受け入れる姿勢や自己改善についての親子対話も記録。",
        "related": ["家庭菜園", "自己分析と成長"],
    },
    "自己分析と成長": {
        "tags": "自己啓発, ADHD, コーチング",
        "summary": "ADHD傾向の自己認識、優先順位付けの課題、エッセンシャリズムの実践。常時録音×AI構造化による認知抜け漏れ対策。",
        "details": "タスクの優先度判断（重要度×緊急度マトリックス）、仮説思考の訓練、「カルピス希釈」の比喩による成長モデル、他者評価と自己基準のバランスなど。40代を前にした自己探求の記録。",
        "related": ["AI活用", "人権研修", "投資と経済"],
    },
    "AI活用": {
        "tags": "テクノロジー, AI, ツール",
        "summary": "Plaud NotePin Sによる常時録音、Claude CodeやCursor IDEの導入、GenSparkの活用など、AI技術を日常業務・生活に統合する取り組み。",
        "details": "録音データからの自動文字起こし・要約、会議議事録の自動生成、MCP経由のメール・Slack連携、ナレッジベースの構築ワークフローなど。「録音資産のインサイト化」をSOP化する試みも。",
        "related": ["自己分析と成長"],
    },
    "投資と経済": {
        "tags": "経済, 投資, 日本株",
        "summary": "日本株市場の分析、NISA活用、経済学理論（シュンペーター、アダム・スミス、フリードマン等）の学習記録。",
        "details": "日経225の目標値分析、為替（ドル円160円台）の影響、インフレと購買力の関係、日本企業のROE改善トレンドなど。投資戦略と経済理論を実務的に結びつける議論。",
        "related": ["自己分析と成長"],
    },
}


def generate_concepts():
    for name, data in CONCEPTS.items():
        slug = re.sub(r'[\s　]+', '-', name)
        related_links = "\n".join([f"- [[{r}]]" for r in data["related"]])
        md = f"""# {name}
<!-- tags: {data['tags']} -->
<!-- updated: {TODAY} -->

## 概要
{data['summary']}

## 詳細
{data['details']}

## 関連概念
{related_links}

## 出典
<!-- 複数のPlaudエントリから抽出 -->
"""
        write_page(os.path.join(WIKI, "concepts", f"{slug}.md"), md)
    return list(CONCEPTS.keys())


# ── エンティティページ ──
ENTITIES = {
    "稲美町教育委員会": {
        "type": "組織",
        "tags": "行政, 教育, 稲美町",
        "summary": "兵庫県稲美町の教育行政機関。生涯学習課・教育課を擁し、部活動の地域展開（いなチャレ）を推進中。",
        "related": ["教育委員会運営", "部活動の地域展開"],
    },
    "生涯学習課": {
        "type": "部署",
        "tags": "行政, 教育",
        "summary": "稲美町教育委員会内の部署。社会体育施設管理、コミュニティスクール運営、生涯学習事業を担当。",
        "related": ["教育委員会運営", "施設管理"],
    },
    "春馬": {
        "type": "人物",
        "tags": "家族",
        "summary": "記録者の子ども（第1子）。ゲームや学習に関する記録が多い。",
        "related": ["家族の日常"],
    },
    "カナタ": {
        "type": "人物",
        "tags": "家族",
        "summary": "記録者の子ども（第2子）。兄弟間のやりとりが記録されている。",
        "related": ["家族の日常"],
    },
    "アオト": {
        "type": "人物",
        "tags": "家族",
        "summary": "記録者の末子。幼稚園児。",
        "related": ["家族の日常"],
    },
    "稲美北中学校": {
        "type": "学校",
        "tags": "教育, 稲美町",
        "summary": "部活動の地域展開（いなチャレ）の対象校の一つ。",
        "related": ["部活動の地域展開"],
    },
    "稲美中学校": {
        "type": "学校",
        "tags": "教育, 稲美町",
        "summary": "部活動の地域展開（いなチャレ）の対象校の一つ。南中学校とも呼ばれる。",
        "related": ["部活動の地域展開"],
    },
}


def generate_entities():
    for name, data in ENTITIES.items():
        slug = re.sub(r'[\s　]+', '-', name)
        related_links = "\n".join([f"- [[{r}]]" for r in data["related"]])
        md = f"""# {name}
<!-- type: {data['type']} -->
<!-- tags: {data['tags']} -->
<!-- updated: {TODAY} -->

## 概要
{data['summary']}

## 関連概念
{related_links}
"""
        write_page(os.path.join(WIKI, "entities", f"{slug}.md"), md)
    return list(ENTITIES.keys())


# ── インデックス再構築 ──
def generate_index(sources, concept_names, entity_names):
    # 概念セクション
    concept_lines = "\n".join([f"- [[{c}]]" for c in sorted(concept_names)])

    # エンティティセクション
    entity_lines = "\n".join([f"- [[{e}]]" for e in sorted(entity_names)])

    # ソースセクション（日付でグループ化）
    sources_by_date = {}
    for s in sources:
        date = s["recorded"][:7] if s["recorded"] else "不明"
        sources_by_date.setdefault(date, []).append(s)

    source_lines = ""
    for date in sorted(sources_by_date.keys(), reverse=True):
        source_lines += f"\n### {date}\n"
        for s in sorted(sources_by_date[date], key=lambda x: x["recorded"]):
            source_lines += f"- [[{s['slug']}|{s['title']}]] ({s['recorded']})\n"

    md = f"""# ナレッジベース インデックス
<!-- updated: {TODAY} -->

## 概念 ({len(concept_names)}件)
{concept_lines}

## エンティティ ({len(entity_names)}件)
{entity_lines}

## 出典 ({len(sources)}件)
{source_lines}
"""
    write_page(os.path.join(WIKI, "index.md"), md)


# ── ログ更新 ──
def update_log(source_count, concept_count, entity_count):
    log_path = os.path.join(WIKI, "log.md")
    md = f"""# 変更ログ

| 日付 | 操作 | 詳細 |
|------|------|------|
| {TODAY} | Ingest | Plaudエントリ {source_count}件を取り込み。概念ページ {concept_count}件、エンティティページ {entity_count}件を生成。 |
"""
    write_page(log_path, md)


# ── メイン ──
def main():
    print("ソース要約を生成中...")
    sources = generate_sources()
    print(f"  → {len(sources)} 件のソース要約を生成")

    print("概念ページを生成中...")
    concept_names = generate_concepts()
    print(f"  → {len(concept_names)} 件の概念ページを生成")

    print("エンティティページを生成中...")
    entity_names = generate_entities()
    print(f"  → {len(entity_names)} 件のエンティティページを生成")

    print("インデックスを再構築中...")
    generate_index(sources, concept_names, entity_names)

    print("変更ログを更新中...")
    update_log(len(sources), len(concept_names), len(entity_names))

    print(f"\nIngest 完了!")
    print(f"  ソース: {len(sources)} 件")
    print(f"  概念:   {len(concept_names)} 件")
    print(f"  エンティティ: {len(entity_names)} 件")


if __name__ == "__main__":
    main()
