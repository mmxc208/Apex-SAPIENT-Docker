# goat context for the SAPIENT proof of concept

This file holds the part of goat that this repository must follow. It is an extract in our own words, not a copy of goat's documents. Read it before you design or change the host tier, the pod bridge, or any key on the fabric.

## How to read this file

- **Goal.** The end goal is a real goatnet: pod 1 at the edge, the host in a cloud or a data centre, and an external host that belongs to a different sovereign. The proof of concept must follow goat's rules on the wire, so that a real goatnet can replace our stand-in host later.
- **Sources.** The local checkouts are in `../usareur-af/`, beside this repository. They were read on 2026-11-11 at these commits:

  | Repository | Commit |
  |---|---|
  | `goatcore` | `cbf2cb7f` |
  | `open-billie` | `7c046be` |
  | `octo-pod` | `fe48297` |
  | `zagros-moon-pod` | `c67d185` |
  | `hello-galaxy-zagros-pod` | `81734a9` |
  | `hello-galaxy-time-hygiene` | `35b2028` |
  | `hello-galaxy-zenoh-patterns` | `c563017` |

  Sections 3.1, 3.4 and 3.5 were updated on 2026-11-14 from ADR 1237 and ADR 1239, read at `goatcore` `e8f223b7`, and from `zagros-moon-pod/docs/partner-contract.md`, read at `zagros-moon-pod` `e44114d`.

  Sections 1, 2.1, 2.2, 2.4, 2.5, 2.9, 2.11, 5.2 and 8 were corrected on 2026-11-18, after step 4, from `goatcore` read at `e44e893d` (the commit `cuaslab` was stood up from), and from what step 4 measured on the goatlite `cuaslab` (`docs/acceptance-goat4.md`). Each correction names its source.

  Sections 2.7, 4.1 and gaps 13 and 14 were added or corrected on 2026-11-19 from `goatcore` read at `b454a0b5`: ADR 1020, ADR 1025 section 5, ADR 1031, ADR 1092, ADR 1122, ADR 1157, ADR 1251, `ops/zenoh-ingress-gateway/README.md` and `ops/goat-zenoh-portal/internal/api/machine_revoke.go`. Nothing was run for them.

  Sections 2.1, 2.6, 2.7, 3.3, 4, 4.1, 8 (gaps 9, 14 and 15) and 9 were updated later on 2026-11-19 from `goatcore` read at `c5bcacee` and `open-entity-gateway` read at `0bdc784`. Read for them: ADR 1225 (status line), ADR 1253 (TL;DR and decision), ADR 1208 ("Consequences"), `ops/ansible/roles/goat-zenoh/files/slot-fragment-reload.py` (its header), `goat-zenoh/defaults/main.yml` lines 338 to 366, `ops/goat-zenoh-portal/internal/api/machine_revoke.go`, `ops/goat-zenoh-portal/internal/registry/leaves.go`, the list of security advisories of `goatcore` on GitHub, and `open-entity-gateway`'s `README.md`, `docs/adapters/sapient.md` and `docs/design/track-egress.md`. Nothing was run for them. The goatlite `cuaslab` is still at `e44e893d`, so where the two commits differ, each statement says which one it is about.

- **Status words.** goat gives each part one of four words, and this file uses them the same way: built, measured, designed, not built.
- **Evidence.** "Read" means the named file was read for this file. "Notes" means the statement comes from the analysis of 9 to 11 November at the same commit, and the source was not read again. No goat software was built or run for this file.
- **Caution.** goat is before version 1.0 (`goat` 0.5.19 at `cbf2cb7f`, notes; `goat` 0.5.20 at `e44e893d`, read at `e44e893d`, and tagged `goat-cli-v0.5.20` by `c5bcacee`; the installed binary that step 4 used in check G4-10 is 0.5.19). Its interfaces can change. Check the commit before you rely on a line here.

## 1. goat in short

A goatnet is one environment. It has a WireGuard mesh that NetBird manages, a Zenoh data fabric, an identity service, a certificate authority (CA), and site records that replicate between sites. One sovereign operates one environment.

On the data fabric, each site has one Zenoh router. Applications connect to that router as clients. goat pins Zenoh 1.9.0 and uses the stock `eclipse/zenoh` image (read: `goatcore/ops/ansible/roles/goat-zenoh/defaults/main.yml`, lines 34 and 47). The pin is still `eclipse/zenoh:1.9.0` in the role defaults at `e44e893d` (read at `e44e893d`; the line numbers above are those of `cbf2cb7f`). But the router that runs on the goatlite `cuaslab` is `zenohd v1.9.0-modified`, image `ghcr.io/usareur-af/zenoh-pqc-fips` (measured on `cuaslab`, 2026-11-18; `docs/superpowers/specs/2026-11-18-goat-step4-cuaslab-design.md` section 2). Our 1.10.2 binding operates with it (check G4-01, `docs/acceptance-goat4.md`).

## 2. Rules on the fabric

These are the rules that our traffic must follow on the host side of the pod bridge.

### 2.1 Identity is a slot

- A system that writes to the fabric has a client certificate for mutual TLS. The common name of the certificate is the slot anchor.
- The router's access list holds a pool of slots that is made in advance. Slot `k` has the anchor `sha256("<salt>:<k>")`, cut to the first 32 hexadecimal characters. The salt is different for each goatnet. The role default is 256 slots.
- Onboarding gives a system a certificate for a free slot. The router does not change and does not restart.
- Status: built. Source (read): `goatcore/docs/adr/1025-zenoh-dynamic-tenant-authz-slot-pool.md` sections 1 and 8; `goat-zenoh/templates/config.json5.j2` lines 1815 to 1820 (read at `e44e893d`; 1803 to 1808 at `cbf2cb7f`); `goat-zenoh/defaults/main.yml` lines 338 and 339.
- Changed at `c5bcacee` (read, not run; the fix for advisory GHSA-rr3p, commit `69f4a745`). Two of the statements above hold only up to `e44e893d`, which is what `cuaslab` runs:
  - The common name is the bare anchor only for a slot's first certificate (generation 0). A later certificate of the same slot has the name `<anchor>.g<generation>` (read: `ops/goat-zenoh-portal/internal/registry/leaves.go`, function `LeafCN`).
  - The router no longer holds a fixed name for every slot. The portal writes the names of the live slots to `slot-fragment.json5`, beside the router's configuration, and a watcher on the router host recreates the router to load it (section 2.6). So onboarding does restart the router: a new certificate works only after the next recreate, which for a change that only adds names comes at most once in 300 s (read: `goat-zenoh/defaults/main.yml` lines 342 to 366).

