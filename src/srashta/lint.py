#!/usr/bin/env python3
"""Step 1 gate - requirements smells plus structural completeness.

Smells are the catalogue from Femmer et al., "Rapid quality assurance with
Requirements Smells" (JSS 2016). Structural checks are the ones that, when they
fail, silently orphan requirements downstream.

Judgment is not automatable: this finds a spec that is inconsistent or untestable,
never one that is WRONG. Keep the prose readable for the humans who can spot that.
"""
import re, sys
from collections import defaultdict
from .common import load_project, out, read_json

SMELLS = [
 ('subjective',   r'\b(user[- ]friendly|easy|easily|simple|appropriate|adequate|sufficient|'
                  r'robust|seamless|intuitive|efficient|flexible|modern|clean)\b'),
 ('ambiguous',    r'\b(significant|minimal|quickly|fast|slow|soon|reasonable|roughly|'
                  r'approximately|almost always|generally|typically|usually|often)\b'),
 ('loophole',     r'\b(if possible|as appropriate|where practical|to the extent feasible|'
                  r'if necessary|as needed|where applicable|if required)\b'),
 ('open_ended',   r'(\betc\.|\band so on\b|\bincluding but not limited to\b|\band\/or\b|\.\.\.)'),
 # "at least" / "at most" are legitimate bounds, not superlatives
 ('superlative',  r'(?<!at )\b(best|worst|most|least|maximum possible|optimal|state of the art)\b'),
 ('comparative',  r'\b(better|faster|slower|improved|enhanced|stronger|richer|more secure)\b'),
 ('vague_pronoun',r'^\s*(It|This|That|These|Those)\b'),
 # a bare number with no unit; identifier fragments (FR-CUR-041, NFR-082) are not that
 ('unit_free',    r'(?<![\w.\-])\d+(?!\s*(%|ms|s\b|seconds|minutes|hours|days|months|years|'
                  r'MB|GB|KB|px|rem|characters|bytes|/|\.|\d))'),
 ('non_singular', r'\bmust\b.{5,180}?\band\b.{5,180}?\bmust\b'),
]
EARS = re.compile(r'^\s*(WHEN|WHILE|IF|WHERE|THE SYSTEM SHALL|THE SYSTEM SHALL NOT)\b')

def lint(reqs, cfg):
    findings = defaultdict(list)
    for r in reqs:
        t = r['text']
        # blank out identifier references first - they are citations, not prose
        scrub = re.sub(r'\b[A-Z]{2,4}-[A-Z]{2,6}-\d{3}\b|\b[A-Z]{3}-\d{3}\b', 'REF', t)
        for name, pat in SMELLS:
            for m in re.finditer(pat, scrub, re.I):
                findings[name].append((r['id'], m.group(0).strip()))
        for c in r.get('criteria') or []:
            if not EARS.match(c):
                findings['non_ears_criterion'].append((r['id'], c[:60]))
    return findings

def structure(reqs, cfg):
    errs = []
    dom2phase = {d: int(p) for p, s in cfg['phases'].items() for d in s.get('domains', [])}
    dom2mod   = {d: m for m, ds in cfg['modules'].items() for d in ds}
    doms = {r['domain'] for r in reqs}
    for d in sorted(doms - set(dom2phase)):
        errs.append(f"domain {d} is named in no phase - it will be orphaned by decomposition")
    for d in sorted(doms - set(dom2mod)):
        errs.append(f"domain {d} is mapped to no module")
    for r in reqs:
        if not r.get('priority'):
            errs.append(f"{r['id']} has no priority")
    without = [r['id'] for r in reqs if not (r.get('criteria') or [])]
    return errs, without

def main(cfg):
    reqs = read_json(out(cfg, 'requirements.json'))
    for r in reqs: r.setdefault('domain', r['id'].split('-')[1] if r['id'].count('-') == 2 else 'NFR')
    findings = lint(reqs, cfg)
    errs, without = structure(reqs, cfg)

    print(f"Spec lint - {len(reqs)} requirements")
    total = sum(len(v) for v in findings.values())
    print(f"  smells: {total}")
    for name, hits in sorted(findings.items(), key=lambda x: -len(x[1])):
        sample = ', '.join(f"{i}:'{w}'" for i, w in hits[:3])
        print(f"    {name:20s} {len(hits):4d}   {sample}")
    if without:
        pct = len(without) * 100 // len(reqs)
        print(f"  requirements with no EARS acceptance criteria: {len(without)} ({pct}%)")
        print(f"    without them, acceptance tests must be inferred rather than derived")
    print()
    if errs:
        print(f"FAILED - {len(errs)} structural error(s):")
        for e in errs: print("  ERROR", e)
        return 1
    print("Structure OK. Smells above are advisory - review, do not blindly rewrite.")
    return 0

