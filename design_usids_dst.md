# Design: `dst_usids` — structured uSID destination field on `Flow.Ipv6`

## Problem

`Flow.Ipv6.dst` is a raw `x-field-pattern` of format `ipv6`. Its description already
explains the no-SRH uSID reduced-encapsulation case (RFC 9800 Section 4) and shows a
worked F3216 example. But callers must manually compute the packed 128-bit container
value themselves. There is no structured way to express "locator + uSID list" — that
structure only appears inside `Flow.Ipv6SegmentRoutingUsid.Segment`, which lives inside
an SRH object.

`dst_usids` gives callers a structured input field alongside `dst` for the no-SRH
single-container path case.

---

## Placement

**File:** `flow/packet-headers/ipv6.yaml`

New property on `Flow.Ipv6` at **UID 9**, parallel to `dst` (UID 8):

```
Flow.Ipv6
  version           (1)
  traffic_class     (2)
  flow_label        (3)
  payload_length    (4)
  next_header       (5)
  hop_limit         (6)
  src               (7)
  dst               (8)   <- existing raw ipv6 pattern
  dst_usids         (9)   <- NEW: structured uSID container input
```

No `choice` discriminator is added to `Flow.Ipv6` itself. `dst_usids` is an optional
`$ref` property; when populated the implementation uses it to derive the dst value.
`dst` and `dst_usids` are mutually exclusive by convention (documented in descriptions).

---

## New schema: `Flow.Ipv6.UsidDst`

Defined in `ipv6.yaml`. Contains three fields — `locator`, `locator_length`, and `usids`.
No flags, no TLVs, no SRH fields.

```yaml
Flow.Ipv6.UsidDst:
  description: >-
    Structured input for the SRv6 uSID reduced encapsulation case (RFC 9800
    Section 4) where the entire SR path fits in a single 128-bit uSID container
    placed directly in the outer IPv6 dst, with no Segment Routing Header.
    The implementation packs the fields as:
    LB (locator block bits) || uSID-1 || uSID-2 || ... || EoC (zero-pad to 128 bits).

    For F3216 format (RFC 9800 Section 3): LB = 32 bits, each uSID = 16 bits,
    up to 6 uSIDs per container.
    Example - locator fc00::/32, usids ["0001","0002","0003"]:
    assembled dst = fc00:0:1:2:3::

    When this field is present, dst (UID 8) should be omitted. Setting both is
    implementation-specific.
  type: object
  required: [locator]
  properties:
    locator:
      x-field-pattern:
        description: >-
          The Locator Block (LB) IPv6 prefix shared by all uSIDs in this
          container (RFC 9800 Section 3). Defines the common high-order bits
          packed into the 128-bit dst. For F3216 this is a /32 prefix
          (e.g., fc00::). The number of bits used is given by locator_length.
        format: ipv6
        default: ::0
        features: [count]
      x-field-uid: 1
    locator_length:
      x-field-pattern:
        description: >-
          Length of the Locator Block in bits (RFC 9800 Section 3).
          Determines how many high-order bits of locator are used as the LB
          and how many bits remain for uSID packing.
          For F3216: 32. For F3208: 32. Valid range: 1-112.
        format: integer
        length: 8
        default: 32
        features: [count]
      x-field-uid: 2
    usids:
      description: >-
        Ordered list of uSID values to pack after the Locator Block
        (RFC 9800 Section 3). For F3216 each uSID is 16 bits (4 hex chars);
        up to 6 uSIDs fit per container. The End-of-Container zero-pad
        is appended automatically by the implementation.
        Example: ["0001","0002","0003"] with locator fc00::/32
        assembles to fc00:0:1:2:3::
      type: array
      minItems: 1
      items:
        $ref: '#/components/schemas/Flow.Ipv6.UsidDst.uSid'
      x-field-uid: 3

Flow.Ipv6.UsidDst.uSid:
  description: >-
    One uSID value within the no-SRH uSID container (RFC 9800 Section 3).
    For F3216 (16-bit uSID): 4 hex characters.
    The value 0x0000 is reserved as the End-of-Container marker and must
    not be used.
  type: object
  properties:
    usid:
      description: >-
        The uSID value as a hex string. For F3216: 4 hex characters.
        Example: "0001".
      type: string
      format: hex
      x-field-uid: 1
```

---

## Property addition to `Flow.Ipv6`

```yaml
dst_usids:
  description: >-
    Structured uSID container for SRv6 reduced encapsulation (RFC 9800
    Section 4) with no Segment Routing Header. When present, the
    implementation assembles the 128-bit IPv6 dst from the locator block
    and the ordered uSID list. Mutually exclusive with dst; do not set both.
    For paths requiring more than one container, use Flow.Ipv6Routing with
    segment_routing_usid instead.
  $ref: '#/components/schemas/Flow.Ipv6.UsidDst'
  x-field-uid: 9
```

---

## UID summary

| Schema | Property | UID |
|--------|----------|-----|
| `Flow.Ipv6` | `dst_usids` | 9 (next after `dst` = 8) |
| `Flow.Ipv6.UsidDst` | `locator` | 1 |
| `Flow.Ipv6.UsidDst` | `locator_length` | 2 |
| `Flow.Ipv6.UsidDst` | `usids` | 3 |
| `Flow.Ipv6.UsidDst.uSid` | `usid` | 1 |

No gaps; no reservations needed.

---

## Design decisions

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| Schema location | `ipv6.yaml` | Self-contained; no cross-file `$ref` into `ipv6_routing.yaml` |
| `uSid` item type | New `Flow.Ipv6.UsidDst.uSid` in `ipv6.yaml` | Avoids coupling `ipv6.yaml` to `ipv6_routing.yaml`; type is trivial to duplicate |
| `locator_length` | Included, default 32 | Matches `Flow.Ipv6SegmentRoutingUsid.Segment`; allows non-F3216 locator widths |
| `choice` on `Flow.Ipv6` | Not added | Would be a breaking structural change; mutual exclusion documented in descriptions |
| `dst` description | Candidate for trimming | Long no-SRH uSID example in `dst` can be shortened to pointer to `dst_usids`; deferred to same PR |

---

## Out of scope

- Flags (OAM, Protected, Alert)
- Padding TLV and other SRH TLVs
- `segments_left`, `last_entry`, `tag` - SRH header fields; use `Flow.Ipv6SegmentRoutingUsid` for multi-container SRH paths

---

## Summary

Pure addition: one new property on `Flow.Ipv6` (UID 9) and two new schemas
(`Flow.Ipv6.UsidDst` with 3 fields, `Flow.Ipv6.UsidDst.uSid`), all in `ipv6.yaml`.
No existing schemas are modified except a description trim on `dst` (recommended but deferrable).
