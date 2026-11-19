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
   - All tests passing: ✓/✗
   - Code coverage acceptable: ✓/✗
   - No known critical bugs: ✓/✗
   - Security reviewed: ✓/✗
   - Compatibility verified: ✓/✗

3. **Documentation Readiness**
   - README complete and accurate: ✓/✗
   - CHANGELOG updated: ✓/✗
   - Migration guide complete: ✓/✗
   - API documentation current: ✓/✗
   - Known limitations documented: ✓/✗

4. **Release Materials**
   - Release notes prepared: ✓/✗
   - Version number determined: ✓/✗
   - Annotated tag target and protection rules verified; create a tag only after explicit authorization: ✓/✗
   - PyPI Trusted Publishing/OIDC configured with `id-token: write` limited to the publish job; no long-lived PyPI token: ✓/✗

5. **Communication**
   - Release announcement prepared: ✓/✗
   - Community notification planned: ✓/✗
   - Issue template updated: ✓/✗
