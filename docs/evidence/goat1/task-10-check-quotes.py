import re, sys, pathlib
W = pathlib.Path(sys.argv[1])
ev = ["task-10-g1-06.txt","task-10-g1-06-logs.txt","task-10-g1-07.txt","task-10-g1-07-logs.txt","task-10-g1-08.txt","task-10-g1-09.txt","task-10-g1-09-logs.txt","task-10-readme-run.txt"]
files = {n: open(W / n, newline="").read().split("\n") for n in ev}
def strip(l):
    return re.sub(r"^(?:%[ \r]*aidev-1% )+", "", l).rstrip("\r")
# README quotes must appear in the run's output in the order the README gives them.
_after = {"pos": 0}
def find_readme(q):
    lines = files["task-10-readme-run.txt"]
    start = lines.index(next(l for l in lines if l.endswith("=== block 7")))
    for i in range(max(start, _after["pos"]), len(lines)):
        if strip(lines[i]) == q:
            _after["pos"] = i + 1
            return f"task-10-readme-run.txt:{i + 1}"
    return None
def find(q):
    if q == "20":
        for i, l in enumerate(files["task-10-g1-07.txt"], 1):
            if l == "20": return f"task-10-g1-07.txt:{i}"
        return None
    parts = [p.strip() for p in q.split("...") if p.strip()]
    for n, lines in files.items():
        for i, l in enumerate(lines, 1):
            pos = 0; ok = True
            for part in parts:
                j = l.find(part, pos)
                if j < 0: ok = False; break
                pos = j + len(part)
            if ok: return f"{n}:{i}"
    return None
quotes = []
readme = pathlib.Path("README.md").read_text()
sec = readme[readme.index("Steps 7 to 9 were added later"):readme.index("To stop the step, run `dg down`.")]
for block in re.findall(r"```text\n(.*?)```", sec, re.S):
    quotes += [("README", l) for l in block.splitlines() if l.strip()]
acc = pathlib.Path("docs/acceptance-goat1.md").read_text()
acc = acc[acc.index("## G1-06 to G1-09"):]
for span in re.findall(r"`([^`]+)`", acc):
    if re.search(r"\| |pod-bridge:|fusion:|router files|passed|^20$|POD1_RADAR2_ID=|no traffic", span):
        quotes.append(("acceptance", span))
bad = 0
for where, q in quotes:
    r = find_readme(q) if where == "README" else find(q)
    if r is None: bad += 1
    print(f"{where}\t{r or 'NOT FOUND'}\t{q}")
print("not found:", bad, "of", len(quotes))
