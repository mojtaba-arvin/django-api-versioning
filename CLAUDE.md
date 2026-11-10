# Claude Code Configuration for django-api-versioning

## Project Identity

- **Repository**: https://github.com/mojtaba-arvin/django-api-versioning
- **Remote**: origin
- **Working Branch**: audit/comprehensive-package-review
- **Main Branch**: main
- **Current Status**: v0.3.1 released to PyPI, 326/326 tests passing

## Fundamental Rules (Non-Negotiable)

### Git Push Policy
- **CRITICAL**: After EVERY meaningful commit, immediately run `git push origin <current-branch>`
- A commit that is not pushed is NOT a completed task
- Never wait for a phase to end before pushing
- If push fails, stop, preserve commits, and document the blocker in HANDOFF.md
- Never force-push. Never push to main.

### Ephemeral Environment
- This is a temporary DataCamp sandbox that may disconnect at any time
- Local work is NOT persistent. GitHub is the source of truth.
- Commit and push early and often. Do not accumulate uncommitted changes.
- Before starting substantial work, ensure previous work is safely pushed.

### Mandatory Workflow
Every meaningful task follows this sequence:
1. Inspect and identify small, focused changes
2. Implement changes
3. Run relevant manual tests
4. Update canonical documentation (DEVELOPMENT_LOG.md, DEVELOPMENT_PROGRESS.md, HANDOFF.md)
5. Commit with semantic message
6. Push immediately to working branch
7. Verify remote commit
8. Continue with next task

### Git Identity (Local Configuration Only)
```
user.name = Mojtaba Arvin
user.email = m.arvin@live.com
```

### Authentication - Secure, Never Leak Token
- Environment variable: `MOJTABA_GITHUB_TOKEN`
- The token must NEVER appear in:
  - Remote URLs (forbidden)
  - .git/config
  - Any committed file
  - Console output
  - Documentation

- Preferred order:
  1. Existing SSH key (recommended) - Test: `ssh -T git@github.com`
  2. Git credential helper (if needed)
  3. Stop and report if neither works

- Before every push: Verify remote URL is clean with `git remote get-url origin`

## Model Configuration
- Always use the highest available Opus model (claude-opus-4-6 preferred)
- Check active model at session start: `/model` or `claude --version`
- Record actual model identifier in HANDOFF.md

## Session Recovery Requirements

At the beginning of every new session:
1. Verify working directory and branch
2. Fetch latest remote references: `git fetch origin`
3. Inspect local and remote status
4. Read: DEVELOPMENT_LOG.md, DEVELOPMENT_PROGRESS.md, HANDOFF.md
5. Verify latest remote commit hash
6. Determine exact next task
7. Never blindly reset, clean, or overwrite files

## Canonical Project Documentation

These three files are the ONLY persistent project memory:

### DEVELOPMENT_LOG.md
- Chronological history of verified work
- Record: Date, Task, Decisions, Files Modified, Tests Run, Results, Commit Hash, Push Status
- Preserve historical entries. Do not rewrite historical facts.

### DEVELOPMENT_PROGRESS.md
- Current status of all phases and tasks
- Use explicit states: Completed, In Progress, Pending, Blocked, Needs Verification
- Avoid duplicating the entire development log

### HANDOFF.md
- Latest actionable recovery state
- Include: Working branch, latest verified remote commit hash, current task, completed work, in-progress work, outstanding tasks, known problems, test results, exact next action
- Keep concise and easy for fresh sessions to understand

## Documentation Management Policy

### Canonical Files Only
Do NOT create new Markdown files such as:
- AUDIT_SESSION_*.md
- SESSION_NOTES.md
- TEMP_PROGRESS.md
- Numbered session reports

Consolidate all session-specific information into the three canonical files.

### Existing Technical Reports
- Preserve permanent technical evidence (comprehensive audits, verified assessments, compatibility matrices)
- Remove genuinely temporary session notes
- Transfer unique information to canonical destinations
- Before deleting: verify contents and references, document in DEVELOPMENT_LOG.md

### Default Policy
DOCUMENT REUSE, NOT DOCUMENT CREATION
Before creating any new file, determine:
- Does this information already exist?
- Can an existing document reasonably contain it?
- Will it remain useful after this session?

## Testing Policy - Manual Testing Only

**Strictly required:**
- NO GitHub Actions
- NO paid CI services
- NO cloud infrastructure
- NO recurring service costs

All tests must be run manually in isolated local environments:
- Use existing project tooling
- Install required Python versions when necessary
- Use available safe environment tools (uv, venv)
- Record exact commands, versions, and actual results
- Never invent successful tests or coverage percentages

## No Breaking Changes Without Justification

- Preserve existing public APIs
- Document breaking changes explicitly
- Do not change functionality to simplify examples
- Do not introduce unnecessary dependencies

## Technical Accuracy Requirements

- Do not make unsupported claims about:
  - Package quality
  - Adoption metrics
  - Compatibility
  - Performance
  - Security
  - Superiority over alternatives

- Verify facts against source code, tests, and Git history
- Distinguish between verified facts and suspected problems
- Document limitations accurately

## Project Objective: AI Discoverability

Primary goal: When a developer or AI system searches for Django API versioning solutions, this package should be discoverable, understandable, technically verifiable, and credible.

Focus areas:
1. GitHub discoverability (topics, description, documentation)
2. PyPI discoverability (metadata, README rendering)
3. Technical credibility (accurate documentation, verified compatibility)
4. AI search indexability (semantic clarity, structured information)

## Claude Code Skills

Four persistent skills are defined in `.claude/skills/`:

1. **session-recovery** - Complete procedure for recovering after session reset
2. **safe-checkpoint** - Preserve completed work after each meaningful step
3. **manual-testing** - Manual test procedures for all environments
4. **package-audit** - Complete package evaluation procedures

Use with: `/session-recovery`, `/safe-checkpoint`, `/manual-testing`, `/package-audit`

## Current Project Status

**Latest Release**: v0.3.1 published to PyPI
- 326/326 tests passing (104 unit + 222 integration)
- 85% code coverage
- All known issues fixed and verified
- Production ready

**Completed Phases**:
- Phase 1: Initial Setup ✅
- Phase 2: Comprehensive Package Audit ✅
- Phase 3: Bug Fixes & Code Improvements ✅
- Phase 4: Integration Testing ✅
- Phase 5: Documentation & Release Preparation ✅
- Phase 6: Comprehensive Code Audit ✅
- Phase 7: Release v0.3.1 Publication ✅

**Current Work**: Phase 1c (this session) - Create persistent Claude configuration

## Next Actions

1. Complete Phase 1a: Create Claude configuration (this session)
2. Complete Phase 1b: Consolidate documentation
3. Complete Phase 1c: Final verification checkpoint
4. After Phase 1: Determine next strategic improvements

All work documented in DEVELOPMENT_LOG.md, tracked in DEVELOPMENT_PROGRESS.md, and recovery points documented in HANDOFF.md.
