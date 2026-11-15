# Historical coding-agent behavior audit: 418 commits

## Scope and method

This review covers exactly the 418 newest commits reachable from \`audit/comprehensive-package-review\` at:

- HEAD: \`6060db59834d77beca8392fb9464b0ae3bd1c5ce\`
- Inclusive oldest commit: \`56d73e53fb3b7ca67e0645134028b0d2cd0716dd\`
- Time window: 2026-11-14 17:54:35 UTC through 2026-11-15 22:06:23 UTC
- Parent immediately before the reviewed range: \`246bf3a0f725f9d97fafeaa0e83b89d3d207fea2\`

The review combined the complete 418-entry commit metadata list, two GitHub compare ranges, changed-path/churn summaries, per-file histories, and targeted diffs for repeated evidence generation, dependency-lock churn, status tracking, formatting, CI changes, migrations, API reverse behavior, DRF registration, packaging, and security-sensitive release workflows. It is a history-level forensic review, not a claim that every line of all 418 diffs was manually audited.

GitHub attributes all 418 commits in this interval to the same account, \`mojtaba-arvin\`. That is not reliable proof that a human or an AI agent authored each change: commit identity was also explicitly configured as the maintainer in automation workflows. Automation attribution is therefore assessed from workflow configuration, not inferred from author metadata.

## Quantitative overview

| Measure | Result |
| --- | ---: |
| Commits reviewed | 418 |
| Distinct changed paths across the range | 177 |
| Aggregated additions across commits | 27,167 |
| Aggregated deletions across commits | 3,945 |
| Merge commits in the interval | 0 |
| Most frequent commit prefix | \`docs:\` — 135 |
| Peak activity hour | 111 commits during 2026-11-14 22:00 UTC |

The line totals are cumulative per-commit churn, not the net size of the final branch diff. Repeated edits to the same file are counted repeatedly.

Commit message prefixes (mutually exclusive, derived from the leading Conventional Commit type):

| Prefix | Count | Share |
| --- | ---: | ---: |
| \`docs\` | 135 | 32.3% |
| \`ci\` | 67 | 16.0% |
| \`fix\` | 53 | 12.7% |
| \`test\` | 50 | 12.0% |
| \`style\` | 38 | 9.1% |
| \`data\` | 31 | 7.4% |
| \`build\` | 14 | 3.3% |
| \`chore\` | 13 | 3.1% |
| \`feat\` | 11 | 2.6% |
| \`refactor\` | 5 | 1.2% |
| \`security\` | 1 | 0.2% |

## Strong engineering behaviors

### 1. Behavior was increasingly verified against executable evidence

The Segment Lab was integrated into the existing Django integration project rather than creating a parallel test project. It records 18 scenarios, runs each scenario in a fresh process because package settings and registry state are process-global, captures Django/DRF/Python versions, and pins output to a full source commit.

The generator hashes package source and evidence inputs, resolves AST symbols and unique source-line anchors, and refuses a mismatched source SHA or dirty evidence inputs. The website presents the committed snapshot as data; it does not claim to execute Python in the browser.

Representative changes:
- [Port Segment Lab into the repository](https://github.com/mojtaba-arvin/django-api-versioning/commit/5dfebaebfba016e34d36a885578992bb7e5eefa5)
- [Pin evidence to the source commit and retry concurrent branch updates](https://github.com/mojtaba-arvin/django-api-versioning/commit/d7ac536bfeaa5b8077302d2e5cffd8da55d67523)
- [Add evidence provenance input hashing](https://github.com/mojtaba-arvin/django-api-versioning/commit/34ffa802d9acbd94edd900e35287941a7779c42a)

### 2. The package received meaningful correctness and compatibility improvements

The history shows focused regression work around Django path converters in \`api_reverse\`, invalid and boolean version values, reverse lookup ambiguity, ViewSet registration errors, lifecycle sunset parsing/time zones, and the endpoint migration command.

The installed-wheel smoke test rejects accidental imports from the source checkout, while artifact checks inspect both wheel and sdist boundaries and require the PEP 561 marker. These are stronger release checks than a passing in-tree pytest run alone.

Representative changes:
- [Validate Django path converter semantics in api_reverse](https://github.com/mojtaba-arvin/django-api-versioning/commit/723a3a44f16023bf1e133abd3eee0467a8596ccd)
- [Reject non-integer api_reverse versions](https://github.com/mojtaba-arvin/django-api-versioning/commit/6f8a5f9df30be17f2b2712529e81f1a8118e99fe)
- [Add syntax-aware endpoint migration](https://github.com/mojtaba-arvin/django-api-versioning/commit/b2c23e7ff12c1fc5f8892407ccc5283bb610f101)
- [Test the installed wheel rather than the source tree](https://github.com/mojtaba-arvin/django-api-versioning/commit/e3e25d82c2bb637b18849a3a2b35e8bf13ba1cf0)
- [Require the PEP 561 marker in distributions](https://github.com/mojtaba-arvin/django-api-versioning/commit/8f9edec517177a71fcc8dba64ee17c83f0b89221)

### 3. Security and release isolation received serious attention

The PyPI publication job was isolated from package building, trusted publishing/OIDC was introduced, and release gating was tied to real compatibility evidence. Website dependency review also caught the conflict between an earlier Astro 6 pin and later critical advisories; the branch moved to a patched Astro 7 line with patched transitive dependencies and documented the reason rather than silently downgrading security.

Representative changes:
- [Isolate PyPI publishing from package build](https://github.com/mojtaba-arvin/django-api-versioning/commit/bd47c3177ed4c770a5f9c77896426e2ddf0d0441)
- [Use patched Astro and image dependencies](https://github.com/mojtaba-arvin/django-api-versioning/commit/7b080d4a95abb159bb165fea908a110b8af60976)
- [Require the full compatibility matrix before PyPI publication](https://github.com/mojtaba-arvin/django-api-versioning/commit/ee34956f30ad3a6c61bbefcdbde75c2c0b8613e4)

### 4. The final migration behavior is safer than its early iteration

The endpoint migration utility evolved from a text-oriented approach to AST/tokenize-aware analysis. The resulting implementation avoids changing comments and string literals, skips unsupported dynamic/positional declarations, preserves source encoding, and previews changes by default. Applying rewrites requires explicit \`--write\`.

The final safety choice is sound. The history also shows that the default write behavior was changed and then reconsidered before the preview-first contract was established. CLI defaults and migration semantics should be decided against the existing contract before implementation, not toggled during successive commits.

## Inefficient or risky behaviors

### 1. Duplicate status documents caused avoidable churn

Three standalone tracking documents were repeatedly maintained and then removed as redundant:

| Document | Commits touching it | Outcome |
| --- | ---: | --- |
| \`docs/engineering/ROADMAP.md\` | 5 | Deleted as redundant |
| \`docs/website/implementation-status.md\` | 12 | Deleted as redundant |
| \`docs/development/ci-strategy.md\` | 15 | Deleted as redundant |
| **Total** | **32** | **All three removed** |

The records duplicated facts already owned by canonical workflow files, architecture/handoff documents, and \`COMPATIBILITY_REPORT.md\`. Their creation looked like process discipline, but updating the same status in multiple locations introduced synchronization work and stale-state risk. The later deletion was the right correction; not creating the duplicates would have been better.

### 2. Formatting was fragmented into many tiny commits

There were 38 commits with the \`style:\` prefix. The targeted history includes nine separate Black/isort commits in roughly 20 seconds, each changing a different file, and four individual test-module spacing commits in another short burst.

Formatting is necessary, but formatting commits should be batched across the complete changed Python scope after implementation. Per-file style commits obscure the logical implementation, inflate review history, and create unnecessary CI activity.

### 3. Generated evidence produced too many commits

The route snapshot has 31 commits with the identical title \`data: generate source-pinned Segment Lab evidence\`. Many are legitimate because source hashes, line references, or scenario outputs change. However, the snapshot also included a volatile \`generated_at\` value even though check mode intentionally ignores that field. At least one observed one-line evidence diff was consistent with timestamp-only churn.

The source pinning and hash records are valuable; committing a new timestamp when the evidence payload is byte-for-byte equivalent is not. The generator now preserves the previous timestamp whenever all non-timestamp evidence fields match. A real source, environment, scenario, or result change still refreshes the timestamp.

### 4. Automated commits were misattributed

Both \`.github/workflows/generate-evidence.yml\` and \`.github/workflows/website-lock.yml\` configured the Git author and committer as the maintainer. The GitHub API confirms that automated evidence/lockfile commits consequently appeared under the maintainer's personal identity.

That weakens provenance and makes authorship history misleading. The workflows now use the dedicated \`github-actions[bot]\` identity.

### 5. Related changes were split across commits

Three separate commits added the same \`synchronize\` pull-request event to three related workflows. This was a real functional fix, not an empty commit, but it could have been one atomic workflow change. The history also contains repeated dependency-lockfile refreshes while the Astro major version and security override strategy were being resolved. Some lockfile churn was necessary because the security decision changed; the avoidable part was discovering the compatibility/security constraint after the initial version pin.

For future work, inspect framework/security constraints before selecting the version line and change related workflow files together.

### 6. Commit identity cannot establish which actor performed the work

Every commit in the interval is attributed to the same GitHub account. Since automation itself was configured to use that account, commit metadata cannot distinguish human-written, agent-written, and bot-generated changes. This audit therefore reports observable repository behavior and workflow attribution, not unsupported claims about which model or agent authored a particular commit.

## Corrections now applied

1. **Generated evidence idempotency:** an unchanged evidence payload retains its last content-change timestamp. This prevents timestamp-only JSON diffs and unnecessary evidence commits.
2. **Correct automation provenance:** evidence-generation and website-lock workflows now commit as \`github-actions[bot]\`, not the maintainer.
3. **Commit hygiene in shared instructions:** related changes are batched; formatters run once over the complete changed scope; no-op CI-trigger commits and duplicate status trackers are prohibited.
4. **Skill-level guardrails:** Safe Checkpoint, Package Engineering, and Agent Maintenance now encode these lessons.
5. **Regression coverage:** tests verify timestamp preservation for identical evidence and timestamp refresh when the source/evidence payload changes.
6. **Agent evaluations:** new scenarios test logical commit batching, bot attribution, avoiding redundant tracker documents, and evidence regeneration idempotency.

## Remaining limitations

- This is a bounded historical review of 418 commits, not a line-by-line audit of every changed line in every commit.
- Git author metadata does not reliably identify whether a human or model authored a change.
- The Agent evaluation scenarios are acceptance prompts for human/model runs. No claim is made that comparative accuracy or token savings have been measured across models.
- Browser-level accessibility/performance and external-host smoke testing remain separate from successful static builds and were not completed by this history review.

## Reproduction references

- [Reviewed branch HEAD](https://github.com/mojtaba-arvin/django-api-versioning/commit/6060db59834d77beca8392fb9464b0ae3bd1c5ce)
- [Earlier end of the 418-commit interval](https://github.com/mojtaba-arvin/django-api-versioning/commit/56d73e53fb3b7ca67e0645134028b0d2cd0716dd)
- [History compare from the commit preceding the interval](https://github.com/mojtaba-arvin/django-api-versioning/compare/246bf3a0f725f9d97fafeaa0e83b89d3d207fea2...6060db59834d77beca8392fb9464b0ae3bd1c5ce)
