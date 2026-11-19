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
   - DRF `APIView` and `GenericAPIView` classes registered through `@endpoint`.
   - DRF ViewSets registered through the optional `VersionedRouter`, which delegates route generation to `SimpleRouter` and registers each generated pattern in the package registry.
   - Verify `VersionedRouterVersioning` request-version identification, namespace-aware `reverse_action()` and hyperlinked fields, per-route inheritance, regex/path-converter routes, and coexistence with decorator endpoints.
   - Verify explicit route removal and endpoint lifecycle metadata on current main separately from the published PyPI artifact until those APIs are released.
   - Keep the boundary explicit: direct `@endpoint(ViewSetClass)` decoration is unsupported, and `DefaultRouter` API-root/format-suffix parity is not implemented. Plain DRF routers remain a valid separate alternative.

3. **Execute Compatibility Tests**
   - Run unit tests with each Django version
   - Run integration tests with each combination
   - Document results in compatibility matrix
   - Note any version-specific workarounds

4. **Verify Settings Compatibility**
   - Test all documented settings options
   - Verify `LifecycleMiddleware` response headers (`Deprecation`, `Sunset`) and configured sunset enforcement (`410 Gone`). Do not expect Python deprecation warnings from this middleware.
   - Check backward compatibility
