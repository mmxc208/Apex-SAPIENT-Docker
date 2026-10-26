"""Send one BSI Flex 335 v2.0 Registration to Apex and print the reply.

Usage: python smoke_test.py [port] [host]   (defaults: 5020 127.0.0.1)
"""
import socket, struct, uuid, sys
from sapient_msg.bsi_flex_335_v2_0.sapient_message_pb2 import SapientMessage

port = int(sys.argv[1]) if len(sys.argv) > 1 else 5020
host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
m = SapientMessage()
m.timestamp.GetCurrentTime()
m.node_id = str(uuid.uuid4())
r = m.registration
r.node_definition.add(node_type=2)  # NODE_TYPE_RADAR
r.icd_version = "BSI Flex 335 v2.0"
r.name = "docker-smoke-radar"
r.short_name = "smoke"
r.capabilities.add(category="test", type="test")
r.status_definition.status_interval.units = 1
r.status_definition.status_interval.value = 5
r.config_data.add(manufacturer="Test", model="Smoke")
md = r.mode_definition.add(mode_name="default", mode_type=1)  # MODE_TYPE_PERMANENT
md.settle_time.units = 1
md.settle_time.value = 1
md.detection_definition.add(location_type=dict(location_units=1, location_datum=2))
md.task.region_definition.region_type.append(1)
md.task.region_definition.region_area.add(location_units=1, location_datum=2)

data = m.SerializeToString()
s = socket.create_connection((host, port), timeout=5)
s.sendall(struct.pack("<I", len(data)) + data)
n = struct.unpack("<I", s.recv(4))[0]
buf = b""
while len(buf) < n:
    buf += s.recv(n - len(buf))
reply = SapientMessage.FromString(buf)
print("reply type:", reply.WhichOneof("content"))
print(reply)
