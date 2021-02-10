# Specifications
- [OpenAPI specification](
https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.3.md)


# Keyword guide
The build script will enforce the following keyword conventions.

- `naming`
  - `property names` MUST be snake_case
  - `schema object names` MUST be PascalCase (upper camel case)
  - `enum names` MUST be lowercase with underscores at natural word breaks.
  Valid characters are `^[a-z0-9_]+$`. 
  Enum names MUST start with an alphabetic character.
    - NO: 100_gpbs
    - YES: one_hundred_gbps
  - `namespaces` MUST be PascalCase (upper camel case) and use a `.` separator

- `oneOf`
  - oneOf OpenAPI keyword support in generation tools is not very well supported at this time
  - this repository uses the `choice` property to discriminate between multiple 
  objects at the same level
  - oneOf can be used when specifing primitive types
    ```yaml
    # demonstrates how to model a choice and primitive oneOf
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
        one_of_sample:
          oneOf:
          - type: string
          - type: number
    ```

- `allOf`
  - is not to be used
  - use the x-include extension instead

- `description`
  - everything MUST have a `description keyword` filled in with a meaningful 
  description

- `schema`
    - top level `schema objects` should avoid properties as simple datatypes and 
    strive to encapsulate those properties in an object to allow for future 
    extensiblity

- `nullable`
  - MUST NOT be used

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


## x-pattern extension
### schema
```yaml
x-pattern: 
  description: >-
    This extension is used by the bundler to generate a unique pattern schema
    object for properties with specific a specific type, enum (if any), default.
  type: object
  required: [format, count, length, default, count]
  properties:
    format:
      description: >-
        The type of the generated value, values properties
      type: string
      enum:
      - ipv4
      - ipv6
      - hex
      - integer
      - number
      - enum
      - string
  length:
    description: >-
      The length of hex, integer and string value(s).
      For hex and integer it is the bit length
      For string it is the byte length
      For a format of ipv4, ipv6 it is ignored.
    type: integer
  enums: 
    description: >-
      If the format is enum this property is used to specify 
      a list of enums that the pattern is constrained to
    type: array
    items:
      type: string
  default:
    description: >-
      The default value of the pattern value. There is no specific type for 
      this property as it is dependent on the format property.
      For a format of ipv4, ipv6, hex, string the default is a string value.
      For a format of enum it MUST be one of the items in the enums property.
      For a format of integer it MUST be a whole number falling within the 
      bounds of the length property.
      For a format of number it MUST be a decimal number. 
  count: 
    description: >- 
      Used to specify whether or not a count property is included in the
      unique generated pattern schema object.
    type: boolean
    default: false
```
### Sample property with extension before bundle
```yaml
Device.Ipv4:
  type: object
  properties:
    address:
      x-pattern:
        format: ipv4
        default: 0.0.0.0
        count: false
```
### Sample property after bundle
```yaml
Device.Ipv4:
  type: object
  properties:
    address:
      $ref: '#/components/schemas/Pattern.Device.Ipv4.Address'

Pattern.Device.Ipv4.Address:
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
    increment:
      $ref: '#/components/schemas/Pattern.Ipv4Counter'
    decrement:
      $ref: '#/components/schemas/Pattern.Ipv4Counter'    
```
### Sample instantiation
```yaml
ipv4:
  address:
    choice: value
    value: 0.0.0.0
```