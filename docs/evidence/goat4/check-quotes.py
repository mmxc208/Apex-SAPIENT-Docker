"""Checks the goat step 4 record: every quoted line is in an evidence file, and no evidence file holds a secret.

Run from the repository root: python3 docs/evidence/goat4/check-quotes.py
Options, for a test against a scratch copy (the defaults are the files of the repository):
  --record PATH   the record to check instead of docs/acceptance-goat4.md
  --readme PATH   the README to check instead of README-goat.md

Quotes checked (the method of docs/evidence/goat1/check-quotes.py):
- README-goat.md, section "Goat step 4: the step 1 rig on cuaslab": every non-empty line of every
  ```text block. Each line is searched only in the evidence files that the README names next to the
  block: the .txt names in the prose between the code block before it and the block, and in the prose
  between the block and the next code block. readme-run.txt is left out of that list, because the
  outputs shown are those of the task runs. A block next to which no file is named fails. Without
  "..." the line must equal a whole line of an evidence file; with "..." each part must appear in
  order in one line that starts with the first part.
- docs/acceptance-goat4.md: every inline code span (single or double backticks) that looks like log
  or command output (see LOGLIKE). The parts between "..." must appear in order in one line of an
  evidence file. Record spans are searched in all the .txt files of this directory.
Trailing white space is ignored on both sides. Only the .txt files of this directory are searched.

Secret rule (added in step 4): every file below this directory, of any type, is searched for the
patterns of SECRET. A match fails the check, unless the whole line is in ALLOWED: a line that names
the patterns in a saved check, not a secret. The patterns are written in pieces so that this file
does not match itself.
"""
import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SECTION = "## Goat step 4: the step 1 rig on cuaslab"
LOGLIKE = re.compile(
    r"\| |pod-bridge:|fusion:|radar:|camera:|recorder:|router files|passed|is (?:un)?authorized|\((?:in|e)gress\)"
    r"|^records|^samples:|^put:|^session:|received:|token seen|^[0-9a-f]{32}$|enroll\.sh:|goat4_ready"
    r"|^exit|^anchor|^msg\.node_id|anchors seen|listening on|done after|event\(s\)|rtt min|offset|bound ="
    r"|^Direction|OSError|couldn't find|probe-fabric-pairing|probe-access|\"level\"|subject=|: OK$"
    r"|portal_bundle_create_bin|directory$|entries:|granted_by|\"custodian\"|\"machines\"|^[a-z0-9-]+ [0-9a-f]{32}$"
    r"|StartedAt|router not restarted|^wrote |deploy: ok|recap|fresh-source|^c3a5e2b9|^f7f5e342|zenohd-fabric listed"
    r"|^- zenohd-fabric|router\.fabric\.h1|count of|fork/exec|stopped; readers|shared values|^FABRIC_|<- step1"
    r"|: (?:True|False|\d+)$|: tls/|^[MAD]\t|registry status"
)
README_RUN = "readme-run.txt"  # the transcript of the README run; not a source of the outputs shown in the README
TXT_NAME = re.compile(r"`([A-Za-z0-9_.-]+\.txt)`")
COMMAND = re.compile(r"^(?:\$ |dg4 |dg |docker |python3 |goat |git |grep |shasum |test |HOST_HOLD|ZENOHD_|colima |limactl )")
SECRET = re.compile(
    "PRIVATE" + " KEY" + "|sbq" + "_[A-Za-z0-9_-]{20,}" + "|api" + "_key" + "|bundle" + "_token" + "|/api/" + "org-bundle/"
)
ALLOWED = {
    # task-2-verify.txt: the header of the secret grep that Task 2 ran; it names the patterns.
    ("task-2-verify.txt", "# grep -rEl 'PRIVATE" + " KEY|sbq_|api" + "_key|bundle" + "_token|org-bundle' docs/evidence/goat4/"
     " ; exit status below (1 = no file matched)"),
}


