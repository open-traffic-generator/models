# Collective Communications Model Refactor — Design Notes & Action Items

Living document for the `ai_workload` → `collective_communications` model refactor.
Part 1 records what changed in the OTG schema and why; Part 2 tracks what is still
outstanding.

**Scope: this repo only.** Everything here concerns the OTG model. Converter and server
middleware work lives in other trees and is deliberately not tracked in this document.
Proto convertibility analysis lives in
[collective_communications_proto_convertibility.md](collective_communications_proto_convertibility.md).

Last updated: 2026-08-25

---

# Part 1 — Design notes

## Name changes

    Trial -> AiWorkload -> CollectiveCommunications

The top-level `ai_workload` config section was renamed to `collective_communications` (Collective Communication
Benchmarks) and restructured into the openconfig/ondatra separation of traffic, testbed
and bindings:

    collective_communications.workload      hardware-independent traffic definition (was workload_type;
                      before that, `app` with a collective_benchmark variant)
    collective_communications.infrastructure      traffic-independent testbed: emulated infrastructure
                      (absorbs bindings.logical_infrastructure)
    collective_communications.platforms     platform inventory, keyed by name (was ai_workload.platforms)
    collective_communications.bindings      workload <-> infrastructure <-> physical mapping
    collective_communications.impairments   test-scenario overlay (unchanged shape)
    collective_communications.transport     CC-specific rank-scoped transport settings
                      (qp_negotiation, qps_per_rank_pair); the transport itself
                      is derived from the emulated device
    collective_communications.result_info   result tags/description (unchanged shape)

The `Topology` wrapper is gone. It had shrunk to `name` + `infrastructure` once `platforms`
moved to the top level, so renaming it would have produced `infrastructure.infrastructure`;
instead it was collapsed — `collective_communications.infrastructure` now refs
`Infrastructure` directly.
`Config.Generate.Request.topology` became `infrastructure` likewise. The wrapper's `name` was
dropped rather than carried down: nothing referenced it (no `x-constraint` targets it),
`infrastructure` is a singleton so there is nothing to disambiguate, and its only consumer was
the display-only `profiles.ProfileInfo.name`. `Infrastructure` is a description of a
testbed, not a named object. The word "topology" is
retained only where it means the *shape of a fabric* (clos, rackplane, trayrack, blackbox),
which is the correct term there, and in the legacy `channels.ChannelsTopology`.

**The normal path is to omit `infrastructure` entirely.** On the config the property is
optional (the generate request still requires it); omitted, the server derives an
infrastructure at runtime from the rest of the config and saves the derived form
alongside the report for the run that used it. Persistence is the server middleware's
responsibility and is out of scope for this repo; the schema is written against that
assumption. Action item 2 tracks it.

*Supplying* an infrastructure is a **future capability**: it lets a script submit a
precompiled definition to be used in place of the one the server would have generated.
`Infrastructure` is therefore a choice of the form that definition takes:

    chakra      CollectiveCommunications.ChakraInfrastructure — an already-compiled
                Chakra graph, carried as opaque JSON, used as given
    infragraph  CollectiveCommunications.InfraGraphInfrastructure — the declarative
                {host, fabric} form the server compiles into a Chakra graph

`{host, fabric}` therefore now sits one level down, on `InfraGraphInfrastructure`, rather
than on `Infrastructure` itself. `x-status: under_review` sits on `Infrastructure` rather
than on either branch, since it is *supplying* an infrastructure that is unimplemented,
not one particular form of it.

`Infra` is no longer abbreviated anywhere in the OTG surface: `CollectiveCommunications.InfraRef`
→ `InfrastructureRef`, `InfraRegion` → `InfrastructureRegion`, and the `infra_ref` property on
all four binding types → `infrastructure_ref`. The legacy proto keeps `bind.InfraRef` and
`binding.infra_annotations`; only the OTG names changed.

Within `workload`, the old `app.collective_benchmark.benchmark` wrapper is gone: the
`single_collective` variant carries `collective_algorithm`, `datasizes`, `iterations` and
`iteration_append_delay` directly.

Binding *generation inputs* no longer live in the configuration. `platform_regions` and
`group_specs` moved to `POST /config/generate` (`CollectiveCommunications.Config.Generate.Request`),
and the `infrastructure_annotations` plus the `logical_infrastructure` copy were dropped
from the config entirely.

