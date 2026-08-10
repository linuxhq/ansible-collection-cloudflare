# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from contextlib import contextmanager
from urllib.parse import quote, urlencode

from ansible.module_utils.basic import missing_required_lib
from ansible.module_utils.common.dict_transformations import recursive_diff

try:
    import cloudflare
    from cloudflare import Cloudflare
except ImportError:
    cloudflare = None
    Cloudflare = None

SENSITIVE_KEY_PARTS = (
    "api_key",
    "api_token",
    "authorization",
    "password",
    "secret",
    "token",
)


class CloudflareResponseError(Exception):
    pass


def api_request(client, method, path, body=None, ok_statuses=None, timeout=None):
    ok_statuses = ok_statuses or []
    request = getattr(client, method)
    options = {"timeout": timeout, "max_retries": 0} if timeout is not None else {}

    try:
        if method in ("post", "put", "patch", "delete"):
            return request(path, cast_to=object, body=body, options=options)
        return request(path, cast_to=object, options=options)
    except cloudflare.APIStatusError as exc:
        if getattr(exc, "status_code", None) in ok_statuses:
            return None
        raise


@contextmanager
def cloudflare_client(module):
    if Cloudflare is None:
        module.fail_json(
            msg=missing_required_lib("cloudflare"),
            missing_python_package="cloudflare",
        )

    api_token = module.params.get("api_token")
    if not isinstance(api_token, str) or not api_token.strip():
        module.fail_json(msg="api_token must not be empty")
    if any(ord(character) < 32 or ord(character) == 127 for character in api_token):
        module.fail_json(msg="api_token must not contain control characters")

    for name, value in module.params.items():
        if (name in {"name", "phase"} or name.endswith("_id")) and isinstance(
            value, str
        ):
            if not value.strip():
                module.fail_json(msg=f"{name} must not be empty")
            if value != value.strip():
                module.fail_json(
                    msg=f"{name} must not contain leading or trailing whitespace"
                )

    try:
        with Cloudflare(api_token=api_token.strip()) as client:
            yield client
    except cloudflare.APIConnectionError as exc:
        fail_from_cloudflare_error(
            module,
            getattr(exc, "_cloudflare_message", "Cloudflare API connection failed"),
            exc,
            **getattr(exc, "_cloudflare_context", {}),
        )
    except cloudflare.APIStatusError as exc:
        fail_from_cloudflare_error(
            module,
            getattr(exc, "_cloudflare_message", "Cloudflare API request failed"),
            exc,
            **getattr(exc, "_cloudflare_context", {}),
        )
    except cloudflare.APIError as exc:
        fail_from_cloudflare_error(
            module,
            getattr(exc, "_cloudflare_message", "Cloudflare API error"),
            exc,
            **getattr(exc, "_cloudflare_context", {}),
        )
    except CloudflareResponseError as exc:
        module.fail_json(msg=str(exc))


def delete_result(client, path):
    return response_result(api_request(client, "delete", path))


def fail_from_cloudflare_error(module, message, exc, **context):
    response = getattr(exc, "response", None)
    status_code = getattr(exc, "status_code", None)
    response_body = None

    if response is not None and hasattr(response, "json"):
        try:
            response_body = response.json()
        except ValueError:
            response_body = None

    failure = {"msg": message, **redact_sensitive_values(context)}
    if response is None:
        failure["error"] = str(exc)
    if status_code is not None:
        failure["status_code"] = status_code
    if response_body is not None:
        failure["response"] = redact_sensitive_values(response_body)

    module.fail_json(**failure)


def cloudflare_path(*segments):
    return "/" + "/".join(quote(str(segment), safe="") for segment in segments)


def cloudflare_query(path, values):
    query = urlencode(
        [(key, value) for key, value in values.items() if value is not None]
    )
    if not query:
        return path
    return f"{path}{'&' if '?' in path else '?'}{query}"


def find_by_field(client, path, field, value, paginate=True):
    for item in iter_items(client, path, paginate=paginate):
        if not isinstance(item, dict):
            raise CloudflareResponseError(
                "Cloudflare API returned malformed resource data"
            )
        item_value = item.get(field)
        if item_value is None or (
            isinstance(item_value, str)
            and (not item_value.strip() or item_value != item_value.strip())
        ):
            raise CloudflareResponseError(
                "Cloudflare API returned malformed resource data"
            )
        if item_value == value:
            return item

    return None


def find_by_name(client, path, name, extra_query=None, paginate=True):
    return find_by_field(
        client,
        cloudflare_query(path, {**(extra_query or {}), "name": name}),
        "name",
        name,
        paginate=paginate,
    )


def get_result(client, path, default=None, ok_statuses=None, timeout=None):
    return response_result(
        api_request(client, "get", path, ok_statuses=ok_statuses, timeout=timeout),
        default=default,
    )


