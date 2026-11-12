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

- **Status words.** goat gives each part one of four words, and this file uses them the same way: built, measured, designed, not built.
- **Evidence.** "Read" means the named file was read for this file. "Notes" means the statement comes from the analysis of 9 to 11 November at the same commit, and the source was not read again. No goat software was built or run for this file.
- **Caution.** goat is before version 1.0 (`goat` 0.5.19, notes). Its interfaces can change. Check the commit before you rely on a line here.

## 1. goat in short

A goatnet is one environment. It has a WireGuard mesh that NetBird manages, a Zenoh data fabric, an identity service, a certificate authority (CA), and site records that replicate between sites. One sovereign operates one environment.

On the data fabric, each site has one Zenoh router. Applications connect to that router as clients. goat pins Zenoh 1.9.0 and uses the stock `eclipse/zenoh` image (read: `goatcore/ops/ansible/roles/goat-zenoh/defaults/main.yml`, lines 34 and 47).

## 2. Rules on the fabric

These are the rules that our traffic must follow on the host side of the pod bridge.

### 2.1 Identity is a slot

- A system that writes to the fabric has a client certificate for mutual TLS. The common name of the certificate is the slot anchor.
- The router's access list holds a pool of slots that is made in advance. Slot `k` has the anchor `sha256("<salt>:<k>")`, cut to the first 32 hexadecimal characters. The salt is different for each goatnet. The role default is 256 slots.
- Onboarding gives a system a certificate for a free slot. The router does not change and does not restart.
- Status: built. Source (read): `goatcore/docs/adr/1025-zenoh-dynamic-tenant-authz-slot-pool.md` sections 1 and 8; `goat-zenoh/templates/config.json5.j2` lines 1803 to 1808; `goat-zenoh/defaults/main.yml` lines 338 and 339.

### 2.2 A slot writes only below its anchor

The write rule for a slot permits `put`, `delete` and `liveliness_token` on three key expressions only:

```text
<anchor>/**
volatile/<anchor>/**
<anchor>/**/@adv/**
```

The slot's policy also permits a schema declaration (rule `trial-peer-w-attest-schema`). All other writes are denied. Source (read): `config.json5.j2` lines 1434 to 1451 and 1956.

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
- Source (read): `zenoh-data-fabric.md`, "No one subscription may match the whole keyspace"; `config.json5.j2` lines 869 to 899.

**For us.** The host fusion node and the host recorder must subscribe with a wildcard in the first chunk only, for example `*/telemetry/sapient/**`. They must never subscribe to `**`.

### 2.5 Release lanes

`release/<set>/**` is the only path for data that leaves the environment. It is denied by default. A producer that has a grant for a set gets one more write rule, `release-w-<anchor>`, on `release/<set>/**`. Source (read): `config.json5.j2` lines 1482 to 1506; `goatcore/docs/adr/1208-sovereign-environments-release-namespaces-and-grant-encryption.md` decision 3.

### 2.6 The access list is static, and a denial is silent

- Zenoh reads `access_control` only at start. A change needs a router restart (read: `zenoh-data-fabric.md`, "Router configuration").
- A denied write or subscription gives no error at the sender or the receiver. Thus you test the access list by asking it, not by watching for errors (read: `zenoh-data-fabric.md`, "Access control").
- goat's tools for that are `acl-evaluate.py` and `goat acl test`. See section 6.

### 2.7 Cut-off

Zenoh has no certificate revocation list. To stop a system immediately, remove its peer from the mesh. A host that connects with one identity for all that is behind it, such as a pod, is cut off as one unit (read: ADR 1025 section 5).

### 2.8 Delivery

- There is no broker. There is no central queue, no broker acknowledgement and no retry. The producer is responsible for delivery (notes: `goatcore/docs/design/zenoh-brokerless-consequences.md`).
- A command that waits during a partition expires. It is not sent again automatically (read: `zenoh-data-fabric.md`, "Deployment topology + ACL contract").
- `goat pub --confirm` reads the value back from the router's storage (read: `goatcore/docs/tutorials/00-goatlite.md` section 8).
- Liveliness tokens and the advanced publisher and subscriber are client features. They operate with the stock router (read: ADR 1025 section 7, the note of 2026-06-11).

### 2.9 Router configuration

A fabric router has one JSON5 file: `mode: "router"`, one listen endpoint `tls/<mesh-ip>:7447`, mutual TLS, the REST plugin, RocksDB storage with one store for each live slot, and `access_control` with `default_permission: "deny"`. goat renders it from a template of 2,032 lines (read: `zenoh-data-fabric.md`, "Router configuration"; `config.json5.j2`).

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

**For us.** Step 1 sets no session ID: the pod bridge, the fusion nodes, the sensors, the recorders and both routers use random IDs, and no publisher attaches source info. Whether the pod bridge and the host fusion node set their ID to their anchor, whether the routers get a fixed ID, and whether our publishers attach source info is open for step 4.

## 3. Pods in goat

### 3.1 Two classes

| Class | What it is |
|---|---|
| POD | A node in our mesh that uses our NetBird, our identity service and our CA. It can operate its own local Zenoh router for the systems behind it. We administer it. |
| MOON | The one uplink peer of a foreign goatnet that has its own full stack. We do not probe it. |

A link from our fabric into a pod's local router is not part of the base rights of a pod. It is a separate grant with the name `router-peer`, given for each pod. goat also says that a moon pod is a learning tool, not the operational path between nations. Source (read): `goatcore/docs/adr/1092-moon-pod-peer-classes.md`.

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

More facts:

