# Goat step 4c: end goal

Written on 2026-11-26. This file gives the end goal of step 4c. It is not the design and not the plan. Nothing was built or run for it. The drawing is tab 2, "2 Internet profile + relay", of `../doc/goatlite-aws-architecture.drawio` (outside this repository).

Each statement says where it comes from: **read** (from goat source or from this repository), **measured** (on the live `cuaslab`), or **inferred** (not checked).

goat source read: `goatcore` at `b454a0b5` for the relay module and the render. The status of the internet profile was read again at `6e3ca30f` (2026-11-26) and is the same.

## 1. The goal in one paragraph

The goatnet moves from the Mac to an AWS account, and the rig reaches it through the internet with no VPN. The goatnet is a goatlite with the internet profile: one goatlite box in a private subnet and one goat relay with a public address. The rig of step 4b stays as it is on the Mac. Its pod bridge and its two host programs connect to the fabric router through goat's own WireGuard mesh (NetBird). After that, the host programs move to an EC2 instance, so that the host is in a cloud, as the end goal of the roadmap says.

## 2. Why this step

- Steps 4 and 4b have no mesh. The pod bridge and the host programs connect to the router's LAN address (`docs/goat-context.md` gap 14, `docs/goat-hierarchy.md` section 5). Step 4c closes that gap: each machine becomes a mesh peer.
- The roadmap's end goal puts the host "in a cloud or a data centre". In steps 4 and 4b all machines are VMs on one Mac.
- A goatnet in a private subnet behind a relay is the nearest small shape to a production goatnet. Step 5 (pod 2) and step 6 (the second sovereign) can then start from a goatnet that is reachable from more than one place.

## 3. The target architecture

| Part | Where | What |
|---|---|---|
| Relay VPC `10.99.1.0/24` | AWS, made by goat's Terraform module `goat-relay` | One public subnet, an internet gateway, one relay instance with an Elastic IP. No NAT gateway. (read) |
| goat relay | Relay VPC | NetBird relay on 33073 TCP and UDP, HTTPS ingress on 443 and the control port 2333 (rathole), STUN on 3478 (coturn). SSH is closed; the instance is managed through SSM. (read) |
| goatlite VPC `10.42.0.0/16` | AWS, our own Terraform | A public subnet `10.42.1.0/24` with a NAT gateway, and a private subnet `10.42.2.0/24`. (our design) |
| goatlite box | Private subnet | Ubuntu 24.04. The Zenoh router listens on the mesh address only. The portal and the dashboard serve mesh clients only. NetBird management and signal, mesh DNS. It has no public address and accepts nothing from the internet. It calls out to the relay on 2333 and 33073. (read for the services, our design for the subnet) |
| Cloudflare DNS | Public | The public zone of the goatnet and the ACME DNS-01 records. (read) |
| Edge site | The Mac mini | Pod 1 in Colima, the host programs in the VM `goathost` (stage 1), the operator's tools, and a NetBird client. (this repository) |
| Host VM | Private subnet (stage 2) | `host-fusion` and `host-recorder` on an EC2 instance that is a mesh peer. |

The paths:

1. **Mesh.** NetBird client on the Mac, to the relay through the relay VPC's internet gateway, to the goatlite box. The box reaches the relay through the NAT gateway.
2. **Fabric.** Zenoh over TLS on port 7447, inside the WireGuard tunnel. Only three programs of the rig use it: `pod-bridge`, `host-fusion` and `host-recorder`. The network `pod1` is internal, so the sensors and the pod router never leave the pod. (read from `docker-compose.goat1.yml` and `docker-compose.goat4.yml`)
3. **Stage 2.** The host VM and the goatlite box are in the same subnet. NetBird usually connects such peers directly on their private addresses, and the relay is not in the path. (inferred)

## 4. Two stages

| Stage | Change | The rig |
|---|---|---|
| 1 | The goatnet is in AWS. | All of the rig stays on the Mac. The fabric address in the overlay changes from a LAN address to the router's mesh address. New certificates and a new grant, because it is a new goatnet. |
| 2 | The host is in AWS. | `host-fusion` and `host-recorder` run on the host VM, as in step 4b but on EC2. Pod 1 stays on the Mac. |

