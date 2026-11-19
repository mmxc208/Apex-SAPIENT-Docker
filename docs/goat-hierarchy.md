# goat: hierarchy, echelon and how step 4b fits the ADRs

Written on 2026-11-19 from a side discussion during step 4b. The ADRs were read in `../usareur-af/goatcore` at `5c5aee66`. Nothing was run for this note. The interactive version is `docs/explainers/goat-hierarchy/index.html`.

## 1. Mesh peer and fabric identity

- **A mesh peer is a machine.** In step 4b these are `goathost` and the pod machine. A mesh peer is a NetBird enrolment that holds a management channel (ADR 1122, the table "System, mesh peer, fabric identity").
- **A fabric identity is a program.** Each program that writes on the fabric holds its own slot certificate (ADR 1025). ADR 1122 counts systems by fabric identity, not by machine: "aggregation reduces peers and never identities".
- **Only a pod with a local router needs a bridge.** A pod router cannot rename keys or join the fabric router as a peer, so a bridge process carries the pod's output. A program on a host has no router of its own and connects to the fabric router directly, with its own slot. In 4b, `host-fusion` and `host-recorder` do that.
- **This holds for many hosts.** Three things grow with the number of hosts:
  1. The bridge's allowlist `FABRIC_HOST_ANCHORS` (`emulators/pod_bridge.py`): each host anchor that may task the pod must be listed.
  2. The operator's machine quota on the portal. `cuaslab` grants a quota of 5 (roadmap section 6, 2026-11-18).
  3. A rule in the application for tasks that conflict, because two hosts can task the same pod and nothing in goat orders them.

## 2. A hierarchy: county, city, region, national

- goat has no cross-site command authority. ADR 0844 says it plainly: "No cross-site command authority in v1". A command echelon at site A cannot publish `cmd/effector/B/...`.
- So a hierarchy is relayed **level by level**. The fusion node of each level reads the level below, fuses, and publishes for the level above. A task goes down the same way, one hop at a time.
- Each level accepts tasks only from the level directly above. In our rig this is what `FABRIC_HOST_ANCHORS` does for the pod: the bridge passes down a task only from a listed anchor.

## 3. ADRs 1165 and 1205: administration, not command

- Both are **Accepted** (2026-11-14, by the operator, as one design).
- They are about administering a goatnet that spans sites: the registry, identities and admins. They are not about the flow of tasks.
- ADR 1165: every site writes, so every site keeps working while cut off (island mode).
- ADR 1205: one site, the hub, outranks every other site. It can override, sever a site, admit a site and create platform admins. Identity edits run at the identity's owner site.
- That is **two tiers** (the hub and the rest), not four. It does not give a county, city, region and national structure.
- State, from ADR 1205's "Acceptance" table:

  | Part | Scope | State |
  |---|---|---|
  | D1, D2, D4: hub declaration, directives, sever and restore | In 1.0 | Built; proven by the partition harness; applied by no play |
  | D3, D5 to D7: precedence through owner sites, identity ownership, collisions | In 1.0 | Built in the applier and the harness; the console and CLI refusals are not built |
  | D8: the default hub at standup | In 1.0 | Designed, not built |
  | D10: the platform-admin ceiling | In 1.0 | Designed, not built |
  | D9: `admit_site` and the join checks | After 1.0 | Designed, not built |
  | D11: the post-sever list | After 1.0 | Designed, not built |
  | D4's live drill on a standing goatnet | After 1.0 | Not measured |

## 4. Echelon and slot

| | ADR 0844 | ADR 1025 |
|---|---|---|
| Status | Proposed (pilot) | Proposed; this is what `cuaslab` runs |
| What a certificate carries | A URI-SAN `urn:goat:peer:site=<site>,role=<role>,echelon=<echelon>` | The slot ID as the common name; that ID is the anchor |
| What the router enforces | Only command echelons at a site may publish `task/<site>/` and `cmd/effector/<site>/` | A slot may write only below its own anchor |
| Site and echelon | Enforced | Not enforced: `<site>` is a descriptive key segment below the anchor, and the echelon is not checked |

- ADR 1025 says that on acceptance a "v2 namespace design doc reconciled with ADR 0844" is to be written. It is not in `goatcore/docs/design/`.
- So **no router enforces task authority today**. Who may task whom is decided by the application: in our rig, by the bridge's allowlist.

## 5. Step 4b against the ADRs

| Verdict | What |
|---|---|
| Meets | Host programs connect directly to the fabric router. Each program has its own slot. A slot writes only below its own anchor. |
| Partly | Task authority: enforced only by the bridge's allowlist `FABRIC_HOST_ANCHORS`, not by the router. |
| Does not meet (known) | No mesh. No way to cut a machine off. One identity for the whole pod. These are `docs/goat-context.md` gap 14 and the non-goals of the 4b design (`docs/superpowers/specs/2026-11-19-goat-step4b-host-vm-design.md` section 3). |
| Not applicable | ADRs 1165 and 1205: 4b has one site. |

## 6. The ingress gateway and the edge router

This comparison was already saved: `docs/goat-context.md` section 4.1. In short, the ingress gateway (ADR 1020) re-publishes data from sources that were not onboarded, under a quarantine prefix and the gateway's own identity. The edge router (ADR 1157) connects two sovereigns, each with its own goatnet and CA, and passes data unchanged into `from/<them>/**`. ADR 1157 takes the gateway out of the cross-sovereign case for provenance. Neither is used in steps 1 to 5.

## 7. Open question

The echelon gap is recorded as an open question in `docs/goat-roadmap.md`, step 4.
