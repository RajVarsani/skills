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
import time
import urllib.error
import urllib.request

API = 'http://localhost:4899/api'
PROJ = os.environ.get('PROJ', 'DAR')
LIVE = {p.strip().upper() for p in os.environ.get('LIVE', '').split(',') if p.strip()}
STATE = pathlib.Path(os.environ.get('STATE', os.path.expanduser('~/.darbar-tick.state')))
PROBEISH = re.compile(r'probe|throwaway|delete me|scratch|\btest\b|\btmp\b', re.I)
OPEN_FB = ('pending', 'triaged', 'accepted', 'in_progress')
CLOSED = ('done', 'cancelled')

# DAR-250. The tunnel is the only part a stakeholder ever sees, and a dead one is invisible
# to a process check (ngrok/zrok can die while the local api and proxy both still look up).
# Short timeout: a dead tunnel must cost the sweep a few seconds, never hang it.
TUNNEL_TIMEOUT_S = 6
# 30s pulse from bot.ts, ~10x margin for a GC pause or a slow LLM turn blocking the event
# loop for a beat — still two orders of magnitude faster than the 21h51m that went
# undetected in the incident this fixes.
GABBAR_STALE_S = 300
GABBAR_HEARTBEAT = pathlib.Path(os.path.expanduser('~/fafo/darbar/data/gabbar-heartbeat.json'))


def base_url():
    if os.environ.get('BASE_URL'):
        return os.environ['BASE_URL']
    try:
        for line in pathlib.Path(os.path.expanduser('~/fafo/darbar/.env')).read_text().splitlines():
            if line.startswith('BASE_URL='):
                return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return None


def tunnel_get(base, path):
    # zrok shows an interstitial to anything that looks like a browser unless told not to;
    # without this header we'd be asserting the interstitial renders, not the board.
    req = urllib.request.Request(f'{base}{path}', headers={'skip_zrok_interstitial': 'true'})
    try:
        with urllib.request.urlopen(req, timeout=TUNNEL_TIMEOUT_S) as r:
            return r.status, r.read(2000)
    except urllib.error.HTTPError as e:
        return e.code, e.read(200)

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

# gabbar's SLACK SOCKET, not its process (DAR-250): the process looped ECONNREFUSED for
# 21h51m after the socket died, staying alive and pgrep-healthy the whole time while nobody
# messaging it got a reply. bot.ts touches this file only while its SocketModeClient
# believes it is connected, so a stuck reconnect loop stops the touches and the mtime goes
# stale. Only meaningful if the process is even up — "DOWN gabbar" above covers the rest.
hb_note = 'n/a (proc down)'
if gabbar:
    try:
        hb_age = time.time() - GABBAR_HEARTBEAT.stat().st_mtime
        hb_note = f'{int(hb_age)}s'
        if hb_age > GABBAR_STALE_S:
            out.append(f'STALE gabbar heartbeat {int(hb_age)}s (>{GABBAR_STALE_S}s) - process is up '
                       'but its slack socket has not reported connected recently; likely stuck reconnecting')
    except FileNotFoundError:
        hb_note = 'MISSING'
        out.append('MISSING gabbar heartbeat - process is up but has never reported a connected socket; '
                   'check apps/gabbar/src/bot.ts started cleanly')

# ---- 2. reads: four calls, whole board in one of them ----
# archived=all: the default view is active-only, and a swept project that finished and got
# archived would otherwise vanish from this list, making the sweep print NO PROJECT and exit
# 2 - a lie, since the project exists and is simply done. The sweep must see archived projects
# to correctly say nothing about them (see the archivedAt check below).
projects = get(f'{API}/projects?archived=all')
me = next((p for p in projects if p['prefix'] == PROJ), None)
if not me:
    print(f'NO PROJECT {PROJ} on this server')
    sys.exit(2)
now = datetime.datetime.now(datetime.timezone.utc)

