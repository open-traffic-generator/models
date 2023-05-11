# Control API

Control API allows controlling state of configured resources on traffic generator or perform relevant actions against them, without modifying the configuration.

These API can be categorized as follows:
1. Control States
2. Control Actions

### Control States

These API shall mostly be used to `change` operational state of various resources configured on traffic generator, where every operational state can be represented purely using `enums`.

Can be further categorized as follows:
1. Traffic
    - Set flow transmit state
2. Protocols
    - Set state of protocol on all or subset of configured resources
    - Set state of routes for subset of active protocols
3. Port
    - Set Port link state
    - Set packet capture state

### Control Actions

These API shall mostly be used to `trigger` 

Can be further categorized as follows:
1. Protocols
    - ipv4
        - send_ping
    - ipv6
        - send ping
    - bgp
        - Send BGP notifications
        - graceful restart
