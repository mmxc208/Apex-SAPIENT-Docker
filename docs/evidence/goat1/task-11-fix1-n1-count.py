"""N1: count slot 3's router lines that are neither its subscriber declaration,
a delivery on a full sample key, nor the cache block of its key expression."""
import re, sys
CN = "ad19ee14f48bda3901a8bea949babb5a"
log = sys.argv[1]
lines = open(log, encoding="utf-8").read().splitlines()
# Goat's session IDs: the ZIDs on lines with slot 3's common name.
zids = sorted({m.group(1) for l in lines if f"CertCommonName({CN})" in l
               for m in [re.search(r"\+([0-9a-f]{32}) is (?:un)?authorized", l)] if m})
print("log:", log)
print("lines in log:", len(lines))
print("goat session IDs:", zids)
mine = [l for l in lines if f"CertCommonName({CN})" in l or any(z in l for z in zids)]
print("lines with slot 3's common name or a goat session ID:", len(mine))
print("of them 'Using cached result' lines:", sum("Using cached result" in l for l in mine))
act = re.compile(r"\+([0-9a-f]{32}) is (?:un)?authorized to (.+?) \((ingress|egress)\) on (\S+)$")
# The cache block of a session: the key of its first access-control line
# (the cached key expression, logged in one burst when the session declares it).
cache_key = {}
for l in mine:
    m = act.search(l)
    if m and m.group(1) not in cache_key:
        cache_key[m.group(1)] = m.group(4)
print("cached key expression per session:", cache_key)
left = []
n_sub = n_del = n_cache = 0
span = {}
for l in mine:
    m = act.search(l)
    if not m:
        left.append(l); continue
    zid, action, flow, key = m.groups()
    if action == "Declare Subscriber" and flow == "ingress":
        n_sub += 1; continue
    if action == "Put" and flow == "egress" and re.fullmatch(r"[0-9a-f]{32}/telemetry/sapient/p1/v2/[a-z_]+/[0-9a-f-]{36}", key):
        n_del += 1; continue
    if key == cache_key.get(zid):
        n_cache += 1; span.setdefault(zid, []).append(l.split()[2]); continue
    left.append(l)
print("removed: Declare Subscriber (ingress):", n_sub)
print("removed: Put (egress) on a full sample key:", n_del)
print("removed: cache block lines:", n_cache)
for zid, ts in span.items():
    print("cache block of", zid + ":", len(ts), "lines, from", min(ts), "to", max(ts))
print("left:", len(left))
for l in left:
    print("LEFT", l)
