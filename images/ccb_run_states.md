# AI Workload State Diagram

Simplified run state diagram for the collective benchmark. See the state
transitions table in
[result/collective_communications.yaml](../result/collective_communications.yaml)
for the complete set of transitions.

```mermaid
stateDiagram-v2
    state "Stopped(Unrun)" as StoppedUnrun
    state "Started" as Started
    state "Stopping" as Stopping
    state "Stopped(Manual)" as StoppedManual
    state "Stopped(Success)" as StoppedSuccess
    state "Stopped(Failure)" as StoppedFailure
    state result <<choice>>

    [*] --> StoppedUnrun
    StoppedUnrun --> Started : set_control_state(start)

    Started --> Stopping : set_control_state(stop)
    Stopping --> StoppedManual : «auto»
    StoppedManual --> Started : set_control_state(start)

    Started --> result
    result --> StoppedSuccess : «successful»
    result --> StoppedFailure : «unsuccessful»
    StoppedSuccess --> Started : set_control_state(start)
    StoppedFailure --> Started : set_control_state(start)

    note left of Started
        set_control_state(start) will attempt to configure
        or reconfigure if config has changed.
    end note
```
