#!/usr/bin/env bash
# Publish site/ to the gh-pages branch, which GitHub Pages serves at
# https://aaryavvatts-lab.github.io/neuroswitch/
#
# This exists because Vercel deploys to the neuroswitch project return 403,
# so pushing to main alone never reaches a URL anyone can look at. A GitHub
# Actions workflow would be tidier but the token here lacks `workflow` scope.
set -euo pipefail
cd "$(dirname "$0")"

REPO=https://github.com/aaryavvatts-lab/neuroswitch
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# Refuse to publish a build with any of the bugs that actually shipped.
grep -q '<svg xmlns' site/index.html \
  || { echo 'FAIL: figures are not inlined (they would render black)'; exit 1; }
! grep -q 'src="figures/' site/index.html \
  || { echo 'FAIL: a figure is still an <img> reference'; exit 1; }
! grep -q 'class="point' site/index.html \
  || { echo 'FAIL: boxed list markup is back (wraps one word per line)'; exit 1; }
for f in index explore privacy terms cookies accessibility; do
  test -s "site/$f.html" || { echo "FAIL: missing $f.html"; exit 1; }
done

git clone -q --depth 1 --branch gh-pages "$REPO" "$WORK/ghp" 2>/dev/null \
  || git clone -q --depth 1 "$REPO" "$WORK/ghp"
cd "$WORK/ghp"
git checkout -q --orphan publish
git rm -rq --cached . 2>/dev/null || true
find . -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
cp -R "$OLDPWD/site/." .
touch .nojekyll
git add -A
git -c user.email=aaryavvatts@gmail.com -c user.name="Aaryav Sharma" \
    commit -qm "Publish site ($(date -u +%Y-%m-%dT%H:%MZ))"
git push -qf origin publish:gh-pages
echo "published $(find . -type f -not -path './.git/*' | wc -l | tr -d ' ') files"
echo "https://aaryavvatts-lab.github.io/neuroswitch/"