The compiled Chakra graph is no longer *unconditionally* dropped: it survives as the
opt-in `infrastructure.chakra` branch above, for callers that have a graph already and
want compilation bypassed. It costs nothing to omit — the server regenerates it — so
the declarative `infragraph` branch remains the normal path.

The *inputs*, however, have no home in the config at all, and deliberately so: a
`run_id` on the configuration was considered as a way to key them and was **rejected**.
The server middleware retains them instead and saves them together with the report for
the run they were used in, so nothing about how a configuration was generated is
modelled on the configuration itself. That retention work is not done, and is out of
scope for this repo.

## Network-stack migration onto the native OTG surface

Layer 1–4 settings were removed from `ai_workload` and are now expressed with native OTG
objects, referenced from `collective_communications.bindings` by name. This section replaces a previously linked
`aiworkload-transport-migration.md`, which was never committed to this repo.

The schemas deleted from the old `ai_workload` tree were `ChassisInfo`, `ServerInfo`,
`Layer1`, `NicSettings`, `NicIpAddressing`, `NicTransport`, `Ipv4Addressing`,
`Ipv6Addressing`, `Vlan`, `VlanTag`, `CongestionControl`,
`ExplicitCongestionNotifications`, `DCQCNRateControl`, `Qos` and `PacketCapture`. Their
native homes:

| Former `ai_workload` schema | Native OTG home |
|---|---|
| `ChassisInfo`, `ServerInfo` | `Port.location` — referenced by `CollectiveCommunications.PhysicalBinding.port_name` |
| `Layer1` | `Config.layer1` |
| `NicSettings`, `NicIpAddressing`, `Ipv4Addressing`, `Ipv6Addressing` | `Device.Ethernet` (+ `ipv4_addresses`) — referenced by `CollectiveCommunications.NicBinding.ethernet_name` |
| `Vlan`, `VlanTag` | `Device.Ethernet.vlans` |
| `CongestionControl` (ECN, DCQCN) | `options.per_port_options[].rocev2` → `Rocev2.PerPortSettings.{cnp,dcqcn_settings}` |
| `CongestionControl` (PFC) | `Layer1.flow_control.ieee_802_1qbb` (`pfc_delay`, `pfc_class_0..7`) |
| `NicTransport`, RoCEv2 retransmission/reordering | `Rocev2.PerPortSettings.connection_type.reliable_connection` (`Rocev2.AckAndNak`) and `enable_rx_reordering` |
| RDMA verb, message size, QP reuse (were `Rocev2TransportSettings`) | `Device.Rocev2Peer.{verb, rdma_message_size, reuse_qps}` |
| RoCEv2 DSCP / ECN per QP | `Device.rocev2` → `Rocev2.V4Peer.qps[]` → `Rocev2.QPParameters` |
| `PacketCapture` | `Config.captures`, `options.per_port_options` |
| `Qos` | no native home yet (PRIVATE in the protos) |

Related notes carried over:

- **RoCEv2 settings** — most moved to `devices/rocev2`; some sit on the QP object
  (still under `rocev2`).
- **TCP settings** — replaced with native OTG.
- **Methods** — converted to state changes (idempotent approach).



## `transport` is CC-specific residue, not a transport selector

`collective_communications.transport` is a singleton sibling of
`workload`/`infrastructure`/`bindings` holding exactly two properties:

    qp_negotiation      how ranks negotiate QPs; one rendezvous per workload
    qps_per_rank_pair   number of QPs to open per rank pair

Both are defined **in terms of ranks**, which is why they have no native home. Everything
else that used to live here moved out:

| Was | Now |
|---|---|
| `choice: rocev2 \| tcp` | derived — see below |
| `verb`, `rdma_message_size`, `reuse_qps` | `Device.Rocev2Peer` (item 3 — per-`Device`, so per-plane) |
| congestion control, reliability, ACK/NAK, reordering | `Rocev2.PerPortSettings` |
| IB MTU, peers, QPs | `Rocev2.V4Interface` / `V4Peer` |

### The transport is derived, not declared

There is no transport selector anywhere. `NicBinding.ethernet_name` designates it:

- **RoCEv2** — a `Device.rocev2` stack references one of that `Device.Ethernet`'s
  addresses (`Rocev2.V4Interface.ipv4_name` → `Device.Ipv4/properties/name`, or the v6
  equivalent).
- **TCP** — nothing references it; the `Device.Ethernet` alone models the NIC.

This works because TCP has no per-NIC settings to carry — `common.TcpTransport` is an
empty message in the legacy protos too. A per-port TCP settings object was considered and
rejected for the same reason: it would have had no properties.

Scale-up vs scale-out therefore needs no naming layer: two NICs differ by their device
configuration. This is what closed item 1 — see the entry for why the earlier
named-`transports[]`-plus-`transport_name` design was abandoned.

### Why these two can't descend

Neither property can attach to a NIC, a port, or a platform:

- **rank ↔ port is many-to-many.** `RankBinding.nic_refs` is a list, `Ethernet.Connection.port_names`
  lets one NIC span ports, and multiple NICs may share a port (the cardinality trap in items
  4–5). So one rank pair maps to many port pairs — a per-port count would multiply or collapse.
- **A rank pair may straddle two platforms**, since `platforms` explicitly supports workloads
  spanning more than one type. There is no answer to "whose value wins" for a heterogeneous pair.
- **The rendezvous is one service.** Per-NIC or per-platform copies of `tcp_store` would be N
  conflicting addresses for a single endpoint.
- **Platform *regions* do not exist in the applied config at all** — they are generate-time
  inputs, collapsed to `PhysicalBinding.platform_name` by generation. Attaching settings to a
  region would reintroduce the copy-that-drifts problem.

Genuinely platform-specific knobs have a home already: `PlatformConfig.custom_settings`.

### Device grouping is the plane boundary

Nothing in the model ties an OTG `Device` to an infrastructure host. The two identities are
independent:

- `Device.name` is free-form, and `Config.devices[]` may partition a host's ethernets any way
  the author likes.
- `NicBinding` references an **ethernet by name** (`ethernet_name`), never a device.
- The infrastructure host identity lives in `infrastructure_ref.device_instance_name`, which is
  the Chakra-side name — unrelated to `Device.name`.
- `Rocev2.V4Interface.ipv4_name` is a **global** constraint
  (`/components/schemas/Device.Ipv4/properties/name`, no `#`), so a RoCEv2 stack's association
  with a NIC is by address name and is not scoped to the enclosing device either.

So a host's scale-up and scale-out NICs can be modelled as two devices —
`host_0_scale_up` and `host_0_scale_out` — each carrying its own `rocev2` peer and therefore
its own `verb` / `rdma_message_size` / `reuse_qps`. That is what makes item 3's device-level
placement sufficient: **the device is the plane boundary**, and no per-NIC override is needed.

## Platforms

Platforms are identified **by name**, not by type. The old model could not express two
platforms of the same type (e.g. two custom platforms from different vendors), so
`CollectiveCommunications.PlatformConfig` carries a `name` plus a free-string `platform_type`, and
`CollectiveCommunications.PhysicalBinding.platform_name` / `CollectiveCommunications.PlatformRegion.platform_name` reference it via
`x-constraint`. `platform_type` is deliberately not an enum so new platform types do not
require a schema change; the implementation validates.


## run_id

**Considered and reverted.** A `run_id` was added to
`CollectiveCommunications.State.Execution` (replacing `Stopped.Success.archive_id`) and
then removed again, and a `run_id` on `CollectiveCommunications` itself was proposed and
rejected. Exposing a run identifier on the model needed the same middleware work either
way, so the field bought nothing; and the configuration should carry no record of how it
was generated. The model therefore carries no run identifier at all. Where a
`generate_config` request's inputs are retained is a middleware concern, out of scope for
this repo.

---

# Part 2 — Action items

## Done

- [x] Rename `ai_workload` → `collective_communications`; split the 1300-line schema into per-concern files
      (`collective_communications/{collective_communications,workload,infrastructure,platform,bindings,impairments,transport,generate}.yaml`).
- [x] Restructure into `workload` / `infrastructure` / `bindings` / `impairments` / `transport` /
      `result_info`; delete the `DetailedBindings`/`StandardBindings` wrappers.
