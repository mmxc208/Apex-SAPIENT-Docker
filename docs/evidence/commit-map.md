# Old and new commit hashes of steps 4 and 4b

On 2026-11-19 the evidence files (`docs/evidence/goat4/*.txt` and `docs/evidence/goat4b/*.txt`) were taken out of the history of the two branches, before their first push. That changed the hash of every commit. The records, the README and the evidence files name the old hashes, because they were written before. This table gives the new hash of each old one. A commit that held only evidence files has no new hash. The old commits were never pushed.

## step 4, branch `goat-step4-cuaslab`

| Old | New | Subject |
|---|---|---|
| `b8e50e6` | `b8e50e6` | docs(goat): the design of step 4, the step 1 rig on the real goatnet cuaslab |
| `397cbb9` | `397cbb9` | docs(goat): the plan of step 4, seven tasks and checks G4-01 to G4-13 |
| `7257fc8` | `7257fc8` | feat(goat4): the enrolment script for a goatnet portal, with tests against a fake portal |
| `5e45098` | `5e45098` | fix(goat4): accept 201 from the portal, verify bundles, bound curl, more stop-path tests |
| `ffd576e` | `ffd576e` | fix(goat4): choose the bundle root by parsing and verifying, keep one root across bundles |
| `49d4b4a` | gone: it held only evidence files | docs(goat4): evidence of the enrolment of three machines on cuaslab |
| `1aa9a97` | `3767537` | feat(goat4): a pairing probe for a goatnet router, and check G4-01 on cuaslab |
| `bec8fee` | gone: it held only evidence files | docs(goat4): the rest of the Task 2 evidence: the grant, the verify output, the decision and the portal change |
| `2ad61b0` | `8e325ad` | fix(goat4): the pairing probe counts only its own run, opens both sessions independently, and always reports |
| `3950b31` | `b728a38` | feat(goat4): the overlay that puts the rig on cuaslab, and checks G4-02 to G4-04 |
| `11a9db4` | gone: it held only evidence files | docs(goat4): evidence of checks G4-05 to G4-10 and G4-13 |
| `560ddce` | gone: it held only evidence files | docs(goat4): evidence of checks G4-11 and G4-12 |
| `ef3e071` | gone: it held only evidence files | docs(goat4): addendum to task 6 evidence (anchors, recorder volume, rig state) |
| `5784f38` | `c7c0487` | docs(goat4): the acceptance record of step 4, the run steps, and the updates to the context and the roadmap |
| `0ddcdae` | gone: it held only evidence files | Add transcript of the step 4 README run as pasted into zsh |
| `5e59bb0` | `ed7391e` | docs(goat4): fix the review findings of the step 4 record, and record the README run |
| `aa47778` | `26038fd` | fix(goat4): stop enrolment before any portal call when a target path is not a regular file, report an unanswered enrolment as unknown, and sharpen goat4_ready |
| `87bc0fd` | gone: it held only evidence files | docs(goat4): transcript of README run 2, from the path checks through the G4-06 short outage, with the gated start |
| `86540ab` | `fe811c1` | docs(goat4): fix the final review findings: widen the secret rule, gate the README start on goat4_ready, record README run 2 and how to remove what step 4 left |
| `0cb7fc0` | `2790b06` | docs(goat4): gate the last start of the long-outage block on goat4_ready |
| `494e64b` | `1394cc9` | docs: the explainer page for goat step 4 and the goatlite stand-up |
| `311b304` | `7a65467` | docs(goat-context): the ingress gateway and the edge router compared; cut-off on our rig |

## step 4b, branch `goat-step4b-host-vm`

| Old | New | Subject |
|---|---|---|
| `7ae0801` | `4bae55a` | docs: the design of goat step 4b, the host on its own machine |
| `d6dd09e` | `db98c30` | docs: settle four questions of the builder check in the step 4b design |
| `2355db4` | `77e34e3` | docs: the plan of goat step 4b |
| `5969c5b` | `34fd47b` | feat(goat4b): the host VM definition, the overlay and the two-engine helpers |
| `bc72f1f` | `b486f73` | feat(goat4b): the host VM runs the host services; G4B-01 and G4B-02 |
| `4a2485f` | `3a761e8` | fix(goat4b): g4b_vm_sync refuses while the host services run |
| `ade0274` | `4d083eb` | fix(goat4b): sync guard fails closed; G4B-01/02 evidence completed |
| `5d1655c` | `d3f298c` | feat(goat4b): readers, a pod subscriber; g4b_state shows Lima's time sync and offset bounds |
| `3904f92` | `bdbf795` | feat(goat4b): g4b_clock_step and g4b_clock_restore stop and restart both clock syncs of goathost |
| `f50fc2f` | `41894a1` | feat(goat4b): readers latency takes --since and --until |
| `f858f52` | gone: it held only evidence files | feat(goat4b): readers and a pod subscriber; G4B-03, 04, 05 and 11 |
| `87ef147` | `7a99358` | fix(goat4b): clock step restarts the syncs when the set fails; restore undoes the steps, needs both syncs active and the offset of before |
| `6351c82` | `4a133b2` | test(goat4b): scripts of G4B-06, G4B-07 and G4B-08, each restoring in a trap |
| `2c8e225` | gone: it held only evidence files | test(goat4b): G4B-06 clock tolerance, G4B-07 and G4B-08 link cuts |
| `eb9431f` | gone: it held only evidence files | test(goat4b): G4B-09 no regression, G4B-10 configuration only |
| `13f8a6c` | `a4fb526` | docs: hierarchy, echelon and how step 4b fits goat's ADRs |
| `f914d68` | `10eba18` | docs(goat4b): the acceptance record, the README section and the roadmap |
| `e24a81f` | `32e7c89` | docs(goat4b): fix round 1 of the record: the README's step 6 run as written, wording of inferred and untested points |
| `9eb749d` | `8b53176` | docs: the explainer page for goat step 4b |
| `a714aec` | `3026010` | fix(goat4b): guards on run/create/start/restart, route recovery in the refusals, hold flag first, optional env file |
| `e8e9bd4` | `c09cd03` | docs(goat4b): final review fixes to the record, the README, the explainer and the explainer index |
