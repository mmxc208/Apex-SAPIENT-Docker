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

Secret rule (added in step 4, widened in the final fix wave): every file below this directory, of any
type, is searched for the patterns of SECRET: a private key header; the field and path names of the
enrolment answer that carry an API key, a bundle token or a bundle path; a machine API key in the shape
the portal mints (prefix "vp", a lower-case id, 64 hex); any 64-hex string, except right after
"sha256:" (a docker image digest); and any standalone token of 40 or more characters of letters,
digits, "_" and "-" that is not purely hexadecimal and has no "/" next to it (the shape of the
operator key, which has no fixed prefix). A match fails the check, unless the whole line is in
ALLOWED: an exact line judged harmless. The earlier rule looked for a key prefix that no key of this
portal has. The patterns are written in pieces so that this file does not match itself.
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
# The secret rule. Each pattern is written in pieces, so that this file does not match itself.
SECRET = re.compile(
    "PRIVATE" + " KEY"                      # a private key header
    + "|api" + "_key" + "|bundle" + "_token" + "|/api/" + "org-bundle/"  # field and path names of the enrolment answer
    + "|vp" + "_[a-z0-9-]+_[0-9a-f]{64}"    # a machine API key as the portal mints it
    + "|(?<![0-9A-Fa-f])[0-9A-Fa-f]{6" + "4}(?![0-9A-Fa-f])"  # any 64-hex string
    # any standalone token of 40 or more characters of [A-Za-z0-9_-] that is not purely
    # hexadecimal and is not part of a path (no "/" next to it): the shape of an operator key
    + "|(?<![A-Za-z0-9_/-])(?=[A-Za-z0-9_-]*[G-Zg-z_-])[A-Za-z0-9_-]{4" + "0,}(?![A-Za-z0-9_/-])"
)
# A 64-hex string right after "sha256:" is a docker image digest, not a secret.
DIGEST = re.compile("sha256:[0-9a-f]{6" + "4}")
# Exact lines that match a pattern and were judged harmless, one by one (see README.md). Long
# tokens are split with "+" so that this file does not match itself.
_TEST_3 = "tests/test_pod_bridg" + "e.py::test_a_task_wi" + "thout_a_timestamp_is" + "_stale PASSED [ 75%]"
_TEST_4 = ("tests/test_pod_bridg" + "e.py::test_registrat" + "ion_ack_is_not_subje" + "ct_to_the_age_limit "
           + "PASSED [100%]")
_SHA_POD = ("c3a5e2b99a4a843d0322" + "ddddd5dde61cf5c9796a" + "25bb1d962af9c9b519b8" + "4627  zenoh/goat1/ro"
            + "uter-pod1.json5")
_SHA_FABRIC = ("f7f5e342377767ddcf0e" + "22d754d22236f1417967" + "dcd2891927b6aea54a3b" + "edf8  zenoh/goat1/ro"
               + "uter-fabric.json5")
ALLOWED = {
    # task-2-verify.txt: the header of the secret grep that Task 2 ran; it names the patterns.
    ("task-2-verify.txt", "# grep -rEl 'PRIVATE" + " KEY|sbq_|api" + "_key|bundle" + "_token|org-bundle' docs/evidence/goat4/"
     " ; exit status below (1 = no file matched)"),
    # the names of two unit tests of G1-08, as pytest prints them (G4-08, and block 13 of the README run)
    ("task-5-g4-08.txt", _TEST_3), ("task-5-g4-08.txt", _TEST_4),
    ("readme-run.txt", _TEST_3), ("readme-run.txt", _TEST_4),
    # the SHA-256 of the two router files of the step 1 generator (G4-09, and block 14 of the README run)
    ("task-5-g4-09.txt", _SHA_POD), ("task-5-g4-09.txt", _SHA_FABRIC),
    ("readme-run.txt", _SHA_POD), ("readme-run.txt", _SHA_FABRIC),
    # a line of 60 "-" that separates the parts of the README run's step 1 appendix
    ("readme-run.txt", "-" * 60),
    # the name of the portal's staging directory of the refused run: "stage", the anchor, a UTC time
    ("task-2-refusal-diagnosis.txt", "# (.stage-7a640b349a" + "c2e03848531fce2000fc" + "57-20261118T233724Z)"
     + ", so that slot was free again."),
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
            if SECRET.search(DIGEST.sub("sha256:digest", line)) and (rel, line.rstrip()) not in ALLOWED:
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
    if not files:
        print("no evidence files in " + str(HERE) + ": from 2026-11-19 they are kept out of git and stay on the "
              "machine that made the runs (see the README.md beside this file). Nothing can be checked here.")
        return 2
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