- [x] Move generation inputs out of the config; drop the compiled Chakra graph.
- [x] Place `transport` at the top level rather than under `bindings`.
- [x] Reduce `CollectiveCommunications.Transport` to the two rank-scoped properties that
      have no native home (`qp_negotiation`, `qps_per_rank_pair`); delete
      `Rocev2TransportSettings` and the `rocev2`/`tcp` selector. The transport is derived
      from the emulated device instead. Closes item 1.
- [x] Add `CollectiveCommunications.State.Execution.run_id` (removing
      `Stopped.Success.archive_id`), then revert it; and reject a `run_id` on
      `CollectiveCommunications` itself. See "## run_id".
- [x] Reserve `Config.artifacts` (uid 102) as an empty `Placeholder.Object` in
      `config/artifacts.yaml`, `x-status: under_review`, a sibling of
      `collective_communications` (uid 101). Reserves the name and the field number for
      artifacts settings without committing to a shape.
- [x] Fix the `mix_of_collectives` orphan and the `AllocationStrategy` uid gap.
- [x] Add descriptions to 16 choice properties in the restructured surface.
- [x] Fold `otg_integration_notes.md` into this document and drop the dangling
      `aiworkload-transport-migration.md` link, replacing it with the
      network-stack migration section in Part 1.
- [x] Add expanded `CollectiveCommunications.Bindings.process_groups`
      (`CollectiveCommunications.ProcessGroup{name, xpu_refs}`) at uid 4, mirroring
      `bind.CustomBinding.process_groups` #4. Resolves items 5 and 9.
      `platform_regions` deliberately stays generate-only — its effect is already
      per-element in `CollectiveCommunications.PhysicalBinding.platform_name`.
- [x] **Item 3** — move the per-NIC RoCEv2 settings onto the native surface:
      `Device.Rocev2Peer` gains `rdma_message_size` (3), `verb` (4) and `reuse_qps` (5), all
      with the defaults they had on the deleted `Rocev2TransportSettings`. This is what made
      collapsing `transport` possible.
- [x] Spell out `Infra` → `Infrastructure` across the OTG surface (`InfrastructureRef`,
      `InfrastructureRegion`, `infrastructure_ref`); legacy proto names unchanged.
- [x] Promote `platforms` out of the testbed wrapper to a top-level sibling at uid 7,
      in its own `collective_communications/platform.yaml`. The inventory is referenced by
      name from `PhysicalBinding.platform_name` and `PlatformRegion.platform_name`, neither
      of which is scoped to the testbed, and a platform is a property of the *run* rather
      than of the emulated infrastructure. This is what left the `Topology` wrapper holding
      only `name` + `infrastructure`, and so led to its deletion below. Opens item 8.
- [x] Prefer `infrastructure` to `topology` throughout: dropped the `Topology` wrapper,
      promoted `Infrastructure` to `collective_communications.infrastructure` (uid 2)
      and to `Generate.Request.infrastructure` (uid 1). Deleted
      `collective_communications/topology.yaml`. Kept "topology" for fabric
      shape and for `channels.ChannelsTopology`.
- [x] Make `infrastructure` optional on the config and shape the supplied form as a
      `chakra` / `infragraph` choice, for the future capability of a script submitting a
      precompiled infrastructure in place of the generated one. The declarative
      `{host, fabric}` form moved down to `CollectiveCommunications.InfraGraphInfrastructure`
      (uid 3); `ChakraInfrastructure` (uid 2) takes an already-compiled graph verbatim.
      `x-status: under_review` moved off `ChakraInfrastructure` onto `Infrastructure`, so it
      covers both branches. Omitting the property — the normal path — leaves the server to
      derive one and save it as a run artifact.
- [x] Drop the infrastructure `name`. It survived two wrapper deletions
      (`LogicalInfrastructure` → `Topology` → `Infrastructure`) without a consumer:
      no `x-constraint` targets it, the object is a singleton, and its only reader was the
      display-only `profiles.ProfileInfo.name`.
- [x] Housekeeping on the shared surface, outside `collective_communications/`: deleted
      four dead schemas from `common/common.yaml` (`ChoiceNone`, `Paginated.Object`, and a
      duplicate pair of `SnowflakeId.Object` definitions where the second silently won —
      none referenced by any schema, only by the generated artifacts), and corrected
      `x-status: under-review` → `under_review` in `flow/flow.yaml` and `layer1/layer1.yaml`
      so every `x-status` in the repo now uses the one spelling.

