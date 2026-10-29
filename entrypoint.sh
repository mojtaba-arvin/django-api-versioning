#!/bin/bash

if [ "$TASK" = "publish" ]; then
  echo "Building package..."
  python -m build

  echo "Checking package..."
  python -m twine check dist/*

  echo "Publishing to PyPI..."

  python -m twine upload dist/* \
    --repository-url https://upload.pypi.org/legacy/ \
    -u "__token__" \
    -p "$PYPI_API_TOKEN"
else
  if [ "$RUN_PRE_COMMIT" == "true" ]; then
    pre-commit run --all-files
  fi
  pytest --capture=no
fi
