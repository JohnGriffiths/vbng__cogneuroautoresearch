"""Shared helpers for the interview toolkit. Stdlib only, on purpose --
see README.md: this toolkit must never depend on any one LLM provider's
SDK, so it stays usable regardless of which chat/agent tool is open."""

import json
import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def session_paths(session_dir: str) -> dict:
    root = Path(session_dir)
    return {
        "root": root,
        "reading_list": root / "reading_list",
        "transcripts": root / "transcripts",
        "prompts": root / "prompts",
        "responses": root / "responses",
        "state": root / "state",
        "backlog": root / "state" / "backlog.json",
        "session_log": root / "state" / "session_log.md",
        "charter_seed": root / "charter_seed.yaml",
    }


def ensure_session_dirs(session_dir: str) -> dict:
    paths = session_paths(session_dir)
    for key in ("prompts", "responses", "state"):
        paths[key].mkdir(parents=True, exist_ok=True)
    return paths


def load_backlog(paths: dict) -> dict:
    if paths["backlog"].exists():
        return json.loads(paths["backlog"].read_text())
    return {"accounts": [], "questions": [], "parking_lot": [], "segments": []}


def save_backlog(paths: dict, backlog: dict) -> None:
    paths["backlog"].write_text(json.dumps(backlog, indent=2))


def extract_json_block(text: str) -> dict:
    """Pull the first ```json ... ``` fenced block out of an LLM reply."""
    match = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    if not match:
        raise ValueError(
            "No ```json block found in the response. Make sure the full "
            "reply (including the fenced block at the end) was pasted in."
        )
    return json.loads(match.group(1))


def summarize_accumulated_state(backlog: dict) -> str:
    if not backlog["accounts"] and not backlog["questions"]:
        return "(nothing synthesized yet -- this is the first segment)"
    lines = []
    if backlog["accounts"]:
        lines.append("Candidate theoretical accounts so far:")
        for a in backlog["accounts"]:
            lines.append(f"- {a['id']}: {a['claim']}")
    if backlog["questions"]:
        lines.append("\nCandidate questions so far:")
        for q in backlog["questions"]:
            lines.append(f"- {q['text']}")
    return "\n".join(lines)
