#!/usr/bin/env python3
"""Append-only execution history.

`attempts: 3` tells you a ticket took three tries and nothing about the first two.
That is exactly what the retrospective needs, so execution is recorded as an event
log rather than as final values.

One JSONL file per phase: events/phase-N.jsonl. Append only - never rewritten,
never compacted. Counts are DERIVED from it, never stored alongside it.

  srashta event T-08 attempt_started --agent codex
  srashta event T-08 tests_failed --data '{"tests":["single-use link"]}'
  srashta event T-08 merged --data '{"diff_lines": 240}'
"""
import json, os, sys, time, re, uuid
from collections import defaultdict

KINDS = {
    'attempt_started':       'a worker began an attempt',
    'tests_failed':          'acceptance tests failed on a run',
    'contract_change_filed': 'the worker stopped and filed a contract-change ticket',
    'out_of_scope_touch':    'a file outside owned_files was modified',
    'review_round':          'a human requested changes',
    'blocked':               'work could not proceed',
    'merged':                'the pull request merged',
    'pack_insufficient':     'the ticket could not proceed at all; rare, an escalation',
    'brief_feedback':        'closing answer: was the brief sufficient (routine, every ticket)',
}

def path(cfg, phase):
    p = os.path.join(cfg.get('events_dir', 'events'), f'phase-{int(phase)}.jsonl')
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p

