# ISIS SRv6 OTG Model — Work Record

**Branch:** `isis-srv6`  
**Working directory:** `c:/Users/suryjana/athena/models`  
**Build status:** PASSING ✓ (as of 2026-04-21, post gap-fill implementation)

## How to Run the Build

Always use the virtual environment python, not the system python:

```
.venv/Scripts/python.exe ./build.py
```

The system python (`C:\Program Files\Python312\python.exe`) has an older openapiart installed that has a bug in `_write_openapi_list` — it fails with `KeyError: '$ref'` for array-type choice properties. The `.venv` openapiart already handles this correctly. **Do not modify `openapiart/generator.py`** — the fix is simply to use the venv.

## Background & Goal

The existing OTG ISIS model (in `device/isis/`) covered only SR-MPLS (RFC 8667): SRGB, SRLB, Prefix-SIDs, Adjacency-SIDs with MPLS label values. No SRv6 existed anywhere in the ISIS schemas. The goal was to add a full OTG model for IS-IS Segment Routing over IPv6 (SRv6) per RFC 9352, suitable for IxNetwork implementation.

## Research Sources Used

| Source | Key Findings |
|--------|-------------|
| RFC 9352 | IS-IS SRv6 TLV/Sub-TLV definitions: Locator TLV (type 27), SRv6 Caps Sub-TLV (type 25), End SID Sub-TLV (type 5), End.X SID Sub-TLV (type 43/44), SID Structure Sub-Sub-TLV (type 1) |
| RFC 8986 | SRv6 endpoint behavior codepoints: End (1-4,28-31), End.X (5-8,32-35), End.DX4/DX6 (17/16), End.DT4/DT6/DT46 (19/18/20) |
| RFC 8491 | MSD sub-TLV types: 41=Max SL, 42=Max End Pop, 43=Max T.Insert, 44=Max H.Encaps, 45=Max End D |
| RFC 7794 | IS-IS Prefix Attribute Flags Sub-TLV (sub-TLV type 4): X (External), R (Re-advertisement), N (Node), A (Anycast) flags |
| RFC 9350 | Flex-Algo IDs 128-255 in `algorithm` field; Source Router ID Sub-TLVs type 11 (IPv4) and type 12 (IPv6) for Flex-Algo prefix identification |
| RFC 9259 | O-flag in SRv6 Capabilities Sub-TLV for OAM support |
| RFC 9800 | uSID/Micro-SID: Argument field in SID Structure sub-sub-TLV used for compressed segment stacking |
| IxNetwork RESTpy | Class hierarchy: `IsisL3Router` → `IsisSRv6LocatorEntryList` → `IsisSRv6EndSIDList`; `IsisL3` → `IsisSRv6AdjSIDList`; attribute names for `CFlag` (uSID), `EndPointFunction`, `LocatorBlockLength`, `LocatorNodeLength`, `FunctionLength`, `ArgumentLength`, `IncludeSRv6SIDStructureSubSubTlv`, all MSD `Include*` and `Max*` pairs |
| OpenConfig | IETF draft `draft-ietf-lsr-isis-srv6-yang-07` used for YANG hierarchy reference; published OpenConfig models (as of Apr 2026) do NOT yet include SRv6 for IS-IS |

---

## Files Changed

### 1. `device/isis/srv6.yaml` — **NEW FILE**

All SRv6 configuration schemas. Contains 7 schemas.

#### `IsisSRv6.NodeCapability`
Maps to: SRv6 Capabilities Sub-TLV (sub-TLV type 25 in TLV 242)  
RFC: RFC 9352 Section 2

| Field | UID | Type | Default | Notes |
|-------|-----|------|---------|-------|
| `o_flag` | 1 | boolean | false | OAM flag; router supports O-bit in SRH (RFC 9259) |
| `node_msds` | 2 | object | — | → `IsisSRv6.NodeMsd` |
| `c_flag` | 3 | boolean | false | Compression/uSID flag; node supports Micro-SID encoding (RFC 9800) |

