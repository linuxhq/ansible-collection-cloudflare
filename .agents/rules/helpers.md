# Helpers

Prefer these `module_utils` helpers over hand-rolled logic — reimplementing one fails review and
sanity. They cover:

- ARNs
- case conversion
- filters
- pagination
- tags
- validation
- waiters

```python
from ansible.module_utils.{{ module }} import {{ name }}
```

## ansible-core

| Module                         | Symbol                     | Use                           |
| ------------------------------ | -------------------------- | ----------------------------- |
| `.basic`                       | `get_all_subclasses`       | All subclasses.               |
| `.basic`                       | `get_module_path`          | Module file path.             |
| `.basic`                       | `get_platform`             | Platform name.                |
| `.basic`                       | `heuristic_log_sanitize`   | Scrub secrets before logging. |
| `.basic`                       | `load_platform_subclass`   | Load platform subclass.       |
| `.basic`                       | `missing_required_lib`     | "install X" message.          |
| `.common.collections`          | `count`                    | Count occurrences.            |
| `.common.collections`          | `is_iterable`              | Is it iterable?               |
| `.common.collections`          | `is_sequence`              | Is it a sequence?             |
| `.common.collections`          | `is_string`                | Is it a string?               |
| `.common.dict_transformations` | `camel_dict_to_snake_dict` | boto3 → snake_case.           |
| `.common.dict_transformations` | `dict_merge`               | Deep-merge dicts.             |
| `.common.dict_transformations` | `recursive_diff`           | Structural diff.              |
| `.common.dict_transformations` | `snake_dict_to_camel_dict` | snake_case → boto3.           |
| `.common.json`                 | `get_decoder`              | JSON decoder.                 |
| `.common.json`                 | `get_encoder`              | JSON encoder.                 |
| `.common.json`                 | `get_module_decoder`       | Module JSON decoder.          |
| `.common.json`                 | `get_module_encoder`       | Module JSON encoder.          |
| `.common.parameters`           | `env_fallback`             | Default from env var.         |
| `.common.parameters`           | `remove_values`            | Strip `no_log` values.        |
| `.common.parameters`           | `sanitize_keys`            | Strip `no_log` keys.          |
| `.common.parameters`           | `set_fallbacks`            | Apply fallback callables.     |
| `.common.text.converters`      | `container_to_bytes`       | Recursively → bytes.          |
| `.common.text.converters`      | `container_to_text`        | Recursively → text.           |
| `.common.text.converters`      | `jsonify`                  | JSON-encode.                  |
| `.common.text.converters`      | `to_bytes`                 | Safe str → bytes.             |
| `.common.text.converters`      | `to_text`                  | Safe bytes → str.             |
| `.common.text.formatters`      | `bytes_to_human`           | Bytes → human size.           |
| `.common.text.formatters`      | `human_to_bytes`           | Human size → bytes.           |
| `.common.text.formatters`      | `lenient_lowercase`        | Lowercase, skip non-str.      |
| `.common.validation`           | `check_missing_parameters` | Missing-params check.         |
| `.common.validation`           | `check_mutually_exclusive` | Mutually-exclusive check.     |
| `.common.validation`           | `check_required_arguments` | Required-args check.          |
| `.common.validation`           | `check_required_by`        | Required-by check.            |
| `.common.validation`           | `check_required_if`        | Required-if check.            |
| `.common.validation`           | `check_required_one_of`    | Required-one-of check.        |
| `.common.validation`           | `check_required_together`  | Required-together check.      |
| `.common.validation`           | `check_type_bits`          | Coerce to bits.               |
| `.common.validation`           | `check_type_bool`          | Coerce to bool.               |
| `.common.validation`           | `check_type_bytes`         | Coerce to bytes.              |
| `.common.validation`           | `check_type_dict`          | Coerce to dict.               |
| `.common.validation`           | `check_type_float`         | Coerce to float.              |
| `.common.validation`           | `check_type_int`           | Coerce to int.                |
| `.common.validation`           | `check_type_jsonarg`       | Coerce to JSON arg.           |
| `.common.validation`           | `check_type_list`          | Coerce to list.               |
| `.common.validation`           | `check_type_path`          | Coerce to path.               |
| `.common.validation`           | `check_type_raw`           | Pass through raw.             |
| `.common.validation`           | `check_type_str`           | Coerce to str.                |
| `.common.validation`           | `count_terms`              | Count present terms.          |
