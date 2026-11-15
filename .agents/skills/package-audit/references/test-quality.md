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
