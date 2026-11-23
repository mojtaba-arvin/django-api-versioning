# CI execution architecture

**Status:** Maintainer contract for pull-request validation and release evidence.

The CI pipeline is divided by change impact. The goal is to preserve the package's quality thresholds while avoiding repeated execution of expensive checks against equivalent source and configuration inputs.

## 1. Fast PR gate

The always-running [PR gate](../../.github/workflows/pull-request-gate.yml) classifies the complete changed-file list before invoking child workflows.

- Documentation-only changes run the website checks when relevant.
- Release metadata changes run lockfile validation and distribution build checks, without package runtime tests, OpenAPI contracts, dependency review, or the compatibility matrix when the parsed TOML proves that only the package version changed.
- Workflow, agent-policy, and dependency changes run the checks that cover those exact inputs.
- Every applicable child workflow must succeed. The final PR gate fails closed if a required child was skipped or failed.

The classifier compares parsed `pyproject.toml` and `uv.lock` data against the PR base. It ignores only the package's own version fields and the uv lock content hash when proving a version-only release edit. A dependency, tool, build, or configuration change prevents metadata-only classification.

## 2. Deep quality gate

Changes to package runtime code, tests, integration consumers, dependencies, or quality-policy inputs run the package unit and real-consumer integration suites. The Deep Quality tier also runs the five-domain mutation campaign and adversarial checks. Existing thresholds remain unchanged:

- 100% mutation score in Decorators, Lifecycle, Negotiation, Registry, and Routers.
- At least 95% line coverage and 95% branch coverage, independently.
- Complete public API and consumer contract coverage.
- Relevant security and adversarial checks.

The expensive campaign is opt-in at the reusable workflow boundary. A `workflow_call` does not itself enable mutation or fuzzing; the classifier must explicitly request Deep Quality. Scheduled and deliberately dispatched campaigns remain available.

## 3. Compatibility matrix scheduling

The compatibility workflow has two mutually exclusive scopes:

- **PR smoke:** boundary Python/Django environments, lint, matrix-definition validation, and cross-platform smoke checks. This is used for ordinary runtime changes.
- **Full matrix:** all configured Python/Django tox environments. Dependency-only and compatibility-configuration changes run the full matrix on the PR. Ordinary runtime changes run the PR smoke checks and the full matrix once after merge to `main`.

The full matrix is no longer run alongside the PR smoke matrix for the same PR. The push trigger is restricted to runtime/test changes; dependency and matrix-configuration changes are validated fully before merge.

## 4. Evidence fingerprints and reuse

A passing test run is useful beyond the commit on which it was produced only when its effective inputs are identical. [`scripts/quality_fingerprint.py`](../../scripts/quality_fingerprint.py) computes three deterministic SHA-256 fingerprints:

- **Deep-quality fingerprint:** package source, tests, real-consumer examples, dependency inputs, and the effective test/mutation/adversarial workflow configuration.
- **Compatibility fingerprint:** dependency and Python/Django matrix inputs, matrix validation, the classifier, and fingerprint implementation.
- **OpenAPI contract fingerprint:** package routing source, executable consumer schemas/examples, the OpenAPI contract workflow, and its design contract.

The fingerprints normalize only the package's own version in `pyproject.toml` and its self-package version plus generated content hash in `uv.lock`. All dependency declarations, runtime source, tests, matrix definitions, and quality workflow settings remain part of the digest.

Successful Deep Quality, OpenAPI consumer-contract, and full compatibility runs upload separate machine-readable evidence artifacts with 90-day retention. Each artifact is checked against its matching fingerprint; OpenAPI evidence uses the dedicated contract fingerprint. The tag-triggered release workflow searches successful runs and reuses evidence only when the corresponding fingerprint exactly matches the tagged source. A documentation edit or package-version bump therefore does not invalidate runtime evidence; a source, dependency, test, or effective CI configuration change does.

If no matching artifact exists or artifacts have expired, release verification fails closed. Run the corresponding workflows deliberately on the candidate source:

```bash
gh workflow run tests.yml --ref main -f run_adversarial=true
gh workflow run compatibility.yml --ref main -f scope=full
gh workflow run openapi-contract.yml --ref main
```

Do not bypass the evidence gate or treat an artifact with a different fingerprint as equivalent.

## 5. Build and publication boundaries

- The PR package-artifact workflow builds and validates wheel/sdist for package-impacting changes. It is not repeated automatically on the merge commit.
- Website static validation is performed in the PR when website content or examples are affected; it is not repeated as a second main-push preflight.
- The tag workflow still builds the final release artifacts from the exact tagged source, verifies reproducibility and package boundaries, and publishes those verified artifacts. This build is not redundant: it is the artifact set actually uploaded to PyPI.
- The OpenAPI consumer contract is validated in the PR and recorded as a separate evidence artifact. The tag workflow reuses it only when its source fingerprint matches.

The PR merge is not a release. Tag creation, PyPI publication, and GitHub Release creation remain separate, ordered operations.

## 6. Safety invariants

1. Quality thresholds are not reduced by tier selection.
2. The PR gate evaluates every applicable check for the exact PR head.
3. Full compatibility evidence is produced only after the complete matrix, platform smoke, and matrix validation succeed.
4. Deep-quality evidence is produced only after package/integration tests and the adversarial campaign succeed.
5. Release evidence is reusable by content fingerprint, never by a matching version string or a loosely related commit.
6. Missing, expired, failed, or mismatched evidence blocks publication.
7. A release tag must still target a commit reachable from `main`; the tag workflow builds and publishes the artifacts from that tag.

See [Quality and release gates](release-gates.md) and the [package release procedure](../../.agents/skills/release/references/release-procedure.md).