# the tunnel: fetch a REAL board through the PUBLIC url, not a process check. This is the
# gap that let ngrok die silently while local api/proxy both stayed healthy.
burl = base_url()
if not burl:
    out.append('TUNNEL CONFIG MISSING - no BASE_URL in ~/fafo/darbar/.env, cannot verify the public url')
else:
    try:
        status, body = tunnel_get(burl, f'/p/{me["capId"]}')
        if status != 200 or b'<title>Darbar' not in body:
            out.append(f'TUNNEL BOARD BROKEN {burl}/p/{me["capId"]} - got {status}, not the board page a stakeholder expects')
    except Exception as e:
        out.append(f'DOWN tunnel {burl} ({e}) - the board is unreachable at the only url a stakeholder has')
    try:
        # /api/tasks is NOT on the public allowlist. 200 here is a security regression, not a finding
        # to note quietly - it means raw task data is exposed to anyone with the tunnel url.
        status, _ = tunnel_get(burl, '/api/tasks')
        if status == 200:
            out.append(f'SECURITY REGRESSION: {burl}/api/tasks returned 200 through the public tunnel - it must 403')
        elif status != 403:
            out.append(f'TUNNEL /api/tasks unexpected status {status} through {burl} (wanted 403)')
    except Exception as e:
        out.append(f'DOWN tunnel /api/tasks check {burl} ({e})')

# An archived project is a closed decision, not a queue: its open rows are what someone chose
# to leave open on purpose, not work waiting on anybody. Reporting them every tick forever
# would be exactly the noise this system exists to prevent - it trains people to stop reading
# the sweep. Stop here, after the machine checks above (api/gabbar/proxy/heartbeat/tunnel -
# those verify the box, not this project, so they still run) and before anything below that
# reads this project's board. Reset the streak file rather than leaving it untouched: if this
# project is later unarchived, the next real tick must not inherit a "clean streak" that
# spans ticks where nothing was actually checked.
if me.get('archivedAt'):
    reason = f", reason: {me['archiveReason']}" if me.get('archiveReason') else ''
    print(f'ARCHIVED {PROJ} at {me["archivedAt"]}{reason} - nothing to sweep')
    try:
        STATE.write_text(json.dumps({'clean': 0, 'fp': None, 'at': now.isoformat(), 'proj': PROJ}))
    except Exception:
        pass
    sys.exit(0)

board = get(f'{API}/p/{me["capId"]}')
ctx = get(f'{API}/projects/{PROJ}/context')
tasks, feedback = board['tasks'], board['feedback']
try:
    held = get(f'{API}/parked?project={PROJ}').get('held', 0)
except Exception:
    held = 0

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
# A project is litter only if it LOOKS like litter. Absence from LIVE used to be enough on its
# own, which meant every genuinely new project read as garbage the moment another session made
# one: MRFIII (5 stakeholders, 4 repos, a 9KB charter) was reported as throwaway within the hour
# of its creation, and REV — 6 repos, a real charter, no stakeholders — every tick before that.
# LIVE still SUPPRESSES, but it may no longer ACCUSE. A probe has none of the substance below.
def is_stray(p):
    # Archived beats every other test, including LIVE. A project closed on purpose is the
    # MOST finished thing on the server, and by the time it closes it may have shed every
    # repo and stakeholder it ever had - to the substance check below that looks identical
    # to a probe. This already cried wolf once on real new projects with thin substance
    # (MRFIII, REV); do not let it cry wolf a second time on real finished ones.
    if p.get('archivedAt'):
        return False
    if p['prefix'].upper() in LIVE:
        return False
    substance = bool(p.get('repos')) or bool(p.get('stakeholders')) or len(str(p.get('charter') or '')) > 400
    return bool(PROBEISH.search(p['name'])) or not substance
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
          f'api {apipid} gabbar {gabbar[0]} hb {hb_note} proxy {proxy[0]} tunnel ok | clean streak {streak}')
    sys.exit(0)
print(f'{PROJ} | {len(inflight)} in flight | {len(out)} finding(s)'
      + (' | SAME AS LAST TICK, nothing you did cleared it' if repeat else ''))
for line in out:
    print(' -', line)
sys.exit(1)
