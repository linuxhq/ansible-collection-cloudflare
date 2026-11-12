# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


import os
from base64 import b64decode
from contextlib import contextmanager

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


@contextmanager
def cloudflare_client(module):
    if Cloudflare is None:
        module.fail_json(
            msg=missing_required_lib("cloudflare"),
            missing_python_package="cloudflare",
        )

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

    return api_token.strip()


def error_response_body(exc):
    response = getattr(exc, "response", None)
    if response is None or not hasattr(response, "json"):
        return None

    try:
        return response.json()
    except ValueError:
        return None


def fail_from_cloudflare_error(module, message, exc, **context):
    status_code = getattr(exc, "status_code", None)
    response_body = error_response_body(exc)

    failure = {"msg": message, **context}
    if getattr(exc, "response", None) is None:
        failure["error"] = str(exc)

    if status_code is not None:
        failure["status_code"] = status_code

    if response_body is not None:
        failure["response"] = response_body

    module.fail_json(**failure)


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


def resource_field(module, resource, field, resource_name, expected=None):
    value = resource.get(field) if isinstance(resource, dict) else None
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        module.fail_json(msg=f"Cloudflare API returned malformed {resource_name} data")

    if expected is not None and value != expected:
        module.fail_json(msg=f"Cloudflare API returned the wrong {resource_name}")

    return value


def resource_id(module, resource, resource_name, expected=None):
    return resource_field(module, resource, "id", resource_name, expected=expected)


def require_mapping(module, value, resource_name):
    if not isinstance(value, dict):
        module.fail_json(msg=f"Cloudflare API returned malformed {resource_name} data")


def resource_list(module, items, resource_name, required_fields=("id",)):
    """Serialize every item of an SDK list, validating its required fields."""
    resources = [serialize_resource(item) for item in items]
    for resource in resources:
        for field in required_fields:
            resource_field(module, resource, field, resource_name)

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
    an arbitrary resource.
    """
    matches = []
    for item in items:
        resource = serialize_resource(item)
        if resource_field(module, resource, field, resource_name) == value:
            matches.append(resource)

    if len(matches) > 1:
        module.fail_json(
            msg=f"Found more than one {resource_name} with {field} {value!r}",
            **{field: value},
            matching_ids=[resource_id(module, resource, resource_name) for resource in matches],
        )

    return matches[0] if matches else None


def payload_from_params(params, fields):
    return {field: params[field] for field in fields if params.get(field) is not None}


def select_fields(value, fields):
    value = serialize_resource(value) or {}
    return {field: value[field] for field in fields if field in value}


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


def differs(current, desired, defaults=None, exact_fields=()):
    """Return whether current differs from desired on the desired fields only.

    Fields the API omits are filled from defaults before comparing. Mappings
    under exact_fields are compared on their complete key sets.
    """
    if not desired:
        return False

    current = {**(defaults or {}), **(serialize_resource(current) or {})}
    return values_differ(normalize_current_by_desired_fields(current, desired, exact_fields), desired)


def require_applied(module, resource, desired, resource_name, defaults=None, exact_fields=()):
    require_mapping(module, resource, resource_name)
    if differs(resource, desired, defaults, exact_fields):
        module.fail_json(msg=f"Cloudflare did not apply the requested {resource_name}")


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


def ensure_settings(module, result_key, resource_name, current, payload, edit, comparable=None, context=None):
    """Converge settings that Cloudflare updates with PATCH semantics.

    comparable optionally maps a settings mapping to its comparable form;
    context names the settings' owner in failures.
    """
    comparable = comparable or (lambda settings: settings)
    label = resource_name[0].upper() + resource_name[1:]
    current = serialize_resource(current) or {}
    require_mapping(module, current, resource_name)

    if not differs(comparable(current), payload):
        module.exit_json(changed=False, message=f"{label} already present", **{result_key: current})

    if module.check_mode:
        module.exit_json(changed=True, message=f"{label} would be updated", **{result_key: current})

    with cloudflare_error_context(f"Cloudflare API request failed while updating {resource_name}", **(context or {})):
        settings = serialize_resource(edit(payload))

    require_mapping(module, settings, resource_name)
    require_applied(module, comparable(settings), payload, resource_name)
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
    context=None,
):
    """Create the resource, or update it when the managed fields differ.

    The update replaces the resource, so preserved_fields omitted from payload
    are carried over from current. context names the resource's owner in failures.
    """
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

        require_applied(module, resource, payload, resource_name, defaults, exact_fields)
        module.exit_json(changed=True, message=f"{label} created", **{result_key: resource})

    current_id = resource_id(module, current, resource_name)
    payload = {**select_fields(current, preserved_fields), **payload}
    if not differs(current, payload, defaults, exact_fields):
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

    require_applied(module, resource, payload, resource_name, defaults, exact_fields)
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
