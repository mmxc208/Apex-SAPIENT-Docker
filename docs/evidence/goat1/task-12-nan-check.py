"""Does Apex's validator, with the fusion node's options, pass a detection at a NaN or infinite location?"""
from datetime import datetime, timezone
import fake_fusion_node as f
from fake_fusion_node import load_template, VALIDATION_OPTIONS, Validator
from sapient_link import stamp
NODE = "1aef1b86-0000-4000-8000-000000000001"
for value in (float("nan"), float("inf")):
    msg = stamp(load_template("sensor", "DetectionReport"), NODE)
    msg.detection_report.location.x = value
    errors = []
    Validator(VALIDATION_OPTIONS).validate_sapient_message(msg, datetime.now(timezone.utc).replace(tzinfo=None), errors)
    print(f"location.x={value}: validator errors {errors}")
    track = f.Track(msg.detection_report)
    print(f"  Track kept at x={track.detection.location.x}; distance to itself {f.distance_m(track.detection.location, msg.detection_report.location)}")
