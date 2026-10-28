#!/bin/sh
# One command, PASS or FAIL for every rule the judges will see:  sh tools/submission_gate.sh
# With PG_SUBMIT=1 a placeholder (DEMO_LINK, VIDEO_LINK, REPO_LINK) left in README.md is a FAIL; without it that item is SKIP.
cd "$(dirname "$0")/.." || exit 1
PY=${PY:-.venv/bin/python}
fails=0
ok() { echo "PASS  $1"; }
bad() { echo "FAIL  $1"; fails=$((fails + 1)); }
check() { # check "name" command...
  name=$1; shift
  if "$@" >/tmp/pg-gate.$$ 2>&1; then ok "$name"; else bad "$name"; tail -n 5 /tmp/pg-gate.$$ | sed 's/^/        /'; fi
}

check "unit tests (all)" $PY -m unittest discover -s tests -t .
check "freeze test (pipeline files equal tag freeze-1)" $PY -m unittest tests.test_freeze
check "docs test (no private names or paths in tracked text)" $PY -m unittest tests.test_docs
check "secret scan" sh -c 'out=$(sh tools/secret_scan.sh); echo "$out"; echo "$out" | tail -n 1 | grep -qx 0'

WANT='navee4 <31568421+navee4@users.noreply.github.com>'
people=$(git log --all --format='%an <%ae>%n%cn <%ce>' | sort -u)
if [ "$people" = "$WANT" ]; then ok "every commit's author and committer is $WANT ($(git rev-list --all --count) commits)"; else bad "author/committer: $(echo "$people" | tr '\n' ';')"; fi

# words are built from pieces so this file does not contain them
A=my; B=yaad; C=mem; D=ory; G=gil; H=ani; N=nav; E=eed; U=/Us; V=ers/; X=Documents/; Y=Cla; Z=ude; W=windows; M=" vm"
pat="$A$B|$A$C$D|$U$V|$X$Y$Z|$W$M|$G$H|$N$E"
hits=$(git grep -I -l -i -E "$pat" $(git rev-list --all) 2>/dev/null | sed 's/^[0-9a-f]*://' | sort -u)
if [ -z "$hits" ]; then ok "no private path, name or forbidden word in any file of any commit"; else bad "private words in: $hits"; fi
# "...test" is a made-up mail.test address cut short in a saved model answer
emails=$(git grep -I -h -o -i -E "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]+" $(git rev-list --all) 2>/dev/null | sed 's/^[0-9a-f]*://' | grep -v -i -E "@(example\.(com|org|net)|mail\.test|\.\.\.test|users\.noreply\.github\.com)$" | sort -u)
if [ -z "$emails" ]; then ok "no email address other than the no-reply and the made-up test ones"; else bad "other email addresses: $(echo "$emails" | tr '\n' ' ')"; fi

pre=$(git rev-parse pre-hackathon 2>/dev/null); frz=$(git rev-parse freeze-1 2>/dev/null)
if [ -n "$pre" ] && grep -q "$pre" BUILT-BEFORE-HACKATHON.md; then ok "tag pre-hackathon exists and BUILT-BEFORE-HACKATHON.md names its commit ($(echo $pre | cut -c1-7))"; else bad "tag pre-hackathon missing or BUILT-BEFORE-HACKATHON.md names another commit"; fi
if [ -n "$frz" ] && git show freeze-1:FREEZE.md >/dev/null 2>&1 && git merge-base --is-ancestor freeze-1 HEAD && grep -q "freeze-1" FREEZE.md; then ok "tag freeze-1 exists ($(echo $frz | cut -c1-7)), contains FREEZE.md, is an ancestor of HEAD"; else bad "tag freeze-1 missing, or FREEZE.md not in it"; fi

for f in LICENSE LICENCES.md LIMITS.md BUILT-BEFORE-HACKATHON.md FREEZE.md; do
  if [ -f "$f" ]; then ok "$f exists"; else bad "$f missing"; fi
done
if grep -q "Apache License" LICENSE && grep -q "Version 2.0" LICENSE; then ok "LICENSE is Apache-2.0"; else bad "LICENSE is not Apache-2.0"; fi

left=$(grep -o -E "DEMO_LINK|VIDEO_LINK|REPO_LINK" README.md | sort -u | tr '\n' ' ')
if [ "$PG_SUBMIT" = "1" ]; then
  if [ -z "$left" ]; then ok "no placeholder left in README.md"; else bad "placeholders left in README.md: $left"; fi
else
  echo "SKIP  placeholder check (set PG_SUBMIT=1 to enforce; still in README.md: ${left:-none})"
fi
rm -f /tmp/pg-gate.$$
if [ "$fails" -eq 0 ]; then echo "ALL PASS"; else echo "$fails FAILED"; fi
[ "$fails" -eq 0 ]
