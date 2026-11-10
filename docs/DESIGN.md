# Autoresearch Framework — Design

Status: draft, consolidating brainstorm. Not yet implemented.

**Working name: MkSPARCS** — Mk(ake) + **S**elf-**P**aced **A**uto **R**esearch
**C**o-**S**cientist. This repo is not yet renamed to reflect it, but any
library code, CLI, or package built from this design should be named
`mksparcs` from the start (package name, import name, CLI entry point) so
no rename is needed later.

## Goal

A framework for semi-autonomous, long-running "autoresearch" in cognitive
neuroscience / neuroimaging. A scientist specifies a landscape of research
questions and datasets; agentic workers (Claude, Codex, Antigravity, GitHub
Copilot, opencode, local models) then work the queue — sometimes
continuously, sometimes on a deliberate slow burn — pushing results back to
this repo for review.

Two constraints shape everything below:

- **Scientific integrity under autonomy.** An agent that runs thousands of
  analyses unsupervised can silently become a p-hacking machine. The garden-
  of-forking-paths problem already plagues human-run neuroimaging work; an
  autonomous agent makes it worse by volume unless the framework forces
  pre-commitment and full provenance.
- **Provider/subscription portability.** Work must survive hitting a token
  or subscription cap on any one provider, on any one machine, without
  losing progress — so state has to live in the repo, not in a session.

## 1. Setup phase (intake)

Canonical artifact: a **research charter** — a structured file (YAML, or
Markdown with YAML frontmatter) committed to the repo. It is the one thing
every worker, on every provider, reads before doing anything. How it gets
authored is separate from what it contains.

**Authoring UX (decided):** a conversational interview (scientist talks to
an agent in natural language; the agent interviews and converges on the
charter file), not a browser wizard or a blank template handed to the
scientist. Rationale: zero extra engineering, handles ambiguity naturally,
lets the schema stabilize before we invest in a guided UI. A browser-based
wizard (published as an Artifact) remains a plausible v2 once the schema is
proven out — not built now.

Interview phases:

1. **Orientation** — domain/theme, hypothesis-driven vs. hypothesis-generating, time horizon.
2. **Question landscape** — enumerate questions/themes; for each, rationale and what would count as disconfirming.
3. **Dataset binding** — datasets, access paths/format, DUA restrictions, available phenotypes/covariates.
4. **Analysis plan per question** — confirmatory plan + exploratory sandbox (see §2).
5. **Autonomy envelope** — budget caps, stop-and-ask triggers, check-in cadence.
6. **Output & success criteria** — deliverable format, reporting cadence.
7. **Freeze** — charter committed to git. Every later edit is just another commit with an honest message; git history *is* the amendment log, no bespoke versioning needed.

## 2. Charter schema (illustrative, not final)

```yaml
program: "resting-state FC and depressive symptom severity"
frozen_at: null   # set on first freeze commit

questions:
  - id: q1
    text: "Does default-mode/salience network connectivity track PHQ-9 severity?"
    rationale: "..."
    falsifiable_if: "no FC-PHQ-9 association survives correction in confirmatory model"
    confirmatory_plan:
      model: "FC_edge ~ PHQ9 + age + sex + motion + site"
      correction: "FDR across pre-specified edge set"
      exclusions: "motion > 0.3mm mean FD"
    exploratory_sandbox:
      allowed: true
      tag_policy: "never reported as confirmatory; always labeled exploratory"

datasets:
  - name: "ds001"
    path: "/data/.../ds001"
    format: "BIDS"
    dua_constraints: "no redistribution, aggregate stats only"

autonomy:
  budget: {tokens: ..., wallclock_days: ...}
  stop_and_ask_if:
    - "result p < 1e-5 in exploratory sandbox"
    - "wants to access dataset not listed above"
    - "cost projection exceeds budget by >20%"
  checkin_cadence: "daily digest, weekly summary"

trigger:
  mode: continuous        # or "cron" for slow-burn projects — see §5
  schedule: null          # e.g. "every 2 days" when mode: cron
  max_claims_per_cycle: null
  budget_per_cycle: null

outputs:
  deliverables: ["running findings log", "final report", "reproducible analysis code"]
```

**Pre-registration discipline (decided: strict).** The charter must
pre-commit a confirmatory analysis plan and correction procedure per
question before exploration begins. Anything outside that plan is logged
and reported as exploratory, never silently promoted to confirmatory.

## 2a. Theory layer: candidate accounts, not just analyses

A flat list of questions invites data dredging dressed up with guardrails —
"we ran 8 tests" instead of a cumulative research programme. The fix: every
charter carries a **theory layer** above the question list, and every
question is tagged with which theoretical account(s) it adjudicates between
and what pattern each account predicts (strong inference — Platt, 1964: set
up competing hypotheses and design the test to kill at least one of them).

```yaml
theory:
  candidate_accounts:
    - id: account_a
      claim: "..."
    - id: account_b
      claim: "..."

questions:
  - id: q1
    ...
    adjudicates:
      account_a: "predicted pattern under this account"
      account_b: "predicted pattern under this account"

synthesis:
  doc: "SYNTHESIS.md"
  update_trigger: "after every N question investigations, or on demand"
  content: >
    current standing of each candidate_account given findings so far — an
    integrative judgment call, not a result list
```

