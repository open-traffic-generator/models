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


