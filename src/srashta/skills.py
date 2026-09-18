#!/usr/bin/env python3
"""srashta skills — compare, sync down from, and promote up to the blueprint.

Two flows, and they are not the same thing:

  LOCAL          this project learns about itself. A retrospective's corrections are
                 edited straight into .claude/skills/. No blueprint involved, nothing
                 to sync. This is the common case.

  CROSS-PROJECT  something one project learned is generally true. --promote opens a
                 pull request against the blueprint repo; --sync pulls a merged
                 improvement down into another project.

Skills carry judgment, not logic - the enforcement is in validate.py - so a bad edit
costs worse advice, never a broken pipeline.

The hazard worth guarding is that --sync OVERWRITES. Local edits carrying your own
retrospective's corrections would be discarded, so sync names them first.
"""
import difflib, os, shutil, subprocess, tempfile, time
from importlib.resources import files
from .status import detect

LOCAL = '.claude/skills'
TEMPLATE_PATH = 'src/srashta/templates/skills'

def _blueprint():
    d = files('srashta') / 'templates' / 'skills'
    return {f.name: f.read_text() for f in d.iterdir() if f.name.endswith('.md')}

def _local(root='.'):
    d = os.path.join(root, LOCAL)
    if not os.path.isdir(d): return {}
    return {f: open(os.path.join(d, f)).read()
            for f in sorted(os.listdir(d)) if f.endswith('.md')}

def _diffstat(a, b, an, bn):
    d = list(difflib.unified_diff(a.splitlines(), b.splitlines(), an, bn, lineterm='', n=2))
    plus = sum(1 for l in d if l.startswith('+') and not l.startswith('+++'))
    minus = sum(1 for l in d if l.startswith('-') and not l.startswith('---'))
    return d, plus, minus

def _retro_note(root='.'):
    """A blueprint change without a rationale is how blueprints rot."""
    d = os.path.join(root, 'retrospectives')
    if not os.path.isdir(d): return None
    rs = sorted(f for f in os.listdir(d) if f.endswith('.md'))
    return rs[-1] if rs else None

def boundary(root='.'):
    """Advisory only. The real hazard is the overwrite, not the timing."""
    cfg, st = detect(root)
    if not cfg: return True, None
    for p, ph in sorted(st['phases'].items()):
        if ph['retro']: continue
        if ph['contracts'] and not ph['handoff']:
            return False, f"phase {p} is mid-decomposition"
        if ph['handoff'] and st['exec']:
            merged = sum(1 for v in st['exec'].values() if v in ('merged', 'done'))
            if merged < len(st['exec']):
                return False, f"phase {p} is mid-execution"
    return True, None

# ---------------------------------------------------------------- promote

def _repo_url(cfg):
    return (os.environ.get('SRASHTA_BLUEPRINT_REPO')
            or cfg.get('blueprint_repo'))

