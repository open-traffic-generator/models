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
3. System
    - Set Port link state
    - Set packet capture state

### Control Actions

These API shall mostly be used to `trigger` 

Can be further categorized as follows:
1. System
    - Send ping
    - Execute traceroute
    - Reboot test port
2. Protocols
    - ping
    - ipv4
        send_ping
    - bgp
        - Send BGP notifications
        - graceful restart
    - Clear learned info
    - Inject learnt info (neighbor entries, routes) 



### Examples

```go
api := gosnappi.NewApi()

c := api.NewConfig()

// set config
api.SetConfig(c)

// start all protocols
ps := gosnappi.NewControlState()
ps.Protocols().All().SetState(gosnappi.ControlProtocolsAllState.START)
api.SetControlState(ps)

// wait for protocol metrics to be ok ...

// start transmit
ts := gosnappi.NewControlState()
ts.Traffic().FlowTransmit().SetState(gosnappi.ControlTrafficFlowTransmitState.START)
api.SetControlState(ts)

// wait for flow metrics to be ok ...

// withdraw some routes
rs := gosnappi.NewControlState()
rs.Protocols().Routes().
    SetNames([]string{"rr1"}).
    SetState(gosnappi.ControlProtocolsRoutesState.WITHDRAW)
api.SetControlState(rs)


// change lacp admin states
la := gosnappi.NewControlState()
la.Protocols().Lacp().Admin()
    SetLagMemberNames([]string{"p1", "p2"}).
    SetState(gosnappi.ControlProtocolsLacpAdminState.DOWN)
api.SetControlState(la)

```


```yaml
control_state:
    - choice: [traffic, protocols]
      traffic:
        choice: [flow_transmit]
        flow_transmit:
            state: [start, stop]
            flow_names: []
      protocols:
        choice: [all, lacp, bgp, routes]
        all:
            state: [start, stop]
        lacp:
            choice: [admin, session]
            admin:
                state: [up, down]
            session:
                state: [up, down]
        lacp:
            choice: [admin]
            admin:
                state: [up, down]
control_action:

```

```go

api.SetProtocols()

api.StartProtocols()

// approach 1
api.StartLacpAdminState()
api.StopLacpAdminState()

// approach 2
la := gosnappi.NewControlState()
la.Protocols().Lacp().Admin()
    SetLagMemberNames([]string{"p1", "p2"}).
    SetState(gosnappi.ControlProtocolsLacpAdminState.DOWN)

p := gosnappi.NewControlProtocols()
api.StopProtocols(p)

// 
func (api *Api) StartProtocols(arg) {
    ps := gosnappi.NewControlState()
    ps.Protocols().All().SetState(gosnappi.ControlProtocolsAllState.START)
    api.SetControlState(ps)
}
```