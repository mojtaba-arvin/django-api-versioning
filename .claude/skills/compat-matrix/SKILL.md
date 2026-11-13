# Skill: Compatibility Matrix - django-api-versioning

Full Python × Django matrix with unit AND integration tests.
One empty commit + push per row. No side files — git commit
messages ARE the state. Resume reads `git log`.

Run only before a release.

## Preconditions
- Clean working tree. If dirty: `/safe-checkpoint` first.

## Procedure

### 1. Install Pythons

```bash
for v in 3.10 3.11 3.12 3.13 3.14 3.15; do uv python install "$v"; done
```

### 2. Write the runner

```bash
cat > /tmp/matrix.sh << 'EOF'
#!/usr/bin/env bash
set -uo pipefail
REPO=/home/repl/django-api-versioning
cd "$REPO"
PY_VERSIONS=(3.10 3.11 3.12 3.13 3.14 3.15)
DJ_VERSIONS=(4.2 5.0 5.1 5.2 6.0 6.1)
FAIL_STREAK=0

row_done() {
  git log --format=%s | grep -qE "^test: matrix PY=$1 DJ=$2 "
}

push_row() {
  if .claude/push.sh >/tmp/push.log 2>&1; then
    FAIL_STREAK=0
  else
    FAIL_STREAK=$((FAIL_STREAK+1))
    echo "PUSH FAILED ($FAIL_STREAK): $(tail -1 /tmp/push.log)" >&2
    [ "$FAIL_STREAK" -ge 3 ] && { echo "HALT: 3 consecutive push failures" >&2; exit 4; }
  fi
}

commit_row() {
  git commit --allow-empty -q -m "$1"
  push_row
}

for PY in "${PY_VERSIONS[@]}"; do
  VENV=/tmp/env-$PY
  if ! uv venv "$VENV" --python "$PY" >/dev/null 2>&1; then
    for DJ in "${DJ_VERSIONS[@]}"; do
      row_done "$PY" "$DJ" && continue
      commit_row "test: matrix PY=$PY DJ=$DJ venv-failed"
    done
    continue
  fi

  for DJ in "${DJ_VERSIONS[@]}"; do
    row_done "$PY" "$DJ" && { echo "SKIP $PY×$DJ"; continue; }

    if ! uv pip install --python "$VENV/bin/python" \
         -e "$REPO" "Django==$DJ.*" pytest pytest-django djangorestframework \
         >/tmp/install-$PY-$DJ.log 2>&1; then
      REASON=$(tail -1 /tmp/install-$PY-$DJ.log | tr -d '\n' | head -c 100)
      commit_row "test: matrix PY=$PY DJ=$DJ incompatible | $REASON"
      continue
    fi

    ACTUAL=$("$VENV/bin/python" -c "import django;print('.'.join(map(str,django.VERSION[:2])))")

    LOGU=/tmp/pytest-unit-$PY-dj$DJ.log
    LOGI=/tmp/pytest-integ-$PY-dj$DJ.log
    "$VENV/bin/python" -m pytest "$REPO/tests/" -q >"$LOGU" 2>&1
    "$VENV/bin/python" -m pytest "$REPO/integration_test_project/tests/" -q >"$LOGI" 2>&1

    parse() { grep -E "passed|failed" "$1" | tail -1; }
    SU=$(parse "$LOGU"); SI=$(parse "$LOGI")
    PU=$(echo "$SU" | grep -oP '\d+(?= passed)'  || echo 0)
    FU=$(echo "$SU" | grep -oP '\d+(?= failed)'  || echo 0)
    PI=$(echo "$SI" | grep -oP '\d+(?= passed)'  || echo 0)
    FI=$(echo "$SI" | grep -oP '\d+(?= failed)'  || echo 0)
    ST=ok; { [ "$FU" -gt 0 ] || [ "$FI" -gt 0 ]; } && ST=FAIL
    commit_row "test: matrix PY=$PY DJ=$DJ $ST unit=$PU/$FU integ=$PI/$FI actual=$ACTUAL"
  done
  rm -rf "$VENV"
done
EOF
chmod +x /tmp/matrix.sh
```

### 3. Run

```bash
/tmp/matrix.sh 2>&1 | tee /tmp/matrix-run.log
```

Each row tests unit + integration. Resume after disconnect:
re-run the same command. `row_done` reads `git log` and skips
completed rows.

### 4. Generate `COMPATIBILITY_REPORT.md` from git log

```bash
git log --reverse --format=%s | grep '^test: matrix ' > /tmp/matrix-rows.txt
```

Parse into a table:

```markdown
# Compatibility Report

**Date**: <date -u +%Y-%m-%d>
**Source**: `git log` commits matching `test: matrix` (actual test runs)

## Python × Django (unit + integration)

| Python | Django | Status | Unit pass | Unit fail | Integ pass | Integ fail | Detail |
|--------|--------|--------|-----------|-----------|------------|------------|--------|

## Verified platforms
- Python: <versions with ≥1 status=ok>
- Django: <versions with ≥1 status=ok>
- DRF: <from `rest_framework.VERSION` in the last successful install log>
- OS: <uname -sm output>

## Untested / incompatible
Rows marked `incompatible` or `venv-failed`. Do NOT label them
SUPPORTED, CERTIFIED, or "compatible via type hints".
```

Commit:

```bash
git add COMPATIBILITY_REPORT.md
git commit -m "docs: update compatibility report from verified matrix"
.claude/push.sh
```

## Never
- Never create TSV or side files — commit messages are the log.
- Never skip `row_done` — resumed sessions must not re-run rows.
- Never claim a row passed unless its commit subject says `ok`.
- Never skip integration tests in a cell.
- Never carry over unverified "SUPPORTED" claims.