### 2.2 A slot writes only below its anchor

The write rule for a slot permits `put`, `delete` and `liveliness_token` on three key expressions only:

```text
<anchor>/**
volatile/<anchor>/**
<anchor>/**/@adv/**
```

The slot's policy also permits a schema declaration (rule `trial-peer-w-attest-schema`). All other writes are denied. Source (read): `config.json5.j2` lines 1438 to 1455 and 1969 (read at `e44e893d`; 1434 to 1451 and 1956 at `cbf2cb7f`; the rules are unchanged).

The router of the goatlite `cuaslab` has these rules as measured on 2026-11-18 (design of step 4, section 2): each slot may `put`, `delete` and declare a `liveliness_token` on `<anchor>/**`, `volatile/<anchor>/**` and `<anchor>/**/@adv/**`, and may also write `attest/schema/**`; the default is `deny`; the pool has 1000 slots. In step 4 two writes below a foreign anchor reached no subscriber, while a control write by the same certificate below its own anchor did (check G4-05, `docs/acceptance-goat4.md`).

### 2.3 Key taxonomy below the anchor

goat's key taxonomy continues below the anchor without change, so a consumer removes one leading segment (read: ADR 1025 section 2). The reserved first segments are (read: `goatcore/docs/design/zenoh-data-fabric.md`, "Top-level key-expression prefixes"):

| Prefix | Use |
|---|---|
| `data/` | Payloads in canonical schemas. Shape: `data/<class>/<site>/<id>`, for example `data/entity/track/<site>/<id>` and `data/alert/<site>/<id>` |
| `telemetry/` | Wire-faithful data in a format that is not canonical. Shape: `telemetry/<format>/<site>/<id>` |
| `task/` | Effector tasking at mid level, limited to one site: `task/<site>/<task-id>` |
| `ack/` | Replies to commands and tasks: `ack/<cmd-id>` |
| `cmd/` | Request and reply control |
| `release/` | Data that the owner released to a named partner or set |
| `volatile/` | Routed live and never stored |
| `health/`, `ops/`, `services/`, `config/`, `attest/`, `agents/` | Health, operations events, service discovery, configuration, attestation and schema declarations, agent output |

Rules that come with the taxonomy (read, same document):

- The `<site>` segment is the site where the entity is. The identity of the sender comes from its certificate, not from the key.
- Organisation names and vendor names stay out of keys.
- Life-cycle state is never in a key.
- Only command identities publish on `task/` and `cmd/effector/`. A command identity at site A publishes only `task/A/...`.
- Canonical schemas are not the same as a vendor format or an open standard. Translation is done at the boundary, in an adapter.
- The quality of service class is bound to the first segment. Status: designed, not built.

**For us.** A SAPIENT message on the fabric is wire-faithful data, so it belongs below `<slot>/telemetry/`. Canonical tracks below `<slot>/data/entity/track/` are a possible later addition. Tasks from the host belong below `<host-slot>/task/`. The drawing of 11 November used `<pod-slot>/fusion/up/<kind>`, which does not follow this taxonomy. The step 1 design must set the final key shape.

### 2.4 Reads

- An onboarded member can read fabric data by default. Secret data uses payload encryption, not a read rule (read: ADR 1025 sections 3 and 4).
- A goatnet can turn on the scoped read (`zenoh_peer_read_scoped: true`, off in the role default). Then a subscriber must not declare the literal `**`. The rule `peer-r-scoped` permits `*/**`, `**/@adv/**`, and each filter shape that the goatnet lists.
- A filter that starts with `**` must be in the list `zenoh_peer_cross_tenant_read`, written exactly as the subscriber declares it. If it is not in the list, the router denies it with no message.
- Zenoh matches a rule to a declaration by inclusion, not by intersection.
- Source (read): `zenoh-data-fabric.md`, "No one subscription may match the whole keyspace"; `config.json5.j2` lines 858 to 888 (read at `e44e893d`; 869 to 899 at `cbf2cb7f`).
- On the goatlite `cuaslab` the scoped read is off: every TLS client may subscribe, query and declare a liveliness subscriber on `**` (measured on 2026-11-18, design of step 4, section 2). So step 1's check that a subscription to `**` is refused does not apply there.

**For us.** The host fusion node and the host recorder must subscribe with a wildcard in the first chunk only, for example `*/telemetry/sapient/**`. They must never subscribe to `**`.

### 2.5 Release lanes

`release/<set>/**` is the only path for data that leaves the environment. It is denied by default. A producer that has a grant for a set gets one more write rule, `release-w-<anchor>`, on `release/<set>/**`. Source (read): `config.json5.j2` lines 1486 to 1510 (read at `e44e893d`; 1482 to 1506 at `cbf2cb7f`); `goatcore/docs/adr/1208-sovereign-environments-release-namespaces-and-grant-encryption.md` decision 3.

### 2.6 The access list is static, and a denial is silent