#### `IsisSRv6.NodeMsd`
Maps to: MSD sub-TLVs in Router Capability TLV  
RFC: RFC 8491, RFC 9352 Section 6

| Field | UID | Type | Default | MSD Type |
|-------|-----|------|---------|----------|
| `include_max_sl` | 1 | boolean | false | controls type 41 advertisement |
| `max_sl` | 2 | uint32 (max 255) | 0 | MSD-Type 41: Max Segments Left |
| `include_max_end_pop_srh` | 3 | boolean | false | controls type 42 advertisement |
| `max_end_pop_srh` | 4 | uint32 (max 255) | 0 | MSD-Type 42: Max End Pop |
| `include_max_h_encaps` | 5 | boolean | false | controls type 44 advertisement |
| `max_h_encaps` | 6 | uint32 (max 255) | 0 | MSD-Type 44: Max H.Encaps |
| `include_max_end_d_srh` | 7 | boolean | false | controls type 45 advertisement |
| `max_end_d_srh` | 8 | uint32 (max 255) | 0 | MSD-Type 45: Max End D |
| `include_max_t_insert` | 9 | boolean | false | controls type 43 advertisement |
| `max_t_insert` | 10 | uint32 (max 255) | 0 | MSD-Type 43: Max T.Insert (transit SRH insertion) |

#### `IsisSRv6.Locator`
Maps to: SRv6 Locator TLV (TLV type 27)  
RFC: RFC 9352 Section 7.1  
Required fields: `locator`, `name` (NOT `prefix_length` — openapiart prohibits a field from being both `required` and having a `default` value)

| Field | UID | Type | Default | Notes |
|-------|-----|------|---------|-------|
| `name` | 1 | string | — | x-include Named.Object; globally unique |
| `locator` | 2 | ipv6 | — | IPv6 locator prefix |
| `prefix_length` | 3 | uint32 (1-128) | 64 | bits in locator field |
| `algorithm` | 4 | uint32 (0-255) | 0 | 0=SPF, 1=Strict SPF, 128-255=Flex-Algo |
| `metric` | 5 | uint32 (max 16777215) | 0 | locator metric |
| `redistribution_type` | 6 | enum: up/down | up | Up/Down redistribution bit |
| `d_flag` | 7 | boolean | false | Down bit; set when leaked L2→L1 |
| `mt_id` | 8 | uint32 (max 4095) | 0 | Multi-Topology ID; 0=default |
| `end_sids` | 9 | array | — | → `IsisSRv6.EndSid[]` |
| `advertise_locator_as_prefix` | 10 | boolean | true | Also advertise locator in TLV 236/237; auto-suppressed for Flex-Algo |
| `route_metric` | 11 | uint32 (max 16777215) | 0 | Metric for TLV 236/237 prefix advertisement |
| `route_origin` | 12 | enum: internal/external | internal | Origin type for TLV 236/237 advertisement |
| `prefix_attr_enabled` | 13 | boolean | false | Include Prefix Attribute Flags Sub-TLV (RFC 7794) |
| `x_flag` | 14 | boolean | false | External prefix flag (Prefix Attr Flags bit 0, RFC 7794) |
| `r_flag` | 15 | boolean | false | Re-advertisement flag (bit 1, RFC 7794) |
| `n_flag` | 16 | boolean | false | Node flag (bit 2, RFC 7794) |
| `a_flag` | 17 | boolean | false | Anycast flag (bit 5, RFC 7794) |
| `include_source_router_id` | 18 | enum: none/ipv4/ipv6/ipv4_and_ipv6 | none | Source Router ID sub-TLV inclusion (RFC 9350 Section 5) |
| `ipv4_source_router_id` | 19 | ipv4 | "0.0.0.0" | IPv4 Source Router ID sub-TLV (type 11, RFC 9350) |
| `ipv6_source_router_id` | 20 | ipv6 | "::" | IPv6 Source Router ID sub-TLV (type 12, RFC 9350) |

