# Goat step 1 (pod 1 to host): acceptance

This checklist covers the plan in `docs/superpowers/plans/2026-11-11-goat-step1-pod-to-host.md`, on branch `goat`. Task 1 is the only task recorded so far; the commit is the one that adds this file.

A ticked box means a run recorded the evidence named on that line. It doesn't mean the whole requirement was met, so each line says what was measured and where it falls short. A check that could not run is recorded as unknown.

## G1-01: version pairing

- [x] **G1-01.** Two sessions of the Python binding in `apex-sapient:4.2.0` (zenoh 1.10.2), A and B, each connected over mutual TLS to a router from `eclipse/zenoh:1.9.0` (`zenohd v1.9.0`, arm64, `zenoh/router-pairing.json5`), exchange data through it. A publishes and declares the token; B subscribes and queries liveliness, so each sample and token had to cross the router. The default of `FABRIC_ZENOH_IMAGE` stays `eclipse/zenoh:1.9.0`.
  - `docker compose -f docker-compose.pairing.yml run --rm probe` printed `PAIRING OK put-sub liveliness`: B received A's StatusReport bytes unchanged on `probe/a`, and B's `alive("probe/live/*")` returned A's token `probe/live/x`.
  - With `PROBE_WAIT_RESTART=1` and `docker compose -f docker-compose.pairing.yml restart zenohd` five seconds in, both sessions reported transport False then True. The probe then printed `PAIRING OK put-sub liveliness` and `PAIRING OK after router restart`, exit code 0. It made no new subscribe or declare call after the restart, so B's subscription and A's token worked again through the router. The probe doesn't tell the binding's replay of declarations apart from any other way the router could have learnt them.
  - Falls short: two sessions with one certificate (`radar.p1.h1`), one subscriber, one token and one StatusReport-sized payload, on one Docker network on one arm64 host. The router has no access control, and one restart was tried. An earlier version of the probe used one session, which delivers its own samples locally and proved nothing about the router; that run is not evidence. Nothing was measured on a router built for x86-64, under load, with several certificates, or with the access lists of Task 2 onward.
