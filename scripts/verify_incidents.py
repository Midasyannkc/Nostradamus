"""For every incident, check out its reproduce and fix commits in scratch worktrees and run the test files the
reproduce commit touched.  Reproduce must fail and fix must pass."""
import json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sh = lambda *a, cwd=ROOT: subprocess.run(a, cwd=cwd, capture_output=True, text=True)
log = [l.split("|", 1) for l in sh("git", "log", "--reverse", "--format=%h|%s").stdout.strip().splitlines()]
notes = json.load(open(os.path.join(ROOT, "docs/incident_notes.json")))
only = set(map(int, sys.argv[1:]))
commit_for = lambda n, k: next(h for h, s in log if s.startswith(f"INC-{n} {k}:"))


def run_at(sha, files):
    with tempfile.TemporaryDirectory() as td:
        wt = os.path.join(td, "wt")
        sh("git", "worktree", "add", "--detach", wt, sha)
        p = sh(sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *files, cwd=wt)
        sh("git", "worktree", "remove", "--force", wt)
        return p.returncode, p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-120:]


bad = 0
for x in notes:
    n = x["n"]
    if only and n not in only:
        continue
    r, f = commit_for(n, "reproduce"), commit_for(n, "fix")
    files = [p for p in sh("git", "show", "--name-only", "--format=", r).stdout.split() if p.startswith("tests/test_")]
    rc1, o1 = run_at(r, files); rc2, o2 = run_at(f, files)
    ok = rc1 != 0 and rc2 == 0
    bad += not ok
    print(f"INC-{n:<2} {'OK ' if ok else 'BAD'} reproduce[{r}]: {o1} | fix[{f}]: {o2}", flush=True)
sys.exit(1 if bad else 0)