#### `IsisSRv6.EndSid`
Maps to: SRv6 End SID Sub-TLV (sub-TLV type 5)  
RFC: RFC 9352 Section 7.2, RFC 8986

| Field | UID | Type | Default | Notes |
|-------|-----|------|---------|-------|
| `sid` | 1 | ipv6 | — | 128-bit SRv6 SID value |
| `endpoint_behavior` | 2 | enum (11 values) | end | see table below |
| `c_flag` | 3 | boolean | false | Compression/uSID flag (IxNetwork `CFlag`) |
| `include_srv6_sid_structure_tlv` | 4 | boolean | false | include sub-sub-TLV type 1 |
| `sid_structure` | 5 | object | — | → `IsisSRv6.SidStructure` |

endpoint_behavior enum values (IsisSRv6.EndSid):

| Value | UID | RFC 8986 Codepoint |
|-------|-----|-------------------|
| `end` | 1 | 1 |
| `end_with_psp` | 2 | 2 |
| `end_with_usp` | 3 | 3 |
| `end_with_psp_usp` | 4 | 4 |
| `end_with_usd` | 5 | 28 |
| `end_with_psp_usd` | 6 | 29 |
| `end_with_usp_usd` | 7 | 30 |
| `end_with_psp_usp_usd` | 8 | 31 |
| `end_dt4` | 9 | 19 |
| `end_dt6` | 10 | 18 |
| `end_dt46` | 11 | 20 |

#### `IsisSRv6.AdjSid`
Maps to: End.X SID Sub-TLV (sub-TLV type 43 P2P, type 44 LAN)  
RFC: RFC 9352 Sections 8.1-8.2, RFC 8986 Section 4.3

| Field | UID | Type | Default | Notes |
|-------|-----|------|---------|-------|
| `sid` | 1 | ipv6 | — | 128-bit SRv6 adjacency SID |
| `endpoint_behavior` | 2 | enum (10 values) | end_x | see table below |
| `b_flag` | 3 | boolean | false | Backup flag; eligible for IP-FRR |
| `s_flag` | 4 | boolean | false | Set flag; refers to adjacency set |
| `p_flag` | 5 | boolean | false | Persistent flag; stable across restart |
| `weight` | 6 | uint32 (0-255) | 0 | Load-balancing weight (used when S-flag set) |
| `algorithm` | 7 | uint32 (0-255) | 0 | IGP algorithm binding |
| `c_flag` | 8 | boolean | false | Compression/uSID flag |
| `include_srv6_sid_structure_tlv` | 9 | boolean | false | include sub-sub-TLV type 1 |
| `sid_structure` | 10 | object | — | → `IsisSRv6.SidStructure` |

endpoint_behavior enum values (IsisSRv6.AdjSid):

| Value | UID | RFC 8986 Codepoint |
|-------|-----|-------------------|
| `end_x` | 1 | 5 |
| `end_x_with_psp` | 2 | 6 |
| `end_x_with_usp` | 3 | 7 |
| `end_x_with_psp_usp` | 4 | 8 |
| `end_x_with_usd` | 5 | 32 |
| `end_x_with_psp_usd` | 6 | 33 |
| `end_x_with_usp_usd` | 7 | 34 |
| `end_x_with_psp_usp_usd` | 8 | 35 |
| `end_dx4` | 9 | 17 |
| `end_dx6` | 10 | 16 |

#### `IsisSRv6.SidStructure`
Maps to: SRv6 SID Structure Sub-Sub-TLV (type 1)  
RFC: RFC 9352 Section 9, RFC 9800 (uSID/Micro-SID)  
Constraint: sum of all four lengths ≤ 128  
Default values represent uSID F3216 format (most common deployment)