## 5. What must be shown

These are candidates for the acceptance checks. The design gives them numbers.

1. The standup of the internet profile ends, and goat's own assay passes on the new goatnet.
2. The goatlite box has no public address, and no security group rule accepts traffic from the internet for it.
3. The Mac enrols as a mesh peer and reaches the portal by its public name with an ACME certificate. No private CA has to be trusted for the portal.
4. The pod bridge and the two host programs connect to the router's mesh address. The host fuses the pod's tracks, and a task goes down to the pod and is acknowledged. These are the checks of step 4, run again on the new path.
5. With the Mac's mesh peer removed on the portal, the rig loses the fabric. Steps 4 and 4b could not show a cut-off of a machine.
6. The clock difference between the Mac and AWS, and whether a fusion node rejects a message for time. The validator's window is -0.1 s to 0.9 s (measured in step 4b on one Mac, where the clocks agreed to a few milliseconds).
7. The round trip of a task through the relay, to compare with the 11 ms median of step 4b.
8. Stage 2: the same checks with the host on EC2, and whether the path between the host VM and the box is direct or through the relay.
9. The earlier rigs still work: the TCP-only rig and steps 1 to 4b on `cuaslab`.

## 6. Not in this step

- More than one relay, more than one region, a second site, federation. These are in the drawing's tabs 3 to 5 (phase 1 with goatlite, phase 2 in the production shape, the two federation cases) and in later steps.
- Performance of the relay. A small relay instance gives no numbers that hold for a production relay.
- A change to goat's source. If the internet standup fails in goat's code, the step records it and reports it; it does not patch goat in place.

## 7. Risks and open points

| # | Point | State |
|---|---|---|
| 1 | No goatlite with the internet profile was stood up against real relays, by anyone. goat's design says "WIP, not for production use". We would be the first. | read at `6e3ca30f` |
| 2 | How a container in Colima or in `goathost` reaches a mesh address. The NetBird client is on macOS; the containers are in VMs behind the Mac. Options: route through the Mac's client, or a NetBird client in each VM (then each VM is its own mesh peer, which is goat's model). | open, nothing tried |
| 3 | The Mac already runs a NetBird client with the profile `cuaslab`. Whether one client can hold two goatnets at a time was not checked. | open |
| 4 | The name in the router's certificate against the mesh address that the rig connects to. | open |
| 5 | The operator's SSH path to the box for Ansible: SSM, or the mesh after the first enrolment. | open |
| 6 | `goat4/enroll.sh` has the custodian, the affiliation and the API key name of `cuaslab` written in it, and `docker-compose.goat4.yml` has the address `192.168.64.4` on three lines. | read; small changes |
| 7 | The render has no setting for the relay's instance type. A smaller relay needs one line in the generated Terraform, and a new render can remove it. | read |
| 8 | The assistant's AWS access is read-only. Richard applies the Terraform himself. | fact of this account |

## 8. What it needs

- A public DNS zone on Cloudflare, with an API token for DNS-01.
- An AWS profile that can create the two VPCs, the instances, the Elastic IPs, the NAT gateway and two Secrets Manager secrets.
- The goat source at a pinned commit, chosen at the start of the design.

## 9. Cost

List prices for us-east-1, taken from memory and not checked against the AWS price list.

| Case | Per month |
|---|---|
| goat's default sizes (relay `c7i.2xlarge`, box `m7g.xlarge`), running all the time | about $430 |
| Small sizes (relay `t3.medium`, box `t4g.large`), running all the time | about $125 |
| Small sizes, stopped between sessions (40 hours per month), NAT gateway kept | about $50 |

Measured on `cuaslab` (4 vCPU, 16 GB) with the rig idle: 1.9 GB of memory in use, load 0.16. The peak during a standup was not measured, so the first standup uses the larger box.

## 10. Effort

5 to 8 working sessions for stage 1 (inferred). The largest unknown is risk 1.

## 11. Questions for Richard before the design

1. Which AWS region?
2. Which public zone on Cloudflare?
3. For risk 2: one NetBird client in each VM (goat's model, the recommendation), or a route through the Mac's client?
4. Is stage 2 a part of step 4c, or its own step?
