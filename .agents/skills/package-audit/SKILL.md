---
name: package-audit
description: Audit the Django API versioning package for architecture, compatibility, security, tests, packaging, documentation, and release readiness. Use for broad technical audits, not routine implementation.
---

# Skill: Package Audit - django-api-versioning

Complete package evaluation procedure for assessing technical quality, compatibility, and production readiness.

## Overview

This skill provides a systematic framework for auditing the django-api-versioning package across multiple dimensions. It distinguishes between:
- Verified facts (observed in actual code/tests/output)
- Suspected problems (unverified claims)
- Implemented capabilities (working in code)
- Partial capabilities (partially working)
- Known limitations (documented constraints)
- Proposed improvements (ideas for enhancement)

## Audit Dimensions

### 1. Architecture Review

**Objectives**:
- Understand overall package design
- Verify design patterns are appropriate
- Identify architectural limitations
- Assess maintainability and extensibility

**Procedures**:

1. **Map Module Dependencies**
   - Chart dependencies between modules
   - Identify cyclic dependencies
   - Check for clear separation of concerns

2. **Review Core Components**
   - `decorators.py` - @endpoint decorator mechanism
   - `registry.py` - URL registry pattern
   - `reverse.py` - URL reversal logic
   - `channels.py` - Version extraction channels
   - `lifecycle.py` - Deprecation/sunset handling

3. **Check Design Patterns**
   - Decorator pattern usage
   - Registry pattern correctness
   - Settings pattern (dataclass validation)
   - Exception hierarchy

4. **Document Findings**
   - Record architectural strengths
   - Note potential design issues
   - Identify extensibility points
   - Document limitations

### 2. Django and DRF Compatibility

**Objectives**:
- Verify compatibility with supported Django versions
- Verify DRF integration patterns
- Test with multiple version combinations

**Procedures**:

1. **Test Matrix Setup**
   Read tox.ini at audit time and derive current Python/Django environments from it. Do not copy environment names, counts, or version ranges into this skill or other instruction files. Run scripts/check_tox_workflow_matrix.py to verify that the GitHub Actions matrix matches tox. Use the manual-testing skill for execution steps and acceptance criteria. DRF is not a separate tox matrix dimension unless separately configured and actually executed.

2. **Test Integration Patterns**
   - Function-based views decorated with `@endpoint`.
   - Django class-based view classes decorated with `@endpoint` at the class level.
   - DRF `APIView` and `GenericAPIView` classes registered through the package.
   - DRF ViewSets and routers tested as separate routing mechanisms to verify coexistence only; do not imply that the package automatically registers ViewSets or creates router routes.

3. **Execute Compatibility Tests**
   - Run unit tests with each Django version
   - Run integration tests with each combination
   - Document results in compatibility matrix
   - Note any version-specific workarounds

4. **Verify Settings Compatibility**
   - Test all documented settings options
   - Verify `LifecycleMiddleware` response headers (`Deprecation`, `Sunset`) and configured sunset enforcement (`410 Gone`). Do not expect Python deprecation warnings from this middleware.
   - Check backward compatibility

### 3. Dependency Review

**Objectives**:
- Verify dependency declarations are accurate
- Check for unnecessary dependencies
- Assess dependency versions and licenses

**Procedures**:

1. **Inspect pyproject.toml**
   - Review `dependencies` section
   - Review `optional-dependencies` section
   - Check version constraints
   - Verify upper bounds are reasonable

2. **Verify Dependency Usage**
   - Grep for imports from each dependency
   - Check if dependency is actually used
   - Verify version requirement matches usage

3. **Check for Circular Dependencies**
   - Map import graph
   - Identify any circular imports
   - Note if design allows removing any dependency

4. **License Compatibility**
   - Check licenses of all dependencies
   - Verify compatibility with package license (MIT)
   - Document any license concerns

### 4. Backward Compatibility

**Objectives**:
- Verify public API stability
- Check for breaking changes between versions
- Assess migration paths for users

**Procedures**:

1. **Identify Public API**
   - List exports from `__init__.py`
   - Document all public functions/classes
   - Check which APIs are stable

2. **Test Version Migration**
   - Test 0.2.0 to 0.3.0 migration
   - Test 0.3.0 forward
   - Document migration procedures
   - Verify migration tools work correctly

3. **Check Deprecation Patterns**
   - Verify deprecation warnings work
   - Check deprecation messages are clear
   - Test sunset behavior (removal of deprecated code)

4. **Document Breaking Changes**
   - List breaking changes per version
   - Provide migration examples
   - Ensure CHANGELOG is complete

### 5. Security Review

**Objectives**:
- Identify security vulnerabilities
- Check for injection vulnerabilities
- Verify secure handling of user input

**Procedures**:

1. **Code Security Analysis**
   - Search for dynamic execution such as `eval()` and `exec()` (should be absent unless explicitly justified).
   - Check string interpolation in URLs
   - Verify regex handling escapes special characters
   - Check for SQL injection potential (N/A for this package)
   - Verify proper input validation

