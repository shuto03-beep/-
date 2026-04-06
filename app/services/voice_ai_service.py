"""音声ノート AI分析エンジン - 5つの専門ロールによる多角的分析"""
import json
import os

AI_MODEL = "claude-sonnet-4-20250514"


def _get_api_key():
    return os.environ.get("ANTHROPIC_API_KEY")


def _call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 4000) -> str:
    """Claude APIを呼び出してテキスト応答を返す"""
    import anthropic

    client = anthropic.Anthropic(api_key=_get_api_key())
    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=max_tokens,
        timeout=60,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )
    return response.content[0].text.strip()


def _extract_json(text: str) -> dict:
    """レスポンスからJSON部分を抽出"""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return {}


def run_full_analysis(content: str, today_str: str) -> dict:
    """5つのロールで完全分析を実行し、結果をまとめて返す"""
    if not _get_api_key():
        return {"error": "ANTHROPIC_API_KEY未設定"}

    results = {}

    # Role 1: タスク抽出
    results['task_extractor'] = _analyze_task_extractor(content, today_str)

    # Role 2: ライフコーチ
    results['life_coach'] = _analyze_life_coach(content)

    # Role 3: 心理分析
    results['psychologist'] = _analyze_psychologist(content)

    # Role 4: 戦略プランナー
    results['strategist'] = _analyze_strategist(content, results)

    # Role 5: 批評家（他の分析結果を検証）
    results['critic'] = _analyze_critic(content, results)

    # 要約生成
    results['summary'] = _generate_summary(content)

    return results


def _analyze_task_extractor(content: str, today_str: str) -> dict:
    """Role 1: タスク抽出エージェント"""
    system = """あなたは日常会話からアクションアイテムを抽出する専門家です。
会話の中から「やるべきこと」「やりたいこと」「約束」「予定」「課題」を見つけ出し、
各タスクに緊急度(1-5)と重要度(1-5)を付与し、適切な期限を設定してください。

必ず以下のJSON形式で回答してください:
{
  "tasks": [
    {
      "title": "タスクのタイトル",
      "description": "詳細説明",
      "urgency": 1-5の数値,
      "importance": 1-5の数値,
      "deadline": "YYYY-MM-DD形式の期限（推測含む）",
      "reasoning": "なぜこの緊急度・重要度にしたかの理由"
    }
  ],
  "summary": "抽出したタスクの全体像"
}"""

    prompt = f"""以下の日常の録音テキストからタスクを抽出してください。
今日の日付: {today_str}

---録音テキスト---
{content}
---

上記から全てのアクションアイテム、やるべきこと、約束、予定を抽出し、JSON形式で回答してください。"""

    try:
        text = _call_claude(system, prompt)
        return _extract_json(text)
    except Exception as e:
        return {"error": str(e), "tasks": []}


def _analyze_life_coach(content: str) -> dict:
    """Role 2: ライフコーチエージェント"""
    system = """あなたは経験豊富なライフコーチです。クライアントの日常会話を分析し、
達成事項、課題、成長の機会を見つけ出します。ポジティブな面も課題も率直に伝え、
具体的で実行可能な改善提案を行ってください。

必ず以下のJSON形式で回答してください:
{
  "achievements": [
    {"title": "達成事項", "description": "詳細", "impact": "影響度(high/medium/low)"}
  ],
  "challenges": [
    {"title": "課題", "description": "詳細", "severity": "深刻度(high/medium/low)"}
  ],
  "suggestions": [
    {"title": "改善提案", "description": "具体的なアクション", "category": "health/career/relationship/mindset/skill/finance/lifestyle", "priority": "high/medium/low"}
  ],
  "encouragement": "励ましのメッセージ",
  "overall_assessment": "全体評価"
}"""

    prompt = f"""以下の日常の録音テキストをライフコーチの視点で分析してください。

---録音テキスト---
{content}
---

達成事項、課題、具体的な改善提案を含めてJSON形式で回答してください。"""

    try:
        text = _call_claude(system, prompt)
        return _extract_json(text)
    except Exception as e:
        return {"error": str(e)}


