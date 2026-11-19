# Evidence of goat step 4b (the host on its own machine)

**The evidence files are not in git.** On 2026-11-19, before the first push of this branch, Richard decided that evidence files are not kept in git. The `.txt` files of `docs/evidence/goat4b/` were taken out of the history of the branch and git ignores them from now on (`.gitignore`). They stay on the machine that made the runs. The record `docs/acceptance-goat4b.md` still names them and quotes from them. A clone of the repository holds the record, the index `docs/evidence/goat4b/README.md` and the quote checker, but not the files, so the checker cannot run in a clone. Taking the files out changed the hash of every commit of the branch. The hashes in the record, in the README and in the files are the old ones; `docs/evidence/commit-map.md` gives the new hash of each, and says which commits held only evidence files and are gone. The rest of this index describes the files as they are on that machine.

These files hold the outputs that `docs/acceptance-goat4b.md` and the section "Goat step 4b: the host on its own machine" of `README-goat.md` quote or rest on. Each was written here during the run it records and then committed; a few have a section appended later in the same task, and the section's heading says when. Each starts with the UTC time and the short commit that was checked out (the files of Task 5 put the two on two lines). Where that commit does not hold the code that ran, the record says so. Where a file is unclear, the record says so; the files are not tidied.

**The run scripts of Task 4.** The files `task-4-*.txt` were made by `goat4b/run_g4b_06.sh`, `run_g4b_07.sh` and `run_g4b_08.sh` as committed in `6351c82`. In the final review's fix wave, `a714aec` changed `run_g4b_07.sh`, `run_g4b_08.sh` and `goat4b/run_lib.sh` (which all three source) after these runs; the changed scripts were not run again.

**What the files hold and what they do not.** They hold anchors, node IDs, task IDs, VM and container addresses on the vzNAT network and on Docker's networks, image IDs, the names and modes of the key files (never their content), and the public route files. They hold no private key, no certificate body, no API key, no bundle token and no operator key. Home paths in the outputs are shortened to `~`, also where a path was URL-encoded (`task-3-clock-step-trial.txt`, line 35, the address of Lima's forwarded Docker socket). The files hold no user name and no host name of the Mac.

**The quote check.** From the repository root, `python3 docs/evidence/goat4b/check-quotes.py` checks two kinds of quote, by the method of step 4. Each line of a `text` block of the README's step 4b section must be in one of the evidence files that the README names next to that block (in the prose between the code block before it and the block, or between the block and the next code block); `readme-run.txt` is not used for this, because the outputs shown are those of the task runs, and a block next to which no file is named fails the check. Each inline code span of the record that looks like a log or output line, by the patterns of the script (`LOGLIKE`), and not like a command (`COMMAND`), must be in one of the `.txt` files here; a span that the patterns do not match is not checked, so a quote with an unusual form can be missed. A record span is found if any `.txt` file of this directory holds it, not only the file the record names beside it, so a short span could be matched by an unrelated file; the checker prints where it found each span. The options `--record` and `--readme` take another path for a test against a scratch copy.

**The two checkers and the README.** This checker reads only the step 4b section of `README-goat.md`: from its heading to the next heading of its level, or the end of the file. The step 4 checker, `docs/evidence/goat4/check-quotes.py`, reads its own section the same way, so it stops at the heading of step 4b; neither rule had to change, and both exit 0.

**The secret rule.** The check also searches every file below this directory, the record and the README's step 4b section, and fails on any match except an allowed line. The patterns are those of step 4: a private key header; three field or path names of the enrolment answer (API key, bundle token, bundle path); a machine API key in the shape the portal mints; any string of 64 hexadecimal characters, except a docker image digest (`sha256:` before it); any standalone token of 40 or more letters, digits, `_` and `-` that is not purely hexadecimal and has no `/` next to it, the shape of the operator key. Step 4b adds one: an absolute path below the Mac's home directories, which would hold the user name. The patterns are written in pieces in the script, so that the script does not match itself.

**The allowed lines.** Each was looked at and judged harmless; each is allowed by its exact text in its file:

| File | Lines | What they are |
|---|---|---|
| `task-2-g4b-01.txt` | 61, 66 | the anonymous Docker volumes of the two host services (the image's `/apex/data`), which Docker names with 64 hexadecimal characters |
| `task-5-unit-suite.txt` | 18 | the line of 70 `-` that `unittest` prints before its count |

**Tests of the rule.** In Task 6, a scratch copy of the record with one quoted count changed, and a scratch copy of `README-goat.md` with one line of a `text` block changed, each made the check exit 1 with the line named as missing; a scratch `.txt` file here with a made-up path below the home directories made it exit 1 with one secret match, and was removed. Then the check exited 0.

## Files

The last column gives the task, the commit that was checked out when the file was made ("on top of", read from the file's header and the times; see the runs table of the record), and the commit that first holds the file ("held in").

| File | What it is | Task: on top of → held in |
|---|---|---|
| `README.md` | This index | 6: `eb9431f` → the commit of the record |
| `check-quotes.py` | The quote check and the secret rule of step 4b | 6: `eb9431f` → the commit of the record |
| `task-2-vm.txt` | The VM `goathost`: version, address, MTU, OS, Docker, the image IDs, the sync, the routes, the engine path, Lima's time sync | 2: `5969c5b` with the code of `bc72f1f` uncommitted → `bc72f1f` |
| `task-2-goatlite-change.txt` | The one change in `goatlite`: the route file, its content, the live route, the merged routes, the two lines that remove them | 2: `5969c5b` with the code of `bc72f1f` uncommitted → `bc72f1f` |
| `task-2-ready.txt` | `goat4b_ready`: the good state and three failure cases, each restored and checked; section 5, at the end of the task, `goat4b_ready` and `g4b_state` | 2: `5969c5b` (cases 1 to 4), `bc72f1f` (section 5) → `bc72f1f`, section 5 added in `4a2485f` |
| `task-2-sync-while-running.txt` | The defect seen live: `g4b_vm_sync` while the host services ran; the refusal after the fix; the restore | 2: `bc72f1f` with the fix uncommitted → `4a2485f` |
| `task-2-g4b-01.txt` | G4B-01: services on each engine, counts on the wrong engine, the image IDs, the files in the VM, the bind mounts, log lines; a section of the fix round with the running instances' lines | 2: `bc72f1f` → `bc72f1f`, fix-round section (`4a2485f`) added in `ade0274` |
| `task-2-g4b-02.txt` | G4B-02: one TCP attempt for each path, the controls, networks and routes; a section of the fix round with two more controls and the networks of all ten services | 2: `bc72f1f` → `bc72f1f`, fix-round section (`4a2485f`) added in `ade0274` |
| `task-3-g4b-05-natural.txt` | G4B-05, first part: `g4b_state`, apparent ages and rejections with no clock touched | 3: `5d1655c` → `f858f52` |
| `task-3-clock-step-trial.txt` | A trial of `g4b_clock_step 0.5` for 45 s and `g4b_clock_restore`; an appendix with the 4 tasks the pod dropped | 3: `3904f92` → `f858f52` |
| `task-3-clock-set.txt` | Why the clock was not disciplined, and `g4b_state` | 3: `3904f92` → `f858f52` |
| `task-3-g4b-03.txt` | G4B-03: detection, alert and registration lines, the host recorder's counts | 3: `3904f92` → `f858f52` |
| `task-3-g4b-04.txt` | G4B-04: a partial first section (12:46 to about 12:47), which stopped because its choice of task found an empty suffix, before the interruption of Task 3, and is not evidence; then the section run again after it: one task hop by hop, and the control with the bridge stopped | 3: `3904f92` → `f858f52` |
| `task-3-g4b-05.txt` | G4B-05, second part: the offsets of the three VMs (30 rounds), apparent ages and rejections over 5 minutes, `g4b_state` | 3: `f50fc2f` → `f858f52` |
| `task-3-g4b-11.txt` | G4B-11: task latency in the window and since the start, and each task of the window | 3: `f50fc2f` → `f858f52` |
| `task-3-state-end.txt` | The state at the end of Task 3 | 3: `f50fc2f` → `f858f52` |
| `task-4-trap-demo.txt` | `run_g4b_06.sh` killed with SIGTERM during a step: its trap restored the clock; a check appended | 4: `6351c82` → `2c8e225` |
| `task-4-g4b-06.txt` | G4B-06: the six offsets, each with both directions and a `SUMMARY` line, the restore, 60 s after it, the trap; a note on the down direction appended | 4: `6351c82` → `2c8e225` |
| `task-4-g4b-07-short.txt` | G4B-07 short: a blackhole of 30 s in Colima | 4: `6351c82` → `2c8e225` |
| `task-4-g4b-07-long.txt` | G4B-07 long: the host services with a hold time of 20 s, a blackhole of 40 s, then the default hold time | 4: `6351c82` → `2c8e225` |
| `task-4-g4b-08.txt` | G4B-08: a blackhole of 30 s in `goathost`, the host's log, records by 5 s, `StartedAt` | 4: `6351c82` → `2c8e225` |
| `task-4-state-end.txt` | The state at the end of Task 4 | 4: `6351c82` → `2c8e225` |
| `task-5-down.txt` | Both projects down, no container left on either engine | 5: `2c8e225` → `eb9431f` |
| `task-5-unit-suite.txt` | G4B-09: the unit suite, and the tests of `goat4/` and `goat4b/` | 5: `2c8e225` → `eb9431f` |
| `task-5-step4-rig.txt` | G4B-09: the step 4 rig, all in Colima | 5: `2c8e225` → `eb9431f` |
| `task-5-step1-rig.txt` | G4B-09: the step 1 rig | 5: `2c8e225` → `eb9431f` |
| `task-5-g4b-10.txt` | G4B-10: the two `git diff` outputs | 5: `2c8e225` → `eb9431f` |
| `task-5-rig-back.txt` | The step 4b rig started again after Task 5 | 5: `2c8e225` → `eb9431f` |
| `readme-run-step6.txt` | Step 6 of the README's step 4b section (G4B-05, G4B-11) run once as written against the running rig, a reading only, 2026-11-19 14:14 to 14:15 UTC; the script is printed in the file | 6, fix round 1: `f914d68` → the commit of the fix round |
| `readme-run.txt` | The README run: steps 1 to 5 and the stop of the README's step 4b section, as one `zsh -f` script with stdin at `/dev/null`, 2026-11-19 13:55 to 14:01 UTC; the script is printed in the file; an appendix with the rig started again, `goat4b_ready` and `g4b_state` | 6: `eb9431f` with the README section uncommitted → the commit of the record |
