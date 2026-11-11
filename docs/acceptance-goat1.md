# Goat step 1 (pod 1 to host): acceptance

This checklist covers the plan in `docs/superpowers/plans/2026-11-11-goat-step1-pod-to-host.md`, on branch `goat`. Task 1 is the only task recorded so far; the commit is the one that adds this file.

A ticked box means a run recorded the evidence named on that line. It doesn't mean the whole requirement was met, so each line says what was measured and where it falls short. A check that could not run is recorded as unknown.

## G1-01: version pairing

- [x] **G1-01.** The Python binding in `apex-sapient:4.2.0` (zenoh 1.10.2) works over mutual TLS with a router from `eclipse/zenoh:1.9.0` (`zenohd v1.9.0`, arm64), with `zenoh/router-pairing.json5`. The default of `FABRIC_ZENOH_IMAGE` stays `eclipse/zenoh:1.9.0`.
  - `docker compose -f docker-compose.pairing.yml run --rm probe` printed `PAIRING OK put-sub liveliness`.
  - With `PROBE_WAIT_RESTART=1` and `docker compose -f docker-compose.pairing.yml restart zenohd` five seconds in, the probe printed `PAIRING OK put-sub liveliness` then `PAIRING OK after router restart`, exit code 0, with no new subscribe or declare call after the restart.
  - Falls short: one session, one subscriber, one token and one StatusReport-sized payload on a Docker network on one arm64 host. The router has no access control and a single restart was tried. Nothing was measured on a router built for x86-64, under load, or with the access lists of Task 2 onward.