2. **Specific Focus Areas**
   - `reverse.py` - Verify parameter substitution, Django converter `to_url()` handling, and final route-pattern regex validation.
   - `decorators.py` - Path and version parameter validation
   - `settings.py` - Configuration value validation
   - Any `eval()` or `exec()` usage (should not exist)

3. **Dependency Security**
   - Check for known vulnerabilities in dependencies
   - Review dependency security advisories
   - Verify no deprecated dependencies

4. **GitHub Actions supply-chain review**
   - Require full commit-SHA pins for every external action, with the release tag in a comment.
   - Verify the SHA corresponds to the intended upstream release.
   - Check workflow-level and job-level permissions for least privilege.
   - Parse every `.github/**/*.yml` file and run the repository's workflow validation job; YAML parsing is not a substitute for reviewing GitHub Actions semantics.
   - Disable persisted checkout credentials in read-only jobs; retain write credentials only in workflows that must commit generated artifacts.
   - Verify Dependabot updates are reviewed and not auto-merged.
   - Require build/test and PyPI publication to run in separate jobs; only the minimal publish job may receive `id-token: write`.
   - Keep the publish job limited to downloading the verified artifact and invoking the pinned PyPI publishing action.

5. **Document Findings**
   - Record any vulnerabilities found
   - Note security best practices followed
   - List any recommendations

### 6. Test Quality

Use the manual-testing skill for test commands, matrix execution, log interpretation, and compatibility-report gates. Do not duplicate its environment list or execution procedure here.

**Objectives**:
- Verify test coverage is comprehensive
- Check test quality and maintainability
- Ensure tests verify actual functionality

**Procedures**:

1. **Coverage Analysis**
   - Run `pytest --cov=django_api_versioning --cov-report=term-missing`
   - Read the coverage configuration from `pyproject.toml`; do not invent a percentage threshold when none is configured.
   - Record the actual result from the identified test run.
   - Review uncovered lines and assess their risk, including defensive and legacy paths.

2. **Test Organization**
   - Verify tests are organized logically
   - Check for redundant tests
   - Assess test independence (no cross-test dependencies)
   - Review test naming conventions

3. **Integration Test Coverage**
   - Verify FBV, CBV, and DRF patterns tested
   - Check edge cases are covered
   - Verify error conditions tested
   - Assess real-world scenario coverage

4. **Test Maintenance**
   - Check for outdated or skipped tests
   - Review test fixtures for duplication
   - Assess test readability and documentation
   - Note any brittle tests

### 7. Documentation Quality

**Objectives**:
- Verify documentation is accurate and complete
- Check for outdated or contradictory information
- Assess user-friendliness

**Procedures**:

1. **README.md Review**
   - Verify installation instructions work
   - Check all examples are correct
   - Review feature descriptions against implementation
   - Verify known limitations are documented
   - Check for broken links

2. **CHANGELOG.md Review**
   - Verify version history is accurate
   - Check breaking changes are documented
   - Review migration guides
   - Verify test counts are correct

3. **Code Documentation**
   - Check docstrings are present and accurate
   - Verify type hints match implementation
   - Review inline comments for clarity
   - Check for `py.typed` marker presence

4. **Configuration Documentation**
   - Verify all settings are documented
   - Check default values are correct
   - Review setting validation behavior
   - Document edge cases

### 8. GitHub Discoverability

**Objectives**:
- Verify repository metadata is complete
- Check for appropriate topics
- Assess README visibility

**Procedures**:

1. **Repository Metadata**
   - Verify repository description is clear
   - Check topics are relevant and accurate
   - Verify README is visible
   - Check for contributing guidelines
   - Verify license is visible

2. **Issues and Discussions**
   - Check issue templates exist
   - Review open issues
   - Assess responsiveness to community
   - Check for documentation of known issues

3. **Releases and Tags**
   - Verify releases are created for versions
   - Check release notes are present
   - Verify version tags are correct
   - Check for changelog links

### 9. PyPI Discoverability

**Objectives**:
- Verify package metadata is complete on PyPI
- Check README renders correctly
- Assess keyword and classifier selection

**Procedures**:

1. **PyPI Metadata**
   - Check package name and version
   - Verify description is clear
   - Review keywords for relevance
   - Check classifiers are accurate
   - Verify author and maintainer info
   - Check project URLs are correct

2. **README Rendering**
   - Verify README renders without errors on PyPI
   - Check links work
   - Verify code examples display correctly
   - Check formatting is preserved

3. **Package Contents**
   - Download and inspect wheel file
   - Verify all modules are included
   - Check for unnecessary files
   - Verify `py.typed` marker is present

### 10. AI Search Discoverability

**Objectives**:
- Ensure content is discoverable by AI systems
- Provide clear, structured information
- Support semantic search

**Procedures**:

