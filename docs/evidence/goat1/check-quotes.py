"""Checks that every quoted log or output line of the goat step 1 record is in an evidence file.

Run from the repository root: python3 docs/evidence/goat1/check-quotes.py

Quotes checked:
- README-goat.md, section "Goat step 1: pod 1 to host" (in README.md until the section moved): every
  non-empty line of every ```text block,
  searched only in README_RUN, the saved output of the run that the README names. Without "..." the line must equal a whole line of an evidence file; with "..." each part must
  appear in order in one line that starts with the first part.
- docs/acceptance-goat1.md: every inline code span that looks like log or command output (see
  LOGLIKE). The parts between "..." must appear in order in one line of an evidence file.

Before matching, the zsh prompts of a pasted run ("% aidev-1% ", "pipe quote> ") are removed from the
start of each evidence line, and trailing white space is ignored on both sides. Only the .txt files
of this directory are searched.
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROMPT = re.compile(r"^(?:%[ \r]*aidev-1% |(?:pipe |d)?quote> )+")
LOGLIKE = re.compile(
    r"\| |pod-bridge:|fusion:|radar:|camera:|router files|passed|PAIRING OK|POD1_RADAR2_ID=|no traffic"
    r"|is (?:un)?authorized|unauthorized to|goat 0\.5|Using cached|\((?:in|e)gress\)|Declare/Undeclare"
    r"|CN=|^records|^samples:|^put:|^[0-9a-f]{32}$|Finished `release`|^=== start|^(?:Updating|Downloading) crates|target\(s\) in"
)
README_RUN = "task-12-readme-run.txt"
COMMAND = re.compile(r"^(?:\$|dg |dc |docker |python3 |goat |git |grep |shasum |test |HOST_HOLD|ZENOHD_)")


def evidence() -> dict[str, list[str]]:
    files = {}
    for path in sorted(HERE.glob("*.txt")):
        with path.open(encoding="utf-8", errors="replace", newline="") as f:  # keep a lone \r inside a line
            text = f.read()
        files[path.name] = [PROMPT.sub("", line).rstrip() for line in text.replace("\r\n", "\n").split("\n")]
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


def main() -> int:
    files = evidence()
    readme = pathlib.Path("README-goat.md").read_text()
    start = readme.index("## Goat step 1: pod 1 to host")
    following = readme.find("\n## ", start + 1)  # the section ends at the next heading of its level
    section = readme[start:following if following != -1 else len(readme)]
    record = pathlib.Path("docs/acceptance-goat1.md").read_text()
    checked = missing = 0
    for block in re.findall(r"```text\n(.*?)```", section, re.S):
        for line in block.split("\n"):
            if not line.strip():
                continue
            where = find({README_RUN: files[README_RUN]}, line, True)
            checked += 1
            missing += where is None
            print("README", where or "MISSING", "|", line[:110])
    for span in re.findall(r"`([^`\n]+)`", record):
        if not LOGLIKE.search(span) or COMMAND.search(span):
            continue
        where = find(files, span, False)
        checked += 1
        missing += where is None
        print("RECORD", where or "MISSING", "|", span[:110])
    print("checked:", checked, "missing:", missing)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
