# Mutation Survivor Triage — 2026-11-23

## Last complete baseline

Source: PR #183, workflow run [45109631394](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/45109631394), head `5d680a3bf4c0b9f5e19a4d61bd26afb702434464`.

| Domain | Killed | Total | Survived | Score |
|---|---:|---:|---:|---:|
| Decorators | 140 | 140 | 0 | 100.00% |
| Lifecycle | 148 | 148 | 0 | 100.00% |
| Negotiation | 308 | 325 | 17 | 94.77% |
| Registry | 553 | 588 | 35 | 94.05% |
| Routers | 310 | 329 | 19 | 94.22% |
| **Combined** | **1459** | **1530** | **71** | **95.36%** |

All 1,530 mutants completed. The baseline recorded zero timeouts, skipped mutants, or suspicious outcomes. This baseline is historical; it is not evidence for the current PR head.

## Work added for the next validation

- Black-only formatting repair for `tests/test_mutation_survivor_contracts.py`.
- Registry contracts for stale suppressed-route cleanup, tombstone ownership, invalid candidate continuation, route specificity, and registered-operation input validation.
- Negotiation contracts for default/custom header behavior, default maximum version, default path-template rejection, and literal path characters.
- Router contracts for lifecycle prefix validation, removal error messages, path-converter prefix validation, below-minimum version warnings, namespace/path agreement, and boolean route-version rejection.
- Import-time probes now assert the runtime type aliases and owner sentinel invariants used by the registry and router modules.

The new tests are deliberately added to test modules already included by the domain test-selection map. The next coverage baseline must be regenerated so the mutation shards can select these tests for the relevant mutated lines.

## Equivalence review — not exclusions

The previous survivor report contains candidate equivalent mutations, including boolean state initializers changed from `False` to `None`, slice start `0` changed to `None`, and the digit-only `lstrip("0")` argument changed to `lstrip("XX0XX")`. These are hypotheses only. They must be verified against the input domain and Python semantics; none is excluded from the mutation denominator by this note.

## Acceptance

The next complete campaign must reconcile all five shard totals, report no incomplete outcomes, and reach 100% independently in all five domains. No mutation threshold, target scope, or outcome classification is weakened to obtain a green result.

## Validation branch

The follow-up contract changes are staged on PR #183's head. This stacked PR is a temporary CI trigger because the repository's pull-request workflow only targets PRs whose base branch is `main`. Its results validate the combined source tree; it is not intended to merge into `main`.
