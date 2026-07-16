# Module documentation

Keep `DOCUMENTATION`, `EXAMPLES`, `RETURN`, and `argument_spec` in lockstep: every option,
return field, alias, choice, and default must agree across all four. The sections below cover the
details that are easy to miss.

## Fragments

- Pull in the standard documentation fragments for common options, region handling, and boto3
  requirements with `extends_documentation_fragment`, the same way the nearest module does.

## Options and returns

- Give list options and list return values an `elements` entry.
- Write `EXAMPLES` using the fully-qualified collection name, `{{ namespace }}.{{ name }}.{{ plugin }}`.

## Validation rules

- Document each argument-spec validation rule in the descriptions of the options it affects:
  - `mutually_exclusive`
  - `required_by`
  - `required_if`
  - `required_one_of`
  - `required_together`
- For an option that's only sometimes required, document the condition instead of setting
  `required: true`.
- Reference nested options with paths like `O(ip_addresses[].ipv6)`.

## Info lookups

- When an info module offers both a singular lookup and list/filter options, spell out the
  split: `O(name)` is mutually exclusive with the list filters, and any option used only by the
  singular lookup should note that it `Requires O(name)`.
