# AGENTS.md

## Model

gpt-5.5 xhigh

## Standards

- Support check mode

- Accept module parameters in snake_case and transform using existing
  helpers where appropriate

- Keep implementations simple, idempotent, and consistent with existing
  ansible.builtin modules

- Keep present and absent flows explicit and easy to follow

- Use official Cloudflare Python SDK for api calls

- Do not create custom helpers unless functionality is shared across multiple
  modules in the api endpoints and no existing helper exists

- Prefer existing helpers from ansible.module_utils before implementing
  custom logic

- Prefer existing helpers listed below, including but not limited to:

    - ansible.module_utils.basic.missing_required_lib
    - ansible.module_utils.common.dict_transformations.camel_dict_to_snake_dict
    - ansible.module_utils.common.dict_transformations.recursive_diff
    - ansible.module_utils.common.dict_transformations.snake_dict_to_camel_dict
    - ansible.module_utils.common.parameters.scrub_none_parameters
    - ansible.module_utils.common.validation.check_mutually_exclusive
    - ansible.module_utils.common.validation.check_required_arguments
    - ansible.module_utils.common.validation.check_required_if

- Ensure modules remain idempotent and avoid unnecessary Cloudflare API calls

- Complete the requested implementation before stopping
