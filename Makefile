.PHONY: release website-check test-unit test-integration test-all

# Run the package's unit suite with the repository's standard fast defaults.
PYTHON ?= python
PYTEST_ARGS ?= --maxfail=1 --disable-warnings -q
INTEGRATION_PYTEST_ARGS ?=

test-unit:
	$(PYTHON) -m pytest $(PYTEST_ARGS) tests

# Keep integration settings explicit and separate from package unit settings.
test-integration:
	$(PYTHON) -m pytest $(PYTEST_ARGS) $(INTEGRATION_PYTEST_ARGS) -c integration_test_project/pytest.ini integration_test_project

# Run both suites in order while preserving caller-supplied pytest options.
test-all:
	$(MAKE) --no-print-directory test-unit PYTHON="$(PYTHON)" PYTEST_ARGS="$(PYTEST_ARGS)"
	$(MAKE) --no-print-directory test-integration PYTHON="$(PYTHON)" PYTEST_ARGS="$(PYTEST_ARGS)" INTEGRATION_PYTEST_ARGS="$(INTEGRATION_PYTEST_ARGS)"

# Run the website's complete local verification pipeline.
website-check:
	@pnpm --dir website install --frozen-lockfile
	@pnpm --dir website run format:check
	@pnpm --dir website run typecheck
	@pnpm --dir website test
	@pnpm --dir website run build
	@pnpm --dir website run test:dist:root
	@pnpm --dir website run test:dist:subpath

# Bootstrap the repository before loading the release implementation. This
# prevents Bash from continuing with an outdated maintain.sh after a self-update.
release:
	@bash scripts/release_bootstrap.sh
