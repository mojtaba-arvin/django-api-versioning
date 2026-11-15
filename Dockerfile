ARG PYTHON_VERSION=3.15
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
# BuildKit keeps downloaded wheels between local image builds. CI installs only
# the minimal test dependencies directly and does not build this dev image.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r requirements-dev.txt

COPY .pre-commit-config.yaml ./
# Initialise a repository for optional pre-commit runs. Hook environments are
# installed lazily only when RUN_PRE_COMMIT=true; normal builds do not need them.
RUN git init .

COPY . .

RUN chmod +x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
