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
