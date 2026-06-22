# Product Direction

SafetyDiff should stay narrow at first.

## First Wedge

Safety regression for AI behavior across versions:

- model version changes
- system prompt changes
- RAG/context changes
- safety policy changes
- application releases

## Not First

- live runtime enforcement
- dashboards
- agent orchestration
- broad security platform claims
- automatic attack generation

ASRT handles attacks. SafetyDiff handles comparisons.

## Core Output

SafetyDiff should produce:

- overall safety delta
- attack success rate delta
- verdict distribution delta
- category-level regressions
- newly unsafe prompts
- newly fixed prompts
- stable failures

The report should be simple enough for developers and concrete enough for security review.
