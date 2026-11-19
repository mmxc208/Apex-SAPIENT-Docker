"""Readers over the recorder's JSON-lines files and the fusion nodes' logs (goat step 4b).

Standard library only. Each function takes an iterable of parsed records (one object per line of
emulators/recorder.py: t, key, kind, node_id, anchor, site, msg) or of log lines, so it runs with
no rig. Apparent age of a message = the recorder's receive time `t` minus the message's
`msg.timestamp`; the validator of emulators/fake_fusion_node.py accepts an age from -0.1 to 0.9 s
(messageTimestampRange [-0.9, 0.1]).

    python3 goat4b/readers.py ages [--anchor A] [--since T] [--until T] [--kinds k,k] [file]
    python3 goat4b/readers.py follow <task id suffix> [file]
    python3 goat4b/readers.py latency [--since T] [--until T] [file]
    python3 goat4b/readers.py rejections [--since HH:MM:SS] [--until HH:MM:SS] [file]

A file of records or log lines is read from the path, or from stdin when none is given.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from typing import Iterable

WINDOW = (-0.1, 0.9)  # accepted apparent age, s
MIN_MESSAGES = 20  # fewer in a step: not judged (plan, Review Focus 5)
_FRACTION = re.compile(r"\.(\d+)")
_CLOCK = re.compile(r"\b(\d\d:\d\d:\d\d)\b")


def parse_time(text: str | datetime) -> datetime:
    """An RFC 3339 / ISO time ('Z' or an offset, any number of fraction digits) as aware UTC."""
    if isinstance(text, datetime):
        return text if text.tzinfo else text.replace(tzinfo=timezone.utc)
    s = text.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    s = _FRACTION.sub(lambda m: "." + (m.group(1) + "000000")[:6], s, count=1)
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _content(msg: dict) -> str | None:
    for k in msg:
        if k not in ("timestamp", "node_id", "destination_id"):
            return k
    return None


def _task_id(msg: dict) -> str | None:
    for k in ("task", "task_ack"):
        if isinstance(msg.get(k), dict):
            return msg[k].get("task_id")
    return None


def _in_range(t: datetime, since, until) -> bool:
    return (since is None or t >= parse_time(since)) and (until is None or t <= parse_time(until))


def follow_task(records: Iterable[dict], task_id_suffix: str) -> list[dict]:
    """The task and its acknowledgements whose task ID ends with the suffix, in file order."""
    out = []
    for r in records:
        msg = r.get("msg")
        if not isinstance(msg, dict):
            continue
        tid = _task_id(msg)
        if tid and tid.endswith(task_id_suffix):
            out.append({"t": r.get("t"), "key": r.get("key"), "from": msg.get("node_id"),
                        "to": msg.get("destination_id"), "content": _content(msg), "task_id": tid})
    return out


def apparent_ages(records: Iterable[dict], since=None, until=None, kinds=None) -> dict:
    """count, min, median, max (s), below_zero, outside_window of t minus msg.timestamp.
    since/until bound t (inclusive); kinds limits the record kinds. Undecoded records are skipped."""
    ages = []
    for r in records:
        msg = r.get("msg")
        if not isinstance(msg, dict) or "timestamp" not in msg or "t" not in r:
            continue
        if kinds is not None and r.get("kind") not in kinds:
            continue
        t = parse_time(r["t"])
        if not _in_range(t, since, until):
            continue
        ages.append((t - parse_time(msg["timestamp"])).total_seconds())
    if not ages:
        return {"count": 0, "min": None, "median": None, "max": None, "below_zero": 0, "outside_window": 0}
    return {"count": len(ages), "min": min(ages), "median": statistics.median(ages), "max": max(ages),
            "below_zero": sum(a < 0 for a in ages),
            "outside_window": sum(a < WINDOW[0] or a > WINDOW[1] for a in ages)}


def task_latency(records: Iterable[dict]) -> dict:
    """For each task with an acknowledgement of the same task ID: ack t minus task t, in ms.
    The first record of each is used. count, min, median, max, unacknowledged."""
    tasks: dict[str, datetime] = {}
    acks: dict[str, datetime] = {}
    for r in records:
        msg = r.get("msg")
        if not isinstance(msg, dict):
            continue
        content = _content(msg)
        tid = _task_id(msg)
        if not tid or content not in ("task", "task_ack"):
            continue
        into = tasks if content == "task" else acks
        into.setdefault(tid, parse_time(r["t"]))
    lat = [(acks[i] - t).total_seconds() * 1000 for i, t in tasks.items() if i in acks]
    unacked = sum(i not in acks for i in tasks)
    if not lat:
        return {"count": 0, "min": None, "median": None, "max": None, "unacknowledged": unacked}
    return {"count": len(lat), "min": min(lat), "median": statistics.median(lat), "max": max(lat),
            "unacknowledged": unacked}


def rejections(log_lines: Iterable[str], since=None, until=None) -> dict:
    """Lines with 'invalid message from' (any sender; includes the next form) and with
    'invalid message from above dropped'. since/until are 'HH:MM:SS' (inclusive), compared with
    the first such time in a line; a line with no time is counted only when neither is given."""
    out = {"invalid message from": 0, "invalid message from above dropped": 0}
    for line in log_lines:
        if since is not None or until is not None:
            m = _CLOCK.search(line)
            if not m or (since is not None and m.group(1) < since) or (until is not None and m.group(1) > until):
                continue
        for form in out:
            if form in line:
                out[form] += 1
    return out


def judge_step(ages: dict, accepted: int, rejected: int) -> str:
    """G4B-06 for one step (spec 6.4): ages all inside the window pass with 0 rejected; all
    outside on one side pass with 0 accepted. Fewer than 20 messages, or ages on both sides of a
    limit: not judged."""
    if not ages.get("count") or ages["count"] < MIN_MESSAGES:
        return "not judged"
    lo, hi = ages["min"], ages["max"]
    if lo >= WINDOW[0] and hi <= WINDOW[1]:
        return "pass" if rejected == 0 else "fail"
    if hi < WINDOW[0] or lo > WINDOW[1]:
        return "pass" if accepted == 0 else "fail"
    return "not judged"


def _fmt(v) -> str:
    return "-" if v is None else f"{v:.3f}"


def _records(f) -> list[dict]:
    return [json.loads(line) for line in f if line.strip()]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="readers.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ages")
    a.add_argument("--anchor")
    a.add_argument("--since")
    a.add_argument("--until")
    a.add_argument("--kinds")
    f = sub.add_parser("follow")
    f.add_argument("suffix")
    lat = sub.add_parser("latency")
    lat.add_argument("--since")
    lat.add_argument("--until")
    r = sub.add_parser("rejections")
    r.add_argument("--since")
    r.add_argument("--until")
    for p in (a, f, lat, r):
        p.add_argument("file", nargs="?")
    args = ap.parse_args(argv)
    src = open(args.file, encoding="utf-8") if args.file else sys.stdin
    with src:
        if args.cmd == "rejections":
            res = rejections(src, args.since, args.until)
            for k, v in res.items():
                print(f"lines with '{k}': {v}")
            return 0
        rows = _records(src)
    if args.cmd == "ages":
        if args.anchor:
            rows = [x for x in rows if x.get("anchor") == args.anchor]
        kinds = args.kinds.split(",") if args.kinds else None
        g = apparent_ages(rows, args.since, args.until, kinds)
        print(f"apparent age (s): count {g['count']} min {_fmt(g['min'])} median {_fmt(g['median'])} "
              f"max {_fmt(g['max'])} below_zero {g['below_zero']} outside_window {g['outside_window']}")
    elif args.cmd == "follow":
        for x in follow_task(rows, args.suffix):
            print(f"{x['t']} {x['key']} | from {(x['from'] or '-')[:8]} to {(x['to'] or '-')[:8]} | "
                  f"{x['content']} {x['task_id']}")
    elif args.cmd == "latency":
        rows = [x for x in rows if "t" in x and _in_range(parse_time(x["t"]), args.since, args.until)]
        g = task_latency(rows)
        print(f"task latency (ms): count {g['count']} min {_fmt(g['min'])} median {_fmt(g['median'])} "
              f"max {_fmt(g['max'])} unacknowledged {g['unacknowledged']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