| Field | UID | Type | Default | Notes |
|-------|-----|------|---------|-------|
| `locator_block_length` | 1 | uint32 (0-128) | 32 | LB bits; common prefix of all SIDs in domain |
| `locator_node_length` | 2 | uint32 (0-128) | 16 | LN bits; node identifier within domain |
| `function_length` | 3 | uint32 (0-128) | 16 | Function bits; endpoint behavior identifier |
| `argument_length` | 4 | uint32 (0-128) | 0 | Arg bits; 0 for standard SIDs, >0 for uSID stacking |

#### `IsisSRv6.LinkMsd`
Maps to: Link-level MSD sub-TLVs in TLV 22/222  
RFC: RFC 8491, RFC 9352 Section 6  
Same 4 MSD type pairs as `IsisSRv6.NodeMsd` but scoped to a specific interface

| Field | UID | MSD Type |
|-------|-----|----------|
| `include_max_sl` | 1 | — |
| `max_sl` | 2 | 41 |
| `include_max_end_pop_srh` | 3 | — |
| `max_end_pop_srh` | 4 | 42 |
| `include_max_h_encaps` | 5 | — |
| `max_h_encaps` | 6 | 44 |
| `include_max_end_d_srh` | 7 | — |
| `max_end_d_srh` | 8 | 45 |
| `include_max_t_insert` | 9 | — |
| `max_t_insert` | 10 | 43 |

---

### 2. `device/isis/segmentrouting.yaml` — **MODIFIED**

#### Fields added to `Isis.SegmentRouting`

| Field | UID | Type | Notes |
|-------|-----|------|-------|
| `srv6_locators` | 2 | array → `IsisSRv6.Locator[]` | SRv6 Locator TLV (type 27) list; one per algorithm/topology |

(uid 1 = existing `router_capability`)

#### Fields added to `Isis.RouterCapability`

| Field | UID | Type | Notes |
|-------|-----|------|-------|
| `srv6_capability` | 8 | object → `IsisSRv6.NodeCapability` | SRv6 Caps Sub-TLV (type 25): O-flag + node MSDs |

(uids 1-7 = existing: choice, custom_router_cap_id, s_bit, d_bit, sr_capability, algorithms, srlb_ranges)

---

### 3. `device/isis/interface.yaml` — **MODIFIED**

#### Fields added to `Isis.Interface`

| Field | UID | Type | Notes |
|-------|-----|------|-------|
| `srv6_adj_sids` | 15 | array → `IsisSRv6.AdjSid[]` | End.X SID sub-TLV (type 43 P2P / 44 LAN) per interface |
| `srv6_link_msd` | 16 | object → `IsisSRv6.LinkMsd` | Link-level MSD for this interface |

(uids 1-14 = existing fields; uid 14 = existing `adjacency_sids` for SR-MPLS)

---

### 4. `result/isislsp.yaml` — **MODIFIED**

This file holds the learned/received LSP state schemas. Six new top-level schemas appended, plus three existing schemas extended.

#### `IsisLsp.Tlvs` — extended

| Field added | UID | Type | Notes |
|-------------|-----|------|-------|
| `srv6_locator_tlvs` | 9 | array → `IsisLsp.SRv6LocatorTlv[]` | Learned SRv6 Locator TLVs (type 27) |

(uid 8 = existing `router_capabilities`)

#### `IsisLsp.Capability` — extended

| Field added | UID | Type | Notes |
|-------------|-----|------|-------|
| `srv6_capability` | 7 | object → `IsisLsp.SRv6Capability` | Learned SRv6 Caps Sub-TLV (type 25) |

(uids 1-6 = existing: router_cap_id, s_bit, d_bit, sr_capability, algorithms, srlb_ranges)

#### `IsisLsp.ExtendedNeighbor` — extended

| Field added | UID | Type | Notes |
|-------------|-----|------|-------|
| `srv6_adj_sids` | 3 | array → `IsisLsp.SRv6AdjSid[]` | Learned End.X SID sub-TLVs (type 43/44) from this neighbor |

(uid 1 = system_id, uid 2 = existing SR-MPLS adjacency_sids)

#### New schemas appended

