#!/usr/bin/env python3
"""public-surface: exit 0 iff every public repo of the account is on the keep table, every listed repo's
default-branch history carries only the owner identity, and its latest CI run on that branch succeeded.

Reads only the public GitHub REST API. The keep table is .github/public-surface.tsv (repo, action, ci).
  python3 .github/public-surface.py             live check
  python3 .github/public-surface.py --selftest  planted cases from a fake API (no network)
"""
import json, os, re, sys, urllib.request

OWNER = os.environ.get("PS_OWNER", "mpuodziukas-labs")
OK_EMAIL = re.compile(r"^(michael@puodziukas\.dev|noreply@github\.com|268780072\+mpuodziukas-labs@users\.noreply\.github\.com)$")
# noreply@github.com is the committer GitHub stamps on web merges; the only noreply allowed is this account's own,
# because any other noreply names a different GitHub account (recall-probe carried the personal handle, 2026-10-02).
SELF_WORKFLOW = "public-surface"  # this check's own run never decides whether main is failing (no self-flap)
TABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public-surface.tsv")


def api(path, fetch):
    return fetch(path)


def live_fetch(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept": "application/vnd.github+json"})
    tok = os.environ.get("GH_TOKEN")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def read_table(path):
    rows = {}
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        repo, action, ci = line.rstrip("\n").split("\t")[:3]
        rows[repo] = (action, ci == "yes")
    return rows


def check(table, fetch):
    red = []
    repos, page = [], 1
    while True:
        batch = fetch(f"/users/{OWNER}/repos?type=owner&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    public = {r["name"]: r for r in repos if not r.get("private")}
    for name, r in sorted(public.items()):
        want = table.get(name, (None, False))[0]
        if want is None:
            red.append(f"RED {name}: public but not on the keep table")
        elif want == "ARCHIVE" and not r["archived"]:
            red.append(f"RED {name}: table says ARCHIVE, repo is live")
        elif want == "KEEP_PUBLIC" and r["archived"]:
            red.append(f"RED {name}: table says KEEP_PUBLIC, repo is archived")
    for name, (action, ci) in sorted(table.items()):
        if name not in public:
            red.append(f"RED {name}: on the keep table but not public")
            continue
        br = public[name]["default_branch"]
        bad, page = set(), 1
        while page <= 20:
            cs = fetch(f"/repos/{OWNER}/{name}/commits?sha={br}&per_page=100&page={page}")
            for c in cs:
                for who in ("author", "committer"):
                    e = c["commit"][who]["email"]
                    if not OK_EMAIL.match(e):
                        bad.add(e.split("@")[-1])
            if len(cs) < 100:
                break
            page += 1
        if bad:
            red.append(f"RED {name}: commit identity outside the owner set (domains: {', '.join(sorted(bad))})")
        if ci:
            runs = fetch(f"/repos/{OWNER}/{name}/actions/runs?branch={br}&per_page=20")["workflow_runs"]
            runs = [x for x in runs if x["name"] != SELF_WORKFLOW and x["status"] == "completed"]
            if not runs:
                red.append(f"RED {name}: no completed CI run on {br}")
            elif runs[0]["conclusion"] != "success":
                red.append(f"RED {name}: latest CI on {br} is {runs[0]['conclusion']} ({runs[0]['name']})")
    return red


def selftest():
    def fake(state):
        def f(path):
            if path.startswith(f"/users/{OWNER}/repos"):
                return [{"name": n, "private": False, "archived": a, "default_branch": "main"} for n, a in state["repos"]]
            name = path.split("/")[3]
            if "/commits" in path:
                e = state["emails"].get(name, "michael@puodziukas.dev")
                return [{"sha": "6fd9602faaa740034e746d542cd47133e95e5812",
                         "commit": {"author": {"email": e}, "committer": {"email": "michael@puodziukas.dev"}}}]
            return {"workflow_runs": state["runs"].get(name, [{"name": "CI", "head_branch": "main", "status": "completed", "conclusion": "success"}])}
        return f

    table = {"cobol-pic-probe": ("KEEP_PUBLIC", True), "old-gate": ("ARCHIVE", True), OWNER: ("KEEP_PUBLIC", False)}
    base = lambda: {"repos": [("cobol-pic-probe", False), ("old-gate", True), (OWNER, False)], "emails": {}, "runs": {}}
    cases = []
    s = base(); cases.append(("control GREEN", s, False))
    s = base(); s["emails"]["cobol-pic-probe"] = "someone@example.org"; cases.append(("non-owner email RED", s, True))
    s = base(); s["runs"]["cobol-pic-probe"] = [{"name": "CI", "head_branch": "main", "status": "completed", "conclusion": "failure"}]
    cases.append(("failing main RED", s, True))
    s = base(); s["repos"].append(("exo", False)); cases.append(("repo off the keep table RED", s, True))
    s = base(); s["repos"] = [x for x in s["repos"] if x[0] != "cobol-pic-probe"]; cases.append(("listed repo gone private RED", s, True))
    s = base(); s["repos"][1] = ("old-gate", False); cases.append(("ARCHIVE row still live RED", s, True))
    s = base(); s["runs"]["cobol-pic-probe"] = []; cases.append(("no CI run RED", s, True))
    s = base(); s["runs"][OWNER] = [{"name": SELF_WORKFLOW, "head_branch": "main", "status": "completed", "conclusion": "failure"}]
    cases.append(("own failing run never counts GREEN", s, False))
    s = base(); s["runs"]["cobol-pic-probe"] = [{"name": SELF_WORKFLOW, "head_branch": "main", "status": "completed", "conclusion": "success"},
                                                {"name": "CI", "head_branch": "main", "status": "completed", "conclusion": "failure"}]
    cases.append(("own green run cannot mask a red CI RED", s, True))
    p = 0
    for label, st, want_red in cases:
        got_red = bool(check(table, fake(st)))
        ok = got_red == want_red
        p += ok
        print(("PASS " if ok else "FAIL ") + label)
    print(f"public-surface selftest {p}/{len(cases)}")
    return p == len(cases)


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if selftest() else 1)
    red = check(read_table(TABLE), live_fetch)
    for line in red:
        print(line)
    if not red:
        print(f"GREEN public surface: every public repo on the keep table, owner identity only, CI green on main")
    sys.exit(1 if red else 0)
