# Specifications
The Open Traffic Generator REST API is based on the [OpenAPI specification](
https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.3.md) which is a standard, language-agnostic interface to RESTful APIs.  

This document includes additional details on the following topics that are specific to this effort:
- [Best Practices](#Best-Practices)
  - naming
  - description
  - nullable
- [OpenAPI keyword limitations](#Keyword-Limitations)
  - oneOf
  - allOf
- [OpenAPI keyword extensions](#Keyword-Extensions)
  - x-status
  - x-include
  - x-constraint
  - x-field-pattern

# Best Practices
- `naming`
  - `property names` MUST be snake_case
  - `schema object names` MUST be PascalCase (upper camel case)
  - `enum names` MUST be lowercase with underscores at natural word breaks.
  Valid characters are `^[a-z0-9_]+$`. 
  Enum names MUST start with an alphabetic character.
    - NO: 100_gpbs
    - YES: one_hundred_gbps
  - `namespaces` MUST be PascalCase (upper camel case) and use a `.` separator
    ```yaml
    # demonstrates how to specify an object within a namespace
    components:
      schemas:
        Router.Bgp.Advanced:
          type: object
    ```

- `schema`
    - top level `schema objects` should avoid properties as simple datatypes and 
    strive to encapsulate those properties in an object to allow for future 
    extensiblity

# Keyword Limitations
The build script will enforce the following keyword conventions.
- `oneOf` keyword
  - MUST not be used
  - this repository uses the `choice` property to discriminate between multiple objects at the same level
    ```yaml
    # demonstrates how to model a choice
    components:
      schemas:
      Choice.Object:
        type: object
        required: [choice]
        properties:
          choice:
            type: string
            enum: [a, b, c]
          a:
            $ref: '#/components/schemas/Choice.A'
          b:
            $ref: '#/components/schemas/Choice.B'
          c:
            $ref: '#/components/schemas/Choice.C'
    ```

- `allOf` keyword
  - MUST not to be used
  - use the x-include extension instead

- `description` keyword
  - MUST be included for every schema object and schema property and include a meaningful description

- `nullable`
  - MUST NOT be used

# Keyword Extensions
- `x-status`: current | under-review | deprecated | obsolete
  - If no status is specified, the default is "current".
  - the `x-status` keyword takes as an argument one of the strings
   "current", "deprecated", or "obsolete", "under-review.
  - "current" means that the definition is current and valid.
  - "deprecated" indicates an obsolete definition, but it permits new/
      continued implementation in order to foster interoperability with
      older/existing implementations.
  - "obsolete" means the definition is obsolete and SHOULD NOT be
      implemented and/or can be removed from implementations.

- `x-include`
    - for object composition use the x-include keyword to merge schema objects 
    into other schema objects instead of using the allOf keyword.
    - tooling does not handle the allOf keyword correctly in all cases and
    this allows the bundler.py to generate a lowest common denominator file.
    - the bundler.py will correctly merge the x-include and drop the x-include
    keyword from the merged object
    - the x-include value follows the same notation as the $ref
    ```yaml
    components:
      schemas:
        Named.Object:
        type: object
        required: [name]
        properties:
          name:
          description: >-
            The primary key for any item to be used in a list or as a
            foreign key reference
          type: string
          pattern: ^[\sa-zA-Z0-9-_()><\[\]]+$
        
        Composite.Object:
          x-include: '#/components/schemas/Named.Object'
          description: >
            This object will include all the items of the Named.Object in
            addition to its own properties
          properties:
            sample:
              type: string
    ```

- `x-constraint`
    - use x-constraint to identify referential integrity targets
    - use yamlpath to specify a constraint within an openapi yaml document
        - there currently is no standard but this serves as a reference 
        https://pypi.org/project/yamlpath/
    - an implementation of the model should use this extension to enforce 
    referential integrity
    - example: constrain a property so that it only contains a Port name 
    ```yaml
    property:
        port_name:
            type: string
            x-constraint:
            - /components/schemas/Port/properties/name
    ```


- `x-field-pattern`
```yaml
x-field-pattern: 
  description: >-
    This extension is used by the bundler to generate a unique pattern schema
    object for flow packet header field properties.
  type: object
  required: [description, format]
  properties:
    description: 
      description: >-
        Description of the parent property hosting the extension
      type: string  
    format:
      description: >-
        Controls the shape of the generated schema object.
      type: string
      enum:
      - mac
      - ipv4
      - ipv6
      - integer
      - checksum
  length:
    description: >-
      The length of integer values in bits.
      If the format is integer then the length MUST be specified as the size of
      a packet field must be exact and not open to interpretation.
      Pre-processing will write minimum and maximum values based on the length.
      Length will be ignored for mac, ipv4, ipv6 formats.
    type: integer
  default:
    description: >-
      The default value of the pattern value. 
      There is no specific type for this property as it is dependent on the 
      format property.
      For a format of mac, ipv4, ipv6 the default MUST be a string value.
      For a format of integer the default MUST be a whole number falling within 
      the bounds of the length property.
  features:
    type: string
    enum: [count, auto, metric_group]
    description: >- 
      count:
      Used to specify whether or not a count property is included in the
      unique generated pattern schema object.

      auto:
      Used to specify whether or not a choice property named auto is included in
      the unique generated pattern schema object.
      The choice property auto indicates that the system should auto generate a
      value for the field.

      metric_group:
      Used to indicate that a flow packet header field can be expanded in
      metrics under the name given to this property.
```
### Sample property with extension before bundle
```yaml
Flow.Ipv4:
  type: object
  properties:
    src:
      x-field-pattern:
        format: ipv4
        default: 0.0.0.0
        count: false
```
### Sample property after bundle
```yaml
Flow.Ipv4:
  type: object
  properties:
    address:
      $ref: '#/components/schemas/Pattern.Flow.Ipv4.Address'

Pattern.Flow.Ipv4.Address:
  type: object
  required: [choice]
  properties:
    choice:
      type: string
      enum: [value, values, increment, decrement]
    value:
      type: string
      format: ipv4
      default: 0.0.0.0
    values:
      type: array
      items:
        type: string
        format: ipv4
        default: 0.0.0.0
    increment:
      $ref: '#/components/schemas/Pattern.Flow.Ipv4.Address.Counter'
    decrement:
      $ref: '#/components/schemas/Pattern.Flow.Ipv4.Address.Counter'
```
### Sample instantiation
```yaml
ipv4:
  address:
    choice: value
    value: 0.0.0.0
```

## x-device-pattern extension
### schema
```yaml
x-field-pattern: 
  description: >-
    This extension is used by the bundler to generate a unique pattern schema
    object for device field properties.
  type: object
  required: [description, format]
  properties:
    description: 
      description: >-
        Description of the parent property hosting the extension
      type: string  
    format:
      description: >-
        Controls the shape of the generated schema object.
      type: string
      enum:
      - mac
      - ipv4
      - ipv6
      - integer
      - enum
  length:
    description: >-
      The length of integer values in bits.
      If the format is integer then the length MUST be specified as the size of
      a packet field must be exact and not open to interpretation.
      Pre-processing will write minimum and maximum values based on the length.
      Length will be ignored for mac, ipv4, ipv6, enum formats.
    type: integer
  default:
    description: >-
      The default value of the pattern value. 
      There is no specific type for this property as it is dependent on the 
      format property.
      For a format of mac, ipv4, ipv6, enum the default MUST be a string value.
      For a format of integer the default MUST be a whole number falling within 
      the bounds of the length property.
```
### Sample property with extension before bundle
```yaml
Router.Ipv4:
  type: object
  properties:
    address:
      x-device-pattern:
        format: ipv4
        default: 0.0.0.0
        count: false
```
### Sample property after bundle
```yaml
Router.Ipv4:
  type: object
  properties:
    address:
      $ref: '#/components/schemas/Pattern.Router.Ipv4.Address'

Pattern.Router.Ipv4.Address:
  type: object
  required: [choice]
  properties:
    choice:
      type: string
      enum: [value, values, increment, decrement]
    value:
      type: string
      format: ipv4
      default: 0.0.0.0
    values:
      type: array
      items:
        type: string
        format: ipv4
        default: 0.0.0.0
    increment:
      $ref: '#/components/schemas/Pattern.Router.Ipv4.Address.Counter'
    decrement:
      $ref: '#/components/schemas/Pattern.Router.Ipv4.Address.Counter'
```
### Sample instantiation
```yaml
ipv4:
  address:
    choice: value
    value: 0.0.0.0
```