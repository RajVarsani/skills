---
name: darbar-project-init
description: Bootstrap a Darbar-tracked project — day-zero OR retro-init of work already underway ("put this session under darbar", "register this project"). Interviews for context (mandatory, includes subagent structure + backlog scope + update cadence), registers the project + charter in Darbar, cuts branches, seeds the task tree so the board carries ALL known pending work, binds the Slack channel for Gabbar intake, then turns the current session into a strict orchestrate-only manager. Use when starting a new agent-orchestrated project ("init project", "new darbar project", "spin up a project") or when bringing an in-flight session/effort under Darbar tracking.
---

# Darbar Project Init

You are bootstrapping a project into Darbar (the self-hosted tracker at
`~/fafo/darbar`, API on `http://localhost:4899`) and becoming its orchestrator.

## Preconditions

1. Darbar server must be up: `curl -s localhost:4899/` returns text. If not:
   `cd ~/fafo/darbar && bun run server > data/server.log 2>&1 &`
2. Gabbar scribe should be up for Slack intake: check with
   `pgrep -f src/bot.ts`; start with `cd ~/fafo/darbar && bun run gabbar > data/gabbar.log 2>&1 &`
3. Register the Darbar MCP tools if not already in this session (see darbar README
   "MCP registration"). All board writes go through them or the REST API.

## Step 1 — Intake (MANDATORY — never skip)

The interview is not optional. Do NOT infer answers from context you already have,
and do NOT start building before it — a skipped interview is the documented failure
mode of this skill. Ask the user in ONE AskUserQuestion round (free-text follow-ups
only if genuinely blocking):

- **Project name** and **short-id prefix** (2 to 6 caps, e.g. MRF, VAR)
- **Repos + base branches** (e.g. saturn-fe from main, mars from stage) and the
  **feature branch name** to cut
- **Sources**: Slack threads, Figma channels, docs, prior session ids
- **Stakeholders**: name, Slack handle, role (design / backend / review). These become
  the identity map Gabbar uses to attribute feedback and the humans tasks can be
  assigned to
- **Project-specific safety rules** (live keys, fixtures not to touch, deploy holds)
- **Slack channel** to bind for feedback intake (optional; DMs always work)
- **Subagent structure**: which review lanes (e.g. code-review, qa, design-qa,
  regression) and who manages each lane — or explicitly none
- **Backlog scope**: which work streams to seed on the board now, including known
  pending items and human-owned work
- **Update cadence**: board-only | chat summaries | Slack via Gabbar (draft-first,
  never send without approval)

## Step 2 — Register the project

POST `http://localhost:4899/api/projects` with name, prefix, repos, stakeholders
(`[{name, slackUserId, role}]` — resolve handles to user ids via Slack API if needed),
`slackChannel`, and a **charter**.

The charter is the standing context pack every agent fetches via the
`get_project_context` MCP tool. Write into it:
- goal + streams of work
- the standing protocols (defaults, adapt as needed): orchestrate-only (builders do the
  work, orchestrator writes no code), builders verify build-only (tsc / go build),
  commit discipline on shared checkouts (stage by explicit path, no `git add -A`,
  `--no-verify`, confirm with `git show --stat`), concurrency cap 3 to 4 agents,
  design QA reads live design-tool values not memory, QA asserts outcomes against DB
  truth not UI interactions
- the project-specific safety rules and update cadence from intake
- links to all sources

Save the returned `boardUrl` and `capId` — the capability URL is what stakeholders get.

Then configure the **review pipeline** from the intake's subagent-structure answer
(`set_pipeline` MCP tool, or PATCH `/api/projects/:ref` with
`{pipeline: {autoAdvance, reviews: [{lane, label, manager}]}}`): one lane per review
kind, each with a `manager` agent name. The server then auto-spawns those lanes as
`type=review` subtasks whenever a dev task moves to `in_review`, gates `done` on the
lanes closing, and (with `autoAdvance`, the default) closes the parent when the last
lane does. Skip the pipeline only if intake explicitly chose "none".

## Retro-init — project already underway

When work exists but was never registered, or the orchestrator has been working
inline ("put this session under darbar"):

1. Run the SAME Step 1 intake — no shortcuts; the interview is mandatory here too.
2. Register the project (Step 2), or PATCH `/api/projects/:ref` if it half-exists.
3. Seed EVERY known pending item as a task — from the session so far, from memory
   files, from the user's answers — including human tasks assigned to stakeholders
   (e.g. "Tanisha: fix file_type hardcode"). Record origins.
4. Record already-done work as done cards so the board tells the true story of the
   project, not just the future.
5. Invariant from here on: **the board reflects ALL known pending work at all
   times.** An empty todo column while work is pending is a bug — fix the board,
   then continue.

Then proceed with Steps 3–6 as applicable (branches may already exist; skip cutting,
verify instead).

## Step 3 — Cut branches

For each repo from intake: fetch, branch from the stated base, push only if the user's
standing rules allow pushes. Confirm each with `git -C <repo> branch --show-current`.

## Step 4 — Recon and seed the task tree

Spawn recon subagents in parallel (Agent tool), one per source: Slack thread digest,
Figma inventory, codebase state, prior session transcripts. Each returns a structured
list of work items with evidence.

Promote their output into Darbar: `create_task` per item (streams as parent tasks,
concrete items as subtasks via `parentTaskRef`), origins recorded, known blockers set.
Cover every stream from the intake's backlog-scope answer; anything pending that you
know about but don't file is a bug. Log a `project bootstrapped` event.

## Step 5 — Announce in Slack

If a channel was bound: draft the announcement as Gabbar (board link + "file feedback
by DMing me or mentioning me with a task id like `PREFIX-12`"). **Show the draft and
wait for explicit approval before sending** (standing Slack rule).

## Step 6 — Become the orchestrator (strict orchestrate-only)

Adopt the manager loop for the rest of the session (and say so). Default is strict
orchestrate-only — the orchestrator writes NO code, ever; relax only if the user
explicitly says so:

- **Dispatch**: one builder subagent per task via the Agent tool, each scoped to
  exactly one task. Builders PATCH their own rows via REST
  (`PATCH /api/tasks/:shortId` — `in_progress` on start, `in_review` with notes when
  done, `blocked` with blocker if stuck).
- **Reviews**: the server auto-spawns review-lane subtasks on `in_review`. Choose
  each task's lanes by judgment at `create_task` time via `lanes` (code-review for
  code, qa for behavior, design-qa only for UI; `[]` = none; omit = all). Spawn
  lane-manager subagents to drain their queues
  (`GET /api/tasks?assignee=<manager>&open=true`), review the work, file findings via
  `POST /api/feedback` (authorType `agent`), and close their lanes. The done-gate +
  `autoAdvance` handle parents.
- **Feedback**: drain `next_pending_feedback` on a self-paced loop; triage every item:
  rework an existing task, `create_task` a new one, reject with a reason, or ask for
  clarification (all via `resolve_feedback`, which auto-replies in the author's
  thread). Dedupe at triage: same defect from two authors = one task, both notified.
- **Commits**: orchestrator commits per task only after its review lanes close,
  following the charter's commit discipline.
- **Board honesty**: the board is the single source of truth and must reflect ALL
  known pending work at all times — file new work the moment you learn of it,
  including human tasks. A fresh session must be able to resume from the API alone.
- **Updates**: follow the cadence chosen at intake; Slack updates always draft-first
  via Gabbar.

Finish the bootstrap by reporting: board URL, task count seeded, branches cut,
stakeholders onboarded, and anything from recon that needs the user's call.
