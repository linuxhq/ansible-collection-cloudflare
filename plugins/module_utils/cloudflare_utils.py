# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


import json
import os
from base64 import b64decode
from contextlib import contextmanager
from ipaddress import ip_address

from ansible.module_utils.basic import missing_required_lib

try:
    import cloudflare
    import pydantic
    from cloudflare import BaseModel, Cloudflare
except ImportError:
    cloudflare = None
    BaseModel = None
    Cloudflare = None
    PYDANTIC_V2 = False
else:
    # The SDK supports Pydantic v1, whose to_dict() rejects the warnings argument.
    PYDANTIC_V2 = int(pydantic.VERSION.split(".", 1)[0]) >= 2


# Differing fields named in a "did not apply" failure message.
MESSAGE_FIELDS = 10

# Longest DNS name and label, in characters, without a trailing dot.
MAX_DNS_NAME_LENGTH = 253
MAX_DNS_LABEL_LENGTH = 63

# Path segments the SDK refuses to put in a request path.
DOT_SEGMENTS = (".", "..")


class CloudflareResponseError(Exception):
    pass


@contextmanager
def cloudflare_error_context(message, **context):
    api_error = getattr(cloudflare, "APIError", ())
    try:
        yield
    except api_error as exc:
        exc._cloudflare_message = message
        exc._cloudflare_context = context
        raise


def require_cloudflare_sdk(module):
    """Fail when the cloudflare SDK cannot be imported."""
    if Cloudflare is None:
        module.fail_json(
            msg=missing_required_lib("cloudflare"),
            missing_python_package="cloudflare",
        )


@contextmanager
def cloudflare_client(module):
    require_cloudflare_sdk(module)
    api_token = validate_cloudflare_params(module)
    # Omit the other authentication headers so ambient credentials never apply,
    # including in client copies made by with_options(), which reload them from
    # the environment. Also override each custom header spelling: SDK header
    # dictionaries are case-sensitive until HTTPX builds the request. Preserve
    # unrelated custom headers.
    headers = {
        "Authorization": f"Bearer {api_token}",
        "X-Auth-Email": cloudflare.omit,
        "X-Auth-Key": cloudflare.omit,
        "X-Auth-User-Service-Key": cloudflare.omit,
    }
    for line in os.environ.get("CLOUDFLARE_CUSTOM_HEADERS", "").split("\n"):
        header = line.split(":", 1)[0].strip()
        if (
            ":" in line
            and header.lower()
            in (
                "authorization",
                "x-auth-email",
                "x-auth-key",
                "x-auth-user-service-key",
            )
            and header not in headers
        ):
            headers[header] = cloudflare.omit

    try:
        with Cloudflare(api_token=api_token, default_headers=headers) as client:
            # Constructor values of None load ambient credentials, which take
            # precedence over api_token. Clear them before issuing requests.
            client.api_email = None
            client.api_key = None
            client.user_service_key = None
            yield client
    except cloudflare.APIError as exc:
        if isinstance(exc, cloudflare.APIConnectionError):
            default_message = "Cloudflare API connection failed"
        elif isinstance(exc, cloudflare.APIStatusError):
            default_message = "Cloudflare API request failed"
        else:
            default_message = "Cloudflare API error"

        fail_from_cloudflare_error(
            module,
            getattr(exc, "_cloudflare_message", default_message),
            exc,
            **getattr(exc, "_cloudflare_context", {}),
        )
    except CloudflareResponseError as exc:
        module.fail_json(msg=str(exc))


def validate_cloudflare_params(module):
    api_token = module.params.get("api_token")
    if not isinstance(api_token, str) or not api_token.strip():
        module.fail_json(msg="api_token must not be empty")

    if any(ord(character) < 32 or ord(character) == 127 for character in api_token):
        module.fail_json(msg="api_token must not contain control characters")

    for name, value in module.params.items():
        if (name in {"domain", "name", "phase", "production_branch"} or name.endswith("_id")) and isinstance(
            value, str
        ):
            if not value.strip():
                module.fail_json(msg=f"{name} must not be empty")

            if value != value.strip():
                module.fail_json(msg=f"{name} must not contain leading or trailing whitespace")

            # The SDK refuses to build a request path with a dot segment.
            if (name == "phase" or name.endswith("_id")) and value in DOT_SEGMENTS:
                module.fail_json(msg=f"{name} must not be '.' or '..'")

    return api_token.strip()


