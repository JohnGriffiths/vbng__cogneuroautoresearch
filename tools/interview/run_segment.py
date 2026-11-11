#!/usr/bin/env python3
"""Assemble the synthesis prompt for one interview segment.

Usage:
    python run_segment.py <session_dir> <segment_number> <topic> <transcript_file>

Prints the assembled prompt and saves it to
<session_dir>/prompts/segment_<N>_prompt.md -- paste that into whatever
LLM chat you have open, then save the reply for ingest_response.py.
"""

import argparse
import json
import sys
from pathlib import Path

from _common import PROMPTS_DIR, ensure_session_dirs, load_backlog, summarize_accumulated_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    parser.add_argument("segment_number", type=int)
    parser.add_argument("topic")
    parser.add_argument("transcript_file")
    args = parser.parse_args()

    paths = ensure_session_dirs(args.session_dir)
    transcript = Path(args.transcript_file).read_text()
    backlog = load_backlog(paths)
    instructions = (PROMPTS_DIR / "synthesis_instructions.md").read_text()

    prompt = f"""{instructions}

---

## Segment {args.segment_number}: {args.topic}

### What's been synthesized in prior segments

{summarize_accumulated_state(backlog)}

### Transcript for this segment

{transcript}
"""

    out_path = paths["prompts"] / f"segment_{args.segment_number}_prompt.md"
    out_path.write_text(prompt)
    meta_path = paths["prompts"] / f"segment_{args.segment_number}_meta.json"
    meta_path.write_text(json.dumps({"segment": args.segment_number, "topic": args.topic}, indent=2))

    print(prompt)
    print(f"\n--- saved to {out_path} ---", file=sys.stderr)
    print(
        f"Paste the above into your LLM chat, then save the reply to "
        f"{paths['responses']}/segment_{args.segment_number}_response.md "
        f"and run ingest_response.py.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