- `hello-galaxy-zagros-pod` runs the moon pod shape on a laptop with no goatnet. Its fabric router is a stand-in that permits everything on purpose (read: `stack/templates/fabric-router.json5.tmpl`).
- The moon pod contract says that the pod router does not connect into a goat core router. It connects to an ingress gateway that goat operates (read: `zagros-moon-pod/docs/partner-contract.md`).
- octo-pod's SAPIENT arm relays only detection reports and alerts, writes its own node ID into each message, and rejects each task (notes).
- Open Billie's SAPIENT encoder makes detection reports only. It makes no registration, status report, task or alert (notes).

**For us.** We use a bridge process, as octo-pod and Open Billie do. A router cannot rename a key in transit, and the keys in our pod are different from the keys on the fabric.

### 3.4 The partner contract

The moon pod contract has seven requirements (read: `zagros-moon-pod/docs/partner-contract.md`). Four of them apply to our pod design:

- Transport: encrypted end to end between the two edges. WireGuard is preferred, and IPsec is accepted.
- Landing interface: data goes in and out at well-known Zenoh keys below the pod's namespace.
- Audit: the pod's owner keeps 90 days or more of access logs for the namespace.
- Schema: each published topic has a schema declaration at `attest/schema/<topic>`. The goat boundary rejects a topic with no declaration.

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
- Status: the first federation between two separately administered environments was on 2026-11-09, with many manual steps. `goatbuilder federate` has six package verbs on `main`. The one-command procedure is not built. Grant encryption across the boundary is not usable yet (read: ADR 1208, "Consequences").
- Tutorials: `goatcore/docs/tutorials/03-boundary-node.md` and `04-two-sovereigns.md`.

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

Not found: a statement that the machine can be arm64, and a procedure that mints a slot identity for a system (such as our pod bridge) on a goatlite. `goat admin onboard` needs operator credentials and the portal.

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

## 8. Gaps and unknowns

1. **Zenoh versions.** Our pod uses 1.10.2 and goat uses 1.9.0. Measured in check G1-01 (`docs/acceptance-goat1.md`): two sessions of our Python binding (zenoh 1.10.2) exchanged a sample and a liveliness token over mutual TLS through a router from `eclipse/zenoh:1.9.0`, and again after one restart of that router, with no new declaration. The step 1 rig then ran with a 1.10.2 pod router and a 1.9.0 fabric router. Not measured: x86-64, load, the full access lists in the pairing probe, and any other pair of versions.
2. **Slot identity on a goatlite.** No procedure found for a system that is not the founder.
3. **Pod at the edge through the internet.** This needs goat's internet profile with relays and a public zone. It is not proven on a goatlite.
4. **Router-to-router pod link.** Designed, not built, for operational pods. We use a bridge.
5. **Schema declaration.** The format at `attest/schema/<topic>` was not read. `goatcore/docs/design/data-dictionary.md` describes it.
6. **Key shape.** Decided in the step 1 design (`docs/superpowers/specs/2026-11-11-goat-step1-pod-to-host-design.md`). The four key forms on the fabric are:
   - `<anchor>/telemetry/sapient/<site>/v2/<kind>/<node_id>` for `registration`, `status_report`, `detection_report`, `alert` and `error`
   - `<anchor>/ack/<site>/sapient/v2/<kind>/<node_id>` for `registration_ack`, `task_ack` and `alert_ack`
   - `<anchor>/task/<site>/sapient/v2/task/<node_id>` for `task`
   - `<anchor>/telemetry/sapient/<site>/v2/live/<node_id>` for the liveliness token

   `<anchor>` is the writer's 32-character slot anchor, `<site>` matches `[a-z0-9]+`, and `<node_id>` is a canonical UUID. A key never holds a report ID, a task ID, an object ID or a timestamp (Zenoh issue 2825: a router can freeze when a face uses up its 16-bit space of expression IDs), so the last segment is the node, not the event. For that reason the `ack/` and `task/` forms end with the node ID, not with goat's `<cmd-id>` or `<task-id>` of section 2.3.
7. **Quality of service.** goat's classes by prefix are designed, not built. Our priorities for each message kind are set by the sender.
8. **Time.** The signed clock report for each host is built. The time quality field for each message is not built (read: `hello-galaxy-time-hygiene/README.md`).
9. **Federation.** The one-command procedure is not built.
10. **Scale.** goat's validated data stops near 100 peers (notes).
11. **Session ID.** goat's ADR 1041 (proposed) fixes a router's session ID for each host and sets a publisher's to its slot anchor. Step 1 sets no session ID anywhere (section 2.11). Open for step 4.

## 9. Where to read more

All paths are in `../usareur-af/`.

- `goatcore/docs/design/zenoh-data-fabric.md`: the fabric, the key taxonomy, the access list.
- `goatcore/docs/design/zenoh-brokerless-consequences.md`: what is not possible with no broker.
- `goatcore/docs/adr/1025-zenoh-dynamic-tenant-authz-slot-pool.md`: slots.
- `goatcore/docs/adr/1041-zenoh-router-zid-pinning-and-source-provenance.md`: the session ID as a label, a fixed router ID, and source info.
- `goatcore/docs/adr/1092-moon-pod-peer-classes.md` and `1122-scale-envelope-systems-vs-peers-pod-tier.md`: pods.
- `goatcore/docs/adr/1157-cross-sovereign-federation-edge-terminated.md` and `1208-sovereign-environments-release-namespaces-and-grant-encryption.md`: sovereigns.
- `goatcore/docs/design/goatlite.md` and `goatcore/docs/tutorials/00-goatlite.md`: the smallest real goatnet.
- `goatcore/ops/ansible/roles/goat-zenoh/`: the router role, its template and `acl-evaluate.py`.
- `hello-galaxy-zagros-pod/`: a pod router and a fabric router on a laptop.
- `octo-pod/` and `open-billie/`: goat's two edge products.