def error_response_body(exc):
    response = getattr(exc, "response", None)
    if response is None or not hasattr(response, "json"):
        return None

    try:
        return response.json()
    except ValueError:
        return None


def cloudflare_error_details(exc):
    """Return the status code and response body of a failure, or its message."""
    status_code = getattr(exc, "status_code", None)
    response_body = error_response_body(exc)

    details = {}
    if getattr(exc, "response", None) is None:
        details["error"] = str(exc)

    if status_code is not None:
        details["status_code"] = status_code

    if response_body is not None:
        details["response"] = response_body

    return details


def fail_from_cloudflare_error(module, message, exc, **context):
    module.fail_json(**{"msg": message, **context, **cloudflare_error_details(exc)})


def serialize_resource(resource):
    if resource is None:
        return None

    if BaseModel is not None and isinstance(resource, BaseModel):
        # Generated models can mistype a field, such as an Access group's
        # is_default; keep the value and skip Pydantic v2's stderr warning.
        options = {"warnings": False} if PYDANTIC_V2 else {}
        return serialize_resource(resource.to_dict(mode="json", **options))

    if isinstance(resource, dict):
        return {key: serialize_resource(value) for key, value in resource.items() if value is not None}

    if isinstance(resource, (list, tuple)):
        return [serialize_resource(value) for value in resource]

    return resource


def resource_field(module, resource, field, resource_name, expected=None, strict=True):
    """Return a string field of resource, failing when it is malformed.

    strict also rejects an empty value or one with surrounding whitespace.
    """
    value = resource.get(field) if isinstance(resource, dict) else None
    if not isinstance(value, str) or strict and (not value.strip() or value != value.strip()):
        failure = {"msg": f"Cloudflare API returned malformed {resource_name} data"}
        if isinstance(resource, dict) and "id" in resource:
            failure["resource_id"] = resource["id"]

        module.fail_json(**failure)

    if expected is not None and value != expected:
        module.fail_json(msg=f"Cloudflare API returned the wrong {resource_name}")

    return value


def resource_id(module, resource, resource_name, expected=None):
    return resource_field(module, resource, "id", resource_name, expected=expected)


def require_mapping(module, value, resource_name):
    if not isinstance(value, dict):
        module.fail_json(msg=f"Cloudflare API returned malformed {resource_name} data")


def resource_list(module, items, resource_name, required_fields=("id",)):
    """Serialize every item of an SDK list, validating its required fields.

    Names need only be strings: Cloudflare can store names with surrounding
    whitespace, which must not fail a listing of every resource.
    """
    resources = [serialize_resource(item) for item in items]
    for resource in resources:
        for field in required_fields:
            resource_field(module, resource, field, resource_name, strict=field != "name")

    return resources


def get_or_none(get, *args, **kwargs):
    """Call an SDK get method, returning None when Cloudflare responds 404."""
    try:
        return get(*args, **kwargs)
    except cloudflare.NotFoundError:
        return None


def find_resource(module, items, resource_name, field, value):
    """Return the serialized item whose field equals value, or None.

    Fail when more than one item matches, so an ambiguous name never selects
    an arbitrary resource. Only the matched items are validated strictly, so
    an unrelated item with surrounding whitespace in its field is skipped.
    """
    matches = []
    for item in items:
        resource = serialize_resource(item)
        if resource_field(module, resource, field, resource_name, strict=False) == value:
            resource_field(module, resource, field, resource_name)
            matches.append(resource)

    if len(matches) > 1:
        module.fail_json(
            msg=f"Found more than one {resource_name} with {field} {value!r}",
            **{field: value},
            matching_ids=[resource_id(module, resource, resource_name) for resource in matches],
        )

    return matches[0] if matches else None


def cidr_from_address(value):
    """Return a bare IP address with its full-length prefix, as Cloudflare stores it."""
    if not isinstance(value, str) or "/" in value:
        return value

    try:
        return f"{value}/{ip_address(value).max_prefixlen}"
    except ValueError:
        return value


def valid_dns_labels(name):
    """Return whether name is at most 253 characters of dot-separated labels.

    Each label must have 1 to 63 characters and must not start or end with
    a hyphen. Callers check the allowed characters and strip a trailing dot.
    """
    return len(name) <= MAX_DNS_NAME_LENGTH and all(
        0 < len(label) <= MAX_DNS_LABEL_LENGTH and not label.startswith("-") and not label.endswith("-")
        for label in name.split(".")
    )


