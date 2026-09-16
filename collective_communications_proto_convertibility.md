# Collective Communications ↔ Legacy Proto Convertibility Analysis

Status: analysis. The model rename is implemented; the converter rename is a required companion
(see §7 and §8).
Date: 2026-08-21

> **Revision note.** An earlier draft of this document claimed that `OtgService` had no `SetConfig`
> implementation and that only `logical_infrastructure` had converters. Both were wrong.
> `SetConfig`/`GetConfig` are implemented and backed by a near-complete, bidirectional, tested
> converter layer. §1, §3.3, §7 and §8 have been rewritten accordingly; the practical effect is
> that this refactor touches **working code with a test suite**, not greenfield.
> A second earlier claim — that `Stopped.Success.archive_id` is never populated — was also wrong;
> see §6.

## Purpose

The planned refactor renames the top-level OTG config section `ai_workload` → `collective_communications` and
restructures the layer below it into an openconfig/ondatra-style separation:

| new section | content |
|---|---|
| `collective_communications.workload` | hardware-independent traffic/workload definition (was `workload_type`) |
| `collective_communications.infrastructure` | traffic-independent testbed: emulated infrastructure (absorbs `bindings.logical_infrastructure`) |
| `collective_communications.platforms` | platform inventory keyed by name (was `ai_workload.platforms`) |
| `collective_communications.bindings` | workload↔infrastructure↔physical mapping |
| `collective_communications.impairments` | scenario overlay, stays top-level |
| `collective_communications.transport` | RoCEv2/TCP transport, top-level rather than under `bindings` |
| `collective_communications.result_info` | unchanged for now (tags + description) |

Binding *generation inputs* (`platform_regions`, `group_specs`, compiled Chakra
`infrastructure`/`infrastructure_annotations`, the `logical_infrastructure` copy) move out of the
config: generation inputs to `CollectiveCommunications.Config.Generate.Request`, compiled outputs to run artifacts.

This document records whether a config expressed in that shape can be converted back and forth
with the legacy proto API, and where the two models genuinely disagree.

## Sources compared

OTG / OpenAPI (`models/otg_models/`):
`ai_workload/ai_workload.yaml`, `ai_workload/logical_infrastructure.yaml`,
`ai_workload/generate.yaml`, `config/config.yaml`, `result/ai_workload.yaml`,
`control/ai_workload.yaml`.

Legacy protos (`models/protos/`):
`dse.proto` (`Trial`, `TrialReport`, `CreateBindingRequest`), `bind.proto` (`Binding`,
`CustomBinding`, `RankBinding`, `NicBinding`, `PhysicalBinding`, `PlatformRegion`, `GroupSpec`,
`ProcessGroup`), `kccb.proto`, `common.proto`, `channels.proto`, `impairment.proto`,
`mix_of_collectives.proto`, `workload_replay.proto`, `profiles.proto`, `dse_infra.proto`,
`simulation.proto`, `storage_v2/storage_v2.proto`.

Converters: `models/converters/` and `models/tests/converters/`.

---

## 1. Headline conclusion: the convertible unit is `Config`, not `CollectiveCommunications`

`CollectiveCommunications` is not a self-contained convertible unit. Network-stack and physical-resource settings that
the legacy protos carry *inside* the binding were deliberately moved onto the native OTG config
surface:

| proto location | OTG location today |
|---|---|
| `bind.NicBinding.nic_settings` (`common.NicSettings`: MTU, IPv4/IPv6 addressing, MAC, VLAN, QoS, ECN/PFC/DCQCN congestion control, RoCE DSCP, packet capture) | `Device.Ethernet`, `Config.captures` — referenced from `CollectiveCommunications.NicBinding.ethernet_name` |
| `bind.PhysicalBinding.chassis_location` / `server_location` | `Port.location` — referenced from `CollectiveCommunications.PhysicalBinding.port_name` |
| `bind.PhysicalBinding.layer1` (`common.Layer1`: speed mode, autoneg, link training, IEEE defaults) | `Config.layer1` |
| `bind.PhysicalBinding.capture` | `Config.captures`, `options.per_port_options` |

This is already how the implemented converter works, and it is worth stating because it constrains
any restructuring:

- The entry point is `Config` ↔ `dse.Trial` (`TrialConverter`, driven by `SetConfig`/`GetConfig`).
  A converter operating on the `collective_communications` subtree alone cannot produce a valid `bind.Binding`.
