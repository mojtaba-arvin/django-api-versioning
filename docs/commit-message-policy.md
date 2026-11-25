# Commit message policy

This document is the reusable implementation contract for enforcing commit-message
quality in this repository and for adopting the same capability in other repositories.

## Policy

Every commit subject and every pull-request title (the squash-merge subject) uses:

```text
type(scope)!: lowercase imperative summary
```

- `type` is required and must be one of: `feat`, `fix`, `docs`, `test`,
  `refactor`, `style`, `perf`, `build`, `ci`, `chore`, `revert`.
- `scope` is optional. When present, use lowercase letters/digits separated by
  single `.`, `/`, or `-` characters; do not start or end with a separator.
- `!` is optional and appears immediately before `: ` to mark a breaking change.
- The summary is required, starts with a lowercase letter or digit, uses lowercase
  letters throughout, has no leading/trailing whitespace, and has no final period.
- The complete subject is at most 100 characters.

| Type | Intended use |
| --- | --- |
| `feat` | Add user-visible behavior |
| `fix` | Correct a defect |
| `docs` | Change documentation only |
| `test` | Add or change tests without production behavior changes |
| `refactor` | Restructure code without changing behavior |
| `style` | Formatting-only changes with no behavior impact |
| `perf` | Improve performance |
| `build` | Change packaging or build configuration |
| `ci` | Change continuous-integration automation |
| `chore` | Maintenance that does not fit a more specific type |
| `revert` | Revert an earlier change |

- Use imperative wording (for example, "add", "fix", "document", not "added" or
  "adding"). Imperative mood is a human writing/review convention: the validator
  deliberately does not pretend to infer English grammar with a fragile regex.
- A breaking change may be marked with `!`, a `BREAKING CHANGE: description`
  footer, or both. A footer must follow a blank line and contain a non-empty
  description. Put migration guidance in the body/footer when useful.
- The body is optional. Separate it from the subject with a blank line. The body
  explains motivation and implementation; it is not subject to lowercase rules.

Examples:

```text
feat(router): support nested route prefixes
fix(negotiation): reject malformed version headers
docs: explain request version selection
perf(registry): reduce route lookup overhead
feat(api)!: change the public routing contract

feat(api): change the public routing contract

BREAKING CHANGE: clients must send the version header.
```

## Enforcement layers

The policy is enforced at two independent points:

1. Local Git `commit-msg` hook: immediate feedback before a commit is created.
   This is convenience/defense in depth; developers can skip or fail to install it.
2. Required GitHub Actions PR check: validates every commit subject in the PR and
   the PR title. With squash merging, the PR title becomes the subject recorded on
   the target branch. Branch protection/rulesets must require the aggregate gate.

Both layers call the same Python validator. Do not duplicate the rules in shell,
YAML expressions, JavaScript, or a second validator.

## Files to add or adapt in another repository

### Required core

| Path | Purpose |
| --- | --- |
| `scripts/check_commit_message.py` | Single source of truth for validation; supports a Git message file, `--message`, and `--subjects-file`. |
| `tests/test_commit_message.py` | Unit tests for valid/invalid subjects, types, scope, length, breaking changes, and PR subject lists. Adapt imports/test runner to the repository. |
| `.pre-commit-config.yaml` | Local `commit-msg` hook invoking the script. Merge into an existing file; never overwrite other hooks. |
| `.github/workflows/pull-request-gate.yml` (or existing PR workflow) | CI validation of PR title and all commit subjects. Integrate into the existing required workflow rather than creating competing required checks. |
| Repository settings | Require the PR gate status on the protected target branch; use squash merge if relying on the PR title as the final commit subject. |

### Recommended developer experience and documentation

| Path | Purpose |
| --- | --- |
| `.gitmessage` | Optional Git commit template with format, allowed types, and body/footer guidance. |
| `CONTRIBUTING.md` | Explain policy, examples, local installation, validation command, and squash-title behavior. |
| `AGENTS.md` / `CLAUDE.md` / editor instructions | Optional short pointer to the canonical policy; avoid copying a second divergent rule list. |

