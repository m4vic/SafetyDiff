# SafetyDiff Implementation Plan

SafetyDiff is a Neuralchemy project for safety regression comparison of AI systems.

This file is the living implementation log. Update it every time the project changes so future work keeps the full context.

## Product Decision

SafetyDiff is not OpenClay and not ASRT.

- ASRT is the attack lab: generate/load attacks, run targets, judge outputs, and save run records.
- SafetyDiff is the comparison layer: compare two safety runs and show whether behavior improved or regressed.
- Polyreasoner can later become the explanation layer for why a regression happened.

The first product wedge is:

> SafetyDiff shows whether a model, prompt, RAG, policy, or app change made AI safety better or worse.

## Current Folder

Project root:

```text
F:\ASRT\SafetyDiff
```

Current structure:

```text
SafetyDiff/
  safetydiff/
    __init__.py
    cli.py
  docs/
    product_direction.md
  examples/
    asrt_run_old.json
    asrt_run_new.json
  tests/
    .gitkeep
  .gitignore
  pyproject.toml
  README.md
  implementation.md
```

## Completed

- Created `SafetyDiff/` as a separate Neuralchemy project beside `asrtloop/`.
- Added package scaffold under `safetydiff/`.
- Added CLI entry point placeholder with `safetydiff compare old_run new_run`.
- Added `pyproject.toml` with package metadata and console script.
- Added `.gitignore` for Python caches, venvs, build outputs, local reports, and run files.
- Added example ASRT-style run JSON files.
- Added `docs/product_direction.md`.
- Added this implementation plan.
- Verified CLI help runs with:

```bash
python -m safetydiff.cli
```

- Verified Python compilation with:

```bash
python -m py_compile safetydiff\cli.py safetydiff\__init__.py
```

## Current Contract

SafetyDiff will initially consume ASRT-style JSON:

```json
{
  "meta": {
    "target": "example-model-v1",
    "suite": "jailbreak_core_v1"
  },
  "summary": {
    "attack_success_rate": 0.1
  },
  "results": [
    {
      "attack_id": "JB-001",
      "category": "jailbreak",
      "verdict": "refused",
      "score": 0.0
    }
  ]
}
```

## MVP Feature List

1. Load two run JSON files.
2. Normalize results by `attack_id`.
3. Compare overall attack success rate.
4. Compare verdict distributions.
5. Identify newly unsafe attacks.
6. Identify newly fixed attacks.
7. Identify stable failures.
8. Export JSON summary.
9. Export Markdown report.
10. Add tests using example fixtures.

## Proposed Modules

```text
safetydiff/
  schema.py      # dataclasses / normalized run model
  loader.py      # read and validate ASRT-style JSON
  diff.py        # comparison engine
  report.py      # markdown/json report rendering
  cli.py         # command interface
```

## CLI Target

```bash
safetydiff compare examples/asrt_run_old.json examples/asrt_run_new.json
```

With output:

```bash
safetydiff compare examples/asrt_run_old.json examples/asrt_run_new.json --out reports/example.md
```

## Definition of Done for v0.1

- `safetydiff compare` works on example ASRT records.
- Console output gives the safety delta clearly.
- Markdown report is generated when `--out` is provided.
- JSON report is supported via `--format json`.
- Unit tests cover newly unsafe, newly fixed, and unchanged cases.
- README includes a working example command.

## What Not To Build Yet

- Dashboard.
- Live runtime guard.
- Attack generation.
- LLM-based explanation.
- Vendor integrations beyond local JSON files.
- OpenClay compatibility wrapper.

## Next Step

The core comparison engine is fully implemented (`schema.py`, `loader.py`, `diff.py`, `report.py`, and `cli.py`). 

Next steps:
- Add tests for the example fixtures
- Test the integration with real ASRT loop outputs
- Further refine the markdown report presentation
