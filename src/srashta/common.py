"""Shared helpers. No project-specific knowledge lives here or anywhere in pipeline/."""
import json, os, re, sys, yaml

def load_project(path='project.yaml'):
    cfg = yaml.safe_load(open(path))
    s = cfg.setdefault('spec', {})
    s.setdefault('id_pattern', r'FR-[A-Z]{2,6}-\d{3}|NFR-\d{3}')
    s.setdefault('priority_pattern', r'P0|P1|P2')
    s.setdefault('body_start_line', 0)
    cfg.setdefault('overrides', {})
    cfg.setdefault('open_questions', {})
    return cfg

def domain_of(rid):
    """FR-ACC-001 -> ACC ; NFR-001 -> NFR. Works for any 2-6 letter domain segment."""
    parts = rid.split('-')
    return parts[1] if len(parts) == 3 else parts[0]

def out(cfg, *parts):
    p = os.path.join(cfg.get('out_dir', 'build'), *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p

def read_json(p):  return json.load(open(p))
def write_json(p, o):
    os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
    json.dump(o, open(p, 'w'), indent=1)

def die(msg):
    # sys.exit(str) prints to stderr AND carries the message, so callers and tests
    # can both see it. sys.exit(1) would discard it.
    sys.exit(f"ERROR: {msg}")