- Zenoh reads `access_control` only at start. A change needs a router restart (read: `zenoh-data-fabric.md`, "Router configuration").
- A denied write or subscription gives no error at the sender or the receiver. Thus you test the access list by asking it, not by watching for errors (read: `zenoh-data-fabric.md`, "Access control").
- goat's tools for that are `acl-evaluate.py` and `goat acl test`. See section 6.
- New at `c5bcacee` (read, not run): the reload watcher `slot-fragment-reload.py`, a systemd path unit and a timer on the router host. Its header confirms that zenohd 1.9 reads `access_control` only at start, refuses a live update of it, and ignores SIGHUP. The watcher recreates the router when the portal's slot fragment changes: 15 s or more after the last recreate for a change that removes a name (a revocation), and at most once in 300 s for a change that only adds names. Each recreate drops every session. It then records what the router loaded in `slot-fragment.loaded.json5`, and the portal reads that file to say whether a slot is live or `pending_router_reload`. The role now fails the play when `slot-fragment.json5` is missing, unless `zenoh_slot_fragment_bootstrap` is true for a first run (read: the header of `goat-zenoh/files/slot-fragment-reload.py`; `goat-zenoh/defaults/main.yml` lines 342 to 366).
- **For us.** If `cuaslab` is upgraded to `c5bcacee` or later, each enrolment and each revocation recreates the fabric router, and the pod bridge and the host clients lose their sessions once. Step 4b saw the host's session come back by itself after a cut of its route (check G4B-08); a recreate of the router was not tried (roadmap, step 4, gap 4).

### 2.7 Cut-off

Zenoh has no certificate revocation list. To stop a system immediately, remove its peer from the mesh. A host that connects with one identity for all that is behind it, such as a pod, is cut off as one unit (read: ADR 1025 section 5).

The portal's machine revoke (`DELETE /api/machines/{anchor}`) cuts at the mesh first and then frees the slot in the registry. Its source says that the registry step moves no authorization: with the slot pool, the router holds a write grant for every slot, so the mesh cut is the only barrier that falls (read: `machine_revoke.go`, ADR 1031). **For us.** The step 4 rig is not on the mesh, and the `cuaslab` portal holds no NetBird credential. So a revoke of our three machines would free their slots and leave their certificates able to connect and write until they expire. This is read from source and was not tried. It holds for `e44e893d`, which `cuaslab` runs.

goat published this as a security advisory on 2026-11-19: GHSA-rr3p, severity high, "Offboarding never revokes the fabric certificate, and the freed anchor is reissued to the next person". At `c5bcacee` the revoke also advances the slot's generation and writes the slot fragment again, so that the name of the revoked certificate is in no rule; the watcher of section 2.6 then recreates the router, and the portal's answer says whether the router has loaded the change yet (read at `c5bcacee`: `machine_revoke.go` lines 155 to 168; the comment at its lines 13 to 16 still describes the old behaviour). Inferred, not run: after the recreate the old certificate can still open a TLS session, because the CA still verifies it, but it matches no write rule. On a goatlite, with the scoped read off, it could still read.

### 2.8 Delivery

- There is no broker. There is no central queue, no broker acknowledgement and no retry. The producer is responsible for delivery (notes: `goatcore/docs/design/zenoh-brokerless-consequences.md`).
- A command that waits during a partition expires. It is not sent again automatically (read: `zenoh-data-fabric.md`, "Deployment topology + ACL contract").
- `goat pub --confirm` reads the value back from the router's storage (read: `goatcore/docs/tutorials/00-goatlite.md` section 8).
- Liveliness tokens and the advanced publisher and subscriber are client features. They operate with the stock router (read: ADR 1025 section 7, the note of 2026-06-11).

### 2.9 Router configuration

A fabric router has one JSON5 file: `mode: "router"`, one listen endpoint `tls/<mesh-ip>:7447`, mutual TLS, the REST plugin, RocksDB storage with one store for each live slot, and `access_control` with `default_permission: "deny"`. goat renders it from a template of 2,045 lines at `e44e893d` (2,032 at `cbf2cb7f`) (read: `zenoh-data-fabric.md`, "Router configuration"; `config.json5.j2`).

### 2.10 Key shape

goat's rule for the order of the parts of a key is: stable parts with few values go first, and the part with many values, which a reader selects on, goes last. For the state of an entity the shape is `<anchor>/<system>/<version>/<entity-id>`.

- Put a version segment in the key from the first day. To add it later is a migration.
- Inspection tools group keys by the last segment. If the last segment is a constant, each entity goes into one group and the tool shows nothing useful.
- Segments are lower case, with no spaces. A key has no leading slash.
- Which pattern applies depends on the data: a track or a known entity has one key for each ID and keeps its current state, a detection is an event with one key for each event, and raw sensor output belongs in the `volatile/` class.
- Source (read): `hello-galaxy-zenoh-patterns/README.md` and `docs/key-expression-design.md`, at commit `c563017`. Not read: `docs/identity-spectrum.md`, `docs/decision-guide.md`, `docs/anti-patterns.md`.

**For us.** A candidate key for SAPIENT on the fabric is `<pod-slot>/telemetry/sapient/<site>/v2/<kind>/<id>`, and for a task from the host `<host-slot>/task/<site>/v2/<task-id>`. Both are proposals. Inside the pod, our keys deliberately hold no report ID or task ID, so the two conventions differ, and the step 1 design must decide.

### 2.11 The session ID is a label, not a credential

- A Zenoh session ID (ZID) names a Zenoh runtime. It is random at each session open unless the configuration sets `id`. goat's ADR 1041 makes it a label for provenance and never a credential: the certificate stays the only input to access control.
- A router's ID is fixed for each host. It is derived at render time from the host's inventory name and the realm, not stored in an image.
- A publisher that goat owns attaches source info (its session ID and a sequence number) to each sample, so that a consumer can tell which node made it.
- goat's command line tool sets a publisher's session ID to its slot anchor with leading zeros removed, because Zenoh rejects an ID with a leading `0`. `goat sub` keeps a random ID on purpose.
- The router permits one transport for each session ID. A second session with the same pinned ID is refused (`MAX_LINKS`) until the first one is gone, or it displaces it.
- Status: proposed (ADR status "Proposed", 2026-06-11); the pin in `goat pub` is built. Source (read): `goatcore/docs/adr/1041-zenoh-router-zid-pinning-and-source-provenance.md`, "Context", "Decision" and "Invariants"; `goatcore/crates/goat-cli/src/cmd/pubsub.rs` lines 25 to 31 and 1205 to 1222.
- New in `goat` 0.5.20: `goat health --domain peer` compares the session's ZID with the anchor pin, and reads the router's verdict on the peer at `ops/peer/verdict/<own zid>`. A client with a random ZID cannot be matched to its verdict. Source (read at `e44e893d`): `goatcore/crates/goat-cli/src/cmd/health.rs`.

