# Specifications
- [OpenAPI specification](
https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.3.md)


# Keyword guide
The build script will enforce the following keyword conventions.

- `naming`
  - `property names` MUST be snake_case
  - `schema object names` MUST be PascalCase (upper camel case)
  - `enum names` MUST be lowercase with underscores at natural word breaks, valid 
  characters are `^[\sa-zA-Z0-9-_()><\.\[\]]+$`. Numbers in enums should be represented 
  with numerals not the names of numbers except for when enums are being used in a choice 
  property then they MUST NOT start with a numeral.
    - YES: 100_gpbs
    - NO: one_hundred_gbps
  - `namespaces` MUST be PascalCase (upper camel case) and use a `.` separator

- `oneOf`
  - oneOf OpenAPI keyword support in generation tools is not very well supported at this time
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

- `allOf`
  - is not to be used
  - use the x-inline extension instead and the bundler will do
  inline replacement

- `description`
  - everything MUST have a `description keyword` filled in with a meaningful 
  description

- `schema`
    - top level `schema objects` should avoid properties as simple datatypes and 
    strive to encapsulate those properties in an object to allow for future 
    extensiblity

- `nullable`
  - MUST NOT be used

- `x-inline`
    - use x-inline to inline snippets into a schema
    - the bundler.py will correctly inline and drop the x-inline-properties
    ```yaml
    components:
    x-inline:
        name:
        description: >-
            The primary key for any item to be used in a list or as a
            foreign key reference
        type: string
        pattern: ^[\sa-zA-Z0-9-_()><\[\]]+$
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
            - /components/schemas/Port.properties.name
    ```