def payload_from_params(params, fields):
    return {field: params[field] for field in fields if params.get(field) is not None}


def select_fields(value, fields):
    value = serialize_resource(value) or {}
    return {field: value[field] for field in fields if field in value}


def unsupported_fields(value, fields, path):
    """Return the path of each key of the mapping value that fields does not list.

    fields lists the allowed keys, or maps each allowed key to the fields of
    its own mapping value, or to None when that value is not checked. Values
    that are not mappings are not checked.
    """
    if not isinstance(value, dict):
        return []

    unknown = []
    for key, item in value.items():
        if key not in fields:
            unknown.append(f"{path}.{key}")
        elif isinstance(fields, dict) and fields[key] is not None:
            unknown.extend(unsupported_fields(item, fields[key], f"{path}.{key}"))

    return unknown


def normalize_current_by_desired_fields(current, desired, exact_fields=()):
    """Project current onto the fields of desired.

    Mappings under a key in exact_fields keep every current key, so entries the
    caller omitted still count as differences.
    """
    if isinstance(current, dict) and isinstance(desired, dict):
        if not desired:
            return current

        projected = {}
        for key, value in desired.items():
            item = current.get(key)
            if key in exact_fields and isinstance(item, dict) and isinstance(value, dict):
                projected[key] = {
                    name: (
                        normalize_current_by_desired_fields(entry, value[name], exact_fields)
                        if name in value
                        else entry
                    )
                    for name, entry in item.items()
                }
            else:
                projected[key] = normalize_current_by_desired_fields(item, value, exact_fields)

        return projected

    if isinstance(current, list) and isinstance(desired, list):
        if len(current) != len(desired):
            return current

        return [
            normalize_current_by_desired_fields(current_item, desired_item, exact_fields)
            for current_item, desired_item in zip(current, desired)
        ]

    return current


def values_equal(current, desired):
    """Compare JSON values, treating Booleans and numbers as different types."""
    if isinstance(current, dict) and isinstance(desired, dict):
        return current.keys() == desired.keys() and all(values_equal(current[key], desired[key]) for key in current)

    if isinstance(current, list) and isinstance(desired, list):
        return len(current) == len(desired) and all(values_equal(*pair) for pair in zip(current, desired))

    if isinstance(current, bool) or isinstance(desired, bool):
        return type(current) is type(desired) and current == desired

    return current == desired


def values_differ(current, desired):
    return not values_equal(serialize_resource(current), serialize_resource(desired))


def projected_current(current, desired, defaults=None, exact_fields=(), exact_values=()):
    """Return current in the form differs compares with desired."""
    current = {**(defaults or {}), **(serialize_resource(current) or {})}
    projected = normalize_current_by_desired_fields(current, desired, exact_fields)
    for field in exact_values:
        if field in desired:
            projected[field] = current.get(field)

    return projected


def differs(current, desired, defaults=None, exact_fields=(), exact_values=()):
    """Return whether current differs from desired on the desired fields only.

    Fields the API omits are filled from defaults before comparing. Mappings
    under exact_fields are compared on their complete key sets. Top-level
    fields in exact_values are compared exactly, at every nesting level.
    """
    if not desired:
        return False

    return values_differ(projected_current(current, desired, defaults, exact_fields, exact_values), desired)


def applied_differences(stored, requested):
    """List each top-level field whose stored value differs from the requested value.

    Like values_differ, a null field matches a missing one.
    """
    stored = serialize_resource(stored) or {}
    requested = serialize_resource(requested) or {}
    fields = [*requested, *(field for field in stored if field not in requested)]
    return [
        {"field": field, "requested": requested.get(field), "stored": stored.get(field)}
        for field in fields
        if not values_equal(stored.get(field), requested.get(field))
    ]


def message_value(module, value):
    """Render value as JSON for a failure message.

    Ansible masks no_log values in the result, but not their JSON-escaped
    forms, so those are masked here.
    """
    text = json.dumps(value, ensure_ascii=False)
    for secret in getattr(module, "no_log_values", ()):
        escaped = json.dumps(secret, ensure_ascii=False)[1:-1]
        if escaped != secret:
            text = text.replace(escaped, "********")

    return text