def _analyze_psychologist(content: str) -> dict:
    """Role 3: 心理分析エージェント"""
    system = """あなたは認知行動療法の専門家です。日常会話のパターンから、
認知バイアス、思考の癖、感情パターン、行動傾向を分析します。
批判的ではなく、気づきを促す形で伝えてください。

必ず以下のJSON形式で回答してください:
{
  "thinking_patterns": [
    {
      "name": "パターン名",
      "type": "cognitive_bias/habit/strength/weakness",
      "description": "このパターンの説明",
      "evidence": "会話中の根拠となる発言や行動",
      "impact": "このパターンが生活に与える影響",
      "suggestion": "より良い方向への具体的なアドバイス"
    }
  ],
  "emotional_state": {
    "primary_emotion": "主要な感情",
    "energy_level": "high/medium/low",
    "stress_indicators": ["ストレスの兆候"]
  },
  "cognitive_summary": "思考パターンの全体的な傾向"
}"""

    prompt = f"""以下の日常の録音テキストを心理学の視点で分析してください。
認知バイアス、思考の癖、感情パターンを特定してください。

---録音テキスト---
{content}
---

JSON形式で回答してください。"""

    try:
        text = _call_claude(system, prompt)
        return _extract_json(text)
    except Exception as e:
        return {"error": str(e)}


def _analyze_strategist(content: str, prior_results: dict) -> dict:
    """Role 4: 戦略プランナーエージェント"""
    context = ""
    if 'life_coach' in prior_results and 'suggestions' in prior_results['life_coach']:
        suggestions = prior_results['life_coach'].get('suggestions', [])
        context = "\n".join([f"- {s.get('title', '')}: {s.get('description', '')}" for s in suggestions])

    system = """あなたは人生戦略の専門家です。日常会話と他の分析結果を基に、
段階的な人生改善プランを策定します。短期（1週間）・中期（1ヶ月）・長期（3ヶ月）の
3段階でプランを作成してください。

必ず以下のJSON形式で回答してください:
{
  "improvements": [
    {
      "category": "health/career/relationship/mindset/skill/finance/lifestyle",
      "title": "改善プランのタイトル",
      "current_state": "現状の評価",
      "target_state": "目標の状態",
      "steps": [
        {"phase": "短期(1週間)", "action": "具体的なアクション"},
        {"phase": "中期(1ヶ月)", "action": "具体的なアクション"},
        {"phase": "長期(3ヶ月)", "action": "具体的なアクション"}
      ]
    }
  ],
  "key_focus": "最も優先すべき改善ポイント",
  "strategic_advice": "戦略的アドバイス"
}"""

    prompt = f"""以下の日常の録音テキストと、事前に行われた分析結果を基に、
段階的な人生改善プランを策定してください。

---録音テキスト---
{content}
---

---事前分析からの改善提案---
{context if context else "（なし）"}
---

JSON形式で回答してください。"""

    try:
        text = _call_claude(system, prompt)
        return _extract_json(text)
    except Exception as e:
        return {"error": str(e)}


def _analyze_critic(content: str, prior_results: dict) -> dict:
    """Role 5: 批評家エージェント - 他の分析を検証"""
    analyses_summary = json.dumps(
        {k: v for k, v in prior_results.items() if k != 'critic'},
        ensure_ascii=False,
        indent=2
    )

    system = """あなたは鋭い洞察力を持つ批評家です。他の4人の専門家が行った分析を検証し、
見落としている点、矛盾点、改善すべき点を指摘してください。
建設的な批評を行い、分析の質を向上させることが目的です。

必ず以下のJSON形式で回答してください:
{
  "review": {
    "strengths": ["分析の良い点"],
    "weaknesses": ["分析の弱い点・見落とし"],
    "contradictions": ["矛盾点"],
    "missing_perspectives": ["欠けている視点"]
  },
  "additional_insights": [
    {"title": "追加の洞察", "description": "詳細"}
  ],
  "refined_priorities": ["改良された優先事項リスト"],
  "quality_score": 1-10の品質スコア,
  "overall_review": "総合レビュー"
}"""

    prompt = f"""以下の日常の録音テキストに対する4人の専門家の分析結果を検証してください。

---録音テキスト---
{content}
---

---4人の専門家の分析結果---
{analyses_summary}
---

分析の品質を評価し、見落としや改善点を指摘してJSON形式で回答してください。"""

    try:
        text = _call_claude(system, prompt, max_tokens=3000)
        return _extract_json(text)
    except Exception as e:
        return {"error": str(e)}


def _generate_summary(content: str) -> str:
    """録音テキストの簡潔な要約を生成"""
    system = "あなたは優秀な要約者です。日常会話のテキストを簡潔に要約してください。要約は3-5文で、重要なポイントを漏らさないようにしてください。プレーンテキストで回答してください。"
    prompt = f"""以下の録音テキストを簡潔に要約してください。

---録音テキスト---
{content}
---"""

    try:
        return _call_claude(system, prompt, max_tokens=500)
    except Exception as e:
        return f"要約生成に失敗しました: {e}"
