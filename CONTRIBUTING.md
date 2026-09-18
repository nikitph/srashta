# Contributing

Srashta is an early Python toolkit for making specification-to-ticket planning explicit, reviewable and portable.

Start with an issue describing a concrete failure: the specification, the intended graph, the actual graph or validator result, and the correction you had to make. Small reproducible examples are especially useful. Remove secrets and private product information before sharing fixtures.

## Local development

```bash
git clone https://github.com/nikitph/srashta.git
cd srashta
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e . pytest jsonschema build
python -m pytest -q
```

Python 3.10+ on macOS/Linux. The Python suite does not require PHP or Composer. The full [Laravel acceptance fixture](examples/notes_demo.py) does.

For behavioral fixes, add a regression demonstrating the failure, then run the affected tests and the full suite. Keep authored planning decisions out of disposable build outputs. Avoid introducing model calls or scheduler-specific assumptions into the CLI.

## Useful contributions

- Decomposition examples that expose missing dependencies, poor task boundaries or insufficient context.
- Validator defects with small fixtures and concrete expected results.
- Portable handoff adapters for execution systems.
- Evidence from supervised builds: correction effort, unexpected shared changes and integration repairs.

The current tests establish mechanical behavior. They do not establish the quality of agent-authored decomposition. Please keep that distinction in documentation and benchmark claims.

The landing page is plain HTML, CSS and JavaScript in `docs/`. Preview with `python -m http.server 8000 --directory docs`. No asset build or external JavaScript dependencies are required.

Srashta is available under the [MIT License](LICENSE). Contributions are provided under the same license.
