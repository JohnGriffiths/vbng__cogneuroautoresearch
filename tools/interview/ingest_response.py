#!/usr/bin/env python3
"""Merge an LLM's synthesis reply into the session backlog.

Usage:
    python ingest_response.py <session_dir> <segment_number> <response_file> [--topic TOPIC]

--topic is only needed for segment 0 (the reading-list seed, which has
no run_segment.py metadata file to read it back from). For segments
1+, the topic is read automatically from what run_segment.py recorded.
"""

import argparse
import json
from pathlib import Path

from _common import ensure_session_dirs, extract_json_block, load_backlog, save_backlog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    parser.add_argument("segment_number", type=int)
    parser.add_argument("response_file")
    parser.add_argument("--topic", default=None)
    args = parser.parse_args()

    paths = ensure_session_dirs(args.session_dir)
    response_text = Path(args.response_file).read_text()
    data = extract_json_block(response_text)

    topic = args.topic
    if topic is None:
        meta_path = paths["prompts"] / f"segment_{args.segment_number}_meta.json"
        if meta_path.exists():
            topic = json.loads(meta_path.read_text())["topic"]
        else:
            topic = "(unknown -- pass --topic)"

    backlog = load_backlog(paths)

    new_accounts = data.get("candidate_accounts", [])
    new_questions = data.get("candidate_questions", [])
    new_parking = data.get("parking_lot", [])

    existing_account_ids = {a["id"] for a in backlog["accounts"]}
    for a in new_accounts:
        if a["id"] in existing_account_ids:
            a = {**a, "id": f"{a['id']}_seg{args.segment_number}"}
        backlog["accounts"].append(a)

    backlog["questions"].extend(new_questions)
    backlog["parking_lot"].extend(new_parking)
    backlog["segments"].append(
        {"segment": args.segment_number, "topic": topic, "summary": data.get("summary", "")}
    )

    save_backlog(paths, backlog)

    with open(paths["session_log"], "a") as f:
        f.write(f"\n## Segment {args.segment_number}: {topic}\n\n")
        f.write(data.get("summary", "") + "\n\n")
        if new_accounts:
            f.write(f"New candidate accounts: {len(new_accounts)}\n")
        if new_questions:
            f.write(f"New candidate questions: {len(new_questions)}\n")
        if new_parking:
            f.write(f"New parking-lot items: {len(new_parking)}\n")

    print(f"Ingested segment {args.segment_number} ({topic}).")
    print(f"  +{len(new_accounts)} accounts, +{len(new_questions)} questions, +{len(new_parking)} parking-lot items")
    print(
        f"  Running totals: {len(backlog['accounts'])} accounts, "
        f"{len(backlog['questions'])} questions, {len(backlog['parking_lot'])} parked"
    )


if __name__ == "__main__":
    main()
