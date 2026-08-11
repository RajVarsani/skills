#!/usr/bin/env python3
"""One Darbar tick sweep. Prints ONLY findings.

The whole point is that the board scan happens in the shell and not in a context
window: a clean tick is one line, so an idle loop costs a tool call and nothing else.
Reads only. Never writes to the board.

  PROJ=DAR python3 sweep.py

Exit codes:  0 clean   1 findings   2 cannot read (api down / no such project)

Env:
  PROJ   project prefix to sweep (default DAR)
  LIVE   comma-separated prefixes that are real projects. Anything else on the
         server is reported as throwaway litter. Unset = fall back to matching
         probe-ish names only, which is the safe default on a shared machine.
  STATE  streak file (default ~/.darbar-tick.state). Makes "nothing found again"
         and "same finding as last tick" mechanical instead of remembered.
"""
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

API = 'http://localhost:4899/api'
PROJ = os.environ.get('PROJ', 'DAR')
LIVE = {p.strip().upper() for p in os.environ.get('LIVE', '').split(',') if p.strip()}
STATE = pathlib.Path(os.environ.get('STATE', os.path.expanduser('~/.darbar-tick.state')))
PROBEISH = re.compile(r'probe|throwaway|delete me|scratch|\btest\b|\btmp\b', re.I)
OPEN_FB = ('pending', 'triaged', 'accepted', 'in_progress')
CLOSED = ('done', 'cancelled')

out = []


def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.split()


# ---- 1. the three processes. api first: if it is down nothing below is readable ----
try:
    with urllib.request.urlopen('http://localhost:4899/healthz', timeout=5) as r:
        apipid = r.headers.get('x-darbar-pid')
except Exception as e:
    print(f'DOWN api 4899 ({e}) - nothing else is readable this tick, stop')
    sys.exit(2)
gabbar = sh('pgrep', '-f', 'src/bot.ts')
proxy = sh('lsof', '-nP', '-iTCP:4800', '-sTCP:LISTEN', '-t')
if not gabbar:
    out.append('DOWN gabbar (no src/bot.ts) - slack intake is reaching nobody and files nothing')
if not proxy:
    out.append('DOWN proxy 4800 - any published shared surface is a dead link')

# ---- 2. reads: four calls, whole board in one of them ----
projects = get(f'{API}/projects')
me = next((p for p in projects if p['prefix'] == PROJ), None)
if not me:
    print(f'NO PROJECT {PROJ} on this server')
    sys.exit(2)
board = get(f'{API}/p/{me["capId"]}')
ctx = get(f'{API}/projects/{PROJ}/context')
tasks, feedback = board['tasks'], board['feedback']
try:
    held = get(f'{API}/parked?project={PROJ}').get('held', 0)
except Exception:
    held = 0

now = datetime.datetime.now(datetime.timezone.utc)
age = lambda s: (now - datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))).total_seconds() / 60
rev = [t for t in tasks if t['type'] == 'review']
kids = lambda p: [r for r in rev if r.get('parentTaskId') == p['_id']]
dev = [t for t in tasks if t['type'] != 'review']

# ---- 3. work waiting on somebody ----
pend = [f for f in feedback if f['status'] in ('pending', 'needs_clarification')]
todo = [t for t in dev if t['status'] == 'todo' and not t.get('dispatchedAt')]
inflight = [t for t in dev if t['status'] == 'in_progress']
openlane = [r for r in rev if r['status'] not in CLOSED]

if pend:
    out.append(f'FEEDBACK pending {len(pend)}: ' + ', '.join(f['shortId'] for f in pend[:8]))
if held:
    out.append(f'PARKED held {held} - gabbar refused these at the stakeholder gate; no feedback query returns them')
if todo:
    out.append(f'TODO undispatched {len(todo)}: ' + ', '.join(t['shortId'] for t in todo[:8]))
if openlane:
    out.append(f'LANES open {len(openlane)}: '
               + ', '.join(f'{r["shortId"]}[{r["lane"]}->{r["assignee"]}]' for r in openlane[:8]))

