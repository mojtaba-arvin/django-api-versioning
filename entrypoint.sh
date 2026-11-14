#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${TASK:-}" == "publish" ]]; then
  echo "Building package..."
  python -m build

  echo "Checking package..."
  python -m twine check dist/*

  echo "Publishing to PyPI..."
  : "${PYPI_API_TOKEN:?PYPI_API_TOKEN must be set for publishing}"
  python -m twine upload dist/* \
    --repository-url https://upload.pypi.org/legacy/ \
    -u "__token__" \
    -p "$PYPI_API_TOKEN"
else
  if [[ "${RUN_PRE_COMMIT:-false}" == "true" ]]; then
    pre-commit run --all-files
  fi

  echo "Running package unit tests..."
  python -m pytest --capture=no tests

  echo "Running Django integration tests..."
  python -m pytest --capture=no -c integration_test_project/pytest.ini integration_test_project

  echo "Building and validating PyPI artifacts..."
  DIST_DIR="$(mktemp -d)"
  trap 'rm -rf "$DIST_DIR"' EXIT
  python -m build --outdir "$DIST_DIR"
  python -m twine check --strict "$DIST_DIR"/*
  python scripts/verify_distribution_contents.py "$DIST_DIR"
fi
