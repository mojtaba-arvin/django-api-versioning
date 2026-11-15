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