# ---- 4. rows that are stuck and say nothing about it ----
for t in dev:
    d = t.get('dispatchedAt')
    if d and t['status'] in ('todo', 'backlog') and age(d) > 15:
        out.append(f'STALE DISPATCH {t["shortId"]} {int(age(d))}m - handed over and never reported in')
    if t['status'] == 'in_review':
        if not kids(t):
            out.append(f'NO LANES EVER {t["shortId"]} - lanes resolved to nothing, or none configured')
        elif not [r for r in kids(t) if r['status'] not in CLOSED]:
            blockers = [f['shortId'] for f in feedback
                        if f.get('taskShortId') == t['shortId'] and f['status'] in OPEN_FB]
            why = ', '.join(blockers) if blockers else 'nothing open - check autoAdvance'
            out.append(f'HELD IN REVIEW {t["shortId"]} lanes closed, held by: {why}')
    if t['status'] == 'blocked' and not t.get('blocker'):
        out.append(f'BLOCKED NO REASON {t["shortId"]}')
for f in feedback:
    if f['status'] in ('triaged', 'accepted', 'in_progress') and not f.get('resolvedTaskShortId'):
        out.append(f'FEEDBACK PARKED NO TASK {f["shortId"]} ({f["status"]}, nobody on it)')

# ---- 5. a second review round nobody meant to order ----
# Only while it is still actionable. A duplicate round on a parent that has already closed,
# with every child closed too, is history: nothing can clear it, and a finding that can never
# be cleared would keep the board from ever reading clean and would trip SAME AS LAST TICK
# forever. Those belong in a one-off audit, not in a recurring sweep.
for t in dev:
    seen = {}
    for r in kids(t):
        seen[r['lane']] = seen.get(r['lane'], 0) + 1
    dup = [f'{k} x{v}' for k, v in sorted(seen.items()) if v > 1]
    live = t['status'] not in CLOSED or any(r['status'] not in CLOSED for r in kids(t))
    if dup and live:
        out.append(f'DUPLICATE ROUND {t["shortId"]} {", ".join(dup)} '
                   '- the parent was pushed out of in_review and back in. Cancel the extra '
                   'children with a reason, do not staff them')

# ---- 6. probe litter ----
vouched = {s['name'].strip().lower() for s in ctx.get('stakeholders', [])}
vouched |= {a['name'].strip().lower() for a in ctx.get('agents', [])}
vouched |= {'gabbar', 'orchestrator'}
# Open rows only, for the same reason as the duplicate-round check: the harm is probe rows
# burying real reports in the triage queue, and a resolved one is not in any queue.
junk = [f for f in feedback
        if f['status'] in OPEN_FB + ('needs_clarification',)
        and (f.get('author') or 'unknown').strip().lower() not in vouched]
if junk:
    names = sorted({(f.get('author') or 'unknown') for f in junk})[:6]
    out.append(f'UNVOUCHED FEEDBACK AUTHORS {len(junk)} open rows by {", ".join(names)} '
               f'- first {junk[0]["shortId"]}; the pending queue is the orchestrator inbox, so probe rows bury real ones')
is_stray = (lambda p: p['prefix'].upper() not in LIVE) if LIVE else (lambda p: bool(PROBEISH.search(p['name'])))
strays = [p for p in projects if p['prefix'] != PROJ and is_stray(p)]
if strays:
    out.append('THROWAWAY PROJECTS LEFT ON THE SERVER: '
               + ', '.join(f'{p["prefix"]} ({p["counts"]["tasks"]} tasks) "{p["name"]}"' for p in strays)
               + ' - there is no DELETE route; clean from mongo by projectId')

# ---- 7. streak, so the stop conditions are read rather than remembered ----
fingerprint = hashlib.sha1('\n'.join(out).encode()).hexdigest()[:12]
try:
    prev = json.loads(STATE.read_text())
except Exception:
    prev = {}
streak = (prev.get('clean', 0) + 1) if not out else 0
repeat = bool(out) and prev.get('fp') == fingerprint
try:
    STATE.write_text(json.dumps({'clean': streak, 'fp': fingerprint,
                                 'at': now.isoformat(), 'proj': PROJ}))
except Exception:
    pass

if not out:
    print(f'CLEAN {PROJ} | {len(dev)} rows, {len(inflight)} in flight | '
          f'api {apipid} gabbar {gabbar[0]} proxy {proxy[0]} | clean streak {streak}')
    sys.exit(0)
print(f'{PROJ} | {len(inflight)} in flight | {len(out)} finding(s)'
      + (' | SAME AS LAST TICK, nothing you did cleared it' if repeat else ''))
for line in out:
    print(' -', line)
sys.exit(1)
