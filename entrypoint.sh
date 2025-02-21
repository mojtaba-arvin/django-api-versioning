#!/bin/bash

if [ "$TASK" = "publish" ]; then
  echo "Publishing to PyPI..."
  python setup.py sdist bdist_wheel
  twine upload dist/* --repository-url https://upload.pypi.org/legacy/ -u "__token__" -p "$PYPI_API_TOKEN"
else
  pre-commit run --all-files && pytest --capture=no
fi
