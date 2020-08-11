# Specification
- [OpenAPI specification](
https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.3.md)
- [Convert OpenAPI to Protobuf](
https://github.com/googleapis/gnostic)

# Keyword guide
The build script will enforce the following keyword conventions.

- `naming`
  - `property names` MUST be snake_case
  - `schema object names` MUST be PascalCase (upper camel case)
  - `enum names` MUST be UPPER_CASE with underscores at natural word breaks
  - `namespaces` MUST be enforced using a `.` separator

- `oneOf`
  - oneOf OpenAPI keyword support in generation tools is not very well supported
  - this repository uses the `choice` property to discriminate between multiple 
  objects at the same level
  ```yaml
  # demonstrates how to model a choice
    Port:
        type: object
        required: [choice]
        properties:
            choice:
                type: string
                enum: [physical, interface, virtual, container]
            physical:
                $ref: '#/components/schemas/Physical'
            interface:
                $ref: '#/components/schemas/Interface'
            virtual:
                $ref: '#/components/schemas/Virtual'
            container:
                $ref: '#/components/schemas/Container'
  ```

- ALLOF
  - is not to be used
  - use the x-inline extension instead and the bundler will do
  inline replacement

- DESCRIPTIONS
  - everything MUST have a `description keyword` filled in with a meaningful 
  description
- SCHEMA OBJECT
    - top level `schema objects` should avoid properties as simple datatypes and 
    strive to encapsulate those properties in an object to allow for future 
    extensiblity
- NULLABLE
  - `nullable` MUST not be used
<!-- - DISCRIMINATOR
  - `discriminator` MUST not be used
    - make each object have a common discriminator property
    - make the property an enum with one value and default that value
    - this indicates to the server the type without having to wait for tooling 
    to catch up (most tooling doesn't work well with it) -->
- DEFAULT
  - default does not apply to oneOf, anyOf so don't bother using it for 
  properties that are polymorphic

# x-oneOf
- use x-inline-properties to inline properties instead of using allOf
- the yaml compiler will correctly inline and drop the x-inline-properties
```yaml
components:
  x-inline-properties:
    name:
      description: >-
        The primary key for any item to be used in a list or as a
        foreign key reference
      type: string
      pattern: ^[\sa-zA-Z0-9-_()><\[\]]+$
```

# Polymorphism
```yaml
components:
  schemas:
    A:
      type: object
      properties:
        name:
          type: string
        protocols:
          type: array
          items:
            oneOf:
            - $ref: B
            - $ref: C
```
```protobuf
message A {
  string name = 1;
  // valid protocols are any of: B, C
  repeated protocols = any;
}
message B {}
message C {}
```
```go
A a = ...;
B b;
C c;
if (a.protocols()[0].UnpackTo(&b)) {
    // first protocol is B
}
```

# Extensions
## `x-namespace`
Use to separate schemas that have the same name.
There are occurrences where stateful protocol schemas share the same name as
flow headers. Examples ethernet, vlan, ipv4
Should be used by language generators.

## `x-primary-key: <pattern>`

## `x-foreign-key: <path to schema property>`
- This extension allows a schema to establish a foreign key to another schema.
- This can only exist on a property.  
- The value of the keyword must be a path to another schema property that is 
enforces unique values.

```yaml
Example: This demonstrates how to model a relationship between schema A and 
schema B using the x-foreign-key extension

components:
  schemas:
    A:
      required: [name]
      properties:
        name:
          x-primary-key: 'pattern'
          type: string
    B:
      required: [name, parent]
      properties:
        name:
          x-primary-key: 'pattern'
          type: string
        parent:
          type: [string, null]
          x-foreign-key: '#/components/schemas/A/name'
```

## Protocol header field extension keywords
Protocol header models should use the following extensions on each property that
 represents a field to provide additional information to be consumed by server 
 implementations
```yaml
Example:

      properties:
        priority:
          type: object
          description: >-
            Vlan priority
          x-fld-bit-offset: 0
          x-fld-bit-length: 3
          x-fld-default: 0

```
### `x-fld-bit-offset`
Bit offset of the field from the start of the protocol header
### `x-fld-bit-length`
Bit length of the field 
### `x-fld-default`
Default value if the protocol field property is omitted
The protocol field property contains an object that can be 
a simple value or the complex Pattern object so the `x-fld-default` indicates 
that nested values below should use the `x-fld-default` until either a default 
or `x-fld-default` keyword appears. 
