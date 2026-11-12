import re, sys, pathlib
W = pathlib.Path(sys.argv[1])
ev = ["task-11-readme-run.txt", "task-11-run.txt", "task-11-run-shortened.txt", "task-11-version.txt",
      "task-11-router-trace-plain.txt", "task-11-readme-fabric-log-plain.txt", "task-11-fix1-n1-count.txt"]
files = {n: [re.sub(r"^(?:%[ \r]*aidev-1% )+", "", l).rstrip("\r") for l in open(W / n, newline="").read().split("\n")] for n in ev}
def find(q, whole):
    parts = [p for p in q.split("...") if p] if "..." in q else [q]
    for n in ev:
        for i, l in enumerate(files[n], 1):
            if whole and "..." not in q:
                ok = l == q
            else:
                pos, ok = 0, True
                for part in parts:
                    j = l.find(part, pos)
                    if j < 0: ok = False; break
                    pos = j + len(part)
                if ok and whole and "..." in q: ok = l.startswith(parts[0])
            if ok: return f"{n}:{i}"
checked = missing = 0
readme = pathlib.Path("README.md").read_text()
sec = readme[readme.index("**10. A real goat client"):readme.index("To stop the step, run `dg down`.")]
for block in re.findall(r"```text\n(.*?)```", sec, re.S):
    for l in block.split("\n"):
        if not l.strip(): continue
        r = find(l, True); checked += 1; missing += r is None
        print("README", r or "MISSING", "|", l[:120])
acc = pathlib.Path("docs/acceptance-goat1.md").read_text()
acc = acc[acc.index("## G1-10"):]
for span in re.findall(r"`([^`\n]+)`", acc):
    if not re.search(r"18214b1a|is authorized|goat 0\.5|Using cached|\(ingress\)|\(egress\)|^[0-9a-f]{32}$|Declare/Undeclare", span): continue
    if span.startswith("$") or "sub \"" in span: continue
    r = find(span, False); checked += 1; missing += r is None
    print("ACCEPT", r or "MISSING", "|", span[:120])
print("checked:", checked, "missing:", missing)