- proto → OTG **synthesizes** `Config.ports`, `Config.layer1` and `Device.Ethernet` objects.
  `BindingsConverter.proto_to_otg_inplace` does this today via `PortLocationConverter`,
  `Layer1Converter` and `EthernetNicSettingsConverter`.
- `Port.location` is a formatted string; `common.ChassisInfo` splits it into `address` + `port`
  with the regex `^([1-9]\d{0,2}(\.[1-9]\d{0,2})?)$`. `PortLocationConverter` owns that
  parse/format contract.

The practical consequence: `collective_communications.bindings` cannot be reshaped in isolation. Any change to it is a
change to `BindingsConverter`, which reaches across `Port`, `Layer1` and `Device.Ethernet`.

---

## 2. Where the refactor improves alignment

**Generate request mirrors `CreateBindingRequest`.** Moving `platform_regions` and `group_specs`
out of `bindings` into `CollectiveCommunications.Config.Generate.Request` makes it a near-exact mirror of the proto:

| `dse.CreateBindingRequest` | `CollectiveCommunications.Config.Generate.Request` |
|---|---|
| `infrastructure_profile` (`profiles.InfraProfile`) | `infrastructure` (`CollectiveCommunications.Infrastructure`) |
| `platform_regions` (`bind.PlatformRegion[]`) | `platform_regions` |
| `group_specs` (`bind.GroupSpec[]`) | `group_specs` |
| `platform` (`common.PlatformType`) | **no equivalent** |
| `prev_binding` (`bind.Binding`) | no equivalent (may not be needed) |

**Flattened bindings match `CustomBinding`.** Deleting the `DetailedBindings` / `StandardBindings`
single-entry choice wrappers leaves `rank_bindings` / `nic_bindings` / `physical_bindings` directly
on `CollectiveCommunications.Bindings`, which is exactly `bind.CustomBinding`'s shape.