`SYNTHESIS.md` is a living document per project repo, not a per-question
report. A **synthesis investigation** is its own claimable unit type: it
doesn't run new analyses, it reviews completed ones and rewrites the
standing of each candidate account. This is what keeps the theory layer
alive instead of being a write-once mission statement.

## 3. Unit of work: self-contained investigation

Each claimed question (or question × dataset pairing) becomes its own git
branch (`investigation/q17-ds001`), checked out into its own worktree. All
work — code, intermediate outputs, report, logs — lives inside that branch,
so concurrent investigations never touch each other's files. This is what
makes the system embarrassingly parallel regardless of provider.

Completion = push branch + open PR.

- Confirmatory, in-plan results → PR can auto-merge.
- Anything tripping a `stop_and_ask_if` condition → PR sits for human review.

Same mechanism either way; only the merge policy differs.

## 4. Task queue: GitHub Issues (decided)

One issue per question/sub-investigation, labeled `open` / `claimed` /
`in-review` / `done`. Claiming = atomic API call (`gh issue edit
--add-assignee`), which sidesteps git-native race conditions and gives a
visible, zero-extra-infra audit trail. Local/offline GPU workers without
GitHub access need a separate reconciliation lane (pull queue state, claim
optimistically, back off on conflict) — not yet designed.

**Dataset-affinity scheduling.** "Pick next question" is not pure FIFO. A
scheduler prefers an unclaimed question whose dataset is already
materialized/preprocessed in the current environment's cache — but this is
a tiebreaker on priority, capped so one agent can't hog a dataset
indefinitely and starve the rest of the queue.

## 5. Continuity across providers and subscription limits

Two tiers, not one:

- **Backbone (portable, mandatory).** A checkpoint log committed to the
  investigation branch at atomic-step granularity: `PROGRESS.md` +
  `log.jsonl` with fields like `{timestamp, provider, model, step, event,
  files_touched, tokens, key_decisions}`. Any worker, any provider, any
  machine resumes from this. This is the only thing that actually survives
  `git clone` onto a different machine, which is why it's mandatory rather
  than optional.

- **Accelerant (optional, same-machine).** [`cli-continues`](https://github.com/yigitkonur/cli-continues)
  reads a provider's *native* session transcript (e.g. Claude Code's JSONL
  under `~/.claude/projects/`) and generates a markdown handoff prompt for a
  different tool on the same machine — useful when a step gets interrupted
  mid-way and checkpointing now would lose meaningful sunk work. It has no
  durable schema of its own to conform to, and it cannot help a different
  machine pick up a branch later, since it depends on local session files
  that don't travel with git. Use it opportunistically; never rely on it.

Default behavior on hitting a provider limit: finish the current atomic
step if possible, write the checkpoint, commit, exit — let the queue
reassign to any available worker. Reserve `cli-continues` hot-swapping for
steps expensive enough that losing them to a coarse checkpoint would hurt.

## 6. Pacing: continuous vs. slow-burn (decided: same machinery, different trigger)

Pace is a trigger-frequency property, not a different code path. The
claim → branch → work → checkpoint → push → PR pipeline is identical
either way:

- **Continuous ("fast lane"):** `trigger.mode: continuous`. Workers pick up
  the queue opportunistically whenever capacity exists.
- **Slow burn:** `trigger.mode: cron` with a `schedule`, `max_claims_per_cycle`
  (typically 1), and `budget_per_cycle`. A scheduled job fires on cadence,
  claims one investigation, runs it through the normal pipeline, stops. No
  daemon, no idle polling — just infrequent invocation of the same loop.
  Intended for low-priority projects that should inch forward over weeks
  or months without competing for subscription headroom.

Not yet designed: a shared usage ledger so a slow-burn trigger can check
current headroom before claiming, rather than firing blindly into a quota
the fast lane is already saturating. Needed before slow-burn projects
coexist with fast-lane ones on the same subscription.

## 7. Repo topology: core tool vs. project repos

The whole architecture is repo-centric (branch-per-investigation, GitHub
Issues as the queue, PR-gated merges), so it matters which repo is "the
tool" and which is "a research program." They're not the same repo.

- **Core tool repo** (this one, eventually renamed `mksparcs`): charter
  schema, scheduler/queue conventions, checkpoint log format, worker CLI
  contract, intake process. Published as an installable CLI
  (`pip install git+...@v0.1.0` once it exists).
- **Project repos** (one per research program, e.g. `mksparcs-mnespmfaces`):
  contain *only* project content — charter, `SYNTHESIS.md`, dataset config,
  investigation branches/issues, reports. No framework code lives here.
- A project repo declares which **pinned version/commit** of the core tool
  it's built against (a line in its README or charter —
  `framework_version: v0.1.0`). This is what keeps every worker's bootstrap
  sequence provider-agnostic: clone project repo → ensure the pinned
  framework version is installed → run the framework CLI against this
  repo's charter. No vendoring, no drift.

## Open / not yet decided

- Offline reconciliation lane for GitHub-Issues queue when a worker has no
  GitHub access (local GPU boxes).
- Shared usage/headroom ledger format and where it lives.
- Concrete worker CLI contract (what command a fresh agent runs on clone to
  read the charter, find/claim next work, and report back) — first attempt
  pending a concrete example topic.
- Browser-based intake wizard (v2, deferred until charter schema is
  exercised on a real topic).
