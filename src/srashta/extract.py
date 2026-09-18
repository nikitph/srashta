#!/usr/bin/env python3
"""Step 3a - parse a spec into requirements.json.

Handles the layout traps that silently drop requirements:
  - domain segments of any length (a 3-letter assumption drops whole domains)
  - a bare identifier on its own line is a CROSS-REFERENCE, not a new row
  - priority may follow on its own line or sit inline at the end of the text
Asserts every identifier mentioned anywhere in the document was parsed.
"""
import re, sys
from collections import defaultdict
from .common import load_project, domain_of, out, write_json, die

def main(cfg):
    sc = cfg['spec']
    text = open(sc['path'], encoding='utf-8').read()
    lines = text.split('\n')
    id_re   = re.compile(rf"^({sc['id_pattern']})\s*(.*)$")
    pri_re  = re.compile(rf"^({sc['priority_pattern']})\s*$")
    pri_in  = re.compile(rf"\s({sc['priority_pattern']})\b")
    foot    = re.compile(sc['footer_pattern']) if sc.get('footer_pattern') else None
    head    = re.compile(sc['header_pattern']) if sc.get('header_pattern') else None
    sec_re  = re.compile(r'^(\d+(?:\.\d+)*)\s+(.{3,80}?)\s{2,}') if False else None

    reqs, order, cur, section = {}, [], None, None
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line: continue
        if foot and foot.search(line): continue
        if head and head.search(line):
            m = re.match(r'^(\d+(?:\.\d+)*)\s+(.+?)\s+' + sc['header_pattern'], line)
            if m: section = f"{m.group(1)} {m.group(2)}"
            continue
        m = id_re.match(line)
        if m and i >= sc['body_start_line']:
            rid, rest = m.group(1), m.group(2).strip()
            if len(rest) <= 1:                      # bare cross-reference
                if cur: reqs[cur]['text'] += ' ' + line
                continue
            cur = rid
            if rid not in reqs:
                reqs[rid] = dict(id=rid, text=rest, priority=None,
                                 section=section, line=i + 1)
                order.append(rid)
            else:
                cur = None                          # duplicate mention elsewhere
            continue
        if pri_re.match(line) and cur:
            if reqs[cur]['priority'] is None: reqs[cur]['priority'] = line
            cur = None
            continue
        if cur: reqs[cur]['text'] += ' ' + line

    res = []
    for rid in order:
        r = reqs[rid]
        r['text'] = re.sub(r'\s+', ' ', r['text']).strip()
        if r['priority'] is None:                   # priority inline at end of text
            m = pri_in.search(r['text'])
            if m:
                r['priority'] = m.group(1); r['text'] = r['text'][:m.start()].strip()
        r['domain'] = domain_of(rid)
        res.append(r)

    parsed_ids = {r['id'] for r in res}

    # Completeness, part one: everything the CONFIGURED pattern matches was parsed.
    mentioned = set(re.findall(rf"\b(?:{sc['id_pattern']})\b", text))
    missing = sorted(mentioned - parsed_ids)
    if missing:
        die(f"{len(missing)} identifiers are mentioned but were not parsed as rows: "
            f"{missing[:20]}. The parser is wrong - fix it before continuing.")

    # Completeness, part two: a pattern cannot validate itself. Scan with a GENERIC
    # identifier shape and flag any family the configured pattern does not cover.
    # This is the bug that silently drops a whole domain when the pattern assumes,
    # say, a three-letter segment and the spec has a five-letter one.
    GENERIC = r'\b[A-Z]{2,6}(?:-[A-Z]{2,6})?-\d{3}\b'
    families = defaultdict(set)
    for tok in re.findall(GENERIC, text):
        families[tok.rsplit('-', 1)[0]].add(tok)
    uncovered = {fam: toks for fam, toks in families.items()
                 if len(toks) >= 3 and not any(t in parsed_ids for t in toks)}
    if uncovered:
        die("identifier families found in the spec that your id_pattern does not match: "
            + ', '.join(f"{fam} ({len(t)})" for fam, t in sorted(uncovered.items()))
            + f". Current pattern: {sc['id_pattern']}. Widen it in project.yaml - a "
              "pattern cannot validate itself, and a narrow one drops a whole domain.")

    p = out(cfg, 'requirements.json'); write_json(p, res)
    from collections import Counter
    print(f"parsed {len(res)} requirements -> {p}")
    print(f"  priority: {dict(Counter(r['priority'] for r in res))}")
    print(f"  domains : {len(set(r['domain'] for r in res))}")
    print(f"  completeness: every one of {len(mentioned)} mentioned identifiers accounted for")
    return res

