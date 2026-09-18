#!/usr/bin/env python3
"""Step 4 - dependency structure matrix over requirements.

The requirement-domain prefix is a PRIOR, not the answer. Cluster the dependency
matrix and report where the two disagree: those requirements are either misfiled
in the spec or genuine cross-module flows. Neither is visible by reading.
"""
import re, sys, itertools
from collections import defaultdict, Counter
from .common import load_project, domain_of, out, read_json, write_json

W_XREF, W_ENTITY, W_ATOMIC = 3.0, 1.0, 2.0
# An entity naming half the spec ("user", "session") carries no information about
# coupling. Weight every entity edge by inverse document frequency and drop the
# ubiquitous ones outright, or the matrix says everything depends on everything.
MAX_ENTITY_SHARE = 0.06      # skip an entity appearing in >6% of requirements
MIN_EDGE = 0.45              # prune edges too weak to mean anything

def build(cfg, reqs):
    ids = {r['id'] for r in reqs}
    id_re = re.compile(rf"\b(?:{cfg['spec']['id_pattern']})\b")
    entities = [e.lower() for e in cfg.get('entities', [])]
    edges = defaultdict(float); why = defaultdict(set)

    def add(a, b, w, tag):
        if a == b: return
        k = tuple(sorted((a, b))); edges[k] += w; why[k].add(tag)

    ent_index = defaultdict(set)
    for r in reqs:
        body = r['text'] + ' ' + ' '.join(r.get('criteria', []))
        t = body.lower()
        # explicit cross-reference: strongest signal
        for other in id_re.findall(body):
            if other in ids: add(r['id'], other, W_XREF, 'xref')
        for e in entities:
            if re.search(rf'\b{re.escape(e)}s?\b', t): ent_index[e].add(r['id'])
        # a single atomic outcome naming several effects couples them
        if re.search(r'in one atomic outcome|atomically|in a single transaction', t):
            r['_atomic'] = True

    import math
    n = len(reqs)
    for e, members in ent_index.items():
        share = len(members) / n
        if share > MAX_ENTITY_SHARE or len(members) < 2: continue
        idf = math.log(n / len(members))
        for a, b in itertools.combinations(sorted(members), 2):
            add(a, b, W_ENTITY * idf / 3.0, f'entity:{e}')

    # A single atomic outcome couples exactly the entities it names, not every
    # requirement that happens to mention one of them.
    for r in (x for x in reqs if x.get('_atomic')):
        named = [e for e in entities
                 if re.search(rf'\b{re.escape(e)}s?\b', r['text'].lower())
                 and 2 <= len(ent_index[e]) and len(ent_index[e]) / n <= MAX_ENTITY_SHARE]
        for e in named:
            for other in sorted(ent_index[e]): add(r['id'], other, W_ATOMIC, f'atomic:{e}')

    edges = {k: v for k, v in edges.items() if v >= MIN_EDGE}
    return edges, {k: why[k] for k in edges}

def cluster(reqs, edges, seed_of):
    """Label propagation seeded with the prefix prior. Deterministic."""
    label = dict(seed_of)
    adj = defaultdict(list)
    for (a, b), w in edges.items():
        adj[a].append((b, w)); adj[b].append((a, w))
    for _ in range(12):
        changed = False
        for r in sorted(adj, key=lambda x: (-len(adj[x]), x)):
            tally = defaultdict(float)
            for n, w in adj[r]: tally[label[n]] += w
            # inertia scaled to the node's own connectivity, so a densely linked
            # requirement is not dragged out of its module by sheer edge count
            tally[label[r]] += 0.35 * sum(w for _, w in adj[r]) + 1.0
            best = max(sorted(tally), key=lambda k: tally[k])
            if best != label[r]: label[r] = best; changed = True
        if not changed: break
    return label

def confidence(reqs, disagreements, flows, modules):
    """Self-assess. The caller NEVER asks a human to tune this - it degrades and moves on."""
    n = max(len(reqs), 1); m = max(len(modules), 1)
    dis_rate = len(disagreements) / n
    # a "flow" bound to most of the system is hub noise, not a flow
    degenerate = sum(1 for f in flows[:10] if f['n'] > m * 0.5) >= 5
    if dis_rate > 0.35 or degenerate: return 'low'
    if dis_rate > 0.22: return 'medium'
    return 'high'


def main(cfg):
    reqs = read_json(out(cfg, 'requirements.json'))
    dom2mod = {d: m for m, ds in cfg['modules'].items() for d in ds}
    prior = {r['id']: dom2mod.get(r['domain'], 'unassigned') for r in reqs}
    edges, why = build(cfg, reqs)
    found = cluster(reqs, edges, prior)

    disagreements = [
        {'id': r['id'], 'prior': prior[r['id']], 'clustered': found.get(r['id'], prior[r['id']]),
         'text': r['text'][:150]}
        for r in reqs if found.get(r['id'], prior[r['id']]) != prior[r['id']]]

    # A cross-module flow is measured by COUPLING STRENGTH, not by how many modules
    # a requirement happens to mention. Sum edge weight per target module and keep
    # only the modules it is genuinely bound to; otherwise every universal
    # requirement ("every object must be findable") outranks the real flows.
    STRONG = 2.0
    cross = defaultdict(lambda: defaultdict(float))
    for (a, b), w in edges.items():
        if prior[a] != prior[b]:
            cross[a][prior[b]] += w; cross[b][prior[a]] += w
    text_of = {r['id']: r['text'] for r in reqs}
    flows = []
    for k, mods in cross.items():
        strong = {m: round(w, 1) for m, w in mods.items() if m != prior[k] and w >= STRONG}
        if len(strong) >= 2:
            flows.append({'id': k, 'home': prior[k],
                          'touches': sorted(strong, key=lambda m: -strong[m]),
                          'weights': strong, 'n': len(strong),
                          'coupling': round(sum(strong.values()), 1),
                          'text': text_of[k][:200]})
    flows.sort(key=lambda x: (-x['coupling'], -x['n']))

    conf = confidence(reqs, disagreements, flows, set(prior.values()))
    # Degrade, never block. The domain prefix is always a usable answer; the matrix is
    # an accelerator. When it is not confident, hand the job to semantic grouping and
    # keep going - nobody should be tuning edge weights during a product design.
    method = {'high': 'matrix', 'medium': 'matrix+review', 'low': 'prefix+llm-review'}[conf]
    if conf == 'low':
        disagreements, flows = [], flows[:15]

    res = {'method': method, 'confidence': conf, 'edges': len(edges),
           'modules': sorted(set(prior.values())),
           'disagreements': disagreements, 'cross_module_flows': flows[:40],
           'llm_review_needed': conf == 'low',
           'review_prompt': (
               "The dependency matrix was not confident for this spec. Group these requirements "
               "into modules by reading them, using the domain prefixes as the starting point, "
               "and list any requirement whose satisfaction needs three or more modules."
               if conf == 'low' else None)}
    p = out(cfg, 'dsm.json'); write_json(p, res)
    return res