def fail_not_applied(module, resource_name, differences):
    """Fail, naming the requested and stored value of each field Cloudflare did not apply."""
    pairs = [
        f"{difference['field']} requested {message_value(module, difference['requested'])}, "
        f"stored {message_value(module, difference['stored'])}"
        for difference in differences[:MESSAGE_FIELDS]
    ]
    if len(differences) > MESSAGE_FIELDS:
        pairs.append(f"{len(differences) - MESSAGE_FIELDS} more fields are listed in differences")

    details = f": {'; '.join(pairs)}" if pairs else ""
    module.fail_json(
        msg=f"Cloudflare did not apply the requested {resource_name}{details}",
        differences=differences,
    )


def require_applied(module, resource, desired, resource_name, defaults=None, exact_fields=(), exact_values=()):
    require_mapping(module, resource, resource_name)
    if differs(resource, desired, defaults, exact_fields, exact_values):
        projected = projected_current(resource, desired, defaults, exact_fields, exact_values)
        fail_not_applied(module, resource_name, applied_differences(projected, desired))


# The SDK renames these snake_case selector keys to their API spellings on
# write, so Cloudflare would store and return keys that never match the request.
ACCESS_SELECTOR_API_KEYS = {
    "azure_ad": "azureAD",
    "github_organization": "github-organization",
}

ACCESS_SELECTOR_FIELDS = ("exclude", "include", "require")

# Cloudflare adds these keys to the selectors below, such as the GitHub
# organization's id, so a stored selector matches a request that omits them.
ACCESS_SELECTOR_ASSIGNED_KEYS = {"github-organization": ("id",)}

# Fields of each Access selector, by its API key, from the cloudflare SDK
# AccessRuleParam types. Cloudflare accepts any other field but drops it.
ACCESS_SELECTOR_KEYS = {
    "any_valid_service_token": (),
    "auth_context": ("ac_id", "id", "identity_provider_id"),
    "auth_method": ("auth_method",),
    "azureAD": ("id", "identity_provider_id"),
    "certificate": (),
    "cloudflare_account_member": ("account_id",),
    "common_name": ("common_name",),
    "device_posture": ("account_id", "integration_uid"),
    "email": ("email",),
    "email_domain": ("domain",),
    "email_list": ("id",),
    "everyone": (),
    "external_evaluation": ("evaluate_url", "keys_url"),
    "geo": ("country_code",),
    "github-organization": ("identity_provider_id", "name", "team"),
    "group": ("id",),
    "gsuite": ("email", "identity_provider_id"),
    "ip": ("ip",),
    "ip_list": ("id",),
    "linked_app_token": ("app_uid",),
    "login_method": ("id",),
    "oidc": ("claim_name", "claim_value", "identity_provider_id"),
    "okta": ("identity_provider_id", "name"),
    "saml": ("attribute_name", "attribute_value", "identity_provider_id"),
    "service_token": ("token_id",),
    "service_token_tag": ("key", "value"),
    "user_risk_score": ("user_risk_score",),
}

# Fields of an Access policy approval group, from the cloudflare SDK
# ApprovalGroupParam type. Cloudflare accepts any other field but drops it.
ACCESS_APPROVAL_GROUP_FIELDS = ("approvals_needed", "email_addresses", "email_list_uuid")


# Approval group fields Cloudflare drops when they hold these empty values.
EMPTY_APPROVAL_GROUP_FIELDS = {"email_addresses": [], "email_list_uuid": ""}


def empty_approval_group_fields(groups, path):
    """Return the path of each empty email_addresses list or email_list_uuid in the approval groups.

    Cloudflare drops it, so it would never match the request.
    """
    return [
        f"{path}[{index}].{field}"
        for index, group in enumerate(groups if isinstance(groups, list) else ())
        if isinstance(group, dict)
        for field, empty in EMPTY_APPROVAL_GROUP_FIELDS.items()
        if field in group and group[field] == empty
    ]


def comparable_access_selector(selector, desired):
    """Return selector without the keys Cloudflare assigned that desired does not set.

    An assigned key that desired sets to null is not set, as it is not stored
    as null.
    """
    if not isinstance(selector, dict) or not isinstance(desired, dict):
        return selector

    comparable = {}
    for name, config in selector.items():
        requested = desired.get(name)
        if isinstance(config, dict) and isinstance(requested, dict):
            assigned = ACCESS_SELECTOR_ASSIGNED_KEYS.get(name, ())
            config = {
                key: value for key, value in config.items() if key not in assigned or requested.get(key) is not None
            }

        comparable[name] = config

    return comparable


