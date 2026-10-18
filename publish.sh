#!/usr/bin/env bash
# Publish site/ to Vercel, which serves it at https://hand-injury-brain-rewiring.vercel.app
#
# The site used to go to the gh-pages branch because deploys to the old Vercel
# project returned 403. That project no longer exists; the site is now a plain
# static deploy to the "neuroswitch" project under the Scholarly Work Projects
# team, and the production URL is public.
#
# Only site/ is uploaded -- see .vercelignore. The repository root also holds a
# 1.4 GB virtual environment and imaging derivatives.
set -euo pipefail
cd "$(dirname "$0")"

SCOPE=scholarly-work-projects
URL=https://hand-injury-brain-rewiring.vercel.app

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

vercel deploy --prod --yes --scope "$SCOPE" >/dev/null

# A deploy that lands but 403s is the failure mode this project already hit
# once, so check the public URL rather than trusting the exit code.
for path in "" explore privacy terms cookies accessibility; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -L "$URL/$path")
  test "$code" = 200 || { echo "FAIL: $URL/$path returned $code"; exit 1; }
done

echo "published $(find site -type f | wc -l | tr -d ' ') files"
echo "$URL"
