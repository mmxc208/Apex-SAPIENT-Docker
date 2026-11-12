# Evidence of goat step 1 (pod 1 to host)

These files hold the outputs, logs and small scripts that `docs/acceptance-goat1.md` and README section "Goat step 1: pod 1 to host" quote or rest on. They were made in the working directory of the plan's tasks and copied here in Task 12, so that the record can be checked later.

**The one change made to the copies:** the absolute path of the workspace, the directory that holds this repository and `usareur-af`, is written `<workspace>`. Nothing else was changed. The private-data check before the copy found no private key material (`PRIVATE KEY`, `BEGIN `), no token and no password: the only `password` text is `"password":null` in the routers' printed configuration.

**Raw and plain files.** The `.txt` outputs and logs are raw: a log saved from `docker compose logs` keeps the routers' ANSI colour codes, and the output of a run pasted into `zsh -f -i -s` keeps zsh's prompts (`%`, carriage returns, the machine name `aidev-1`, `pipe quote>`). A file whose name ends in `-plain.txt` is the same log with the ANSI colour codes removed. To keep this directory below about 3 MB, Task 11's three raw logs that have a plain twin (`task-11-fabric-log-full.txt`, `task-11-readme-fabric-log.txt`, `task-11-router-trace.txt`) and Task 12's raw logs are left out; only their plain versions are here.

**The quote check.** From the repository root, `python3 docs/evidence/goat1/check-quotes.py` checks that every quoted log or output line of the README section and of the acceptance record is in a `.txt` file here, and that every README quote is in `task-12-readme-run.txt`.

**Scripts.** The scripts are kept as they ran, with the workspace path replaced. They source a local file `docker-env.sh` (it sets `DOCKER_HOST` and `DOCKER_CONFIG` for the sandbox the tasks ran in) that is not copied, and the older quote checks read the task working directory, so they do not run from here as they are.

## Files

The file names keep the task number of the plan. "On" names the commit the run was made on; Task 1 to Task 11 entries were recorded in later commits of the same task.

