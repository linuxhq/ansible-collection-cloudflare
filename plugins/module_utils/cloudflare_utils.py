# Copyright: (c) 2026, Taylor Kimball
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from contextlib import contextmanager

from ansible.module_utils.basic import missing_required_lib
from ansible.module_utils.common.dict_transformations import recursive_diff

try:
    import cloudflare
    from cloudflare import Cloudflare
except ImportError:
    cloudflare = None
    Cloudflare = None


def api_request(client, method, path, body=None, ok_statuses=None):
    ok_statuses = ok_statuses or []
    request = getattr(client, method)

    try:
        if method in ("post", "put", "patch", "delete"):
            return request(path, cast_to=object, body=body)
        return request(path, cast_to=object)
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

    try:
        with Cloudflare(api_token=module.params["api_token"]) as client:
            yield client
    except cloudflare.APIConnectionError as exc:
        fail_from_cloudflare_error(
            module,
            getattr(exc, "_cloudflare_message", "Cloudflare API connection failed"),
            exc,
            **getattr(exc, "_cloudflare_context", {})
        )
    except cloudflare.APIStatusError as exc:
        fail_from_cloudflare_error(
            module,
            getattr(exc, "_cloudflare_message", "Cloudflare API request failed"),
            exc,
            **getattr(exc, "_cloudflare_context", {})
        )


def delete_result(client, path):
    return response_result(api_request(client, "delete", path))


def fail_from_cloudflare_error(module, message, exc, **context):
    response = getattr(exc, "response", None)
    status_code = getattr(exc, "status_code", None)
    response_body = None

    if response is not None:
        if hasattr(response, "json"):
            try:
                response_body = response.json()
            except Exception:
                response_body = None
        if response_body is None and hasattr(response, "text"):
            response_body = response.text

    module.fail_json(
        msg=message,
        error=str(exc),
        status_code=status_code,
        response=response_body,
        **context
    )


def find_by_field(client, path, field, value):
    result = response_result(api_request(client, "get", path), default=[])
    if isinstance(result, dict):
        result = result.get("result", [])

    for item in result:
        if isinstance(item, dict) and item.get(field) == value:
            return item

    return None


def get_result(client, path, default=None, ok_statuses=None):
    return response_result(
        api_request(client, "get", path, ok_statuses=ok_statuses),
        default=default,
    )


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


def put_result(client, path, body):
    return response_result(api_request(client, "put", path, body=body))


def response_result(response, default=None):
    response = serialize_resource(response)

    if isinstance(response, dict) and "result" in response:
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
