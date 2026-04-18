"""エントリ JSON を圧縮して冗長なフィールドを除去する。"""
import copy
import json
from typing import Any

_EFFORT_BOILERPLATE = "(AI 未使用のためタスク抽出はスキップ)"
_TRANSCRIPT_CAP: dict[str, int | None] = {
    "safe": None,
    "balanced": 4000,
    "aggressive": 1500,
}
_EMPTY_FIELDS_LIFELOG = ("people", "locations", "mood", "key_points")
_EMPTY_FIELDS_TASK_ANALYSIS = ("blockers",)


def compact_entry(
    entry: dict,
    *,
    mode: str = "balanced",
    transcript_chars: int | None = None,
) -> tuple[dict, dict]:
    """エントリを圧縮して (new_entry, stats) を返す。

    stats = {bytes_before, bytes_after, bytes_saved, actions}
    """
    if mode not in _TRANSCRIPT_CAP:
        raise ValueError(f"unknown mode: {mode!r}")

    bytes_before = _measure(entry)
    out = copy.deepcopy(entry)
    actions: list[str] = []

    # --- すべてのモードで適用 ---
    _step_unwrap_envelope(out, actions)

    if mode in ("balanced", "aggressive"):
        _step_drop_boilerplate_effort(out, actions)
        _step_drop_empty_fields(out, actions)
        _step_dedupe_narrative(out, actions)

    if mode == "aggressive":
        _step_drop_metadata(out, actions)
        _step_drop_plaud_only_tag(out, actions)

    # transcript 文字数上限
    cap = transcript_chars if transcript_chars is not None else _TRANSCRIPT_CAP[mode]
    if cap is not None:
        _step_truncate_transcript(out, cap, actions)

    bytes_after = _measure(out)
    stats = {
        "bytes_before": bytes_before,
        "bytes_after": bytes_after,
        "bytes_saved": bytes_before - bytes_after,
        "actions": actions,
    }
    return out, stats


# ---------- 各ステップ ----------


def _step_unwrap_envelope(entry: dict, actions: list[str]) -> None:
    raw = entry.get("raw")
    if not isinstance(raw, dict):
        return
    transcript = raw.get("transcript", "")
    new_transcript, changed = _maybe_unwrap_envelope(transcript)
    if changed:
        raw["transcript"] = new_transcript
        actions.append("unwrap_envelope")


def _step_drop_boilerplate_effort(entry: dict, actions: list[str]) -> None:
    ta = entry.get("task_analysis")
    if not isinstance(ta, dict):
        return
    if ta.get("effort_summary") == _EFFORT_BOILERPLATE:
        ta["effort_summary"] = ""
        actions.append("drop_boilerplate_effort")


def _step_drop_empty_fields(entry: dict, actions: list[str]) -> None:
    dropped: list[str] = []

    lifelog = entry.get("lifelog")
    if isinstance(lifelog, dict):
        for key in _EMPTY_FIELDS_LIFELOG:
            if key in lifelog and _is_empty(lifelog[key]):
                del lifelog[key]
                dropped.append(key)

    ta = entry.get("task_analysis")
    if isinstance(ta, dict):
        for key in _EMPTY_FIELDS_TASK_ANALYSIS:
            if key in ta and _is_empty(ta[key]):
                del ta[key]
                dropped.append(key)

    if dropped:
        actions.append(f"drop_empty:{','.join(dropped)}")


def _step_dedupe_narrative(entry: dict, actions: list[str]) -> None:
    lifelog = entry.get("lifelog")
    raw = entry.get("raw")
    if not isinstance(lifelog, dict) or not isinstance(raw, dict):
        return
    narrative = lifelog.get("narrative", "")
    summary = raw.get("summary", "")
    if narrative and summary and narrative.strip() == summary.strip():
        del lifelog["narrative"]
        actions.append("drop_narrative_dup")


def _step_truncate_transcript(entry: dict, cap: int, actions: list[str]) -> None:
    raw = entry.get("raw")
    if not isinstance(raw, dict):
        return
    transcript = raw.get("transcript", "")
    if len(transcript) > cap:
        raw["transcript"] = transcript[:cap] + "\n…(以下略)…"
        actions.append(f"truncate_transcript:{cap}")


def _step_drop_metadata(entry: dict, actions: list[str]) -> None:
    changed = False
    lifelog = entry.get("lifelog")
    if isinstance(lifelog, dict) and "source" in lifelog:
        del lifelog["source"]
        changed = True
    if "source_file" in entry:
        del entry["source_file"]
        changed = True
    if changed:
        actions.append("drop_metadata")


def _step_drop_plaud_only_tag(entry: dict, actions: list[str]) -> None:
    lifelog = entry.get("lifelog")
    if not isinstance(lifelog, dict):
        return
    tags = lifelog.get("tags")
    if tags == ["plaud"]:
        lifelog["tags"] = []
        actions.append("drop_plaud_only_tag")


# ---------- ヘルパー ----------


def _maybe_unwrap_envelope(transcript: str) -> tuple[str, bool]:
    if not isinstance(transcript, str):
        return transcript, False
    stripped = transcript.strip()
    if not stripped.startswith("{"):
        return transcript, False
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return transcript, False
    if isinstance(parsed, dict) and isinstance(parsed.get("ai_content"), str):
        return parsed["ai_content"], True
    return transcript, False


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _measure(entry: dict) -> int:
    return len(json.dumps(entry, ensure_ascii=False, indent=2).encode("utf-8"))