## Adoption procedure

1. Inspect the existing test runner, Python version, directory conventions, pre-commit
   configuration, workflows, merge strategy, and branch protection. Preserve existing
   tooling and hooks.
2. Add the validator and tests. Keep the allowed type list and syntax in one place
   in code; keep the human-facing explanation in the policy document and link to it.
3. Merge the local hook into the existing `.pre-commit-config.yaml`:

   ```yaml
   repos:
     - repo: local
       hooks:
         - id: conventional-commit-message
           name: Validate Conventional Commit message
           entry: python scripts/check_commit_message.py
           language: system
           stages: [commit-msg]
           pass_filenames: true
           always_run: true
   ```

   If the repository does not use pre-commit, an equivalent executable
   `.git/hooks/commit-msg` script can invoke the Python validator with
   `"$1"`. Prefer pre-commit for reproducible installation and maintenance.
4. Install the hook in each clone:

   ```bash
   python -m pip install pre-commit
   pre-commit install --hook-type commit-msg
   ```

   If pre-commit is already a development dependency, do not install it twice.
   The `.gitmessage` template is optional and must be enabled per clone:

   ```bash
   git config commit.template .gitmessage
   ```

5. Add the PR checks to the existing workflow, triggered on `pull_request`
   events including `opened`, `edited`, `reopened`, and `synchronize`.
   Check out the PR head, set up the required Python version, validate the title
   using `--message`, fetch all PR commits with pagination, extract each first
   message line, and validate them with `--subjects-file`. Use the GitHub token
   with read-only `pull-requests: read` permission. Avoid interpolating untrusted
   PR title text directly into shell source; pass it through an environment variable.
6. Make the PR validation job a dependency of the aggregate required gate. Ensure
   the aggregate gate fails when validation fails; a skipped or unrelated green
   job must not mask a failed validation.
7. Configure branch protection/rulesets to require the aggregate PR gate. Local
   hooks alone are not enforcement because they can be bypassed.
8. Document the policy and installation commands in `CONTRIBUTING.md`. Keep
   `AGENTS.md` or other agent instructions as pointers to this canonical document.
9. Run the focused unit tests, the repository's normal lint/test commands, and
   validate the workflow YAML. Test both valid and invalid examples locally:

   ```bash
   python scripts/check_commit_message.py --message "fix(api): reject malformed headers"
   python scripts/check_commit_message.py --message "Fix API"
   pytest tests/test_commit_message.py
   ```

## CI integration example

Insert these steps into the existing PR validation job after checkout and Python
setup. Do not blindly copy a standalone workflow if the repository already has a
single required aggregate gate.

```yaml
- name: Validate squash-merge title
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: python scripts/check_commit_message.py --message "$PR_TITLE"

- name: Fetch and validate all PR commit subjects
  env:
    GH_TOKEN: ${{ github.token }}
    GH_PROMPT_DISABLED: "1"
  run: |
    gh api --paginate \
      "repos/${GITHUB_REPOSITORY}/pulls/${{ github.event.pull_request.number }}/commits?per_page=100" \
      --jq '.[].commit.message | split("\n")[0]' \
      > "$RUNNER_TEMP/commit-subjects.txt"
    python scripts/check_commit_message.py \
      --subjects-file "$RUNNER_TEMP/commit-subjects.txt"
```

## Operational notes

- Existing history is not rewritten. The policy applies to new commits and PR titles.
- If the PR workflow targets a branch other than `main`, adjust its branch filter
  and protect that actual target branch.
- If merge commits or rebase merges are enabled, decide explicitly how final
  integration commits are named and checked. The PR-title-as-final-subject guarantee
  applies to squash merges.
- For non-Python repositories, keep the policy but port the small validator to an
  already-supported runtime or invoke Python as a documented development dependency.
  Do not add a heavyweight commit-lint framework solely for this check.
- Do not silently add new types. Update the validator, tests, template, and docs
  together when changing the allowed type set.
