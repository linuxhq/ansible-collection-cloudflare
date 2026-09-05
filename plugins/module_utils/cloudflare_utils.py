# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


from base64 import b64decode
from contextlib import contextmanager
from copy import deepcopy
from urllib.parse import quote, urlencode

from ansible.module_utils.basic import missing_required_lib
from ansible.module_utils.common.dict_transformations import recursive_diff

try:
    import cloudflare
    from cloudflare import BaseModel, Cloudflare
except ImportError:
    cloudflare = None
    BaseModel = None
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


@contextmanager
def cloudflare_error_context(message, **context):
    api_error = getattr(cloudflare, "APIError", ())
    try:
        yield
    except api_error as exc:
        exc._cloudflare_message = message
        exc._cloudflare_context = context
        raise


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

        exc._cloudflare_message = f"Cloudflare API {method.upper()} request failed"
        exc._cloudflare_context = {"method": method.upper(), "path": path}
        raise
    except cloudflare.APIError as exc:
        exc._cloudflare_message = f"Cloudflare API {method.upper()} request failed"
        exc._cloudflare_context = {"method": method.upper(), "path": path}
        raise


@contextmanager
def cloudflare_client(module):
    if Cloudflare is None:
        module.fail_json(
            msg=missing_required_lib("cloudflare"),
            missing_python_package="cloudflare",
        )

    api_token = validate_cloudflare_params(module)

    try:
        with Cloudflare(api_token=api_token) as client:
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


def delete_result(client, path, expected_id=None):
    result = response_result(api_request(client, "delete", path))
    if expected_id is not None and (not isinstance(result, dict) or result.get("id") != expected_id):
        raise CloudflareResponseError("Cloudflare API returned the wrong deleted resource")

    return result


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
    query = urlencode([(key, value) for key, value in values.items() if value is not None])
    if not query:
        return path

    return f"{path}{'&' if '?' in path else '?'}{query}"


def find_by_field(client, path, field, value, paginate=True):
    for item in iter_items(client, path, paginate=paginate):
        if not isinstance(item, dict):
            raise CloudflareResponseError("Cloudflare API returned malformed resource data")

        item_value = item.get(field)
        if (
            item_value is None
            or isinstance(value, str)
            and (not isinstance(item_value, str) or not item_value.strip() or item_value != item_value.strip())
        ):
            raise CloudflareResponseError("Cloudflare API returned malformed resource data")

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

        fetched += len(result)
        for field in ("page", "count", "total_pages", "total_count"):
            value = result_info.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise CloudflareResponseError("Cloudflare API returned malformed pagination data")

        total_pages = result_info.get("total_pages")
        total_count = result_info.get("total_count")
        if result_info.get("page", page) != page or result_info.get("count", len(result)) != len(result):
            raise CloudflareResponseError("Cloudflare API returned malformed pagination data")

        if (
            result
            and (total_pages is not None and page > total_pages or total_count is not None and fetched > total_count)
        ) or (
            not result
            and (total_pages is not None and page < total_pages or total_count is not None and fetched < total_count)
        ):
            raise CloudflareResponseError("Cloudflare API returned malformed pagination data")

        yield from result

        if not result:
            return

        if total_pages is not None and page >= total_pages:
            if total_count is not None and fetched < total_count:
                raise CloudflareResponseError("Cloudflare API returned malformed pagination data")

            return

        if total_pages is None and total_count is not None and fetched >= total_count:
            return

        if total_pages is None and total_count is None and len(result) < per_page:
            return

        page += 1


def list_all(client, path, per_page=50, paginate=True):
    return list(iter_items(client, path, per_page=per_page, paginate=paginate))


def normalize_current_by_desired_fields(current, desired):
    if isinstance(current, dict) and isinstance(desired, dict):
        if not desired:
            return current

        return {key: normalize_current_by_desired_fields(current.get(key), value) for key, value in desired.items()}

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
        if "success" in response and not isinstance(response["success"], bool):
            raise CloudflareResponseError("Cloudflare API returned malformed list data")

        if response.get("success") is False:
            raise CloudflareResponseError("Cloudflare API returned an unsuccessful response")

        if "result" not in response:
            raise CloudflareResponseError("Cloudflare API returned malformed list data")

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


def payload_from_params(params, fields):
    payload = {}

    for field in fields:
        value = params.get(field)
        if value is not None:
            payload[field] = value

    return payload


def post_result(client, path, body):
    return response_result(api_request(client, "post", path, body=body))


def put_result(client, path, body, timeout=None):
    return response_result(api_request(client, "put", path, body=body, timeout=timeout))


def remove_fields(value, fields):
    if isinstance(value, dict):
        for field in fields:
            value.pop(field, None)

        for item in value.values():
            remove_fields(item, fields)
    elif isinstance(value, list):
        for item in value:
            remove_fields(item, fields)


def redact_access_app_secrets(resource):
    if isinstance(resource, dict):
        remove_fields(resource, ("client_secret", "password", "token"))

    return resource


def redact_pages_secrets(resource):
    redacted = deepcopy(resource)

    def redact(value):
        if isinstance(value, dict):
            value.pop("web_analytics_token", None)
            if value.get("type") == "secret_text":
                value.pop("value", None)

            for item in value.values():
                redact(item)
        elif isinstance(value, list):
            for item in value:
                redact(item)

    redact(redacted)

    return redacted


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


def resource_field(module, resource, field, resource_name, expected=None):
    value = resource.get(field) if isinstance(resource, dict) else None
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        module.fail_json(
            msg=f"Cloudflare API returned malformed {resource_name} data",
        )

    if expected is not None and value != expected:
        module.fail_json(msg=f"Cloudflare API returned the wrong {resource_name}")

    return value


def resource_id(module, resource, resource_name, expected=None):
    return resource_field(module, resource, "id", resource_name, expected=expected)


def require_mapping(module, value, resource_name):
    if not isinstance(value, dict):
        module.fail_json(msg=f"Cloudflare API returned malformed {resource_name} data")


def validate_resource_fields(module, resources, field, resource_name):
    fields = (field,) if isinstance(field, str) else field
    for resource in resources:
        for required_field in fields:
            resource_field(module, resource, required_field, resource_name)


def validate_requested_values(module, resource, desired, resource_name):
    require_mapping(module, resource, resource_name)
    if values_differ(
        normalize_current_by_desired_fields(resource, desired),
        desired,
    ):
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


def response_result(response, default=None):
    null_result = isinstance(response, dict) and "result" in response and response["result"] is None
    response = serialize_resource(response)
    if null_result:
        response["result"] = None

    if isinstance(response, dict) and ("result" in response or "success" in response):
        if "success" in response and not isinstance(response["success"], bool):
            raise CloudflareResponseError("Cloudflare API returned malformed data")

        if response.get("success") is False:
            raise CloudflareResponseError("Cloudflare API returned an unsuccessful response")

        if "result" not in response:
            raise CloudflareResponseError("Cloudflare API returned malformed data")

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

    if BaseModel is not None and isinstance(resource, BaseModel):
        return serialize_resource(resource.to_dict(mode="json"))

    if hasattr(resource, "to_dict"):
        return serialize_resource(resource.to_dict())

    if isinstance(resource, dict):
        return {key: serialize_resource(value) for key, value in resource.items() if value is not None}

    if isinstance(resource, (list, tuple)):
        return [serialize_resource(value) for value in resource]

    return resource


def values_differ(current, desired):
    current = serialize_resource(current)
    desired = serialize_resource(desired)
    if not isinstance(current, dict) or not isinstance(desired, dict):
        return current != desired

    return recursive_diff(current, desired) is not None