**Caveat on the same move.** `bind.Binding` deliberately echoes generation inputs back
(`infrastructure_profile` #4, `platform_regions` #10) so trials can be re-run. With
`platform_regions` gone from the config, that echo has no OTG home on the return trip.
(Note: the server does not populate `platform_regions` today either — `binding_creator.py` sets
only `custom_binding`, `infrastructure`, `infra_annotations`, `infrastructure_profile`.)

---

## 3. Load-bearing schisms

### 3.1 Channels have no OTG representation

`kccb.Benchmark.channels` is a `channels.ChannelsTopology`:

```
channels.ChannelsTopology { channels: Channel[] }
channels.Channel         { algorithm_type: common.AlgorithmType, rank_distribution: RankDistribution }
channels.RankDistribution{ oneof: ascending | descending | interleaved | custom{custom_order: int32[]} }
```

`AiWorkload.SingleCollective.Config` has no `channels` property. Any multi-channel trial is
unconvertible in both directions.

Compounding this, `AiWorkload.RankDistribution` (ai_workload.yaml:510) **is defined but referenced
by nothing** — it is the leaf of the missing container. The refactor carries it into
`collective_communications/workload.yaml` still orphaned.

**This is the largest single-collective gap.**

### 3.2 `process_groups` — RESOLVED, expanded form added to `CollectiveCommunications.Bindings`

`bind.CustomBinding.process_groups` #4 is the expanded form:

```
bind.ProcessGroup { name: string (regex ^\S(.{0,33}\S)?$), npus: InfraRef[] }
```

`CollectiveCommunications.Bindings` now carries the matching `process_groups` #4 (`CollectiveCommunications.ProcessGroup{name, xpu_refs}`),
so `proto → collective_communications → proto` is lossless and the config is a complete binding source. The two sides
line up field-for-field:

| `bind.CustomBinding` | `CollectiveCommunications.Bindings` |
|---|---|
| `rank_bindings` #1 | `rank_bindings` #1 |
| `nic_bindings` #2 | `nic_bindings` #2 |
| `physical_bindings` #3 | `physical_bindings` #3 |
| `process_groups` #4 | `process_groups` #4 |

Three reasons the expanded form was chosen over relying on server-side derivation from the saved
generate-request artifact:

- **Groups cannot be derived.** Overlap is explicitly allowed (*"the same NPU ref can be in
  multiple process groups"*), so `rank_bindings` does not determine them.
- **The workload references them by name.** `mix_of_collectives.proto:148` carries
  `process_group_name`, and `bind.ProcessGroup.name`'s tooltip says it is *"used to link workloads
  in the Mix of Collectives config"*. `CollectiveCommunications.MixOfCollectives` is still a `PLACEHOLDER`, so nothing
  dangles yet — but when it is modelled, `process_group_name` needs an `x-constraint` target, and
  `CollectiveCommunications.Bindings.process_groups[].name` is it.
- **It is state, not a generation input.** `group_specs` (prefix + count + strategy) stays in
  `CollectiveCommunications.Config.Generate.Request`; the groups it expands to belong in the applied configuration,
  the same way the infrastructure it compiles belongs in `collective_communications.infrastructure`.

`BindingsConverter` converts both directions, applying the same `xpu` ⇄ `npu` component renaming
it already applies to rank bindings, and warns when a group references an XPU that no
`rank_bindings` entry binds (the reference is still carried through; the server validates).

The OTG schema uses `minLength: 1` / `maxLength: 35` rather than the proto regex, because nothing
in the model uses `pattern:` — openapiart does not support it. The regex is documented in the
property description instead.

`platform_regions` remains a generate-only input by contrast: its effect is already expressed
per-element as `CollectiveCommunications.PhysicalBinding.platform_name`, so carrying the region form too would create
two representations of platform assignment that could disagree.

### 3.3 Compiled Chakra infra — RESOLVED, no action needed

`bind.Binding.infrastructure` (`keysight_chakra.infra.Infrastructure`) and `infra_annotations`
(#5, #6) are removed from the config by this refactor. This is **safe**: the server already
regenerates them. `otg_servicer._derive_chakra_infrastructure` (`:184`) runs whenever the converted
trial has no `binding.infrastructure`, calling
`TrialSpecToConfigConverter.generate_chakra_infrastructure(binding.infrastructure_profile.infrastructure)`
and populating both fields. Its docstring states the intent directly: "The OTG config carries the
logical infrastructure but (normally) not the derived chakra graph."

So the refactor is aligned with how the servicer already behaves — the config was never expected to
carry the compiled form. The only requirement is that `collective_communications.infrastructure` continues to
populate `binding.infrastructure_profile.infrastructure`, which `BindingsConverter` does today.

### 3.4 Four `dse.Trial` fields have nowhere to live in `collective_communications`

| `dse.Trial` field | type | note |
|---|---|---|
| `sim_config` #10 | `dse.SimConfig` — `Ns3SimAdvancedConfig` (DCQCN: ECN thresholds, EWMA weight, alpha/rate-control ~16 fields; PFC: shared/ingress buffer managers) or `AstraAdvancedConfig` (`SimAstraBackend`) | ~40 structured numeric fields; flattening into a `StringMap` would be badly lossy |
| `hf_sampling` #11 | `common.HighFreqSamplingConfig` (`enabled`, `metric_set` ∈ {CONGESTION, THROUGHPUT, MIXED}, `window` µs, `locations[]` → `ChassisInfo`) | note `result/ai_workload/` already defines `hf_*` metrics, so results exist for a config that cannot be expressed |
| `nccl_config` #5 | `common.NcclConfig { custom_env_vars: map<string,string> }` | fits `PlatformConfig.custom_settings` naturally |
| `trial_meta` #8 | `dse.TrialMeta { model_version, is_readonly }` | |

### 3.5 Platform: enum vs free string, and no global

`common.PlatformType` is an enum with six values (`PLATFORM_UNSPECIFIED`,
`PLATFORM_KEYS_NCCL_TEST`, `PLATFORM_KEYS_SW_AGENT`, `PLATFORM_KEYS_HW`, `PLATFORM_EXTERNAL`,
`SCP_SIMULATION`) appearing in four places:

1. `dse.Trial.platform` #3 — global default, `PLATFORM_KEYS_HW`
2. `dse.CreateBindingRequest.platform` #11
3. `bind.PhysicalBinding.platform` #2 — per physical resource
4. `bind.PlatformRegion.platform` #2 — per infra region

The OTG model has a named `CollectiveCommunications.PlatformConfig` list (free-string `platform_type` +
`custom_settings`) referenced by name from `PhysicalBinding.platform_name` and
`PlatformRegion.platform_name`. Implications:

- OTG → proto needs a validated string→enum table; unknown strings must fail loudly.
- The global `Trial.platform` must be picked from, or synthesized into, the platform list.
- proto → OTG must invent `PlatformConfig` names.
- `PlatformConfig.custom_settings` has no proto home except the platform-specific side blocks
  (`nccl_config`, `sim_config`, `PhysicalBinding.chassis_location`/`server_location`).

### 3.6 Both placeholder workload types are rich on the proto side

`mix_of_collectives.proto` defines a full model — `CollectiveMix` → `WorkloadSet[]` → `Workload[]` →
`Operation[]`, plus `PointToPoint`/`ManualSizing`/`AutoSizing`/`P2PFlow`, `CollectiveMixMetadata`,
a per-workload `RoCEv2Settings.qps_per_rankpair` override, and a presence-tracked
`Workload.enabled` where absent ≠ false.

`workload_replay.proto` defines `CompactedWorkload[]` (Chakra `mlcommons.Node`s, ranks, path),
`collective_algorithms[]`, `channels`, `iterations`.

Both are single-`placeholder`-string schemas in OTG. The refactor fixes the orphaned
`mix_of_collectives` choice (which today has an enum value but no payload property) by giving it a
payload, but the payload remains a placeholder. **No round-trip for either.**

### 3.7 RoCEv2 retransmission settings changed cardinality

`common.Rocev2Transport` carries these as one global set:

`retx_retry_interval_ms` #8, `retx_retry_count` #9, `max_retry_on_rnr_nak` #10,
`ack_request_interval` #11, `support_rx_reordering` #13

The OTG model moved them to per-port options. OTG → proto is therefore ambiguous unless every port
carries identical values; the converter needs an explicit "all ports must agree, else error" rule.

Separately, `tcp_store_host` #6 / `tcp_store_port` #7 are **flat on `Rocev2Transport` regardless of
negotiation method**, while OTG nests them under `qp_negotiation.tcp_store`. A proto message with
`METHOD_TCP` *and* a tcp_store host set cannot round-trip.

---

## 4. Smaller mismatches

### result_info

- `dse.Trial` has **no `description` field at all**. Description exists only on
  `dse.TrialReport.description` #5 and `storage_v2.TrialReportInfo.description` #10 — i.e. post-run.
  `collective_communications.result_info.description` has no legacy config home.
- The proto has **two tag lists**: `dse.Trial.tags` #2 and `dse.Trial.workspace.tags`
  (`WorkspaceSpec.tags` #2), against one `result_info.tags`.
- `dse.WorkspaceSpec` (`name`, default `"Default"`) has no `collective_communications` home at all.

### Infrastructure / infrastructure

- `profiles.ProfileInfo` has no OTG counterpart at all. `uuid` #2 went with
  `LogicalInfrastructure.id`, and `name` #1 went when `Infrastructure.name` was removed:
  a stored, named, referenceable infra *profile* is not a concept the OTG model has, since the
  infrastructure is inline and singleton. `BindingsConverter` writes `ProfileInfo(name="")`.
  Nothing in the server reads `.info.name` — every read of `infrastructure_profile` goes to
  `.infrastructure` (`trial_defaults.py:52`, `trial_validator.py:317,384`, `dse_service.py:154`,
  `binding_util.py:34`).
- `dse_infra.ClosFabric.host_count` #5 has no OTG counterpart and is already dropped in both
  directions by the existing converter (host count travels only via `Host.count`).
- `dse_infra.Host.zionex` (PRIVATE) has no OTG counterpart — the converter raises.
- `dse_infra.NVLinkVersionBandwidth` has only an `UNSPECIFIED` value, so
  `AiWorkload.NVLinkInterconnect.nvlink_version` (5 values) cannot be converted; raises today.
- OTG puts per-host NIC counts on the *fabric* (`fabric.rackplane.per_host`,
  `fabric.trayrack.per_host`) and `nic_assignment_mode` on `fabric.trayrack`; the proto puts all of
  it on `Host`. The existing converter bridges this with a `MutableHolder` and a
  `TrayRackHostConfig` NamedTuple explicitly labelled "TEMPORARY KLUDGE". The refactor preserves the
  OTG shape, so this burden is unchanged — neither better nor worse.
- Name asymmetry in the existing converter: proto `""` → OTG `None`.

### Bindings

- `bind.NicBinding.associated_physical_bindings` #3 (`InfraRef[]`) has no OTG counterpart; the
  NIC→physical association is indirect via `Device.Ethernet` → port connection and must be
  reconstructed by resolution.
- `CollectiveCommunications.PhysicalBinding.custom_settings` (`StringMap`) has no proto home — lost proto-ward.

### Workload / transport details

- `iterations`: OTG `uint64` max 4294967295 vs `kccb.Benchmark.iterations` `int32` max 2147483647.
  OTG can express values the proto cannot.
- `kccb.Datasize` uses `step` #3 where OTG uses `multiplier` — cosmetic, defaults match
  (start 134217728, step/multiplier 2, end 4294967296).
- Algorithm enums align 1:1: 20 OTG `CollectiveAlgorithmEnum` values ↔ 20 non-unspecified
  `common.AlgorithmType` values (proto numbering is sparse: 1, 2, 10–13, 20, 30, 40, 50, then
  `_PP` variants 60, 61, 70–73, 80, 90, 100, 110). A mapping table is needed but nothing is lost.
- `common.FlowControl.compute_delay_config` oneof has **no default** (neither `manual` nor
  `automatic` set is a valid proto state), while `AiWorkload.ComputeDelay.choice` defaults to
  `manual`. "Neither set" is lost on proto → OTG → proto.
- `common.FlowControl.compute_delay` #3 is deprecated but still present alongside
  `manual.compute_delay` — two sources for one value; OTG models only the oneof (correct).
- QP negotiation: proto `METHOD_KEYS_PROPRIETARY` is a bare enum value, while OTG `custom` is
  `CustomQpNegotiation { negotiation_type, custom_settings }`. OTG is richer;
  `custom_settings` is lost OTG → proto.
- `common.FalconTransport` (PRIVATE, `Trial.transport` oneof member #32) has no OTG choice.
  `common.TcpTransport` is an empty message, which matches OTG's payload-less `tcp` choice.

### Enum / presence subtleties to preserve

- `bind.GroupSpec.group_size` #3 is `optional` — absent means "derive from profile".
- `mix_of_collectives.Workload.enabled` is `optional` — absent ≠ false.
- Single-member oneofs that need care: `bind.Binding.type` (only `custom_binding`),
  `impairment.PacketConditions.packet_conditions` (only `rdma`), `common.NicSettings.transport`,
  `common.HFLocationSelector.location`.

---

## 5. Best-aligned area: impairments

`impairment.proto` maps essentially 1:1 onto the OTG impairment schemas, and the refactor does not
disturb it:

| proto | OTG |
|---|---|
| `Impairments{packet_drop, packet_reorder}` | `CollectiveCommunications.Impairments` |
| `PacketDrop{enabled, match_conditions[], skip_count, drop_count}` | `CollectiveCommunications.PacketDrop` |
| `PacketReorder{enabled, match_conditions[], skip_count, reorder_count, hold_count}` | `CollectiveCommunications.PacketReorder` |
| `MatchConditions{location, collective, packet[]}` | `CollectiveCommunications.MatchConditions` |
| `CollectiveMatchConditions{src_nic, dst_nic, flow_index}` | `CollectiveCommunications.CollectiveMatchConditions` |
| `PacketConditions{oneof rdma}` | `CollectiveCommunications.PacketConditions` |
| `RdmaMatchConditions{opcode_list[]}` | `CollectiveCommunications.RdmaMatchConditions` |
| `RdmaOpcodeMatch{value}` | `CollectiveCommunications.RdmaOpcodeMatch` |
| `Location` enum (SRC/DST), `RdmaOpcode` enum (7 values) | matching `x-enum`s |
| `bind.InfraRef` | `CollectiveCommunications.InfrastructureRef` |

Ranges match too (`drop_count` 1–16777215, `reorder_count`/`hold_count` 1–511).
Note the result side has a `packet_drop` metrics file but no `packet_reorder` metrics file, while
`storage_v2.DataFileType` defines both `PACKET_DROP_METRICS` 12 and `PACKET_REORDER_METRICS` 13.

---

## 6. run_id vs result_id

**Reverted: `run_id` has been removed from `CollectiveCommunications.State.Execution` again.**
The analysis below is kept for context on the storage-id landscape (`result_id` vs. the
never-exposed `app_base` run id) but no longer reflects a field on the model. The
replacement plan carries no OTG model field: `generate_config`'s converted inputs are
saved by the server middleware and attached to artifacts when the report is saved.

The refactor removed `AiWorkload.State.Stopped.Success.archive_id` in favour of a `run_id` exposed
on `CollectiveCommunications.State.Execution`. **Note: `archive_id` is not a dead field.** The servicer populates it on
success — `otg_servicer.py:387` sets `stopped.success.archive_id = self._last_run_outcome.result_id`,
and the surrounding code deliberately keeps reporting `started` until the outcome is stored "so a
stopped/success response always carries the run's archive_id". Today it is the only OTG-visible,
storage-addressable identifier. Removing it is a behavioral replacement, not a cleanup: the
middleware change that populates `run_id` must land together with the model change, or OTG clients
regress from "can retrieve the result id on success" to "cannot retrieve any id at all".

Storage keys everything by **`result_id`**:

- storage folder: `result/<YYYY-MM-DD>/<HH-MM-SS>_<result_id>`
  (`storage/keysight_storage_service/results/result_set_util.py:89`)
- `DseService.GetTrialReportDetails` → `storage_v2.TrialReportDetailInfo.result_id`
- `run_id` is minted at run start (`server/keys_ai_ml_server/app_framework/apps/app_base.py:430`)
  and sent in `InitializeResultRequest.run_id`, but is persisted only as a DB column and never read
  back — there is no `GetRunId` and no API exposes it. (The id the servicer exposes via
  `archive_id` is the *result_id*, not this run_id.)

If `run_id` and `result_id` are not made equal, an OTG client holding only `run_id` has no way to
fetch its report. Resolve by either making `result_id == run_id` at `__initiate_result`, or
exposing both on the state. Since `run_id` is readable in the `started` state (before any result
exists), making the two equal is the option that keeps a single identifier valid across the whole
run lifecycle.

---

## 7. State of the converter layer

**The OTG ↔ proto round trip is implemented and live**, not hypothetical. `OtgService` implements
`SetConfig` (`otg_servicer.py:119`) and `GetConfig` (`:206`):

- `SetConfig` deserializes the OTG config, calls `TrialConverter.otg_to_proto(...)` to produce a
  `dse.Trial`, then hands it to `configure_trial`.
- `GetConfig` reverse-converts the configured trial with `TrialConverter.proto_to_otg_inplace(...)`.

`models/converters/__init__.py` exports a near-complete converter set: `TrialConverter`,
`BindingsConverter`, `InfrastructureConfigConverter`, `EthernetNicSettingsConverter`,
`Layer1Converter` / `SpeedModeConverter`, `PlatformTypeConverter`, `PortLocationConverter`,
`SingleCollectiveConfigConverter` / `AlgorithmTypeConverter`, `Rocev2TransportConverter` /
`QpNegotiationMethodConverter` / `RdmaVerbConverter`, plus the error types and a `warning_sink`
(`collect_warnings` / `record_warning`) used to report lossy conversions.

- Every converter subclasses `Converter` / `ScalarConverter` / `EnumConverter`
  (`converters/core/converter.py`), which **forces both directions** to be implemented.
- Tests cover the whole set (`models/tests/converters/`, ~1670 lines across 9 test modules plus
  `otg_factories.py`): trial, bindings, transport, single_collective, nic_settings,
  layer1_settings, platform, port, logical_infrastructure.
- Round-trip tests assert field-by-field on the way back, not whole-object equality, because of
  known losses (host template choice collapses to `generic`; `xpu_interconnect` dropped for
  rackplane/trayrack; `""` ⇄ `None`; custom speeds unsupported on rackplane/trayrack;
  `ClosFabric.host_count` dropped).
- **These tests do not run in CI.** `models/Makefile:456` runs
  `pytest --ignore=tests/converters ./tests`, and `unit-tests` is what the publish pipeline calls.
  The `test-converters` target (line 458) is referenced by no Makefile or CI job.
- **`Rocev2.PerPortSettings` has no converter.** Nothing in `converters/` references
  `PerPortSettings` or `per_port_options`, so the per-port RoCEv2 surface (CNP, DCQCN, ACK/NAK,
  retx, `enable_rx_reordering`) is a one-way dead end: OTG can express it, nothing maps it to
  proto, and proto values are dropped. `Rocev2TransportConverter` documents this explicitly for
  the `retx_*` / `max_retry_on_rnr_nak` / `ack_request_interval` / `support_rx_reordering` fields,
  which are dropped with a recorded warning.
- The compiled Chakra infrastructure is **derived server-side**, not carried in the config:
  `otg_servicer._derive_chakra_infrastructure` (`:184`) calls
  `TrialSpecToConfigConverter.generate_chakra_infrastructure(...)` from
  `binding.infrastructure_profile.infrastructure` and fills `binding.infrastructure` +
  `infra_annotations` whenever the converted trial lacks them. This resolves §3.3 — removing the
  compiled form from the config costs nothing, because the server already regenerates it.
- One piece of OTG↔proto mapping lives outside `models/converters`: the hand-rolled trial-state →
  `AiWorkloadState.execution` mapping in `otg_servicer.GetStates`.

Consequences for the refactor:

1. The `AiWorkload.*` → `CollectiveCommunications.*` rename breaks the converter layer mechanically — **16 files**
   under `converters/` and `tests/converters/` reference generated snappi classes
   (`AiWorkloadTransport`, `AiWorkloadQpNegotiation`, `AiWorkloadInfraRef`,
   `AiWorkloadSingleCollectiveConfig`, `AiWorkloadInfrastructure*`, `AiWorkload*Fabric*`,
   `AiWorkloadXPUInterconnect`, …) — as does `otg_servicer.py`'s
   `from converters import ConversionError, TrialConverter`. Because the tests are CI-excluded,
   **the breakage would be silent**, and it would break the live `SetConfig`/`GetConfig` path.
   The converter rename is a required companion to this model change, not a follow-up.
2. Most schisms in §3–§4 are therefore **regressions to avoid, not greenfield design decisions**.
   Where a converter already exists, its current behaviour is the compatibility baseline.
3. Any proposal to move transport settings onto per-port options lands in a converter blind spot
   (see the `PerPortSettings` bullet). Device-level is safer: `EthernetNicSettingsConverter`
   already maps `Device.Ethernet` → `common.NicSettings` and can be extended.

---

## 8. Recommended follow-ups

**Required by the rename** (the converter layer is live, so these are not optional):

1. Rename `AiWorkload*` → `CollectiveCommunications*` across the 16 files in `converters/` and `tests/converters/`, and
   repoint `bindings.logical_infrastructure` → `infrastructure`. Without this the
   `SetConfig`/`GetConfig` path is broken (§7).
2. Wire `test-converters` into CI so this class of breakage cannot go unnoticed (§7).

**Open design decisions**, each forced into the open by the refactor:

3. ~~Decide whether `CollectiveCommunications.Bindings` gains an expanded `process_groups`.~~ **Done** — added as
   `process_groups` #4 with `BindingsConverter` support in both directions (§3.2).
4. Model channels, or accept that multi-channel trials are OTG-inexpressible; either way, resolve
   the orphaned `RankDistribution` schema. `SingleCollectiveConfigConverter` has no channels
   handling (§3.1).
5. Find homes for `sim_config`, `hf_sampling`, `nccl_config`, `trial_meta` — or record explicitly
   that they are legacy-only (§3.4).
6. Confirm the `platform_type` string → `common.PlatformType` mapping is complete
   (`PlatformTypeConverter` implements it today) and how the global `Trial.platform` is derived
   (§3.5).
7. Add `platforms` to `CollectiveCommunications.Config.Generate.Request`. Now that `platforms` is a
   sibling of `infrastructure` under `CollectiveCommunications`, the generate request — which carries only
   `infrastructure` — has no platform inventory for its `platform_regions` to reference by name (§2).
8. Settle `run_id` vs `result_id`, and land the middleware change with the model change so
   `archive_id`'s behaviour is not lost (§6).
9. Give `Rocev2.PerPortSettings` a converter before moving any further transport settings onto
   per-port options (§7).

**Resolved** — previously listed here, now answered:

- *Who synthesizes Ports/Layer1/Ethernets on proto → OTG?* `BindingsConverter`, using
  `PortLocationConverter` / `Layer1Converter` / `EthernetNicSettingsConverter` (§1).
- *Where does the compiled Chakra infrastructure come from?* The server derives it in
  `otg_servicer._derive_chakra_infrastructure`, so dropping it from the config is safe (§3.3, §7).