def comparable_access_rules(rules, desired):
    """Return rules with each selector paired, by position, with the one desired sets.

    Keys Cloudflare assigned to a stored selector are dropped when the paired
    selector does not set them.
    """
    rules = serialize_resource(rules)
    if not isinstance(rules, dict) or not isinstance(desired, dict):
        return rules

    comparable = dict(rules)
    for field in ACCESS_SELECTOR_FIELDS:
        stored, requested = rules.get(field), desired.get(field)
        if isinstance(stored, list) and isinstance(requested, list) and len(stored) == len(requested):
            comparable[field] = [comparable_access_selector(*pair) for pair in zip(stored, requested)]

    return comparable


def validate_access_selectors(module, rules=None, prefix=""):
    """Fail when an Access selector is not one rule, uses an SDK spelling, or holds a value Cloudflare drops.

    Each selector is a mapping that sets one rule, as every SDK AccessRuleParam type has one key; Cloudflare drops an
    empty selector and splits a selector with several rules into separate selectors. SDK spellings must use their API
    keys instead. A known selector's value must be a mapping, as in the SDK AccessRuleParam types; Cloudflare stores a
    null value as {}. Its fields must be ones Cloudflare stores, and not empty strings, which Cloudflare drops. Unknown
    selector keys are left to Cloudflare, which rejects them. rules defaults to the module parameters; prefix names
    their location in failure messages, such as "policies[0].".
    """
    rules = module.params if rules is None else rules
    unknown = []
    empty = []
    for field in ACCESS_SELECTOR_FIELDS:
        for index, selector in enumerate(rules.get(field) or ()):
            path = f"{prefix}{field}[{index}]"
            if not isinstance(selector, dict):
                module.fail_json(msg=f"{path} must be a mapping that sets one selector, such as {{'everyone': {{}}}}")

            if not selector:
                module.fail_json(msg=f"{path} must set one selector; Cloudflare drops an empty selector")

            for key, api_key in ACCESS_SELECTOR_API_KEYS.items():
                if key in selector:
                    module.fail_json(
                        msg=f"{prefix}{field} selector {key!r} must use the Cloudflare API key {api_key!r}"
                    )

            if len(selector) > 1:
                module.fail_json(
                    msg=f"{path} sets the selectors {', '.join(repr(key) for key in selector)}, which "
                    f"Cloudflare splits into separate {field} entries; list each selector as its own entry"
                )

            for key, config in selector.items():
                if key not in ACCESS_SELECTOR_KEYS:
                    continue

                if not isinstance(config, dict):
                    module.fail_json(
                        msg=f"{path}.{key} must be a mapping; use {{}} for a selector without "
                        "fields, as Cloudflare stores a null selector as {}"
                    )

                fields = ACCESS_SELECTOR_KEYS[key] + ACCESS_SELECTOR_ASSIGNED_KEYS.get(key, ())
                unknown.extend(unsupported_fields(config, fields, f"{path}.{key}"))
                empty.extend(f"{path}.{key}.{name}" for name, value in config.items() if value == "")

    if unknown:
        module.fail_json(
            msg=f"Cloudflare does not store these Access selector fields: {', '.join(unknown)}",
            unsupported_fields=unknown,
        )

    if empty:
        module.fail_json(
            msg=f"Cloudflare does not store an empty value for these Access selector fields: {', '.join(empty)}; "
            "omit them instead",
            empty_fields=empty,
        )


def validate_tunnel_secret(module, secret):
    if secret is None:
        return

    try:
        if len(b64decode(secret, validate=True)) >= 32:
            return
    except ValueError:
        pass

    module.fail_json(msg="tunnel_secret must be base64-encoded and at least 32 bytes")


def exit_resource_list(module, result_key, items, resource_name, required_fields=("id", "name")):
    """Exit an info module with the serialized and validated items."""
    module.exit_json(changed=False, **{result_key: resource_list(module, items, resource_name, required_fields)})


