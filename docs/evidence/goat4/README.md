# Evidence of goat step 4 (the step 1 rig on cuaslab)

These files hold the outputs that `docs/acceptance-goat4.md` and the section "Goat step 4: the step 1 rig on cuaslab" of `README-goat.md` quote or rest on. Most files were written here during the run they record and then committed: those of Tasks 3 to 6, `task-2-enrol-refused.txt`, `task-2-enrol.txt`, `task-2-machines.txt`, and the transcripts of the two README runs (`readme-run.txt`, `readme-run-2.txt`). Some were written after the event, and the table says so: `task-6-addendum.txt`, after the run of Task 6; and `task-2-decision-and-portal-change.txt`, `task-2-grant.txt` and `task-2-verify.txt`, written on top of `49d4b4a` by the controller of the session, after the deploy and the second enrolment. The decision file is an account, with output lines copied from the session and from the deploy log. One file was changed after it was first committed: `task-2-refusal-diagnosis.txt`, first held in `49d4b4a`, changed in `bec8fee`. Where a file is unclear, the record says so; the files are not tidied.

**What the files hold and what they do not.** They hold anchors, machine handles, node IDs and the public subject lines of certificates. They hold no operator key, no slot private key, no API key, no bundle token, no bundle download path and no slot pool salt. Portal answers were saved with chosen fields only (`task-2-machines.txt`, `task-2-grant.txt`). `task-5-extra-missing-env.txt` holds the absolute path of the workspace, as compose printed it. `task-2-verify.txt` line 8 is the header of the secret search that Task 2 ran; it names the search patterns, and the quote check allows that one line. That search looked for a key prefix that no key of this portal has, so it was weaker than it reads (see below).

**The quote check.** From the repository root, `python3 docs/evidence/goat4/check-quotes.py` checks two kinds of quote. Each line of a `text` block of the README section must be in one of the evidence files that the README names next to that block (in the prose between the code block before it and the block, or between the block and the next code block); `readme-run.txt` is not used for this, because the outputs shown are those of the task runs, and a block next to which no file is named fails the check. Each inline code span of the record that looks like a log or output line, by the patterns of the script (`LOGLIKE`), must be in one of the `.txt` files here; a span that the patterns do not match is not checked, so a quote with an unusual form can be missed. The options `--record` and `--readme` take another path for a test against a scratch copy. It also searches every file below this directory for secrets, and fails on any match except an allowed line. Since the final fix wave the patterns are: a private key header; three field or path names of the enrolment answer (API key, bundle token, bundle path); a machine API key in the shape the portal mints (a fixed prefix, an id, 64 hexadecimal characters); any string of 64 hexadecimal characters, except a docker image digest (`sha256:` before it); and any standalone token of 40 or more letters, digits, `_` and `-` that is not purely hexadecimal and has no `/` next to it, the shape of the operator key, which has no fixed prefix. Before that wave the rule had a key prefix pattern that matched no real key of this portal, so a bare API key, token or operator key would have passed. The patterns are written in pieces in the script, so that the script does not match itself.

**The allowed lines.** Each was looked at and judged harmless; each is allowed by its exact text in its file:

| File | Lines | What they are |
|---|---|---|
| `task-2-verify.txt` | 8 | the header of Task 2's secret grep; it names the patterns |
| `task-5-g4-08.txt` | 15, 16 | two unit test names of G1-08, as pytest prints them |
| `readme-run.txt` | 462, 463 | the same two test names (block 13) |
| `task-5-g4-09.txt` | 4, 5, 13, 14 | the SHA-256 of the two router files of the step 1 generator, before and after |
| `readme-run.txt` | 488, 489, 497, 498 | the same two SHA-256 lines (block 14) |
| `readme-run.txt` | 727, 730, 794, 801, 810 | a line of 60 `-` that separates the parts of the step 1 appendix |
| `task-2-refusal-diagnosis.txt` | 20 | the name of the portal's staging directory of the refused run: `stage`, the anchor and a UTC time |

**Tests of the rule.** In Task 7 and in its first fix round a scratch file with one of the old patterns made the check fail, and a scratch copy of the record, and of the README, each with one quoted line altered, made it fail too. In the final fix wave a scratch `.txt` file here held, in turn, a made-up string of each of the three key shapes (a machine API key, a bare 64-hex string, a 43-character token); each time the check exited 1, and the file was removed.

**Scripts.** The scripts that ran the checks of Tasks 4 to 6 were in the working directory of the plan and are not kept here. Each file prints its commands, or names them in a comment. `README-goat.md` writes them out for zsh.

## Files

The last column gives the task, the commit that was checked out when the file was made ("on top of"), and the commit that first holds the file ("held in"). "On top of" is read from the times of the files and of the commits; no run saved `git rev-parse HEAD`. See the runs table of `docs/acceptance-goat4.md`.

| File | What it is | Task: on top of → held in |
|---|---|---|
| `README.md` | This index | 7: `ef3e071` → `5784f38`, changed in fix round 1 of Task 7 and in the final fix wave |
| `check-quotes.py` | The quote check and the secret rule of step 4 | 7: `ef3e071` → `5784f38`, changed in fix round 1 of Task 7 and in the final fix wave (the secret rule) |
| `task-2-enrol-refused.txt` | The first run of `goat4/enroll.sh`: refused, HTTP 500, code `mint` | 2: `ffd576e` → `49d4b4a` |
| `task-2-refusal-diagnosis.txt` | Read-only diagnosis of the refusal: the portal's log line, the empty directory on the box, the setting, the portal's state after | 2: `49d4b4a` → `49d4b4a`, changed in `bec8fee` |
| `task-2-decision-and-portal-change.txt` | Written after the event: an account of Richard's decision, the fast-forward of the goatcore checkout, the diff of the setting, lines of the `goatbuilder deploy` output, the portal's state after | 2: `49d4b4a` → `bec8fee` |
| `task-2-enrol.txt` | The second run of `goat4/enroll.sh`: three handles and anchors | 2: `ffd576e` → `49d4b4a` |
| `task-2-machines.txt` | The portal's machine list, six fields of each machine | 2: `ffd576e` → `49d4b4a` |
| `task-2-grant.txt` | Written after the event: the grant of the custodian, and the key names of a machine entry | 2: `49d4b4a` → `bec8fee` |
| `task-2-verify.txt` | Written after the event: `openssl verify` of the three certificates against the root, and the secret search | 2: `49d4b4a` → `bec8fee` |
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
| `readme-run.txt` | The README run: the step 4 section of `README-goat.md` run as written, as one `zsh -f` script with stdin at `/dev/null`, 2026-11-19 00:30 to 00:41 UTC; 18 blocks, the enrolment not run; then steps 1 to 3 of the step 1 section and `dg down`. Its first line and the subject of `0ddcdae` say "pasted"; it was not a paste | README run: `5784f38` → `0ddcdae` |
| `readme-run-2.txt` | README run 2: blocks 1 to 11 of the step 4 section (the path checks through the G4-06 outage, with the gated start and the wait of 60 s), as one `zsh -f` script with stdin at `/dev/null`, 2026-11-19 01:07 to 01:13 UTC; the enrolment not run; a gate exercise with `goat4.env` moved aside; then `dg4 down` | README run 2: `aa47778` and the uncommitted README → `87bc0fd` |
| `task-6-addendum.txt` | Addendum to G4-11, written after the run at 00:13 UTC: the `dg` definition, the step 1 and `cuaslab` anchors, the recorder check script, the anchors in the step 1 host recorder's volume, and the state of both compose projects afterwards | 6: `560ddce` → `ef3e071` |
