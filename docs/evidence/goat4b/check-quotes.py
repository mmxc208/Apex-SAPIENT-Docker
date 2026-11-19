"""Checks the goat step 4b record: every quoted line is in an evidence file, and no file holds a secret.

Run from the repository root: python3 docs/evidence/goat4b/check-quotes.py
Options, for a test against a scratch copy (the defaults are the files of the repository):
  --record PATH   the record to check instead of docs/acceptance-goat4b.md
  --readme PATH   the README to check instead of README-goat.md

Quotes checked (the method of docs/evidence/goat4/check-quotes.py):
- README-goat.md, section "Goat step 4b: the host on its own machine" only: it starts at that heading
  and ends at the next heading of its level ("## ") or at the end of the file. The step 4 checker,
  docs/evidence/goat4/check-quotes.py, ends its own section at the next "## " heading, so the two
  checkers cover separate sections. Every non-empty line of every ```text block is searched only in
  the evidence files that the README names next to the block: the .txt names in the prose between
  the code block before it and the block, and in the prose between the block and the next code block.
  readme-run.txt is left out of that list, because the outputs shown are those of the task runs. A
  block next to which no file is named fails. Without "..." the line must equal a whole line of an
  evidence file; with "..." each part must appear in order in one line that starts with the first part.
- docs/acceptance-goat4b.md: every inline code span (single or double backticks) that looks like log
  or command output (see LOGLIKE) and not like a command (see COMMAND). The parts between "..." must
  appear in order in one line of an evidence file. Record spans are searched in all the .txt files of
  this directory, the task files first.
Trailing white space is ignored on both sides. Only the .txt files of this directory are searched.

Secret rule (that of step 4, with one pattern added): every file below this directory, of any type,
the record, and the step 4b section of the README are searched for the patterns of SECRET: a private
key header; the field and path names of the enrolment answer that carry an API key, a bundle token or
a bundle path; a machine API key in the shape the portal mints (prefix "vp", a lower-case id, 64 hex);
any 64-hex string, except right after "sha256:" (a docker image digest); any standalone token of 40
or more characters of letters, digits, "_" and "-" that is not purely hexadecimal and has no "/" next
to it (the shape of the operator key); and, new in step 4b, an absolute path below the Mac's home
directories, which would hold the user name. A match fails the check, unless the whole line is in ALLOWED: an exact line
judged harmless. The patterns are written in pieces so that this file does not match itself.
"""
import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SECTION = "## Goat step 4b: the host on its own machine"
LOGLIKE = re.compile(
    r"\| |fusion:|pod-bridge:|recorder:|^apparent age|^task latency|^lines with|^records:|^anchors seen|^anchor not"
    r"|^msg\.node_id|did not decode|sensor node ID|^SUMMARY|g4b_clock_restore:|g4b_vm_sync:|goat4b_ready|^synced "
    r"|cannot connect|CONNECTED$|\(control\)|^apex-goat4b? |count on both|^goathost|^colima|^goatlite|^route |^t\+\d"
    r"|offset|bound =|rounds|passed in|^Ran \d|^Ubuntu|version|lima-goathost|Time sync|OCI runtime|error during"
    r"|^\d+: lima0|^-rw|^host-fusion: |^StartedAt|StartedAt:|^G4B-0\d: |seconds from|^count: |^NODE_HOLD|^tasks sent"
    r"|^containers of|^task 01|^\(end|^\(eval\)|section run again|clock back by|nothing to restore|^RUN-END"
    r"|^after down|^A\t|^dropped|Timestamp delta|^\d{4}-\d\d-\d\dT[\d:.]+\+00:00$|^-?\d\.\d{3},-?\d\.\d{3}$"
    r"|judge_step|^192\.168\.64\.\d+$|exit 0$|running$|^host tasks sent|^seen on the pod|^received by|^acknowledged at"
    r"|^the pod's own|^[0-9a-f]{32}/|^01[0-9A-Z]{24}$|re-registration|via 192\.168\.64\.1 dev|^OK$"
)
README_RUN = "readme-run.txt"  # the transcript of the README run; not a source of the outputs shown in the README
TXT_NAME = re.compile(r"`([A-Za-z0-9_.-]+\.txt)`")
COMMAND = re.compile(
    r"^(?:\$ |dg4b?_[a-z]+ |dg4 |dg |docker |python3 |goat |git |grep |test |HOST_HOLD|colima |limactl (?!version)"
    r"|g4b_[a-z_]+(?: (?!exit)|$)|\. |zsh )"
)
# The secret rule. Each pattern is written in pieces, so that this file does not match itself.
SECRET = re.compile(
    "PRIVATE" + " KEY"                      # a private key header
    + "|api" + "_key" + "|bundle" + "_token" + "|/api/" + "org-bundle/"  # field and path names of the enrolment answer
    + "|vp" + "_[a-z0-9-]+_[0-9a-f]{64}"    # a machine API key as the portal mints it
    + "|(?<![0-9A-Fa-f])[0-9A-Fa-f]{6" + "4}(?![0-9A-Fa-f])"  # any 64-hex string
    # any standalone token of 40 or more characters of [A-Za-z0-9_-] that is not purely
    # hexadecimal and is not part of a path (no "/" next to it): the shape of an operator key
    + "|(?<![A-Za-z0-9_/-])(?=[A-Za-z0-9_-]*[G-Zg-z_-])[A-Za-z0-9_-]{4" + "0,}(?![A-Za-z0-9_/-])"
    + "|/Us" + "ers/"                       # an absolute path below the Mac's home directories
)
# A 64-hex string right after "sha256:" is a docker image digest, not a secret.
DIGEST = re.compile("sha256:[0-9a-f]{6" + "4}")
# Exact lines that match a pattern and were judged harmless, one by one (see README.md). Long
# hexadecimal names are split with "+" so that this file does not match itself.
ALLOWED = {
    # task-2-g4b-01.txt: the anonymous Docker volumes of the two host services (/apex/data of the image),
    # named by Docker with 64 hexadecimal characters
    ("task-2-g4b-01.txt", "host-fusion: volume /var/lib/docker/volumes/6fb305c056c344c8" + "5ecea45878dbb53fc1c793f5"
     + "bb1e2bc507d47ef1fda31f6e/_data -> /apex/data"),
    ("task-2-g4b-01.txt", "host-recorder: volume /var/lib/docker/volumes/266961aafcd509ce" + "eabb6f6701601709f595ba58"
     + "a1568456bc313a4cb45d5139/_data -> /apex/data"),
    # task-5-unit-suite.txt: the line of 70 "-" that unittest prints before its count
    ("task-5-unit-suite.txt", "-" * 70),
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


def secret_lines(rel: str, text: str) -> int:
    found = 0
    for number, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        if SECRET.search(DIGEST.sub("sha256:digest", line)) and (rel, line.rstrip()) not in ALLOWED:
            found += 1
            print("SECRET", f"{rel}:{number}", "| a secret pattern matched (line not printed)")
    return found


def secrets(extra: dict[str, str]) -> int:
    found = 0
    for path in sorted(p for p in HERE.rglob("*") if p.is_file()):
        found += secret_lines(path.relative_to(HERE).as_posix(), path.read_bytes().decode("utf-8", errors="replace"))
    for name, text in extra.items():
        found += secret_lines(name, text)
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
    parser = argparse.ArgumentParser(description="The quote check and the secret rule of goat step 4b.")
    parser.add_argument("--record", default="docs/acceptance-goat4b.md")
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
    found = secrets({"acceptance-goat4b.md": record, "README-goat.md (step 4b section)": section})
    print("checked:", checked, "missing:", missing, "secret matches:", found)
    return 1 if missing or found else 0


if __name__ == "__main__":
    sys.exit(main())
