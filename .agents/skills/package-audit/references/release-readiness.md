### 12. Release Readiness

**Objectives**:
- Verify package is ready for release
- Check all pre-release steps are complete
- Assess documentation and communication

**Procedures**:

1. **Published Artifact Provenance**
   - Resolve the latest published version to its exact annotated Git tag and commit; verify the version-specific PyPI endpoint.
   - Compare the tag commit with current `main`; inspect source, `pyproject.toml`, `CHANGELOG.md`, README/reference, and workflow definitions at both revisions.
   - Verify whether each claimed API/example/CI gate existed at the tag. Do not infer published-wheel contents from current-main source or documentation.
   - Distinguish package runtime APIs from repository-only examples, schema snapshots, test fixtures, and CI tooling.
   - Inspect the built wheel contents and run an isolated installed-wheel smoke test for the exact candidate commit.

2. **Code Readiness**
   - All tests passing on the exact candidate commit: ✓/✗
   - Mutation score is exactly 100% in Decorators, Lifecycle, Negotiation, Registry, and Routers, with no incomplete or unresolved mutant outcomes: ✓/✗
   - Line coverage >=95% and branch coverage >=95%, independently: ✓/✗
   - Full configured 16-environment tox matrix passed: ✓/✗
   - Public API and real-consumer OpenAPI contracts passed: ✓/✗
   - CodeQL, Atheris, Schemathesis, and applicable property-based adversarial checks passed: ✓/✗
   - No known critical bugs: ✓/✗
   - Backward compatibility reviewed across routing, schema, and runtime semantics: ✓/✗

3. **Documentation Readiness**
   - README complete and accurate: ✓/✗
   - CHANGELOG updated: ✓/✗
   - Migration guide complete: ✓/✗
   - API documentation current: ✓/✗
   - Known limitations documented: ✓/✗

4. **Release Materials**
   - Wheel and sdist built, metadata and distribution contents validated, and installed-wheel smoke test passed: ✓/✗
   - Reproducible-build check completed for the exact source and build environment: ✓/✗
   - Release notes prepared: ✓/✗
   - Version number determined: ✓/✗
   - Annotated tag target and protection rules verified; create a tag only after explicit authorization: ✓/✗
   - PyPI Trusted Publishing/OIDC configured with `id-token: write` limited to the publish job; no long-lived PyPI token: ✓/✗

5. **Communication**
   - Release announcement prepared: ✓/✗
   - Community notification planned: ✓/✗
   - Issue template updated: ✓/✗
