### Feature Overview
- **Related Issue:** (e.g., Fixes `#<issue_number>`)
- **Brief Description:**  
  Summarize the new feature. What problem does it solve? Who benefits from it?

---

### Feature Details
 - [Redocly docs for this feature/branch](<url>)
- **New Locations/Nomenclature:**  
  Specify where new attributes/nodes have been added in the models hierarchy to allow viewers to quickly navigate to the correct areas in the generated Redocly view corresponding to the model change.

- [Dev-Snappi branch reference](<url>)
- Example command to fetch the dev-snappi branch:
  ```
  go get github.com/open-traffic-generator/snappi/gosnappi@<dev-snappi-branch>
  ```

---

### Code snippets
Please provide a concise, well-commented code snippet demonstrating how to use the new feature in snappi/gosnappi:
The snippet should we within
```go/python
// Please provide clear and concise comments for the newly added code snippets. 
// Well-written comments help document the purpose and reasoning behind the code, making it easier for others to understand, maintain, and extend the codebase.
```

---

### Test Specification (Optional)
While not mandatory, add a simple port-DUT or port-DUT-port test case or scenario demonstrating how the feature can be used to test a representative `Device Under Test`.
- **Example test scenario:**
  - Configuration details: Description or example of usage of the new attributes or nodes in set_config or other APIs that can be used to emulate the test case on the test ports.
  - GetStats/GetStates/DUT telemetry to verify: 
  New added attributes or choices in get_metrics/get_states or other APIs that can be used to verify the specified test case(s)