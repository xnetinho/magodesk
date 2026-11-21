#!/usr/bin/env bash
# Merge the newest rustdesk/rustdesk into THIS checkout, only to see whether our rules still fit it.
#   magodesk/preview_merge.sh
# It rewrites the working tree and makes a local merge commit: run it only in a throwaway checkout
# (the daily check does). It never pushes. Outputs, for the workflow: new=<commits>, up=<short sha>,
# merge=none|ok|conflict, and the conflicting files in $GITHUB_STEP_SUMMARY when the merge fails.
set -uo pipefail
if [ "${GITHUB_ACTIONS:-}" != "true" ] && [ "${MAGODESK_PREVIEW:-}" != "1" ]; then
  echo "refusing: this changes the working tree. Run it in CI, or set MAGODESK_PREVIEW=1 in a throwaway checkout." >&2
  exit 2
fi
out="${GITHUB_OUTPUT:-/dev/null}"; sum="${GITHUB_STEP_SUMMARY:-/dev/null}"
git remote get-url upstream >/dev/null 2>&1 || git remote add upstream https://github.com/rustdesk/rustdesk.git
git fetch --quiet upstream master || { echo "could not fetch upstream" >&2; exit 3; }
new=$(git rev-list --count HEAD..upstream/master)
up=$(git rev-parse --short upstream/master)
echo "new=$new" >> "$out"; echo "up=$up" >> "$out"
if [ "$new" = 0 ]; then
  echo "merge=none" >> "$out"
  echo "Upstream has nothing new ($up). Checked the tree as it is." >> "$sum"
  exit 0
fi
git config user.name "magodesk-check"; git config user.email "magodesk-check@users.noreply.github.com"
if git merge --no-edit --quiet upstream/master; then
  echo "merge=ok" >> "$out"
  echo "Upstream has $new new commit(s) up to \`$up\`. Simulated merge: no conflict. Checked the merged tree." >> "$sum"
  git submodule update --init --recursive --quiet || true
  exit 0
fi
files=$(git diff --name-only --diff-filter=U)
git merge --abort
echo "merge=conflict" >> "$out"
{ echo "Upstream has $new new commit(s) up to \`$up\`. The simulated merge has CONFLICTS in:"; echo; echo "$files" | sed 's/^/- `/;s/$/`/'; } | tee -a "$sum"
exit 1
