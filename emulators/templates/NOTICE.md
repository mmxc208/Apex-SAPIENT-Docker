# Message templates

These JSON files are copied unchanged from the SAPIENT BSI Flex 335 v2 Test Harness 5.2.4 (commit `6a2999d`):

- `sensor/` comes from `SapientAsmSimulator/SapientAsmSimulator/Default*.json`, the edge-node (ASM) simulator.
- `fusion_node/` comes from `SapientDmmSimulator/SapientDmmSimulator/Default*.json`, the fusion-node (DMM) simulator.

Crown owned Copyright 2021-2024. Licensed under the Apache License, Version 2.0.

The emulators load each file as a v2.0 `SapientMessage` to get its structure. They then replace the IDs, timestamps, locations, classes and task commands with live values. The files hold placeholder values, for example UTM zone `30U` next to latitude/longitude numbers, so do not use them as examples of correct content.