**For us.** Step 1 sets no session ID: the pod bridge, the fusion nodes, the sensors, the recorders and both routers use random IDs, and no publisher attaches source info. Whether the pod bridge and the host fusion node set their ID to their anchor, whether the routers get a fixed ID, and whether our publishers attach source info is open for step 4.

## 3. Pods in goat

### 3.1 Two classes

| Class | What it is |
|---|---|
| POD | A node in our mesh that uses our NetBird, our identity service and our CA. It can operate its own local Zenoh router for the systems behind it. We administer it. |
| MOON | The one uplink peer of a foreign goatnet that has its own full stack. We do not probe it. |

A link from our fabric into a pod's local router is not part of the base rights of a pod. It is a separate grant with the name `router-peer`, given for each pod. goat also says that a moon pod is a learning tool, not the operational path between nations. Source (read): `goatcore/docs/adr/1092-moon-pod-peer-classes.md`.

ADR 1239 (proposed, 2026-11-14) states the position of a moon pod once, and every goat document now points to it:

1. A moon pod is used today only to learn. It is rung 2 of goat's learner ladder (ADR 1238), and it is not in operational use.
2. It is not a sovereignty guarantee. The pod joins an environment that someone else runs, and the owner of that environment controls enrolment, the access rules and what data may leave the pod. This is the POD class above.
3. It can become a real capability on one condition: the pod's operator accepts the environment owner as trusted, and as the authority over data that leaves the pod.
4. A party that needs sovereignty runs its own environment and federates across a boundary (section 4). That is not a moon pod.

ADR 1239 also withdraws the word "sovereign" from the moon pod claims in ADRs 0223, 0856, 1025, 1157 and 1164. It changes no code and no configuration. Source (read): `goatcore/docs/adr/1239-a-moon-pod-is-a-learning-tool-and-not-a-sovereignty-guarantee.md` decisions 1 and 2.

**For us.** Pod 1 and the host belong to one party and sit in one environment, so pod 1 is a POD, and ADR 1239 agrees with our design. The pod has no sovereignty of its own, and we do not claim it. A pod run by another nation or organisation that must keep control of its data does not join our host as a pod. It runs its own environment and receives data by release, as the external host does in step 6. The roadmap has no such pod today.

### 3.2 The pod is an aggregation tier

- goat counts three units: systems, mesh peers and fabric identities. A pod is one mesh peer with a local router, and the systems behind it are not mesh peers.
- "Aggregation reduces peers, never identities." A system that produces or consumes on the fabric must have its own fabric identity. Legacy equipment that cannot hold a certificate gets a key that shows its source address.
- Status today: systems behind a pod also enrol as mesh peers, because the router-to-router link for pods is designed, not built.
- Source (read): `goatcore/docs/adr/1122-scale-envelope-systems-vs-peers-pod-tier.md` decisions 1 and 2.

**For us.** Our sensors publish only inside the pod. The pod fusion node is the system that produces on the fabric, through the pod bridge, with one slot. If raw sensor data must go to the fabric later, each sensor needs its own identity there.

### 3.3 How goat's own edge products reach the fabric

| Product | Method | Source |
|---|---|---|
| octo-pod 0.6 | A local router with a CA on the pod and a generated access list. An uplink bridge publishes only the released local feeds below the pod's slot anchor. A downlink bridge brings only approved fabric keys into the pod. Queues have limits, and there is no store and forward. The pod has one slot certificate from a signed bundle. | Read: `octo-pod/README.md` lines 77 and 78. The other statements: notes. |
| Open Billie | A local Zenoh island on loopback, and a second Zenoh process in client mode with mutual TLS to the fabric. A one-way bridge adds the authorised prefix. No fabric data goes back to the node. | Read: `open-billie/docs/architecture/GOLDEN_PATH_ZENOH.md` |
| Moon pod | The pod router dials the fabric router, router to router, with mutual TLS. The pod router denies by default and has one partner namespace. | Read: `hello-galaxy-zagros-pod/stack/templates/pod-router.json5.tmpl` |
| open-entity-gateway | Not an edge product: a gateway that turns decoded records and tracks into CoT, SAPIENT and ASTERIX CAT062. It has two ways out. A receiver that its host can reach gets one of the gateway's own destinations. For a receiver that cannot join the mesh, the gateway publishes the encoded payload to a key `release/<lane>/...`, and an octo-pod egress destination (`udp://`, `tcp://`, `tcp-server://`, `sapient://`) whose downlink allow list names that key delivers it. | Read at `0bdc784`: `open-entity-gateway/docs/design/track-egress.md` |

More facts:

- `hello-galaxy-zagros-pod` runs the moon pod shape on a laptop with no goatnet. Its fabric router is a stand-in that permits everything on purpose (read: `stack/templates/fabric-router.json5.tmpl`).
- The moon pod contract says that the pod router does not connect into a goat core router. It connects to an ingress gateway that goat operates (read: `zagros-moon-pod/docs/partner-contract.md`).
- octo-pod's SAPIENT arm relays only detection reports and alerts, writes its own node ID into each message, and rejects each task (notes).
- Open Billie's SAPIENT encoder makes detection reports only. It makes no registration, status report, task or alert (notes; not read again at `fd074f3`, where the two commits since `7c046be` do not name SAPIENT in their subjects).
- open-entity-gateway's `sapient` adapter is a SAPIENT edge node over TCP: it connects to a fusion node or to middleware, sends a registration, waits for the acknowledgement, sends status reports, sends each track as a detection report, and says goodbye. Its own record says: measured against Dstl's Apex 4.2.0 with the default validation; tasks, alerts and range-bearing locations not built. The node ID is one UUID for each destination, set in configuration (read at `0bdc784`: `open-entity-gateway/docs/adapters/sapient.md`). We did not run it.

