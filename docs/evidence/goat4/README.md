# Evidence of goat step 4 (the step 1 rig on cuaslab)

These files hold the outputs that `docs/acceptance-goat4.md` and the section "Goat step 4: the step 1 rig on cuaslab" of `README-goat.md` quote or rest on. Each task of the plan wrote its files here directly during its run and committed them; nothing was copied or changed afterwards. Where a file is unclear, the record says so; the files are not tidied.

**What the files hold and what they do not.** They hold anchors, machine handles, node IDs and the public subject lines of certificates. They hold no operator key, no slot private key, no API key, no bundle token, no bundle download path and no slot pool salt. Portal answers were saved with chosen fields only (`task-2-machines.txt`, `task-2-grant.txt`). `task-5-extra-missing-env.txt` holds the absolute path of the workspace, as compose printed it. `task-2-verify.txt` line 8 is the header of the secret search that Task 2 ran; it names the search patterns, and the quote check allows that one line.

**The quote check.** From the repository root, `python3 docs/evidence/goat4/check-quotes.py` checks that every line of a `text` block of the README section, and every quoted log or output line of the record, is in a `.txt` file here. Step 4 has no single README run, so README lines are searched in all the `.txt` files. It also searches every file below this directory for five secret patterns (a private key header, a portal key prefix, and three field or path names of the enrolment answer) and fails on any match except the allowed line above. The patterns are written in pieces in the script, so that the script does not match itself. The rule was tested once with a scratch file that held one of the patterns: the check failed, and the file was removed.

**Scripts.** The scripts that ran the checks of Tasks 4 to 6 were in the working directory of the plan and are not kept here. Each file prints its commands, or names them in a comment. `README-goat.md` writes them out for zsh.

## Files

The last column gives the task, the commit that was checked out when the file was made ("on top of"), and the commit that first holds the file ("held in"). "On top of" is read from the times of the files and of the commits; no run saved `git rev-parse HEAD`. See the runs table of `docs/acceptance-goat4.md`.

| File | What it is | Task: on top of → held in |
|---|---|---|
| `README.md` | This index | 7: `ef3e071` → the commit of the record |
| `check-quotes.py` | The quote check and the secret rule of step 4 | 7: `ef3e071` → the commit of the record |
| `task-2-enrol-refused.txt` | The first run of `goat4/enroll.sh`: refused, HTTP 500, code `mint` | 2: `ffd576e` → `49d4b4a` |
| `task-2-refusal-diagnosis.txt` | Read-only diagnosis of the refusal: the portal's log line, the empty directory on the box, the setting, the portal's state after | 2: `49d4b4a` → `49d4b4a`, changed in `bec8fee` |
| `task-2-decision-and-portal-change.txt` | Richard's decision, the fast-forward of the goatcore checkout, the diff of the setting, lines of the `goatbuilder deploy` output, the portal's state after | 2: `49d4b4a` → `bec8fee` |
| `task-2-enrol.txt` | The second run of `goat4/enroll.sh`: three handles and anchors | 2: `ffd576e` → `49d4b4a` |
| `task-2-machines.txt` | The portal's machine list, six fields of each machine | 2: `ffd576e` → `49d4b4a` |
| `task-2-grant.txt` | The grant of the custodian, and the key names of a machine entry | 2: `49d4b4a` → `bec8fee` |
| `task-2-verify.txt` | `openssl verify` of the three certificates against the root, and the secret search | 2: `49d4b4a` → `bec8fee` |
| `task-3-g4-01.txt` | G4-01, the pairing probe, success case (replaces the run of `1aa9a97`) | 3: `bec8fee` → `2ad61b0` |
| `task-3-g4-01-unreachable.txt` | G4-01 failure case: port 7449 | 3: `bec8fee` → `2ad61b0` |
| `task-3-g4-01-reader-bad-ca.txt` | G4-01 failure case: the reader has the step 1 pod CA | 3: `bec8fee` → `2ad61b0` |
| `task-4-config-and-ready.txt` | The merged configuration of `dg4`, and the cases of `goat4_ready` | 4: `2ad61b0` → `3950b31` |
| `task-4-start.txt` | Generator, `goat4_ready`, `dg4 up -d`, services, router error count | 4: `2ad61b0` → `3950b31` |
| `task-4-rig-state.txt` | `dg4 ps`: images and containers of the rig | 4: `2ad61b0` → `3950b31` |
| `task-4-g4-02.txt` | G4-02, tracks, alert and host records | 4: `2ad61b0` → `3950b31` |
| `task-4-g4-03.txt` | G4-03, registration, and the pod bridge's lines | 4: `2ad61b0` → `3950b31` |
| `task-4-g4-04.txt` | G4-04, a task down | 4: `2ad61b0` → `3950b31` |
| `task-5-g4-05-fabric.txt` | G4-05 fabric part: two directions, each with a control write | 5: `3950b31` → `11a9db4` |
| `task-5-g4-05-pod.txt` | G4-05 pod part: case 4 of G1-05 | 5: `3950b31` → `11a9db4` |
| `task-5-g4-06-precheck.txt` | With `mesh` disconnected, the bridge cannot reach the router | 5: `3950b31` → `11a9db4` |
| `task-5-g4-06.txt` | G4-06, short outage | 5: `3950b31` → `11a9db4` |
| `task-5-g4-07.txt` | G4-07, long outage | 5: `3950b31` → `11a9db4` |
| `task-5-g4-08.txt` | G4-08, the unit tests of G1-08 | 5: `3950b31` → `11a9db4` |
| `task-5-g4-09.txt` | G4-09, join with no router restart, and the clean-up | 5: `3950b31` → `11a9db4` |
| `task-5-g4-10.txt` | G4-10, `goat sub` on the Mac: keys counted, payloads not printed | 5: `3950b31` → `11a9db4` |
| `task-5-g4-13.txt` | G4-13, the clock offsets of the two VMs | 5: `3950b31` → `11a9db4` |
| `task-5-extra-connected.txt` | The three fabric clients' connection lines to the `cuaslab` router | 5: `3950b31` → `11a9db4` |
| `task-5-extra-missing-env.txt` | With `goat4.env` moved aside, compose refuses | 5: `3950b31` → `11a9db4` |
| `task-6-unit-suite.txt` | G4-11, the unit suite | 6: `11a9db4` → `560ddce` |
| `task-6-step1-rig.txt` | G4-11, the step 1 rig: start, G1-03, G1-02, `dg down` | 6: `11a9db4` → `560ddce` |
| `task-6-g4-12.txt` | G4-12, the two `git diff` outputs | 6: `11a9db4` → `560ddce` |
| `task-6-addendum.txt` | Addendum to G4-11, written after the run at 00:13 UTC: the `dg` definition, the step 1 and `cuaslab` anchors, the recorder check script, the anchors in the step 1 host recorder's volume, and the state of both compose projects afterwards | 6: `560ddce` → `ef3e071` |