1. **Documentation Structure**
   - Verify clear headings and sections
   - Check for explicit feature descriptions
   - Review use case documentation
   - Verify example code is self-explanatory

2. **Semantic Clarity**
   - Identify common search intents:
     - "Django API versioning"
     - "Version-based URL routing"
     - "Backward-compatible Django APIs"
     - "Multiple API versions"
   - Verify documentation addresses these intents
   - Check for clear problem-solution pairings

3. **Structured Content**
   - Verify feature lists are clear
   - Check for comparison with alternatives
   - Review usage examples
   - Check for troubleshooting documentation

### 11. External Adoption

**Objectives**:
- Identify adoption opportunities
- Assess real-world usage
- Find community engagement

**Procedures**:

1. **Real-World Usage**
   - Research if package is used in production
   - Identify known users (with permission)
   - Review GitHub stars/forks
   - Check social media mentions

2. **Community Engagement**
   - Review GitHub discussions
   - Assess quality of bug reports
   - Check contribution patterns
   - Review feedback from users

3. **Educational Resources**
   - Search for tutorials using this package
   - Review blog posts or articles
   - Check for conference presentations
   - Identify educational content needs

### 12. Release Readiness

**Objectives**:
- Verify package is ready for release
- Check all pre-release steps are complete
- Assess documentation and communication

**Procedures**:

1. **Code Readiness**
   - All tests passing: ✓/✗
   - Code coverage acceptable: ✓/✗
   - No known critical bugs: ✓/✗
   - Security reviewed: ✓/✗
   - Compatibility verified: ✓/✗

2. **Documentation Readiness**
   - README complete and accurate: ✓/✗
   - CHANGELOG updated: ✓/✗
   - Migration guide complete: ✓/✗
   - API documentation current: ✓/✗
   - Known limitations documented: ✓/✗

3. **Release Materials**
   - Release notes prepared: ✓/✗
   - Version number determined: ✓/✗
   - Git tags ready: ✓/✗
   - PyPI credentials configured: ✓/✗

4. **Communication**
   - Release announcement prepared: ✓/✗
   - Community notification planned: ✓/✗
   - Issue template updated: ✓/✗

## Audit Execution Workflow

1. **Initial Setup**
   - Clone repository
   - Set up development environment
   - Install all dependencies

2. **Documentation Review** (1-2 hours)
   - Read README, CHANGELOG, and documentation
   - Identify claims and features
   - Note any inconsistencies

3. **Code Review** (2-4 hours)
   - Read all core modules
   - Understand architecture
   - Identify issues or concerns
   - Review security-sensitive code

4. **Test Execution** (1-2 hours)
   - Run unit tests
   - Run integration tests
   - Measure coverage
   - Test compatibility matrix

5. **Verification** (1 hour)
   - Verify all findings against source
   - Cross-reference documentation and code
   - Identify verified facts vs suspected issues

6. **Report Generation** (1 hour)
   - Document all findings
   - Create recommendations
   - Prepare release readiness assessment

## Output Format

Document audit findings in a clear, structured format. Populate all counts, versions, and coverage from the current source or a specific recorded test run; never reuse historical numbers as current results.

**VERIFIED FACTS**:
- [ ] Unit tests: `<count from the identified run>`; command and exit code recorded
- [ ] Integration tests: `<count from the identified run>`; command and exit code recorded
- [ ] Coverage: `<value from the identified run>`
- [ ] Configured tox matrix: `<environment list read from current tox.ini>`
- [ ] Actual environment results: `<PASS / FAIL / NOT-RUN per environment>`

**SUSPECTED ISSUES** (unverified):
- [ ] State the observation and the evidence still needed.

**IMPLEMENTED CAPABILITIES**:
- [ ] List only behavior verified in current source and tests.

**PARTIAL CAPABILITIES**:
- [ ] Version-channel parsing utility supports `path`, `header`, and `query` in `channels.py`; verify call sites before describing this as end-to-end request routing. In the current source tree, the utility is tested directly, but is not wired into the endpoint registry's request dispatch.
- [ ] DRF ViewSet classes cannot be registered directly without an action map; a specifically configured callable such as `MyViewSet.as_view({"get": "list"})` can be registered, while router-style route generation remains the application's responsibility.

**KNOWN LIMITATIONS**:
- Direct ViewSet class decoration is not supported as a substitute for DRF router/action configuration.
- `API_VERSIONING_CHANNELS` and `extract_version()` do not currently provide end-to-end header/query-based routing through the package registry.
- Python versions below 3.10 are outside the declared package requirement.

**RECOMMENDATIONS**:
- If header/query-based request routing is a product goal, trace and test the integration from channel extraction through request dispatch before claiming support.
- Keep ViewSet/router responsibilities explicit in documentation.
- Expand documentation only where it adds verified behavior or clarifies a real limitation.

## When to Use This Skill

- Before major releases
- When planning new features
- When investigating reported issues
- When assessing compatibility changes
- When community asks "is this production-ready?"
- During regular maintenance cycles
