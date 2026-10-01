---
name: cosmos
description: Spin up, use and tear down isolated Saturn app instances (galaxy stack or saturn-fe/area51 against a deployed backend) on this Mac with the cosmos CLI. Use when you need a running Saturn app to test, QA, screenshot or develop against, or when asked to start, check, log or remove a cosmos instance. Not for Docker, Colima or the cosmos dashboard process.
---

# cosmos

`~/all-things-saturn/cosmos/bin/cosmos` runs isolated Saturn instances. Every command takes
`--json`; always pass it and parse the output. `cosmos --help` is the reference for
commands and flags. This skill only says when and how to use them safely.

Alias for the commands below: `C=~/all-things-saturn/cosmos/bin/cosmos`.

## When to use

You need a running Saturn app: browser QA, a screenshot, an API to call, a change to try
against a real stack. If a suitable instance of yours already exists, reuse it.

## Hard rules

1. Only touch instances you created. Read `owner` in `$C ls --json` (`cwd`, `sessionId`,
   `via`). Yours means the owner matches your cwd and session. Anything else, or
   `via: "dashboard"`, belongs to someone else: never stop, start, down, rm, seed or
   reconfigure it. Reading `status`, `ports` and `logs` is fine.
2. Never touch Docker, Colima, or the dashboard process (`cosmos dashboard`). Do not run
   `docker` commands against cosmos containers either; use `cosmos logs`.
3. Never use `--all` on `down` or `rm`. Name your instances.
4. No writes to stage, devx, devz, sjp-stage or production data. Remote profiles hit
   deployed backends. `production` and `sjp` are `live: true` in `catalog`: read-only
   browsing at most, no form submits, no mutations, and prefer not to use them at all.
5. Local profiles are heavy. Check memory before `up` (below).

## Pick the lightest profile

1. `$C profiles --json`: each profile has `estMiB`, `services`, `backends`, `canRun` and a
   `reason` when it cannot run now.
2. `$C catalog --json`: every backend x profile, plus `vm.availableMiB` (free VM memory)
   and `vm.floorMiB` (what must stay free).

Choose the smallest set that covers the task:
- Consumer app only: `consumer-remote` (about 0.7 GB) on `stage` or `devx`.
- Admin only: `admin-remote`. Both: `both-remote`.
- Needs a real backend you can write to: `consumer-local` (about 8 GB), then `everything`
  (about 10 GB, includes area51, abe, coplanner-word) only if you need those.

Prefer remote on `stage`/`devx`/`devz` for UI work. Go local only when the task writes
data or needs backend code running. Local needs `canRun: true` and `vm.availableMiB` well
above the profile's `estMiB` plus `floorMiB`. If it is short, pick a lighter profile or
report it; do not stop other people's instances to make room.

## Up

Name the instance after the project you are working on, free text is fine:

```
$C up --backend stage --profile consumer-remote --name "Letter Platform" --json
```

- The id is the slug (`letter-platform`). Use that id in every later command.
- Reruns reuse by name: `up` with the same `--name` brings up the existing instance
  instead of making a new one. Backend or profile must match, else it errors and asks for
  `rm` first. Use one stable name per project.
- `up` blocks until ready and prints JSON with `name`, `url`, `urls` (per service),
  `ports`, `cors`, `warnings`, `memory`. Open `url` for the app, `urls.<svc>` for others.
- Local backend needs `--backend local` (the default for local profiles).
- Cold local starts take minutes (the dev stack took about 3 minutes). Allow it; use
  `--timeout S` if you need a ceiling. `--src svc=<path>` mounts your checkout of a service.

Check any `warnings` and `cors` entries with `allowed: false` before trusting the app.

## Confirm ready

```
$C status letter-platform --json
```

Each service has `running`, `health` and, for HTTP services, `http.ok`. Ready means every
long-running service is `running` and healthy. One-shot jobs (`minio-init`,
`localstack-init`, `saturn-bootstrap`) show `exited`; that is normal. `workers` and `cors`
are in the same output. If something is not ready, wait and poll again; do not rerun `up`
on a half-started instance unless status says a service failed.

## Login

The seeded test user is in `~/all-things-saturn/cosmos/cosmos.config.yaml` under `login:`
(email and password, local test credentials). `$C ls --json` also returns `login` at the
top level. Read the password from the file when you need it; do not paste it into PRs,
commits or Slack.

## Logs and debugging

```
$C logs letter-platform saturn-backend --tail 200 --json
```

The service defaults to `saturn-fe`. Skip `-f` (it never returns). `cosmos seed <name>` re-runs the
local bootstrap on your running local instance.

## Done

When the work is finished, remove what you created:

```
$C rm letter-platform --json
```

`rm` drops volumes and frees the slot. `down` only stops it (keeps the slot and data) and
is right if you will come back soon in the same task. Leave nothing running that you
started. Never rm an instance you did not create, even if it looks idle.

## Report

Say the instance id, `url`, profile, backend and whether it is still running, so the next
agent or Raj can find it.