def promote(cfg, names, root='.'):
    bp, loc = _blueprint(), _local(root)
    todo = [n for n in (names or []) if n in loc] or \
           [n for n in loc if n in bp and loc[n] != bp[n]]
    todo = [n for n in todo if loc.get(n) != bp.get(n)]
    if not todo:
        print("  nothing to promote - your skills match the blueprint"); return 0

    url = _repo_url(cfg)
    if not url:
        print("  no blueprint repo configured. set one of:")
        print("    project.yaml:  blueprint_repo: git@github.com:you/srashta.git")
        print("    environment:   SRASHTA_BLUEPRINT_REPO=…")
        return 1
    if not shutil.which('gh'):
        print("  `gh` is not installed - it is what opens the pull request.")
        print("  install it, or copy these files into the blueprint repo by hand:")
        for n in todo: print(f"    {os.path.join(root, LOCAL, n)}  ->  {TEMPLATE_PATH}/{n}")
        return 1

    project = cfg.get('project', 'project')
    branch = f"promote/{project}-{time.strftime('%Y%m%d-%H%M%S')}"
    retro = _retro_note(root)
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(['git', 'clone', '--depth', '1', url, tmp],
                           capture_output=True, text=True)
        if r.returncode:
            print(f"  could not clone {url}\n  {r.stderr.strip().splitlines()[-1:]}"); return 1
        dst = os.path.join(tmp, TEMPLATE_PATH)
        if not os.path.isdir(dst):
            print(f"  {url} does not look like the srashta repo "
                  f"({TEMPLATE_PATH} not found)"); return 1
        body = [f"Promoted from **{project}**.", ""]
        if retro:
            body += [f"Motivated by `retrospectives/{retro}` in that project. "
                     f"Paste the relevant finding here before merging — a blueprint "
                     f"change without a rationale is how blueprints rot.", ""]
        for n in todo:
            open(os.path.join(dst, n), 'w').write(loc[n])
            d, plus, minus = _diffstat(bp.get(n, ''), loc[n], f'blueprint/{n}', f'{project}/{n}')
            body += [f"### {n}  (+{plus} −{minus})", "```diff", *d[:60], "```", ""]
        for cmd in (['git', 'checkout', '-b', branch],
                    ['git', 'add', TEMPLATE_PATH],
                    ['git', 'commit', '-m', f"skills: promote {', '.join(todo)} from {project}"],
                    ['git', 'push', '-u', 'origin', branch]):
            r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True)
            if r.returncode:
                print(f"  {' '.join(cmd[:2])} failed:\n  {r.stderr.strip()}"); return 1
        r = subprocess.run(['gh', 'pr', 'create', '--title',
                            f"skills: {', '.join(n[:-3] for n in todo)} (from {project})",
                            '--body', '\n'.join(body)],
                           cwd=tmp, capture_output=True, text=True)
        if r.returncode:
            print(f"  gh pr create failed:\n  {r.stderr.strip()}"); return 1
        print(f"\n  opened a pull request against the blueprint:")
        print(f"    {r.stdout.strip()}")
        print(f"  {len(todo)} skill(s): {', '.join(todo)}")
        if not retro:
            print("  no retrospective in this project - add the rationale to the PR "
                  "before merging.")
    return 0

# ---------------------------------------------------------------- main

def main(args, cfg=None, root='.'):
    cfg = cfg or {}
    if getattr(args, 'promote', None) is not None:
        return promote(cfg, args.promote, root)

    bp, loc = _blueprint(), _local(root)
    added   = sorted(set(bp) - set(loc))
    removed = sorted(set(loc) - set(bp))
    changed = sorted(f for f in set(bp) & set(loc) if bp[f] != loc[f])

    if not (added or changed or removed):
        print("  project skills match the blueprint"); return 0

    if not args.sync:
        for f in changed:
            d, plus, minus = _diffstat(loc[f], bp[f], f'{root}/{f}', f'blueprint/{f}')
            print(f"\n  ~ {f}   sync would add {plus}, remove {minus} line(s)")
            if args.full:
                for l in d: print('    ' + l)
        for f in added:   print(f"\n  + {f}   (new in the blueprint)")
        for f in removed: print(f"\n  - {f}   (yours only — sync leaves it alone)")
        print("\n  --sync     take the blueprint version (discards your edits above)")
        print("  --promote  open a PR sending your version up to the blueprint")
        if not args.full: print("  --full     line by line")
        return 0

    # sync overwrites. Say exactly what would be lost.
    if changed:
        print("\n  these local edits would be DISCARDED:")
        for f in changed:
            d, plus, minus = _diffstat(bp[f], loc[f], f'blueprint/{f}', f'{root}/{f}')
            own = [l[1:].strip() for l in d
                   if l.startswith('+') and not l.startswith('+++') and l[1:].strip()]
            print(f"    {f}  ({len(own)} line(s) of yours)")
            for l in own[:3]: print(f"        {l[:88]}")
            if len(own) > 3: print(f"        … and {len(own) - 3} more")
        print("\n  if any of that came from a retrospective, `--promote` it first.")
        if not args.force:
            print("  re-run with --force once you have.")
            ok, why = boundary(root)
            if not ok: print(f"  (also: {why} — prefer a phase boundary.)")
            return 1

    ok, why = boundary(root)
    if not ok: print(f"\n  note: {why}. Syncing now changes the guidance mid-phase.")
    d = os.path.join(root, LOCAL); os.makedirs(d, exist_ok=True)
    for f in changed + added:
        open(os.path.join(d, f), 'w').write(bp[f])
    print(f"\n  synced {len(changed) + len(added)} skill(s) from the blueprint")
    if removed: print(f"  left your project-only skill(s) alone: {', '.join(removed)}")
    print("  commit them — they travel with the repo.")
    return 0
