"""Build docs/incidents.md and the README incident table from git history and docs/incident_notes.json."""
import json
import re
import subprocess

notes = json.load(open("docs/incident_notes.json"))
log = [l.split("|", 1) for l in subprocess.check_output(["git", "log", "--reverse", "--format=%h|%s"], text=True).strip().splitlines()]


def find(n, kind):
    return next((h for h, s in log if s.startswith(f"INC-{n} {kind}:")), None)


rows = [{**x, "repro": find(x["n"], "reproduce"), "fix": find(x["n"], "fix")} for x in notes]
missing = [r["n"] for r in rows if not r["repro"] or not r["fix"]]
if missing:
    raise SystemExit(f"missing commits for incidents {missing}")
table = "\n".join(["| # | Incident | Found by | Reproduce | Fix |", "| --- | --- | --- | --- | --- |"] +
                  [f"| INC-{r['n']} | {r['title']} | {r['found']} | `{r['repro']}` | `{r['fix']}` |" for r in rows])
detail = "\n".join(f"### INC-{r['n']}: {r['title']}\n\n{r['detail']}\n\nReproduce `{r['repro']}`, fix `{r['fix']}`. Found by: {r['found']}.\n" for r in rows)
open("docs/incidents.md", "w").write("# Incident log\n\nEvery incident has two commits. The first adds a test that fails for the right reason; a later one fixes the code and the same test passes. Hashes below come from `git log`.\n\n" + table + "\n\n" + detail)
try:
    readme = open("README.md").read()
    open("README.md", "w").write(re.sub(r"<!-- incidents:start -->[\s\S]*<!-- incidents:end -->", lambda m: f"<!-- incidents:start -->\n{table}\n<!-- incidents:end -->", readme))
except FileNotFoundError:
    pass
print(len(rows), "incidents")