| Schema | Fields (UIDs) |
|--------|---------------|
| `IsisLsp.SRv6Capability` | `o_flag`(1), `node_msds`(2) → `IsisLsp.SRv6NodeMsd`, `c_flag`(3) |
| `IsisLsp.SRv6NodeMsd` | `max_sl`(1), `max_end_pop_srh`(2), `max_h_encaps`(3), `max_end_d_srh`(4), `max_t_insert`(5) — no include_* flags; just the learned values |
| `IsisLsp.SRv6LocatorTlv` | `locator`(1), `prefix_length`(2), `algorithm`(3), `metric`(4), `redistribution_type`(5), `d_flag`(6), `mt_id`(7), `end_sids`(8) → `IsisLsp.SRv6EndSid[]`, `x_flag`(9), `r_flag`(10), `n_flag`(11), `a_flag`(12), `ipv4_source_router_id`(13), `ipv6_source_router_id`(14) |
| `IsisLsp.SRv6EndSid` | `sid`(1), `endpoint_behavior`(2, same 11 enum values), `sid_structure`(3) → `IsisLsp.SRv6SidStructure` |
| `IsisLsp.SRv6AdjSid` | `type`(1: end_x_sid/lan_end_x_sid), `neighbor_id`(2), `sid`(3), `endpoint_behavior`(4, same 10 enum values), `b_flag`(5), `s_flag`(6), `p_flag`(7), `weight`(8), `algorithm`(9), `sid_structure`(10) → `IsisLsp.SRv6SidStructure` |
| `IsisLsp.SRv6SidStructure` | `locator_block_length`(1), `locator_node_length`(2), `function_length`(3), `argument_length`(4) |

Note: `IsisLsp.SRv6NodeMsd` omits `include_*` flags (unlike the config counterpart) because in a received LSP, only advertised MSD values appear — absence means not advertised.

---

## Design Decisions

1. **SRv6 is additive, not replacing SR-MPLS.** `Isis.SegmentRouting` now has two parallel branches: `router_capability` (SR-MPLS, uid 1) and `srv6_locators` (SRv6, uid 2). The SRv6 Capabilities Sub-TLV sits as `srv6_capability` (uid 8) inside the existing `Isis.RouterCapability` because it is also a sub-TLV of TLV 242 — co-located where it belongs per RFC 9352.

2. **x-field-uid continuity.** All new fields are assigned the next available UID in their parent schema. This preserves the existing wire encoding for implementations that use UIDs for serialization. Never reuse or renumber existing UIDs.

3. **Locator TLV vs. Router Capability TLV.** The SRv6 Locator (TLV 27) is a top-level IS-IS TLV, not a sub-TLV of TLV 242. Modelling it as `Isis.SegmentRouting.srv6_locators` (array) correctly represents that one Locator TLV is emitted per locator/algorithm pair.

4. **c_flag for uSID.** IxNetwork exposes uSID support as `CFlag` on both End SID and Adj SID classes. Modelled as `c_flag` (boolean, default false) on `IsisSRv6.EndSid` and `IsisSRv6.AdjSid`. When set, `include_srv6_sid_structure_tlv` should also be true to advertise the bit lengths.

5. **SID Structure defaults = F3216.** `locator_block_length=32`, `locator_node_length=16`, `function_length=16`, `argument_length=0` match the most widely deployed uSID format. These are overrideable but sensible defaults.

6. **include_* pattern for MSD.** Each MSD type has a paired boolean `include_*` flag (controlling advertisement) and a `max_*` value. This mirrors IxNetwork's `IncludeMaxSlMsd`/`MaxSlMsd` pattern and avoids ambiguity between "not configured" (field absent) and "advertised as zero" (explicitly 0).

7. **Learned state has no include_* flags.** `IsisLsp.SRv6NodeMsd` and `IsisLsp.SRv6SidStructure` omit all `include_*` booleans — in received LSPs, presence of a field means it was advertised; absence means it was not present in the LSP.

