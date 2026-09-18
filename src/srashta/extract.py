"""Parse both the published Markdown/EARS format and legacy text specifications."""
import re
from collections import Counter, defaultdict
from .common import domain_of, out, write_json, die


def main(cfg):
    sc = cfg['spec']
    text = open(sc['path'], encoding='utf-8').read()
    ident = re.compile(rf"^({sc['id_pattern']})(?=\s|$)\s*(.*)$")
    priority = sc.get('priority_pattern', 'P0|P1|P2')
    pri_line = re.compile(rf'^\[?({priority})\]?$')
    pri_inline = re.compile(rf'(?:^|\s)\[?({priority})\]?(?=\s|$)')
    footer = re.compile(sc['footer_pattern']) if sc.get('footer_pattern') else None
    header = re.compile(sc['header_pattern']) if sc.get('header_pattern') else None
    rows, current, section = {}, None, 'text'
    for index, raw in enumerate(text.splitlines()):
        line = raw.strip()
        if index < sc.get('body_start_line', 0) or not line:
            continue
        if (footer and footer.search(line)) or (header and header.search(line)):
            continue
        candidate = re.sub(r'^#{1,6}\s+', '', line)
        candidate = re.sub(r'\*\*([^*]+)\*\*', r'\1', candidate)
        match = ident.match(candidate)
        if match and current and raw[:1].isspace() and not pri_inline.search(match.group(2)):
            match = None  # An indented cross-reference in criteria/rationale is not a declaration.
        if match:
            rid, body = match.groups()
            if not body.strip():
                if current and section == 'text': current['text'] += ' ' + rid
                continue
            if rid in rows:
                die(f'duplicate requirement declaration {rid} at line {index + 1}')
            pm = pri_inline.search(body)
            current = dict(id=rid, text=(body[:pm.start()] + body[pm.end():]).strip() if pm else body,
                           priority=pm.group(1) if pm else None, criteria=[],
                           section=None, line=index + 1, domain=domain_of(rid))
            rows[rid], section = current, 'text'
            continue
        if current and candidate.strip('*: ').lower() == 'acceptance criteria':
            section = 'criteria'
            continue
        if line.startswith('```') or line.startswith('#') or line == '---':
            current = None
            continue
        if not current:
            continue
        pm = pri_line.fullmatch(line)
        if pm:
            current['priority'] = pm.group(1)
            current = None  # legacy priority is a record terminator
            continue
        label = line.strip('*: ').lower()
        if label == 'acceptance criteria':
            section = 'criteria'
            continue
        if label in ('rationale', 'conformance') or label.startswith('rationale:'):
            section = 'rationale'
            continue
        line = re.sub(r'^(?:[-*]|\d+[.)])\s+', '', line)
        if re.match(r'^(WHEN|WHILE|WHERE|IF|THE SYSTEM SHALL)\b', line): section = 'criteria'
        if section == 'text':
            current['text'] += ' ' + line
        elif section == 'criteria':
            criteria = current['criteria']
            starts = re.match(r'^(WHEN|WHILE|WHERE|IF)\b', line)
            independent = line.startswith('THE SYSTEM SHALL') and criteria and 'THE SYSTEM SHALL' in criteria[-1]
            if not criteria or starts or independent:
                criteria.append(line)
            else:
                criteria[-1] += ' ' + line
    result = list(rows.values())
    for row in result:
        row['text'] = re.sub(r'\s+', ' ', row['text']).strip()
    if not result:
        die('no requirement declarations parsed; check specification path and identifier pattern')
    # Completeness, part one: do not count only successful declarations.
    mentioned = {m.group(0) for m in re.finditer(rf"\b(?:{sc['id_pattern']})\b", text)}
    missing = sorted(mentioned - rows.keys())
    if missing:
        die(f'identifiers mentioned but not parsed as rows: {missing}')
    # A pattern cannot validate itself: independently discover identifier families.
    families = defaultdict(set)
    for token in re.findall(r'\b[A-Z]+(?:-[A-Z]+)?-\d{3}\b', text):
        families[token.rsplit('-', 1)[0]].add(token)
    uncovered = [family for family, ids in families.items()
                 if len(ids) >= 3 and not all(re.fullmatch(sc['id_pattern'], token) for token in ids)]
    if uncovered:
        die(f'identifier families your id_pattern does not match: {sorted(uncovered)}')
    path = out(cfg, 'requirements.json')
    write_json(path, result)
    print(f'parsed {len(result)} requirements -> {path}')
    print(f"  priority: {dict(Counter(r['priority'] for r in result))}")
    print(f'  completeness: every one of {len(mentioned)} mentioned identifiers accounted for')
    return result
