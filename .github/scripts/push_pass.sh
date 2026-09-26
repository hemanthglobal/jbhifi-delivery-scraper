#!/usr/bin/env bash
# Called by scraper.py after every pass (JB_PASS_HOOK) inside GitHub Actions.
# Copies this run's raw files + analysis export (not screenshots) to the
# repo's `data` branch under <run_id>/ and pushes. Additive only.
set -euo pipefail
SRC="${JB_OUT_DIR}"
D="${RUNNER_TEMP:-/tmp}/databranch"
URL="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
if [ ! -d "$D/.git" ]; then
  if ! git clone -q --depth 1 --branch data "$URL" "$D" 2>/dev/null; then
    rm -rf "$D"; mkdir -p "$D"; cd "$D"; git init -q; git checkout -q --orphan data
    git remote add origin "$URL"; echo "Collected data, one folder per run_id." > README.md; cd - >/dev/null
  fi
fi
mkdir -p "$D/$JB_RUN_ID"
rsync -a --exclude screenshots "$SRC/" "$D/$JB_RUN_ID/"
cd "$D"
git add -A
git -c user.name="jbhifi-collector" -c user.email="actions@users.noreply.github.com" \
  commit -q -m "${JB_RUN_ID} after slot ${JB_SLOT}" || { echo "nothing new"; exit 0; }
for i in 1 2 3; do
  if git push -q origin data 2>/dev/null; then echo "pushed ${JB_RUN_ID} slot ${JB_SLOT}"; exit 0; fi
  git pull -q --rebase origin data || true; sleep 5
done
echo "push failed"; exit 1
