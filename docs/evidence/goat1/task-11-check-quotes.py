import re, sys, pathlib
W = pathlib.Path(sys.argv[1])
ev = ["task-11-readme-run.txt", "task-11-run.txt", "task-11-run-shortened.txt", "task-11-version.txt", "task-11-build.txt", "task-11-router-trace-plain.txt", "task-11-readme-fabric-log-plain.txt"]
files = {n: [re.sub(r"^(?:%[ \r]*aidev-1% )+", "", l).rstrip("\r") for l in open(W / n, newline="").read().split("\n")] for n in ev}
def find_line(q):
    for n in ev:
        for i, l in enumerate(files[n], 1):
            if l == q: return f"{n}:{i}"
def find_sub(q):
    for n in ev:
        for i, l in enumerate(files[n], 1):
            if q in l: return f"{n}:{i}"
readme = pathlib.Path("README.md").read_text()
sec = readme[readme.index("**10. A real goat client"):readme.index("To stop the step, run `dg down`.")]
bad = 0
for block in re.findall(r"```text\n(.*?)```", sec, re.S):
    for l in block.split("\n"):
        if not l.strip(): continue
        r = find_line(l); bad += r is None
        print("README  ", r or "MISSING", "|", l[:110])
acc = pathlib.Path("docs/acceptance-goat1.md").read_text()
acc = acc[acc.index("## G1-10"):]
for q in ["goat 0.5.19", "18214b1a…/telemetry/sapient/p1/v2/status_report/f0000001-0000-4000-8000-000000000001",
          "18214b1a34e3c722d1cac283b272a62c/telemetry/sapient/p1/v2/detection_report/f0000001-0000-4000-8000-000000000001",
          "Declare Subscriber (ingress)", "Put (egress)", "Declare/Undeclare Liveliness Token", "CertCommonName(ad19ee14f48bda3901a8bea949babb5a)"]:
    if q.split("CertCommonName(")[-1].rstrip(")") not in acc and q not in acc: continue
    r = find_sub(q); bad += r is None
    print("ACCEPT  ", r or "MISSING", "|", q[:110])
print("missing:", bad)
