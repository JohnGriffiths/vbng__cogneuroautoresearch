# Intake interview toolkit

Turns a live, 3-party informational interview (host/interviewer + domain
scientist + an LLM doing synthesis) into a charter seed — candidate
theoretical accounts and candidate questions, ready for the offline
drafting pass that turns them into a real `charter.yaml` (see the core
design doc, `docs/DESIGN.md`).

**Harness/provider/model agnostic by construction.** None of these
scripts call any LLM API. Every step just assembles a plain text prompt
file; you paste that into whatever chat interface you have open —
Claude Code, Claude.ai, ChatGPT, Codex CLI, Gemini, a local model, it
doesn't matter — and paste the reply back into a response file for the
next script to ingest. No API keys, no SDKs, no vendor dependency
anywhere in this toolkit.

Only dependency: Python 3 stdlib. PDF text extraction (reading-list
stage only) uses `pypdf` if it's installed, and degrades gracefully
(falls back to filenames only) if it isn't.

## Workflow

Everything lives under one session directory per interview, e.g.
`sessions/2026-11-face-identity/`. Nothing here is specific to any one
research topic — pass a fresh `session_dir` for each new scientist/topic.

### Stage 0: reading list (before the call)

1. Scientist drops background PDFs into `<session_dir>/reading_list/`.
2. `python seed_from_reading_list.py <session_dir>`
   — prints an assembled prompt (also saved to
   `<session_dir>/prompts/reading_list_prompt.md`) asking an LLM to
   propose initial candidate theoretical accounts from the literature.
3. Paste that prompt into any LLM chat. Save its reply as
   `<session_dir>/responses/reading_list_response.md`.
4. `python ingest_response.py <session_dir> 0 <session_dir>/responses/reading_list_response.md --topic "reading list seed"`
   — merges the structured output into the running backlog.

### Stages 1-4: live interview segments (during the call)

Record the call (see `docs/DESIGN.md` discussion on this — Meet
transcript requires a Workspace account; Otter.ai or similar works on
any account). For each ~15-minute subtopic:

1. Save the segment's transcript as plain text, e.g.
   `<session_dir>/transcripts/segment_1.txt`.
2. `python run_segment.py <session_dir> 1 "Landscape: what questions do you actually care about, and why" <session_dir>/transcripts/segment_1.txt`
   — assembles a prompt (instructions + everything synthesized in prior
   segments, for continuity + the new transcript) and prints/saves it.
3. Paste into your LLM chat of choice. This is the "Claude, what have
   you heard" moment — read the synthesis back to the room.
4. Save the reply as `<session_dir>/responses/segment_1_response.md`.
5. `python ingest_response.py <session_dir> 1 <session_dir>/responses/segment_1_response.md`
   — topic is read back automatically from step 2's metadata. Merges
   new candidate accounts/questions/parking-lot items into the backlog
   and prints running totals.
6. Move to the next subtopic. Repeat for segments 2-4.

### Final: consolidate

`python consolidate.py <session_dir>`

Flattens the whole session's backlog into `<session_dir>/charter_seed.yaml`
— candidate theoretical accounts and candidate questions in the same
shape as a real `charter.yaml`'s `theory` and `questions` blocks, minus
`confirmatory_plan`/`falsifiable_if` (that's the offline drafting pass,
not this tool's job). The parking lot comes along as an appendix.

**This is a backlog, not a frozen charter.** Hand `charter_seed.yaml` to
whoever does the drafting pass (today: ask an LLM to flesh out each
question's confirmatory plan and dataset binding; eventually: a
dedicated mksparcs CLI step). Nothing here gets frozen or executed
directly.

## Expected LLM output format

Every synthesis prompt this toolkit generates ends with a strict
instruction: respond with a short human-readable summary paragraph,
followed by one fenced ```json block with this shape:

```json
{
  "summary": "one paragraph, for reading back to the room",
  "candidate_accounts": [
    {"id": "short_slug", "claim": "one or two sentences"}
  ],
  "candidate_questions": [
    {
      "text": "...",
      "rationale": "...",
      "tentative_adjudicates": ["short_slug"],
      "dataset_hint": "...",
      "confidence": "low|medium|high"
    }
  ],
  "parking_lot": ["anything off-topic for this segment worth revisiting"]
}
```

`ingest_response.py` extracts and parses that block; everything outside
it (the human-readable summary) is only for reading aloud live, not
machine-processed. If the LLM's reply doesn't contain a parseable block,
the script says so clearly rather than silently dropping content.