8. **LAN vs P2P End.X.** `IsisLsp.SRv6AdjSid` has a `type` field (`end_x_sid` for sub-TLV 43, `lan_end_x_sid` for sub-TLV 44) and an optional `neighbor_id` field (present only for LAN type 44). The config-side `IsisSRv6.AdjSid` does not distinguish type explicitly — the implementation derives it from the interface `network_type` field (`broadcast` → type 44, `point_to_point` → type 43).

9. **Locator as prefix (TLV 236/237).** `advertise_locator_as_prefix` (default true) mirrors IxNetwork's "Advertise Locator as Prefix" control. When enabled, the same locator is also emitted as a standard IPv6 Reachability prefix so non-SRv6 routers can route toward it. The paired `route_metric` and `route_origin` fields apply only to that secondary advertisement.

10. **Prefix Attribute Flags on the locator.** `prefix_attr_enabled` (default false) gates emission of the Prefix Attribute Flags Sub-TLV (RFC 7794, sub-TLV type 4) in the locator's TLV 236/237 advertisement. `x_flag`, `r_flag`, `n_flag`, `a_flag` are only meaningful when `prefix_attr_enabled` is true. The A-flag (anycast, bit 5) was previously in the "Not Yet Modelled" list.

11. **Source Router ID sub-TLVs.** `include_source_router_id` (enum) controls whether IPv4 Source Router ID (type 11) and/or IPv6 Source Router ID (type 12) sub-TLVs are included in the locator's TLV 236/237 advertisement (RFC 9350 Section 5). Used primarily with Flex-Algo (algorithm 128-255) to unambiguously identify the originating router. Both sub-TLVs were previously in the "Not Yet Modelled" list.

12. **T.Insert MSD (type 43) on both node and link.** MSD-Type 43 (Max T.Insert) signals the maximum number of SIDs a router/link can insert as a new SRH via the transit T.Insert headend behavior. Added as `include_max_t_insert`/`max_t_insert` pair (uids 9/10) to both `IsisSRv6.NodeMsd` and `IsisSRv6.LinkMsd`. Mirrored as `max_t_insert` (uid 5) in `IsisLsp.SRv6NodeMsd`. Was previously missing from the model (gap found in IxNetwork docs review).

13. **Node-level c_flag.** The `c_flag` at `IsisSRv6.NodeCapability` level (uid 3) announces node-wide uSID support in the SRv6 Capabilities Sub-TLV Flags field, distinct from the per-SID `c_flag` on `IsisSRv6.EndSid` / `IsisSRv6.AdjSid`. Both are needed: the node-level flag is a global capability announcement; the per-SID flag marks individual SIDs that carry the uSID encoding.

---

## What Is NOT Yet Modelled

- **SRv6 Flex-Algo Definition (FAD) sub-TLV** (sub-TLV 26 in TLV 242, RFC 9350): Flex-Algo definitions with metric-type, calc-type, priority, and admin-group constraints. Flex-Algo participation is currently expressed only through the `algorithm` field on the locator. IxNetwork exposes this via `IsisFlexAlgorithmList` — a separate OTG Flex-Algo schema would be needed.
- **SRv6 per-prefix SIDs on route ranges — NOT APPLICABLE for IS-IS.** RFC 9352 does not define SRv6 sub-TLVs within TLV 135 or TLV 236/237. In IS-IS SRv6, SIDs are bound to a locator via the dedicated SRv6 Locator TLV (TLV 27), not to prefix reachability entries. IxNetwork confirms this — no SRv6 attributes exist on ISIS route range objects. `Isis.V4RouteRange` and `Isis.V6RouteRange` are complete as-is for SRv6.
- **SRv6 Micro-Loop Avoidance** (`srv6-rib-update-delay` from IETF YANG draft).
- **SRv6 TI-LFA** fast-reroute configuration.
- **Metrics/counters** specific to SRv6 (no new fields added to `Isis.Metric` schema).