def exit_settings(module, result_key, settings, resource_name):
    """Exit an info module with account-wide settings."""
    settings = serialize_resource(settings) or {}
    require_mapping(module, settings, resource_name)
    module.exit_json(changed=False, **{result_key: settings})


def ensure_settings(
    module, result_key, resource_name, current, payload, edit, comparable=None, context=None, exact_values=()
):
    """Converge settings that Cloudflare updates with PATCH semantics.

    comparable optionally maps a settings mapping to its comparable form;
    context names the settings' owner in failures. exact_values are compared
    exactly, for settings that the PATCH replaces as a whole.
    """
    comparable = comparable or (lambda settings: settings)
    label = resource_name[0].upper() + resource_name[1:]
    current = serialize_resource(current) or {}
    require_mapping(module, current, resource_name)

    if not differs(comparable(current), payload, exact_values=exact_values):
        module.exit_json(changed=False, message=f"{label} already present", **{result_key: current})

    if module.check_mode:
        module.exit_json(changed=True, message=f"{label} would be updated", **{result_key: current})

    with cloudflare_error_context(f"Cloudflare API request failed while updating {resource_name}", **(context or {})):
        settings = serialize_resource(edit(payload))

    require_mapping(module, settings, resource_name)
    require_applied(module, comparable(settings), payload, resource_name, exact_values=exact_values)
    module.exit_json(changed=True, message=f"{label} updated", **{result_key: settings})


def ensure_resource_present(
    module,
    result_key,
    resource_name,
    current,
    payload,
    create,
    update,
    expected_name=None,
    defaults=None,
    preserved_fields=(),
    exact_fields=(),
    exact_values=(),
    context=None,
    comparable=None,
):
    """Create the resource, or update it when the managed fields differ.

    The update replaces the resource, so preserved_fields omitted from payload
    are carried over from current. exact_values are compared exactly. context
    names the resource's owner in failures. comparable optionally maps a
    resource to its comparable form; the unmodified resource is returned.
    """
    comparable = comparable or (lambda resource: resource)
    context = context or {}
    label = resource_name[0].upper() + resource_name[1:]

    def checked(resource, expected_id=None):
        resource = serialize_resource(resource)
        resource_id(module, resource, resource_name, expected=expected_id)
        if expected_name is not None:
            resource_field(module, resource, "name", resource_name, expected=expected_name)

        return resource

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True, message=f"{label} would be created")

        name_context = {} if expected_name is None else {"name": expected_name}
        with cloudflare_error_context(
            f"Cloudflare API request failed while creating the {resource_name}",
            **name_context,
            **context,
        ):
            resource = checked(create(payload))

        require_applied(module, comparable(resource), payload, resource_name, defaults, exact_fields, exact_values)
        module.exit_json(changed=True, message=f"{label} created", **{result_key: resource})

    current_id = resource_id(module, current, resource_name)
    payload = {**select_fields(current, preserved_fields), **payload}
    if not differs(comparable(current), payload, defaults, exact_fields, exact_values):
        module.exit_json(
            changed=False,
            message=f"{label} already present",
            **{result_key: current},
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            message=f"{label} would be updated",
            **{result_key: current},
        )

    with cloudflare_error_context(
        f"Cloudflare API request failed while updating the {resource_name}",
        resource_id=current_id,
        **context,
    ):
        resource = checked(update(current_id, payload), expected_id=current_id)

    require_applied(module, comparable(resource), payload, resource_name, defaults, exact_fields, exact_values)
    module.exit_json(changed=True, message=f"{label} updated", **{result_key: resource})


def ensure_resource_absent(module, result_key, resource_name, current, delete, context=None):
    """Delete the resource when it exists; context names its owner in failures."""
    label = resource_name[0].upper() + resource_name[1:]
    if current is None:
        module.exit_json(changed=False, message=f"{label} already absent")

    current_id = resource_id(module, current, resource_name)
    if module.check_mode:
        module.exit_json(changed=True, message=f"{label} would be deleted", **{result_key: current})

    with cloudflare_error_context(
        f"Cloudflare API request failed while deleting the {resource_name}",
        resource_id=current_id,
        **(context or {}),
    ):
        deleted = serialize_resource(delete(current_id))

    if isinstance(deleted, dict) and "id" in deleted:
        resource_id(module, deleted, resource_name, expected=current_id)

    module.exit_json(changed=True, message=f"{label} deleted", **{result_key: current})
