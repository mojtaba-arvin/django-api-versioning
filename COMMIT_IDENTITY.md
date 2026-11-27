# Commit identity and attribution policy

For maintainer-directed AI-assisted implementation, use Git author `Mojtaba Arvin <m.arvin@live.com>`. This identity was checked against the authenticated GitHub profile (`mojtaba-arvin`, matching name and email). Do not use model, assistant, AI-agent, Copilot, Claude, Cursor, Codex, Gemini, generic agent, or bot identities as the author. Do not add bot/AI `Co-authored-by` trailers.

Include `<!-- maintainer-directed-ai-work -->` in the PR body for owner-authorized AI-assisted work. This machine-readable marker requires at least one commit whose GitHub author resolves to `mojtaba-arvin` and whose exact author name/email match the verified maintainer identity. Other human contributor identities remain unchanged. Disclose AI assistance in the PR description; the marker does not claim the maintainer personally typed every line.

Preserve every real human contributor's original author name/email. Never relabel another person as the maintainer and never rewrite historical commits.

Genuine GitHub Actions/Dependabot automation may author a commit only when all of the following hold: the PR has the explicit `allow-automation-commits` label; GitHub resolves the commit author to the exact `github-actions[bot]` or `dependabot[bot]` account with Bot account type; and the commit's author name/email match that account's canonical GitHub noreply identity. The exception does not cover agent-written implementation or other bot accounts. Bot co-author trailers remain prohibited. The commit author is the attribution identity; a distinct `web-flow` committer does not turn a human-authored commit into a bot-authored commit.

Convenience defaults (not enforcement):

```sh
git config --global user.name "Mojtaba Arvin"
git config --global user.email "m.arvin@live.com"
```

`scripts/check_commit_identity.py` checks all PR commits, rejects bot/agent authors and bot co-author trailers, permits only the explicitly labelled canonical GitHub Actions/Dependabot author identities, and enforces the maintainer identity when the marker is present. The check runs inside the existing `PR gate` workflow, so it contributes to the repository's sole required status context. It uses the existing read-only pull-request token and GitHub API metadata; it introduces no runtime dependencies.

The PR gate follows the repository's existing pull-request validation model and checks out the proposed PR head. It is not a trusted-base `pull_request_target` workflow. Do not describe this check as independent of PR-supplied workflow/source changes; the protected `PR gate` remains the required merge gate.

Git metadata is self-asserted: validation cannot prove who physically typed code or detect every disguised agent identity. Verify the email association and disclose AI assistance transparently.

Never amend, rebase, or cherry-pick a contributor's work under the maintainer identity. Preserve the contributor's original author fields and add a separate maintainer-authored commit for AI-assisted changes.
