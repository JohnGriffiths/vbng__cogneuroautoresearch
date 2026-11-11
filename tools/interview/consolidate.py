#!/usr/bin/env python3
"""Flatten a session's backlog into a charter seed.

Usage:
    python consolidate.py <session_dir>

Writes <session_dir>/charter_seed.yaml in roughly the shape of a real
charter.yaml's theory/questions blocks, minus confirmatory_plan and
falsifiable_if -- those get added in the offline drafting pass, not
here. No PyYAML dependency: this writes YAML by hand since the shape
is simple and fixed, keeping the whole toolkit stdlib-only.
"""

import argparse

from _common import ensure_session_dirs, load_backlog


def yaml_str(s: str) -> str:
    # block scalar for anything with special chars/newlines, quoted otherwise
    if any(c in s for c in ':\n"\'#') :
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    return s


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    args = parser.parse_args()

    paths = ensure_session_dirs(args.session_dir)
    backlog = load_backlog(paths)

    lines = [
        "# Charter seed -- NOT a frozen charter. Output of the intake interview",
        "# toolkit (tools/interview/). Needs an offline drafting pass: each",
        "# question needs a confirmatory_plan and falsifiable_if before this",
        "# becomes a real charter.yaml. See docs/DESIGN.md.",
        "",
        "theory:",
        "  candidate_accounts:",
    ]
    for a in backlog["accounts"]:
        lines.append(f"    - id: {a['id']}")
        lines.append(f"      claim: {yaml_str(a['claim'])}")

    lines.append("")
    lines.append("questions:")
    for i, q in enumerate(backlog["questions"], start=1):
        lines.append(f"  - id: q{i}_draft")
        lines.append(f"    text: {yaml_str(q.get('text', ''))}")
        lines.append(f"    rationale: {yaml_str(q.get('rationale', ''))}")
        if q.get("tentative_adjudicates"):
            lines.append(f"    tentative_adjudicates: {q['tentative_adjudicates']}")
        if q.get("dataset_hint"):
            lines.append(f"    dataset_hint: {yaml_str(q['dataset_hint'])}")
        if q.get("confidence"):
            lines.append(f"    confidence: {q['confidence']}")
        lines.append("    confirmatory_plan: null  # TODO: offline drafting pass")
        lines.append("    falsifiable_if: null  # TODO: offline drafting pass")

    lines.append("")
    lines.append("parking_lot:")
    for item in backlog["parking_lot"]:
        lines.append(f"  - {yaml_str(item)}")

    paths["charter_seed"].write_text("\n".join(lines) + "\n")

    print(f"Wrote {paths['charter_seed']}")
    print(
        f"  {len(backlog['accounts'])} candidate accounts, "
        f"{len(backlog['questions'])} candidate questions, "
        f"{len(backlog['parking_lot'])} parking-lot items across "
        f"{len(backlog['segments'])} segments"
    )


if __name__ == "__main__":
    main()
