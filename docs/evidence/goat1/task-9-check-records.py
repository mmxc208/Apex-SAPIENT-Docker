"""G1-02: read the host recorder's JSON lines on stdin; check anchors and node IDs."""
import collections, json, os, sys
env = dict(line.strip().split("=", 1) for line in open("zenoh/goat1/goat1.env") if "=" in line)
anchors = {env["FABRIC_POD1_ID"], env["FABRIC_HOST_FUSION_ID"]}
sensors = {env["POD1_RADAR_ID"], env["POD1_CAMERA_ID"], env["POD1_VEHICLE_ID"]}
lines = [json.loads(l) for l in sys.stdin if l.strip()]
bad_anchor = [r for r in lines if r.get("anchor") not in anchors]
sensor_node = [r for r in lines if r.get("msg", {}).get("node_id") in sensors]
kinds = collections.Counter((r.get("anchor", "?")[:8], r.get("kind", "?")) for r in lines)
print("records:", len(lines))
print("keys of first record:", sorted(lines[0]) if lines else None)
for k, n in sorted(kinds.items()):
    print("  ", k, n)
print("node_ids seen:", sorted({r.get("msg", {}).get("node_id") for r in lines}))
print("records with an anchor outside FABRIC_POD1_ID/FABRIC_HOST_FUSION_ID:", len(bad_anchor))
print("records whose msg.node_id is the radar, camera or vehicle:", len(sensor_node))
print("PASS" if lines and not bad_anchor and not sensor_node else "FAIL")
