#!/bin/bash

if [ "$TASK" = "publish" ]; then
  echo "Publishing to PyPI..."
  python setup.py sdist bdist_wheel
  twine upload dist/* --repository-url https://upload.pypi.org/legacy/ -u "__token__" -p "$PYPI_API_TOKEN"
else
  if [ "$RUN_PRE_COMMIT" == "true" ]; then
    pre-commit run --all-files
  fi
  pytest --capture=no
fi