def append(cfg, phase, ticket, kind, data=None, agent=None, event_id=None):
    if kind not in KINDS:
        raise SystemExit(f"unknown event kind '{kind}'. one of: {', '.join(sorted(KINDS))}")
    if not isinstance(ticket, str) or not re.fullmatch(r'[CTI]-[0-9]{2,3}[a-z]?', ticket):
        raise ValueError('valid ticket ID required')
    data = dict(data or {})
    if cfg.get('artifact_version'):
        from .common import read_json, out
        records = read_json(out(cfg, f'tickets/phase-{int(phase)}.json'))
        if ticket not in {t['id'] for t in records}: raise ValueError('unknown ticket for this phase')
        if kind == 'brief_feedback' and not (type(data.get('sufficient')) is bool or data.get('sufficient') == 'partial'):
            raise ValueError('brief_feedback needs sufficient: true, false, or "partial"')
        if kind == 'merged':
            record = next(t for t in records if t['id'] == ticket)
            if record['kind'] in ('contract', 'integration') and not str(data.get('reviewed_by', '')).strip():
                raise ValueError('contract/integration merges require reviewed_by')
            from .execution import merge_evidence
            data['evidence_sha256'] = merge_evidence(cfg, phase, ticket, data)
    for field in ('tests', 'files'):
        if field in data and (not isinstance(data[field], list) or not all(isinstance(x, str) for x in data[field])):
            raise ValueError(f'{field} must be a string array')
    rec = {'id': event_id or str(uuid.uuid4()), 'phase': int(phase),
           'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'ticket': ticket, 'kind': kind, 'data': data}
    if agent: rec['agent'] = agent
    # One locked read/check/append operation across processes. POSIX supported in v0.1.
    import fcntl
    with open(path(cfg, phase), 'a+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        previous = [json.loads(line) for line in stream if line.strip()]
        for old in previous:
            if old.get('id') == rec['id']:
                if any(old.get(k) != rec.get(k) for k in ('phase', 'ticket', 'kind', 'data', 'agent')):
                    raise ValueError('event id reused with different content')
                return old
        if cfg.get('artifact_version') and kind == 'merged':
            feedback = [e for e in previous if e['ticket'] == ticket and e['kind'] == 'brief_feedback']
            if not feedback: raise ValueError('record brief_feedback before merge')
        stream.write(json.dumps(rec, sort_keys=True) + '\n')
        stream.flush(); os.fsync(stream.fileno())
    return rec

def read(cfg, phase):
    p = path(cfg, phase)
    if not os.path.exists(p): return []
    import fcntl
    with open(p) as stream:
        fcntl.flock(stream, fcntl.LOCK_SH)
        return [json.loads(l) for l in stream if l.strip()]

def derive(events):
    """Counts are derived from history, never stored. This is the whole point."""
    d = defaultdict(lambda: {'attempts': 0, 'first_run_test_failures': 0,
                             'contract_change_filed': False, 'out_of_scope_files_touched': [],
                             'review_rounds': 0, 'merged': False, 'agent': None,
                             'diff_lines': None, 'failed_tests': [],
                             'pack_gaps': [], 'brief_sufficient': None,
                             'brief_notes': []})
    for e in events:
        t = d[e['ticket']]; k = e['kind']; data = e.get('data') or {}
        if e.get('agent'): t['agent'] = e['agent']
        if k == 'attempt_started': t['attempts'] += 1
        elif k == 'tests_failed':
            names = data.get('tests', [])
            if t['attempts'] <= 1: t['first_run_test_failures'] += len(names) or 1
            t['failed_tests'] += names
        elif k == 'contract_change_filed': t['contract_change_filed'] = True
        elif k == 'out_of_scope_touch':
            t['out_of_scope_files_touched'] += data.get('files', [])
        elif k == 'review_round': t['review_rounds'] += 1
        elif k == 'pack_insufficient': t['pack_gaps'].append(data.get('needed', ''))
        elif k == 'brief_feedback':
            t['brief_sufficient'] = data.get('sufficient')
            if data.get('note'): t['brief_notes'].append(data['note'])
        elif k == 'merged':
            t['merged'] = True; t['diff_lines'] = data.get('diff_lines')
    return dict(d)

def main(cfg, args):
    if args.list_kinds:
        for k, v in sorted(KINDS.items()): print(f"  {k:24s} {v}")
        return 0
    if args.summary:
        ev = read(cfg, args.phase)
        if not ev:
            print("  no events recorded yet"); return 0
        d = derive(ev)
        merged = sum(1 for v in d.values() if v['merged'])
        retries = [k for k, v in d.items() if v['attempts'] > 1]
        oos = [k for k, v in d.items() if v['out_of_scope_files_touched']]
        cc = [k for k, v in d.items() if v['contract_change_filed']]
        gaps = [(k, g) for k, v in d.items() for g in v['pack_gaps']]
        print(f"  {len(ev)} events across {len(d)} tickets")
        print(f"  merged                    {merged}")
        print(f"  needed more than one try  {len(retries)}" + (f" -> {retries}" if retries else ""))
        print(f"  touched files they did not own  {len(oos)}" + (f" -> {oos}" if oos else ""))
        print(f"  filed a contract change   {len(cc)}" + (f" -> {cc}" if cc else ""))
        fb = {k: v for k, v in d.items() if v['brief_sufficient'] is not None}
        if fb:
            bad = [k for k, v in fb.items() if v['brief_sufficient'] is False]
            part = [k for k, v in fb.items() if v['brief_sufficient'] == 'partial']
            print(f"  briefs answered for        {len(fb)}/{len(d)} ticket(s)")
            print(f"      sufficient             {len(fb) - len(bad) - len(part)}")
            if part: print(f"      had to infer something {len(part)} -> {part}")
            if bad:  print(f"      insufficient           {len(bad)} -> {bad}")
            notes = [(k, n) for k, v in fb.items() for n in v['brief_notes']]
            for k, n in notes: print(f"      {k}: {n}")
        missing_fb = [k for k, v in d.items() if v['merged'] and v['brief_sufficient'] is None]
        if missing_fb:
            print(f"  merged without answering   {len(missing_fb)} -> {missing_fb}")
            print(f"      the orchestrator is not recording it; fix that before the next phase")
        if gaps:
            print(f"  could not proceed at all   {len(gaps)}")
            seen = {}
            for tid, g in gaps: seen.setdefault(g, []).append(tid)
            for g, tids in sorted(seen.items()):
                mark = "   <- belongs in the pack template" if len(tids) > 1 else ""
                print(f"      {', '.join(tids)}: {g}{mark}")
        return 0
    rec = append(cfg, args.phase, args.ticket, args.kind,
                 json.loads(args.data) if args.data else None, args.agent, getattr(args, 'id', None))
    print(f"  recorded {rec['kind']} for {rec['ticket']}")
    return 0