**For us.** We use a bridge process, as octo-pod and Open Billie do. A router cannot rename a key in transit, and the keys in our pod are different from the keys on the fabric.

### 3.4 The partner contract

The moon pod contract has seven requirements (read: `zagros-moon-pod/docs/partner-contract.md`). Four of them apply to our pod design:

- Transport: encrypted end to end between the two edges. WireGuard is preferred, and IPsec is accepted.
- Landing interface: data goes in and out at well-known Zenoh keys below the pod's namespace.
- Audit: the pod's owner keeps 90 days or more of access logs for the namespace.
- Schema: each published topic has a schema declaration at `attest/schema/<topic>`. The goat boundary rejects a topic with no declaration.

Requirement 6 was named the "sovereignty floor". It is now the **custody floor**: the partner's data at rest, operator credentials and audit logs live on the partner's side. The contract says that this is where three things live, and not a sovereignty guarantee. The goat-hosted coordination plane still enrols the pod and holds its connection metadata, and the goat-operated boundary processes the pod's data in flight (read: `zagros-moon-pod/docs/partner-contract.md`, at `e44114d`; ADR 1239 decision 2).

**For us.** We keep the four requirements above as engineering rules for the pod, because each one is sound on its own. Their basis is the contract's boundary behaviour and the custody floor, not a claim that the pod is sovereign (section 3.1).

The contract also says that a moon pod is a Tier-2 peer: its router connects to a goat-operated ingress gateway, which admits the pod's data scoped to its origin, and not to a goat core router (read: same file). Step 4 must check how a pod reaches the fabric on a real goatnet, and whether our pod bridge meets that gateway or a fabric router.

### 3.5 Rebuilding a pod from its identities

ADR 1237 (proposed, 2026-11-14) decides how a site is rebuilt after it may have been compromised. A tactical pod counts as a site.

- **The extract.** `goatbuilder extract <site>` writes one signed file with the people, machines and processes that the site owns and that no configuration declares. Keys are carried only by reference (a public key, a certificate serial and fingerprint, the name of the variable that holds a secret). No private key, password hash or secret is carried, and no session, log, audit object or replication state.
- **A cut-off site.** The extract is taken at the hub, from the hub's copy of the site's records. The site's own extract is evidence only.
- **The rebuild.** Teardown, then `goatbuilder join-node` (or `standup` for the hub), then `goatbuilder import <site> --extract <file>`. No disk, dump or volume is restored. A pod is rebuilt with `join-node`.
- **The comb.** The import checks each element again before it creates it. Routine elements get machine checks (declared or sponsored, still enrolled at the hub, not revoked, not dormant, grants within the class ceiling). Privileged elements also need a signed approval by a named person. Each element carries indicators of concern, for example "created at a cut-off site" or "credential changed shortly before the sever".
- **A machine may need to enrol again.** It keeps its key only when the comb matches it against the hub's record.
- **Status.** Not built. `extract` and `import` do not exist, and the pattern is a fast follow after goatbuilder 1.0. Machines and processes do not record all the provenance fields yet (`created_site`, `owner_site`, sponsor, last credential change).
- Source (read): `goatcore/docs/adr/1237-a-site-is-rebuilt-from-nothing-and-a-combed-extract-of-its-identities.md` decisions 1 to 5 and 7, and its consequences.

**For us.** Nothing in steps 1 to 6 uses this pattern. Two things can be prepared now:

1. The condition for step 5 on node ID ownership (`docs/goat-roadmap.md`, step 5) is the same kind of problem as ADR 1237's provenance. If a node ID is bound to the anchor of an accepted registration, or taken from the registry, the registry can later say which pod owns which node ID, as the comb needs.
2. The pod must not assume that its slot certificate lives for ever. After a rebuild the pod may enrol again and get a new certificate, so the five facts of section 5.1 must stay configuration only.

## 4. Between sovereigns

The statements in this section are from notes of 11 November (ADR 1157, ADR 1224, the edge router template, the republisher and the driver code), with ADR 1208 read again today.

```text
 release/<set>/**                                            release/<set>/**
       | republisher (our core host)      republisher (their core host) |
       v                                                                 v
 from/<us>/<set>/**                                        from/<them>/<set>/**
our core router -- our edge router == tunnel == their edge router -- their core router
  trusts OUR CA      trusts THEIR CA             trusts OUR CA        trusts THEIR CA
```

- Each sovereign operates its own environment with its own CA. Data crosses only by release.
- An application publishes to `release/<set>/...`. The republisher publishes each sample again as `from/<our sovereign id>/<set>/...`. A router cannot rename a key, thus a process does it.
- There is one edge router process for each partner. The Zenoh access list matches the certificate common name and cannot see which CA issued the certificate.
- The partner's edge router permits our writes only below `from/<us>/**`.
- Data grants list each offered set. Interest grants must keep the full `from/<us>/**`, or Zenoh refuses the subscription and no data crosses.
- Released data goes one hop, unless the owner marks it as a general release.
- The tunnel between the two edge hosts is WireGuard or IPsec.
- Status: the first federation between two separately administered environments was on 2026-11-09, with many manual steps. `goatbuilder federate` has six package verbs on `main`. Corrected on 2026-11-19: the one-command procedure is built. ADR 1225 is accepted (2026-11-15), and its status line says that the six federation verbs and `goatbuilder federate <partner>` run on the `goat-federation` library (read at `c5bcacee`: the status line of ADR 1225 only; we did not run it). Grant encryption across the boundary is not usable yet: nothing carries the partner's recipient key across the boundary, and ADR 1223 (proposed) designs the fix (read at `c5bcacee`: ADR 1208, "Consequences").
- Tutorials: `goatcore/docs/tutorials/03-boundary-node.md` and `04-two-sovereigns.md`.

### 4.1 The ingress gateway and the edge router compared

goat has two ways for data from outside to come in. They serve different cases. Both ADRs are proposed.