def iter_items(client, path, per_page=50, paginate=True):
    if not paginate:
        response = serialize_resource(api_request(client, "get", path))
        yield from parse_list_response(response)[0]
        return

    fetched = 0
    page = 1

    while True:
        result, result_info = parse_list_response(
            serialize_resource(
                api_request(
                    client,
                    "get",
                    cloudflare_query(path, {"page": page, "per_page": per_page}),
                )
            )
        )

        yield from result

        fetched += len(result)

        if not result_info or not result:
            return

        total_pages = result_info.get("total_pages")
        total_count = result_info.get("total_count")
        if total_pages is not None:
            if isinstance(total_pages, bool) or not isinstance(total_pages, int):
                raise CloudflareResponseError(
                    "Cloudflare API returned malformed pagination data"
                )
            if page >= total_pages:
                return
        elif total_count is not None:
            if isinstance(total_count, bool) or not isinstance(total_count, int):
                raise CloudflareResponseError(
                    "Cloudflare API returned malformed pagination data"
                )
            if fetched >= total_count:
                return
        elif len(result) < per_page:
            return

        page += 1


def list_all(client, path, per_page=50, paginate=True):
    return list(iter_items(client, path, per_page=per_page, paginate=paginate))


def normalize_current_by_desired_fields(current, desired):
    if isinstance(current, dict) and isinstance(desired, dict):
        if not desired:
            return current
        return {
            key: normalize_current_by_desired_fields(current.get(key), value)
            for key, value in desired.items()
        }

    if isinstance(current, list) and isinstance(desired, list):
        if len(current) != len(desired):
            return current
        return [
            normalize_current_by_desired_fields(current_item, desired_item)
            for current_item, desired_item in zip(current, desired)
        ]

    return current


def parse_list_response(response):
    if isinstance(response, dict) and ("result" in response or "success" in response):
        if response.get("success") is False:
            raise CloudflareResponseError(
                "Cloudflare API returned an unsuccessful response"
            )
        result = response.get("result")
        result_info = response.get("result_info")
        if result is None:
            result = []
        if result_info is None:
            result_info = {}
    else:
        result = [] if response is None else response
        result_info = {}

    if not isinstance(result, list) or not isinstance(result_info, dict):
        raise CloudflareResponseError("Cloudflare API returned malformed list data")

    return result, result_info


def patch_result(client, path, body):
    return response_result(api_request(client, "patch", path, body=body))


def payload_from_params(params, fields, defaults=None):
    defaults = defaults or {}
    payload = {}

    for field in fields:
        value = params.get(field, defaults.get(field))
        if value is not None:
            payload[field] = value

    return payload


def post_result(client, path, body):
    return response_result(api_request(client, "post", path, body=body))


def put_result(client, path, body, timeout=None):
    return response_result(api_request(client, "put", path, body=body, timeout=timeout))


def redact_scim_secrets(resource):
    if not isinstance(resource, dict):
        return resource

    scim_config = resource.get("scim_config")
    if not isinstance(scim_config, dict):
        return resource

    authentication = scim_config.get("authentication")
    entries = authentication if isinstance(authentication, list) else [authentication]
    for entry in entries:
        if isinstance(entry, dict):
            for field in ("client_secret", "password", "token"):
                entry.pop(field, None)

    return resource


def redact_sensitive_values(value):
    if isinstance(value, dict):
        return {
            key: (
                "********"
                if any(part in str(key).lower() for part in SENSITIVE_KEY_PARTS)
                else redact_sensitive_values(item)
            )
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [redact_sensitive_values(item) for item in value]

    return value


def resource_field(module, resource, field, resource_name):
    value = resource.get(field) if isinstance(resource, dict) else None
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        module.fail_json(
            msg=f"Cloudflare API returned malformed {resource_name} data",
        )
    return value


def resource_id(module, resource, resource_name):
    return resource_field(module, resource, "id", resource_name)


def require_mapping(module, value, resource_name):
    if not isinstance(value, dict):
        module.fail_json(msg=f"Cloudflare API returned malformed {resource_name} data")
    return value


def validate_resource_fields(module, resources, field, resource_name):
    for resource in resources:
        resource_field(module, resource, field, resource_name)
    return resources


def response_result(response, default=None):
    response = serialize_resource(response)

    if isinstance(response, dict) and ("result" in response or "success" in response):
        if response.get("success") is False:
            raise CloudflareResponseError(
                "Cloudflare API returned an unsuccessful response"
            )
        result = response.get("result")
        if result is None:
            return default
        return result

    if response is None:
        return default

    return response


def select_fields(value, fields):
    value = serialize_resource(value) or {}
    return {field: value.get(field) for field in fields if field in value}


def serialize_resource(resource):
    if resource is None:
        return None

    if hasattr(resource, "to_dict"):
        return serialize_resource(resource.to_dict())

    if isinstance(resource, dict):
        return {
            key: serialize_resource(value)
            for key, value in resource.items()
            if value is not None
        }

    if isinstance(resource, (list, tuple)):
        return [serialize_resource(value) for value in resource]

    return resource


def values_differ(current, desired):
    current = serialize_resource(current)
    desired = serialize_resource(desired)
    if not isinstance(current, dict) or not isinstance(desired, dict):
        return current != desired

    return recursive_diff(current, desired) is not None
