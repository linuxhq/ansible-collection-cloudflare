# AGENTS.md

## Model

gpt-5.5 high

## Standards

* Support check mode

* Keep present and absent flows explicit and easy to follow

* Ensure modules remain idempotent and avoid unnecessary cloudflare api calls

* Keep implementations consistent with existing ansible.builtin module patterns

* Accept module parameters in snake_case and transform using existing
  helpers where appropriate

* Use official cloudflare python sdk for api calls

* Do not create custom helpers unless functionality is shared across multiple
  modules in the api endpoints and no existing helper exists

* Prefer the following collection helpers before implementing custom logic
  * ansible.module_utils

* Use existing ansible helpers listed below, including but not limited to
  * ansible.module_utils.basic.get_all_subclasses
  * ansible.module_utils.basic.get_module_path
  * ansible.module_utils.basic.get_platform
  * ansible.module_utils.basic.heuristic_log_sanitize
  * ansible.module_utils.basic.load_platform_subclass
  * ansible.module_utils.basic.missing_required_lib
  * ansible.module_utils.common.collections.count
  * ansible.module_utils.common.collections.is_iterable
  * ansible.module_utils.common.collections.is_sequence
  * ansible.module_utils.common.collections.is_string
  * ansible.module_utils.common.dict_transformations.camel_dict_to_snake_dict
  * ansible.module_utils.common.dict_transformations.dict_merge
  * ansible.module_utils.common.dict_transformations.recursive_diff
  * ansible.module_utils.common.dict_transformations.snake_dict_to_camel_dict
  * ansible.module_utils.common.json.get_decoder
  * ansible.module_utils.common.json.get_encoder
  * ansible.module_utils.common.json.get_module_decoder
  * ansible.module_utils.common.json.get_module_encoder
  * ansible.module_utils.common.parameters.env_fallback
  * ansible.module_utils.common.parameters.remove_values
  * ansible.module_utils.common.parameters.sanitize_keys
  * ansible.module_utils.common.parameters.set_fallbacks
  * ansible.module_utils.common.text.converters.container_to_bytes
  * ansible.module_utils.common.text.converters.container_to_text
  * ansible.module_utils.common.text.converters.jsonify
  * ansible.module_utils.common.text.converters.to_bytes
  * ansible.module_utils.common.text.converters.to_text
  * ansible.module_utils.common.text.formatters.bytes_to_human
  * ansible.module_utils.common.text.formatters.human_to_bytes
  * ansible.module_utils.common.text.formatters.lenient_lowercase
  * ansible.module_utils.common.validation.check_missing_parameters
  * ansible.module_utils.common.validation.check_mutually_exclusive
  * ansible.module_utils.common.validation.check_required_arguments
  * ansible.module_utils.common.validation.check_required_by
  * ansible.module_utils.common.validation.check_required_if
  * ansible.module_utils.common.validation.check_required_one_of
  * ansible.module_utils.common.validation.check_required_together
  * ansible.module_utils.common.validation.check_type_bits
  * ansible.module_utils.common.validation.check_type_bool
  * ansible.module_utils.common.validation.check_type_bytes
  * ansible.module_utils.common.validation.check_type_dict
  * ansible.module_utils.common.validation.check_type_float
  * ansible.module_utils.common.validation.check_type_int
  * ansible.module_utils.common.validation.check_type_jsonarg
  * ansible.module_utils.common.validation.check_type_list
  * ansible.module_utils.common.validation.check_type_path
  * ansible.module_utils.common.validation.check_type_raw
  * ansible.module_utils.common.validation.check_type_str
  * ansible.module_utils.common.validation.count_terms

* Complete the requested implementation before stopping

* Do not commit changes
