# Governance and maintenance continuity

**Last reviewed:** 2026-11-20  
**Current state:** This is a maintainer-led project with one primary maintainer. No second project owner or named successor is designated yet. There is no guaranteed response or security-remediation SLA.

This document defines how the project can add maintainers, share release responsibility, or transfer stewardship without sharing personal account credentials. It is a process, not a promise that a successor has already been appointed.

## 1. Project decision-making

- The project is open to contributions through issues and pull requests. Technical changes must follow `CONTRIBUTING.md`, preserve the public contract, and pass the required `PR gate`.
- Package runtime behavior, tests, changelog, docs, and release automation are maintained together. A release requires the normal review and verification process; a maintainer role is not permission to bypass branch protection or release checks.
- The primary maintainer coordinates releases while the project has a single maintainer. A second maintainer should progressively take on review, compatibility-matrix, documentation, and release-verification duties.
- Contributors can disagree on design. Decisions should be recorded in issues, PR discussions, or an ADR when they affect the public architecture or compatibility contract.
- No contributor is expected to accept a maintenance role. A role should match the person's availability and intended level of responsibility.

## 2. Contributor-to-maintainer trust ladder

Access is granted gradually and only to the minimum level needed:

1. **Contributor:** reports issues, improves docs/tests, and submits pull requests from a fork. No repository write access is needed.
2. **Regular reviewer:** demonstrates repeated, constructive reviews and understands the public routing contract. The maintainer may request reviews on relevant PRs.
3. **Project maintainer:** has an established contribution history, can diagnose regressions, understands compatibility and release checks, and agrees to help with issue triage and review. Grant the least-privileged GitHub role that supports the agreed work.
4. **Release maintainer:** can complete the documented release checklist and is added to PyPI as a project Maintainer, which permits uploads but not project-collaborator administration or destructive project actions.
5. **Project owner / successor:** receives GitHub repository administration and PyPI Owner privileges only after an explicit handover agreement. PyPI Owner can manage collaborators and project files/releases; this is full administrative trust, not an ordinary contributor role.

The primary maintainer should seek at least one active second maintainer and, once trust is established, a second PyPI Owner. Until then, downstream users should treat this package as a dependency they can replace if maintenance becomes unavailable.

## 3. Planned handover

A normal handover should be a staged process, not a password or token exchange.

### Phase A — Prepare

- The outgoing maintainer identifies the proposed successor(s), expected responsibilities, and whether the handover is temporary or permanent.
- Review open issues, pull requests, active security reports, supported Python/Django/DRF combinations, pending releases, known limitations, and any unmerged or experimental work.
- Verify the release workflow, GitHub environments, tag rulesets, branch rulesets, PyPI Trusted Publisher configuration, and package metadata.
- Document operational knowledge that currently exists only with the outgoing maintainer. Do not store passwords, recovery codes, private keys, or API tokens in this repository.

### Phase B — Grant and prove access

- Invite the incoming maintainer to the repository using their own GitHub account and enable required two-factor authentication.
- Start with a contributor/reviewer role. Increase repository permissions only after the responsibilities and trust level are clear.
- Add the incoming release maintainer as a PyPI Maintainer for upload capability. Only an established successor should be made a PyPI Owner.
- Trusted Publishers are configured on the PyPI project, not attached to an individual PyPI collaborator. Review the registered owner, repository, workflow file, and `pypi` environment. Do not create a long-lived API token as a handover shortcut.
- Have the incoming release maintainer complete a supervised release-readiness exercise: run the local preflight, inspect a release candidate, validate the exact commit's CI evidence, and explain how to resume an interrupted release. Do not publish an extra package version just to test access.

### Phase C — Transfer or share stewardship

Choose one explicit outcome:

**Shared stewardship:** keep the repository under the current GitHub account, retain the current PyPI project, and keep at least two trusted maintainers active. The original maintainer may remain the primary owner while the second maintainer handles routine reviews/releases.

**Transfer to a GitHub organization:** use GitHub's supported repository-transfer flow after selecting an organization with suitable ownership, billing, two-factor, security, and repository-creation policies. Repository transfer requires administrator permission on the source and permission to create repositories in the target organization. Verify GitHub Pages separately: repository redirects do not automatically redirect the old GitHub Pages site. Update the PyPI Trusted Publisher configuration to match the new repository owner/name and the approved workflow, then test a release through the protected environment.

**Transfer PyPI ownership:** add the successor as a PyPI Owner first. Confirm that they can manage collaborators, verify the Trusted Publisher configuration, and complete a release. Only after all access has been verified should the outgoing owner remove their own PyPI ownership. PyPI supports multiple Owners; do not leave the project with zero Owners.

### Phase D — Close the handover

- Update the maintainer list, repository links, PyPI project roles, security contact, README badges/metadata, release instructions, website configuration, and any external publisher registration.
- Review and revoke obsolete collaborator access and deploy keys. Review Trusted Publisher registrations separately; removing a PyPI collaborator does not remove a Trusted Publisher.
- Record the handover date, new responsibilities, and any known limitations in a public issue or release note. Never record private contact details or account recovery material.
- Confirm the new maintainer can access the issue tracker, review PRs, observe Actions, administer the release environment, and publish using Trusted Publishing without a personal long-lived token.

## 4. If the primary maintainer becomes unavailable

1. Do not bypass rulesets, substitute credentials, or publish an unverified build.
2. An existing project owner should triage urgent bugs and security reports, and make only minimal, tested maintenance releases.
3. If no project owner is available, contributors should keep work in forks and open PRs/issues; do not assume that an open PR grants transfer rights.
4. If the project becomes dormant, mark its maintenance status clearly and keep the published source/release history available. Do not delete the PyPI project or yank old releases merely because active maintenance has stopped.
5. Consider a community stewardship path when a qualified maintainer cannot be found. Django Commons accepts applications from projects that benefit the Django ecosystem; its process requires a prospective contributor to join first and then open a transfer-project issue. Jazzband is another option for established projects with outside contributions and an orderly handover. Neither organization is an automatic successor; acceptance is determined by its own criteria.
6. If no sustainable steward is available, archive the repository with a clear notice rather than leaving users to infer that new issues or security fixes will be handled.

## 5. Review cadence

- Review maintainer access, PyPI collaborators, Trusted Publisher registrations, and release permissions at least twice a year and after every ownership change.
- Review open security reports and releases before changing maintainer responsibility.
- Keep at least two people familiar with the package's route registration, middleware, DRF integration, compatibility matrix, and release process.
- The primary maintainer should periodically confirm whether the project remains actively maintained. If not, update the project status and invite a successor before disappearing.

## 6. Platform references

- [GitHub: repository transfers](https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository)
- [GitHub: personal repository collaboration and successors](https://docs.github.com/en/repositories/creating-and-managing-repositories/access-to-repositories)
- [GitHub: organization repository roles](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization)
- [PyPI: managing project collaborators](https://docs.pypi.org/project-management/managing-collaborators/)
- [PyPI: adding a Trusted Publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
- [PyPI: Trusted Publisher security model](https://docs.pypi.org/trusted-publishers/security-model/)
- [Django Commons: project stewardship](https://django-commons.org/)
- [Django Commons: project maintenance governance](https://django-commons.org/governance/project-maintenance/)
- [Jazzband: project transfer and participation guidelines](https://jazzband.co/about/guidelines)
