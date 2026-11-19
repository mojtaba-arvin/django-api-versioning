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
   - Derive migration scenarios from the current and previous published versions; do not keep historical version pairs as a permanent checklist.
   - Verify the 0.2.x decorator-flag migration path only when auditing that legacy upgrade path.
   - Test the latest published-to-candidate upgrade and any documented breaking changes against the exact tagged artifacts.
   - Verify migration tools and examples against current source and executable tests.

3. **Check Deprecation Patterns**
   - Verify deprecation warnings work
   - Check deprecation messages are clear
   - Test sunset behavior (removal of deprecated code)

4. **Document Breaking Changes**
   - List breaking changes per version
   - Provide migration examples
   - Ensure CHANGELOG is complete
