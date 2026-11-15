# Compatibility Report

**Package version:** 0.3.7 (`pyproject.toml`)  
**Branch:** `audit/comprehensive-package-review`  
**Verified source/test revision:** `e9e1c545aa6bfe3f3ee67a174c11a8d580d7eb21`  
**Package source baseline:** `035a4054f3e0d7e3e47adfeef1889e89e0660443`  
**Latest matrix workflow commit:** `e9e1c545aa6bfe3f3ee67a174c11a8d580d7eb21`  
**Full compatibility run:** [GitHub Actions #24](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43760780144) — **15/15 test environments and lint passed**

The matrix workflow executed at commit `e9e1c545aa6bfe3f3ee67a174c11a8d580d7eb21`. The package implementation is unchanged from source baseline `035a4054f3e0d7e3e47adfeef1889e89e0660443`; the test revision adds a regression test proving that `api_reverse()` uses a custom path converter's `to_url()` method. The matrix validator also confirmed that all 16 tox environments (15 test environments plus lint) match the explicit GitHub Actions matrix.

## Test matrix

Every test environment passed **247 unit tests**, **258 Django integration tests**, and reported **96% package coverage**. DRF 3.18.3 was the resolved development/test dependency.

| Django | Python versions tested | Environments |
| --- | --- | ---: |
| 4.2 | 3.10, 3.11, 3.12 | 3 |
| 5.2 | 3.10, 3.11, 3.12, 3.13, 3.14 | 5 |
| 6.0 | 3.12, 3.13, 3.14 | 3 |
| 6.1 | 3.12, 3.13, 3.14, 3.15 | 4 |
| **Total** | **15 combinations** | **15** |

The separate lint environment passed all three checks:

- flake8
- `black --check .`
- `isort --check-only .`

## Package artifact verification

[Python package artifacts run #83](https://github.com/mojtaba-arvin/django-api-versioning/actions/runs/43760780109) completed successfully. It built the wheel and source distribution, passed strict Twine metadata validation, checked distribution contents, installed the wheel in isolation, and verified that all 15 packaged files matched the source tree.

## Declared requirements vs. verified combinations

The package metadata declares:

- Python `>=3.10`
- Django `>=4.2`
- Django REST Framework is optional and is not a core runtime dependency.

The matrix explicitly verifies the combinations in the table above. Django 5.0 and 5.1 are not included. Python/Django combinations absent from the table are **not verified by this report**; do not infer support from classifiers or from a broader minimum-version declaration.

The matrix ran on GitHub-hosted Ubuntu runners. This report does not claim separate Windows/macOS verification or a fully pinned dependency resolution for every environment. DRF 3.18.3 is the observed resolved version for this run, not a future version guarantee.

## Interpretation

This report records actual automated test and artifact results for the linked revisions. It is not a claim that every possible Python/Django/DRF combination, operating system, or deployment configuration has been tested.