def evidence() -> dict[str, list[str]]:
    files = {}
    # the files of the task runs first, the README run last, so that a record quote is found in a task file if it is in one
    for path in sorted(HERE.glob("*.txt"), key=lambda q: (q.name == README_RUN, q.name)):
        with path.open(encoding="utf-8", errors="replace", newline="") as f:
            text = f.read()
        files[path.name] = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return files


def find(files: dict[str, list[str]], quote: str, whole: bool) -> str | None:
    quote = quote.rstrip()
    parts = [p for p in quote.split("...") if p]
    for name, lines in files.items():
        for number, line in enumerate(lines, 1):
            if whole and "..." not in quote:
                ok = line == quote
            else:
                pos, ok = 0, True
                for part in parts:
                    j = line.find(part, pos)
                    if j < 0:
                        ok = False
                        break
                    pos = j + len(part)
                if ok and whole:
                    ok = quote.startswith("...") or line.startswith(parts[0])
            if ok:
                return f"{name}:{number}"
    return None


def secrets() -> int:
    found = 0
    for path in sorted(p for p in HERE.rglob("*") if p.is_file()):
        rel = path.relative_to(HERE).as_posix()
        text = path.read_bytes().decode("utf-8", errors="replace")
        for number, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
            if SECRET.search(line) and (rel, line.rstrip()) not in ALLOWED:
                found += 1
                print("SECRET", f"{rel}:{number}", "| a secret pattern matched (line not printed)")
    return found


def spans(text: str) -> list[str]:
    """Inline code spans: first those in double backticks (they may hold a backtick), then single ones."""
    found = []
    def double(m: re.Match) -> str:
        found.append(m.group(1).strip(" "))
        return " "
    rest = re.sub(r"``(.+?)``", double, text)
    found += re.findall(r"`([^`\n]+)`", rest)
    return found


def named_files(section: str, files: dict[str, list[str]]) -> list[tuple[str, set[str]]]:
    """Each ```text block of the section, with the evidence files named in the prose next to it."""
    fences = list(re.finditer(r"^```(\w*)\n(.*?)^```$", section, re.S | re.M))
    blocks = []
    for k, fence in enumerate(fences):
        if fence.group(1) != "text":
            continue
        before = section[fences[k - 1].end() if k else 0:fence.start()]
        after = section[fence.end():fences[k + 1].start() if k + 1 < len(fences) else len(section)]
        names = {n for n in TXT_NAME.findall(before + after) if n in files and n != README_RUN}
        blocks.append((fence.group(2), names))
    return blocks


def main() -> int:
    parser = argparse.ArgumentParser(description="The quote check and the secret rule of goat step 4.")
    parser.add_argument("--record", default="docs/acceptance-goat4.md")
    parser.add_argument("--readme", default="README-goat.md")
    args = parser.parse_args()
    files = evidence()
    readme = pathlib.Path(args.readme).read_text()
    start = readme.index(SECTION)
    following = readme.find("\n## ", start + 1)  # the section ends at the next heading of its level
    section = readme[start:following if following != -1 else len(readme)]
    record = pathlib.Path(args.record).read_text()
    checked = missing = 0
    for block, names in named_files(section, files):
        if not names:
            missing += 1
            print("README NO FILE NAMED next to the block that starts |", block.split("\n")[0][:90])
            continue
        subset = {n: files[n] for n in sorted(names)}
        for line in block.split("\n"):
            if not line.strip():
                continue
            where = find(subset, line, True)
            checked += 1
            missing += where is None
            print("README", where or "MISSING in " + ", ".join(sorted(names)), "|", line[:110])
    for span in spans(record):
        if not LOGLIKE.search(span) or COMMAND.search(span):
            continue
        where = find(files, span, False)
        checked += 1
        missing += where is None
        print("RECORD", where or "MISSING", "|", span[:110])
    found = secrets()
    print("checked:", checked, "missing:", missing, "secret matches:", found)
    return 1 if missing or found else 0


if __name__ == "__main__":
    sys.exit(main())