| | Ingress gateway (ADR 1020) | Edge router (ADR 1157) |
|---|---|---|
| Who is on the other side | A source that was not onboarded end to end: a vendor's router that relays its suppliers, or a moon pod in the learning setup | A sovereign with its own complete goatnet and its own CA |
| The relation | One way: they send, we receive | The same four steps on both sides |
| What it does to the data | Rewrites each key to `<peering entity>/<peering id>/<original key>` and publishes it again with the gateway's own goat identity | Passes each message inward unchanged |
| Where the data lands | A quarantine prefix, with its own storage and audit, marked as not onboarded | `from/<their sovereign id>/**` |
| Who the publisher is afterwards | The gateway | The original source |
| The trust | Only the directly connected peer is authenticated | Each side federates the other's SPIRE trust domain; one `zenohd` for each partner trusts that partner's CA and no other |
| The link | Router to router | One WireGuard or IPsec tunnel between the two edge hosts, on neither side's NetBird |
| Status | Decisions 3 and 4 proposed; a v0 exists in `ops/zenoh-ingress-gateway/`; the design says designed and not built | Proposed; tutorial 4 rehearses it in containers |

- ADR 1157 amends ADR 1020: it takes the re-publishing gateway out of the cross-sovereign case. Its reason is provenance: a re-publisher is the publisher of record, so a partner's data would reach our core as if we had sent it. The gateway stays as an exception for a partner that cannot change its key names, with the loss of provenance accepted in writing.
- The edge has three levels, each with a mechanism that stops a peer: recognised (their CA material is on the edge host), connected (tunnel up, no access rule matches, default deny) and exchanging (an access block for the agreed certificate name).
- To choose: a party with its own goatnet and an agreement meets an edge router. Data that reaches us through someone else's router, from sources we never enrolled, meets the gateway.
- ADR 1253 (proposed, 2026-11-19; read at `c5bcacee`: TL;DR and decision) adds two more boundary nodes and calls the edge router of ADR 1157 the canonical boundary node.
  - A simple boundary node (`simple-bn`, in `ops/simple-bn/`) is one process on a dedicated host. It sends declared `release/<set>/**` keys one way to one receiver that is not goat, as UDP datagrams in the receiver's format; for radar, ASTERIX CAT034 and CAT048. Plain UDP is for synthetic data only; real data needs a WireGuard tunnel to the receiver or the receiver's own protected transport. Until the fabric subscription is built, its only input is notional sensor feeds.
  - A pseudo boundary node (`pseudo-bn`) crosses to another goatnet of the same sovereign. Each crossing declares a `crossing.mode`: `join` (enrolled in both goatnets, admitted on the far side as a machine with a scoped write grant), `tunnel` (WireGuard) or `plain` (synthetic data only).
  - Every boundary service writes a `goat.boundary-status/v1` document for one monitor, `bn-monitor`.
  - Its design, `goatcore/docs/design/simple-boundary-node.md`, was not read.

**For us.** Neither is used in steps 1 to 5. Our pod is enrolled in its own goatnet with that goatnet's CA (class `POD`, ADR 1092) and connects to the core router as a client. Step 6, the external host, is the edge router case if the second sovereign is a different sovereign. If it is a second goatnet that we operate ourselves (an open question of step 6), ADR 1253's pseudo boundary node is the pattern that goat names for it. The ingress gateway would be met only if our pod joined another party's environment as a moon pod, which ADR 1239 sets as a learning use.

## 5. How a system joins a real goatnet

### 5.1 The bundle

An operator gives a new member a signed bundle (a `.cbor` file) and the CA certificate that verifies it. The member runs `goat ca add`, `goat profile init`, `goat init` and `goat doctor` (read: `goatcore/docs/goat-cli-book/src/getting-started.md`).

A fabric client needs five facts, and the bundle carries them: the CA roots, the client certificate, the private key, the router endpoint, and its anchor. The `goat` profile directory shows the same set (read: `hello-galaxy-zagros-pod/lib/common.sh`, function `hg_mkprofile`):

```text
<profile dir>/config.toml                      current_context = "<name>"
<profile dir>/contexts/<name>/profile.toml     router_endpoint, device_id
<profile dir>/contexts/<name>/mtls.cert.pem
<profile dir>/contexts/<name>/mtls.key.pem
<profile dir>/contexts/<name>/ca-roots.pem
```

**For us.** The pod bridge and the host clients must take these five facts from configuration, and nothing else. Then a move to a real goatnet changes configuration only.

### 5.2 goatlite, the smallest real goatnet

Source (read): `goatcore/docs/design/goatlite.md` and `goatcore/docs/tutorials/00-goatlite.md`.

| Subject | Fact |
|---|---|
| What it is | The lite preset of `goatbuilder`. It makes a real goatnet on one machine: mesh, identity service, CA, fabric router and portal. |
| The machine | One Ubuntu 24.04 host or VM with 4 cores and 16 GB, with SSH access by key |
| The workstation | Linux or macOS, with Rust, Go 1.26 or newer, `yq` version 4, `age`, Python 3.12 to 3.14, `ansible-core`, Node with Playwright, and `netbird` |
| The run | `goatbuilder standup <name>`: fourteen phases, with one step in a browser. The tutorial says an hour or more. |
| Your identity | A script mints a founder identity that writes below `founder/`. A goatlite has no identity console. |
| Limits | Never for production. It is a LAN goatnet. The internet profile is rendered, but no internet goatlite was stood up with real relays. |

Not found: a statement that the machine can be arm64. (Measured since: `cuaslab` runs on an arm64 Lima VM; step 4.)

Corrected on 2026-11-18: the statement here that no procedure mints a slot identity for a system on a goatlite was wrong. The procedure is in `goatcore/docs/operations/gear-enrollment-sop.md` (it was there at `cbf2cb7f`; read at `e44e893d`): the operator runs `goat machine grant <custodian> --quota N --affiliation <unit>` with the operator key, then `goat machine enroll <handle> --node-class <CLASS> --autonomy <level>`. The classes `POD` and `FUSION` exist; `PROCESSOR` is refused. The portal's API for the same is `POST /api/machines/grant`, then `POST /api/machines/enroll`.

