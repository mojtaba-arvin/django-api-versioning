# Mutation-equivalence register

The mutation campaigns use **mutmut 2.5.1**. This register records mutations
intentionally excluded with inline `# pragma: no mutate` markers. Each
exclusion is justified by local input/state invariants; it is not an untested
behavior or a threshold exception. Every remaining generated mutant must be
killed. CI requires exactly 100% per domain and rejects skipped, suspicious,
timed-out, incomplete, or surviving mutants.

## Negotiation

| Location | Equivalent mutation | Reason |
|---|---|---|
| `negotiation.py` — path-version digit normalization | `lstrip("0")` → `lstrip("XX0XX")` | The captured value is constrained to ASCII digits, so X characters cannot occur. |
| `negotiation.py` — quoted-header parser state | `0` → `None`; `False` → `None` | The offset is used as a slice start, where both mean the start; quote/escape flags are consumed only in truthiness checks. |
| `negotiation.py` — media-range parser state | `False` → `None` | The local flags are consumed only in truthiness checks. |
| `negotiation.py` — Accept version state | `False` → `None` | `saw_version` is read only as a boolean. |
| `negotiation.py` — middleware path fallback | `"/"` → `"XX/XX"` | An empty path is outside the configured API prefix under either fallback and returns before rewriting; a non-empty path does not use the fallback. |
| `negotiation.py` — path reconstruction condition | `and` → `or` | For non-empty paths, the left predicate is already true. Empty paths are rejected by the earlier API-prefix guard. |

## Registry

| Location | Equivalent mutation | Reason |
|---|---|---|
| `registry.py` — unowned route grouping | unowned identity tuple → `None` | The key is only used in a set: all unowned entries remain one group and owned identities remain distinct tuples. |
| `registry.py` — canonical-route escape state | `False` → `None` | The escape flag is used only in truthiness checks. |
| `registry.py` — resolved-route suffix loop | `continue` → `break` after a failed segment boundary | Candidate strings differ only by stripping anchors. If the longer suffix fails the preceding-slash boundary, removing its trailing anchor makes the shorter candidate cease to be a suffix, or removing its leading anchor leaves a non-slash character at the boundary. No later candidate can make that boundary valid. |
| `registry.py` — route-specificity escape state | `False` → `None` | The escape flag is used only in truthiness checks. |

## Routers

| Location | Equivalent mutation | Reason |
|---|---|---|
| `routers.py` — missing namespace fallback | empty namespace → `"XXXX"` | Version extraction accepts only components beginning with `v` followed by decimal digits; neither value yields a version. |
| `routers.py` — route/namespace match flag | `False` → `None` | The flag is used only in truthiness checks. |
| `routers.py` — configured route prefix test | outer sentinel slashes → `XX/` and `/XX` | The searched prefix retains the slash immediately before and after the route path, so substring membership is unchanged. |

If a later refactor changes any of these invariants, the exclusion must be
reviewed and removed or replaced with a behaviorally meaningful mutant.