## Model design decisions (need PM / architecture input)

| # | Item | Notes |
|---|---|---|
| 1 | ~~**Two transports (scale-up / scale-out).**~~ **RESOLVED, no naming layer needed.** Two NICs differ by their `Device.rocev2` configuration, so scale-up and scale-out are already distinct without named transports. `transport` was briefly made an array of named transports with a proposed `NicBinding.transport_name`; that was abandoned once it was clear the device config already states the transport and `transport_name` would be a second, contradictable representation of it. `Transport` now holds only `qp_negotiation` and `qps_per_rank_pair`. | |
| 2 | **Scale-up/scale-out is positional, not first-class.** `RackPlaneHost` builds one `nic` component of `scale_up + scale_out` count; membership is an index-range convention (`scale_up_offset`). `InfrastructureRef` cannot say which network a NIC is on. | Blocks #1 from being expressible cleanly. First-class option: a network/plane concept in `collective_communications.infrastructure` that NICs belong to. Splitting the Chakra `nic` component is guarded by a backcompat comment. Only rackplane/trayrack have the concept, and both are `x-status: under_review`. |
| 3 | ~~**Move `Transport` fields onto `Device.Rocev2Peer` as defaults.**~~ **DONE** — `rdma_message_size` (3), `verb` (4), `reuse_qps` (5) added to `Device.Rocev2Peer` with their previous defaults; `Rocev2TransportSettings` deleted. `qp_negotiation` and `qps_per_rank_pair` stayed on `transport`, being rank-scoped. | Granularity is **per-`Device`**, and a `Device` is any grouping of ethernets the author chooses — nothing ties one to an infrastructure host. So scale-up and scale-out get their own settings by being separate `Device`s (see "Device grouping is the plane boundary" in Part 1). |
| 4 | **Channels are unmodelled.** `kccb.Benchmark.channels` (`ChannelsTopology` → `Channel{algorithm_type, rank_distribution}`) has no OTG counterpart. | `CollectiveCommunications.RankDistribution` is **defined but referenced by nothing** — the stranded leaf of the missing container. Either model channels or delete the orphan. Largest single-collective gap. |
| 5 | ~~**`process_groups` have no config home.**~~ **RESOLVED** — `CollectiveCommunications.Bindings.process_groups` #4 added. | Chosen over server-side derivation because groups may overlap (so they are not derivable from `rank_bindings`) and `mix_of_collectives.proto:148` references them by name. |
| 6 | **Four homeless `dse.Trial` fields:** `sim_config` (~40 structured fields), `hf_sampling` (results already exist for it), `nccl_config`, `trial_meta`. | `nccl_config` fits `PlatformConfig.custom_settings`; `sim_config` would be badly served by flattening. Decide homes or record as legacy-only. |
| 7 | **`result_info` / templates.** Deferred by decision; currently unchanged (tags + description). | A `templates` category referencing report templates by name can be added later as a sibling top-level property without breaking. |
| 8 | **Add `platforms` to `CollectiveCommunications.Config.Generate.Request`.** `platforms` is now a top-level sibling of `infrastructure`, but the generate request carries only `infrastructure`, `platform_regions` and `group_specs` — so `PlatformRegion.platform_name` points by `x-constraint` at an inventory that is not in the request. Either add the inventory to the request or define it as resolving against the `platforms` already on the server's config. | |
| 9 | ~~`CollectiveCommunications.Bindings` uid 4 is free after the transport move. Reuse or reserve?~~ **RESOLVED** — reused for `process_groups`, which also makes the uid match `bind.CustomBinding.process_groups` #4. | |

## Model hygiene

| # | Item |
|---|---|
| 10 | **28 metrics properties still lack descriptions** (all in `result/collective_communications/*.yaml`). MODEL-GUIDE says descriptions are a MUST. |
| 11 | **`packet_reorder` has no metrics file** though `packet_drop` does, and `storage_v2.DataFileType` defines both `PACKET_DROP_METRICS = 12` and `PACKET_REORDER_METRICS = 13`. |
| 12 | `mix_of_collectives` and `workload_replay` are single-`placeholder` schemas; the protos model both richly (`WorkloadSet`/`Workload`/`Operation`/`PointToPoint`, and `CompactedWorkload` + Chakra nodes). |