What step 4 measured (`docs/acceptance-goat4.md`, section "Enrolment"): on `cuaslab`, stood up from `e44e893d`, the first enrolment was refused with HTTP 500, code `mint`. The lite preset sets `portal_bundle_create_bin: "/usr/local/bin/bundle-create"` (`ops/scripts/goatlite-render.py:767` at `e44e893d`), and on the box that path is an empty directory. So a goatlite stood up at `e44e893d` cannot enrol a machine until that setting is turned off or the binary is installed. With the setting off, three machines were enrolled through the portal API with `curl` (the `goat` portal client does not trust a goatlite's private CA). A bundle then holds the certificate, the key and the root, and no goat-cli profile.

## 6. goat tools that operate with no goatnet

| Tool | What it does | Source |
|---|---|---|
| `eclipse/zenoh:1.9.0` | The router image that goat pins | Read: `goat-zenoh/defaults/main.yml` |
| `acl-evaluate.py` | Decides what a Zenoh 1.9.0 access list permits, with no router. It uses only the Python standard library, and `--self-test` runs the upstream test vectors. | Read: `goatcore/ops/ansible/roles/goat-zenoh/files/acl-evaluate.py` |
| `goat` command line tool | `goat sub` and `goat pub` operate with any mutual TLS router, if you make the profile directory of section 5.1 by hand. It is built from `goatcore/crates/goat-cli`. | Read: `hello-galaxy-zagros-pod/tests/smoke/loopback.sh` |
| One file for all configurations | `stack/registry/fabric.yaml` is the input. `stack/render.py` makes each router configuration, and `stack/gen-certs.sh` makes a test CA and certificates. | Read: `hello-galaxy-zagros-pod/README.md` |

## 7. What this means for our parts

| Our part | goat rule that applies | Section |
|---|---|---|
| Pod router, sensors, pod CA | goat does not govern the inside of a pod. A pod has its own local router, and octo-pod also has its own CA. | 3.1, 3.3 |
| Pod bridge | One slot certificate. It writes only below its anchor. It takes the five facts from configuration. It needs an allow list in each direction and queues with limits. | 2.1, 2.2, 3.3, 5.1 |
| Fabric router | Zenoh 1.9.0, mutual TLS, deny by default, a slot pool, and the scoped read | 2.1 to 2.6, 2.9 |
| Host fusion node and display | A client with its own slot. It subscribes with a filter and never with `**`. | 2.4 |
| Host recorder | A client that only reads, with a filter subscription | 2.4 |
| Tasks from host to pod | Below the host's own slot, in the `task/` taxonomy, for one site. A task that waits during a partition expires. | 2.3, 2.8 |
| Keys for SAPIENT on the fabric | Below `<slot>/telemetry/`, wire-faithful | 2.3 |
| External host | Release lane, republisher, one edge router for each partner, `from/<us>/` | 2.5, 4 |
| A pod run by another party | Not a pod of our host. It runs its own environment and receives data by release. | 3.1, 4 |
| Pod identities after a compromise | Rebuilt from a combed extract of identities, not restored from disk. Not built. | 3.5 |

## 8. Gaps and unknowns

1. **Zenoh versions.** Our pod uses 1.10.2 and goat uses 1.9.0. Measured in check G1-01 (`docs/acceptance-goat1.md`): two sessions of our Python binding (zenoh 1.10.2) exchanged a sample and a liveliness token over mutual TLS through a router from `eclipse/zenoh:1.9.0`, and again after one restart of that router, with no new declaration. The step 1 rig then ran with a 1.10.2 pod router and a 1.9.0 fabric router. Not measured: x86-64, load, the full access lists in the pairing probe, and any other pair of versions.
2. **Slot identity on a goatlite.** Corrected on 2026-11-18: the procedure exists (`goatcore/docs/operations/gear-enrollment-sop.md`, section 5.2). Measured in step 4: on a goatlite at `e44e893d` it fails until the portal setting `portal_bundle_create_bin` is turned off or the binary is installed; with it off, three machines were enrolled on `cuaslab`.
3. **Pod at the edge through the internet.** This needs goat's internet profile with relays and a public zone. It is not proven on a goatlite.
4. **Router-to-router pod link.** Designed, not built, for operational pods. We use a bridge.
5. **Schema declaration.** The format at `attest/schema/<topic>` was not read. `goatcore/docs/design/data-dictionary.md` describes it.
6. **Key shape.** Decided in the step 1 design (`docs/superpowers/specs/2026-11-11-goat-step1-pod-to-host-design.md`). The four key forms on the fabric are:
   - `<anchor>/telemetry/sapient/<site>/v2/<kind>/<node_id>` for `registration`, `status_report`, `detection_report`, `alert` and `error`
   - `<anchor>/ack/<site>/sapient/v2/<kind>/<node_id>` for `registration_ack`, `task_ack` and `alert_ack`
   - `<anchor>/task/<site>/sapient/v2/task/<node_id>` for `task`
   - `<anchor>/telemetry/sapient/<site>/v2/live/<node_id>` for the liveliness token

   `<anchor>` is the writer's 32-character slot anchor, `<site>` is 1 to 32 characters of `[a-z0-9]`, and `<node_id>` is a canonical UUID. A key never holds a report ID, a task ID, an object ID or a timestamp (Zenoh issue 2825: a router can freeze when a face uses up its 16-bit space of expression IDs), so the last segment is the node, not the event. For that reason the `ack/` and `task/` forms end with the node ID, not with goat's `<cmd-id>` or `<task-id>` of section 2.3.
7. **Quality of service.** goat's classes by prefix are designed, not built. Our priorities for each message kind are set by the sender.
8. **Time.** The signed clock report for each host is built. The time quality field for each message is not built (read: `hello-galaxy-time-hygiene/README.md`). Added on 2026-11-18 (read at `e44e893d`): ADR 1232 and `goatcore/docs/design/peer-fault-handling.md` say that the router replaces a timestamp more than 500 ms ahead and logs the peer's ZID. Status: partly built, not deployed on any goatnet.
9. **Federation.** Corrected on 2026-11-19: the one-command procedure, `goatbuilder federate <partner>`, is built (ADR 1225, accepted; read at `c5bcacee`, status line only). We did not run it. Grant encryption across the boundary is still not usable (section 4).
10. **Scale.** goat's validated data stops near 100 peers (notes).
11. **Session ID.** goat's ADR 1041 (proposed) fixes a router's session ID for each host and asks for source info on goat's own publishers. goat's command line tool also sets a publisher's session ID to its slot anchor, which its code credits to ADR 1039. Step 1 sets no session ID anywhere (section 2.11). Open for step 4.
12. **Rebuild of a pod.** goat's pattern for rebuilding a compromised site from its identities (ADR 1237) is proposed and not built, and it comes after goatbuilder 1.0. Until then a compromised pod has no goat procedure to return. Section 3.5.
13. **Pod ingress on a real goatnet.** Closed on 2026-11-19 by reading. The moon pod contract sends a pod through a goat-operated ingress gateway, not to a core router. That is the case of a pod in someone else's environment. Our pod is enrolled in its own goatnet, so its bridge connects to the core router as a client, and ADR 1020 does not ask for a gateway (section 4.1).
14. **Pod carriage and provenance.** ADR 1251 (proposed, 2026-11-18), "every source keeps its identity through a pod", was read on 2026-11-19 at `b454a0b5`; its design `docs/design/pod-carriage-and-provenance.md` was not. It lists "keep everything under the pod's slot", which is our shape, as a rejected alternative. ADR 1122 already says that aggregation reduces peers and never identities. So our rig does not conform in four points, and step 4 changes none of them: the pod's machine is not a mesh peer (ADR 1092), nothing can cut a machine off (ADR 1025, ADR 1031, section 2.7), the sensors and the pod fusion node have no fabric identity (ADR 1122), and every source appears as the pod (ADR 1251). The first two cannot be met on a goatlite, where the router listens on the LAN and the box is not a mesh peer. The carriage rules of ADR 1251 are not built. Checked at `c5bcacee`: ADR 1251 and its design have no commit after the one that added them (`e0c2e2bf`), the ADR is still proposed, and the design is still not read.
15. **Security advisories.** `goatcore` published 20 advisories on 2026-11-19 (2 critical, 7 high, 10 medium, 1 low; read from the GitHub advisory list). The fixes are in commit `69f4a745`, "fixes for the advisories published with this release". `cuaslab` runs `e44e893d`, which is before that commit. Only the titles were read, except for GHSA-rr3p. The ones that touch what our rig uses:
    - GHSA-rr3p (high): offboarding never revokes the fabric certificate, and the freed anchor is reissued. Sections 2.1, 2.6 and 2.7.
    - GHSA-fghv (medium): a reused slot inherits the previous holder's machine custody, quotas and data grants. It matters if the three machines of step 4 are revoked and their slots are given out again.
    - GHSA-qc75 (critical): the portal's bundle download link, which serves the private key, never expires. Our three bundles came from the `cuaslab` portal API.
    - GHSA-6828 (critical): a Docker socket mounted read-write into a mesh-facing service. Whether a goatlite has that mount was not checked.

    `cuaslab` is a lab on one Mac with no real data. An upgrade is Richard's decision; section 2.6 says what it changes for the rig.

## 9. Where to read more

All paths are in `../usareur-af/`.

- `goatcore/docs/design/zenoh-data-fabric.md`: the fabric, the key taxonomy, the access list.
- `goatcore/docs/design/zenoh-brokerless-consequences.md`: what is not possible with no broker.
- `goatcore/docs/adr/1025-zenoh-dynamic-tenant-authz-slot-pool.md`: slots.
- `goatcore/docs/adr/1041-zenoh-router-zid-pinning-and-source-provenance.md`: the session ID as a label, a fixed router ID, and source info.
- `goatcore/docs/adr/1092-moon-pod-peer-classes.md` and `1122-scale-envelope-systems-vs-peers-pod-tier.md`: pods.
- `goatcore/docs/adr/1239-a-moon-pod-is-a-learning-tool-and-not-a-sovereignty-guarantee.md`: the position of a moon pod.
- `goatcore/docs/adr/1237-a-site-is-rebuilt-from-nothing-and-a-combed-extract-of-its-identities.md`: rebuilding a site or a pod from its identities.
- `goatcore/docs/adr/1238-the-learning-program-is-a-ten-rung-ladder-and-a-lane-beyond-it-in-use-while-proposed.md`: the learner ladder.
- `zagros-moon-pod/docs/partner-contract.md`: the seven requirements and the custody floor.
- `goatcore/docs/adr/1157-cross-sovereign-federation-edge-terminated.md` and `1208-sovereign-environments-release-namespaces-and-grant-encryption.md`: sovereigns.
- `goatcore/docs/adr/1225-federation-belongs-to-goatbuilder-one-command-one-decision.md`: federation in one command.
- `goatcore/docs/adr/1253-simple-boundary-node-pseudo-boundary-node-and-one-boundary-monitor.md` and `goatcore/docs/design/simple-boundary-node.md`: the simple and the pseudo boundary node.
- `goatcore/docs/adr/1251-every-source-keeps-its-identity-through-a-pod-carriage-rules-provenance-at-entry-and-pod-local-authority.md` and `goatcore/docs/design/pod-carriage-and-provenance.md`: what a pod must keep of each source. Read the design before step 5.
- `goatcore/ops/ansible/roles/goat-zenoh/files/slot-fragment-reload.py`: how a slot change reaches the router.
- `open-entity-gateway/docs/adapters/sapient.md` and `docs/design/track-egress.md`: a SAPIENT edge node session, and SAPIENT delivered through a pod's egress.
- `goatcore/docs/design/goatlite.md` and `goatcore/docs/tutorials/00-goatlite.md`: the smallest real goatnet.
- `goatcore/ops/ansible/roles/goat-zenoh/`: the router role, its template and `acl-evaluate.py`.
- `hello-galaxy-zagros-pod/`: a pod router and a fabric router on a laptop.
- `octo-pod/` and `open-billie/`: goat's two edge products.