| File | What it is | Task, on commit |
|---|---|---|
| `README.md` | This index | 12 |
| `check-quotes.py` | The quote check of the final record, against this directory | 12 |
| `dg.sh` | The `dg` helper the scripted runs sourced | 9, `08ef7c2` |
| `task-1-run-1.9.0.txt` | First pairing probe run, one session: not evidence (see G1-01) | 1, `03adfca` |
| `task-1-run-1.9.0-restart.txt` | First pairing probe restart run, one session: not evidence | 1, `03adfca` |
| `task-1-run-1.9.0-fix1.txt` | Pairing probe with two sessions: `PAIRING OK put-sub liveliness` | 1, `8cb1bbe` |
| `task-1-run-1.9.0-restart-fix1.txt` | Pairing probe with a router restart: both `PAIRING OK` lines | 1, `8cb1bbe` |
| `task-9-up.txt` | Bring-up of the step 1 rig | 9, `08ef7c2` |
| `task-9-g1-02.txt` | G1-02, tracks, alert and host records | 9, `08ef7c2` |
| `task-9-g1-03.txt` | G1-03, registration | 9, `08ef7c2` |
| `task-9-g1-04.txt` | G1-04, a task down | 9, `08ef7c2` |
| `task-9-g1-05.sh` | Script of the G1-05 access probes | 9, `08ef7c2` |
| `task-9-g1-05.txt` | G1-05 output, with trace lines shortened to `CN=` | 9, `08ef7c2` |
| `task-9-g1-11.txt` | G1-11, unit suite and stage 4 steps 1 and 2 | 9, `08ef7c2` |
| `task-9-host-restart.txt` | Host fusion node restart, with the whole chain of task `N7F0BG` | 9, `08ef7c2` |
| `task-9-check-records.py` | Checker of the host recorder's records | 9, `08ef7c2` |
| `task-9-readme-blocks.zsh` | README steps 1 to 6 as pasted into zsh | 9, `08ef7c2` |
| `task-9-readme-run.txt` | Output of that README run | 9, `08ef7c2` |
| `task-9-radar2-mount.txt` | Check that `radar2` mounts its own files | 9, `e64193e` |
| `task-9-quote-check.txt` | Quote check of the Task 9 record | 9, `8db9951` |
| `task-10-g1-06.sh`, `task-10-g1-06.txt`, `task-10-g1-06-logs.txt` | G1-06 script, output and saved logs | 10, `8db9951` |
| `task-10-g1-07.sh`, `task-10-g1-07.txt`, `task-10-g1-07-logs.txt` | G1-07 script, output and saved logs | 10, `8db9951` |
| `task-10-g1-08.txt` | G1-08 unit tests | 10, `8db9951` |
| `task-10-g1-09.sh`, `task-10-g1-09.txt`, `task-10-g1-09-logs.txt` | G1-09 script, output and saved logs | 10, `8db9951` |
| `task-10-readme-blocks.zsh` | README steps 1 to 9 as pasted into zsh | 10, `8db9951` |
| `task-10-readme-run.txt` | Output of that README run | 10, `8db9951` |
| `task-10-readme-logs-1-7.txt`, `task-10-readme-logs.txt` | Logs saved before `dg down` in that run | 10, `8db9951` |
| `task-10-suite.txt` | Unit suite | 10, `8db9951` |
| `task-10-fix1-evidence.txt` | Counts and computed values added in the fix round | 10, `c3ed2aa` |
| `task-10-check-quotes.py`, `task-10-quote-check.txt`, `task-10-fix1-quote-check.txt` | Quote check of the Task 10 record and its outputs | 10 |
| `task-11-build.txt`, `task-11-build-full.txt` | First build of `goat-cli` (cache filled), short and full | 11, `4df6e2f` |
| `task-11-version.txt` | `goat --version` | 11, `4df6e2f` |
| `task-11-sub-help.txt` | `goat sub --help` | 11, `4df6e2f` |
| `task-11-run.txt`, `task-11-run-shortened.txt`, `task-11-run-times.txt` | `goat sub` runs by hand | 11, `4df6e2f` |
| `task-11-router-trace-plain.txt`, `task-11-fabric-log-plain.txt` | Fabric router trace of the runs by hand, plain | 11, `4df6e2f` |
| `task-11-readme-blocks.zsh` | README step 10 as pasted into zsh | 11, `4df6e2f` |
| `task-11-readme-run.txt` | Output of that README run | 11, `4df6e2f` |
| `task-11-readme-fabric-log-plain.txt` | Fabric router trace of that run, plain | 11, `4df6e2f` |
| `task-11-fix1-n1-count.py`, `task-11-fix1-n1-count.txt` | Count of goat's lines in that trace | 11, `607749b` |
| `task-11-check-quotes.py`, `task-11-fix1-check-quotes.py`, `task-11-quote-check.txt`, `task-11-fix1-quote-check.txt` | Quote checks of the Task 11 record and their outputs | 11 |
| `task-12-suite.txt` | Unit suite of the final run | 12, `c6a2db1` |
| `task-12-make-blocks.py` | Writes the paste file from the README's bash blocks, verbatim, with marker and log-saving lines between blocks | 12, `c6a2db1` |
| `task-12-readme-blocks.zsh` | README steps 1 to 10 as pasted into zsh in the final run | 12, `c6a2db1` |
| `task-12-readme-run.txt` | Output of the final run; every README quote is from this file | 12, `c6a2db1` |
| `task-12-logs-1-4-plain.txt` | All logs before the router restart of step 5 | 12, `c6a2db1` |
| `task-12-logs-5-plain.txt` | All logs with both routers at the access-control trace (step 5) | 12, `c6a2db1` |
| `task-12-logs-6-7-plain.txt` | All logs before `dg down` of step 8 (steps 5 to 7) | 12, `c6a2db1` |
| `task-12-logs-8-10-plain.txt` | All logs at the end of the run (steps 8 to 10) | 12, `c6a2db1` |
| `task-12-fabric-trace-10-plain.txt` | Fabric router trace of step 10 | 12, `c6a2db1` |
| `task-12-g1-10-count.txt` | `task-11-fix1-n1-count.py` on that trace | 12, `c6a2db1` |
| `task-12-g1-01-08-11.sh`, `task-12-g1-01-08-11.txt` | G1-08 tests, G1-11 stage 4 steps 1 and 2, and G1-01 pairing probe of the final run | 12, `c6a2db1` |
| `task-12-nan-check.py`, `task-12-nan-check.txt` | Apex's validator on a detection at a NaN and an infinite location | 12, `c6a2db1` |
