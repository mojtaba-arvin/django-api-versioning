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
