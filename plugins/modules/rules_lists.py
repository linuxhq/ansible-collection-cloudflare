#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)


DOCUMENTATION = r"""
---
module: rules_lists
short_description: Manage Cloudflare Rules Lists
description:
  - Create, update, populate, and delete Cloudflare Rules lists by name.
  - Item updates wait for the resulting bulk operation to complete and fail when
    Cloudflare reports the operation failed.
  - When this run creates the Rules list and Cloudflare then rejects its items,
    or the item operation fails or times out, the module fails and the new list
    remains without the requested items. The next run finds the list by name and
    applies the items.
version_added: '2.0.0'
author:
  - Taylor Kimball (@tkimball83)
notes:
  - Cloudflare may store a requested value in a canonical form that differs from the request. The module then
    fails after the write, naming the requested and stored value of each differing field in the message and in
    C(differences), so the stored form can be requested instead.
extends_documentation_fragment:
  - linuxhq.cloudflare.cloudflare
  - linuxhq.cloudflare.cloudflare.account
  - linuxhq.cloudflare.cloudflare.create
options:
  name:
    required: true
    type: str
    description:
      - Rules list name.
  kind:
    type: str
    choices:
      - ip
      - redirect
      - hostname
      - asn
    description:
      - Data type stored by the Rules list.
      - Required when creating a Rules list.
      - Existing list kinds cannot be changed.
  description:
    type: str
    description:
      - Human-readable purpose of the Rules list.
      - Defaults to O(name) when creating a Rules list; an existing list's
        description is preserved when omitted.
      - V("") clears the description; Cloudflare then omits it from the list.
  elements:
    type: list
    elements: dict
    description:
      - Complete set of entries that the Rules list must contain.
      - Each entry must set the field named by the list kind, such as C(ip) or
        C(hostname), and may also set C(comment). Any other key must be null,
        or one of C(id), C(created_on), and C(modified_on), which are not sent.
      - A C(comment) must be a string of at most 500 characters.
      - A C(hostname) entry must be a mapping with a non-empty string
        C(url_hostname).
      - A C(redirect) entry must be a mapping with non-empty strings
        C(source_url) and C(target_url).
      - A C(hostname) entry accepts only C(url_hostname) and
        C(exclude_exact_hostname). A C(redirect) entry accepts only
        C(source_url), C(target_url), C(include_subdomains),
        C(preserve_path_suffix), C(preserve_query_string), C(status_code), and
        C(subpath_matching). C(exclude_exact_hostname), C(include_subdomains),
        C(preserve_path_suffix), C(preserve_query_string), and
        C(subpath_matching) must be V(true) or V(false). A field set to null
        is not sent.
      - These checks run before any change, because Cloudflare rejects such
        entries only after the list and its description are written.
      - An C(ip) entry must be an IP address, or a CIDR with a prefix length of
        8 to 32 for IPv4 or 12 to 128 for IPv6 and no host bits set.
        IPv4-mapped IPv6 addresses and scoped IPv6 addresses such as
        C(fe80::1%eth0) are not supported.
      - A C(/32) IPv4 or C(/128) IPv6 entry is the same as the bare address,
        which is how Cloudflare stores it, and a prefix length with leading
        zeros such as C(/08) is the same as C(/8).
      - A C(hostname.url_hostname) entry may contain only ASCII letters,
        digits, C(.), C(-), C(_), and a C(*) wildcard, so it must not include a
        scheme, a path, or a port. Write internationalized names in their
        C(xn--) form.
      - A C(hostname.url_hostname) entry may use a C(*) wildcard only as a
        single leading C(*.) label.
      - Each other label of a C(hostname.url_hostname) entry must have 1 to 63
        characters and must not start or end with C(-), so C(a..example.com),
        C(.example.com), C(-a.example.com), C(a-.example.com), and a bare
        C(*.) are not supported. A single trailing C(.) is accepted.
      - A C(hostname.url_hostname) entry must have at most 253 characters, not
        counting a leading C(*.) or a single trailing C(.).
      - C(hostname.exclude_exact_hostname=false) may be set only when
        C(hostname.url_hostname) is a wildcard such as C(*.example.com).
      - An C(asn) entry must be an integer from 1 to 4294967295.
      - Entries must not repeat a value of the list kind field, such as the same
        C(ip) with different C(comment) values; identical entries are merged.
      - C(hostname) entries must not repeat a C(hostname.url_hostname), and
        C(redirect) entries must not repeat a C(redirect.source_url), even when
        their other fields differ.
      - Write C(redirect.source_url) as Cloudflare stores it, such as
        C(example.com/) rather than C(example.com); values are compared exactly
        as written. When Cloudflare stores a different form, the module fails
        and its message names each requested value next to the stored one.
      - C(hostname) entries must not include both a wildcard such as
        C(*.example.com) and its exact hostname C(example.com), whatever the
        value of C(exclude_exact_hostname); Cloudflare treats them as
        duplicates.
      - A C(redirect.source_url) must not include a query string such as
        C(?x=1), a fragment such as C(#top), userinfo such as C(user@), or a port
        such as C(:8080), and may use only the C(http) or C(https) scheme,
        followed by C(://), so C(http:example.com) and C(example.com:/) are
        not supported. It must have a host, so C(/a) and C(https:///a) are not
        supported, and its host must not be an IPv6 address, because Cloudflare
        stores C([2001:db8::1]/) without its brackets, a form it rejects.
      - A C(redirect.source_url) or C(redirect.target_url) may use C(%) only
        in a percent-escape of two hexadecimal digits, such as C(%20), so
        C(example.com/%zz) is not supported.
      - A C(redirect.source_url) must not contain C(%3F), C(%23), or C(%25), in
        any case, because Cloudflare decodes them to C(?), C(#), and C(%),
        which it then rejects.
      - A C(redirect.target_url) must start with a scheme, such as
        C(https://example.com/path); C(example.com/path), C(/path), and
        C(//example.com/path) are not supported. Its authority must not contain
        whitespace, and its port, when set, must contain only digits, so
        C(https://example.com:abc/) is not supported. It must not start with
        whitespace or contain an ASCII control character, such as a tab or
        newline, anywhere.
      - A C(redirect.status_code), when set, must be the integer 301, 302,
        307, or 308.
  operation_timeout:
    type: int
    default: 240
    description:
      - Maximum seconds to wait for the bulk item operation to complete, including
        retrying submission while another bulk operation is pending on the account.
      - Each submission and polling request is made as a single attempt whose
        timeout is the remaining budget, and the module retries only while budget
        remains, so polling sleeps never extend past it.
      - The budget bounds each request's timeout rather than enforcing a hard
        wall-clock limit, so a single slow request can briefly exceed it.
      - Must be at least 1 second.
      - When executed asynchronously, the async budget must exceed this value.
  state:
    type: str
    choices:
      - present
      - absent
    default: present
    description:
      - Desired state of the resource.
"""

EXAMPLES = r"""
- name: Ensure Rules list exists
  linuxhq.cloudflare.rules_lists:
    account_id: "{{ account_id }}"
    api_token: "{{ cloudflare_api_token }}"
    name: uptime_robot
    kind: ip
    elements:
      - ip: 1.2.3.4
"""

RETURN = r"""
---
rules_list:
  description: Cloudflare Rules list.
  returned: when available
  type: dict
  contains:
    id:
      description: Rules list identifier.
      returned: always
      type: str
    name:
      description: Rules list name.
      returned: always
      type: str
    kind:
      description: Data type stored by the Rules list.
      returned: always
      type: str
    num_items:
      description: Number of entries in the Rules list.
      returned: when available
      type: float
items_operation:
  description: Bulk operation returned when list items were updated.
  returned: when list items changed
  type: dict
  contains:
    id:
      description: Bulk operation identifier.
      returned: always
      type: str
    status:
      description: Final bulk operation status.
      returned: always
      type: str
differences:
  description: Each Rules list field that Cloudflare stored differently from the request.
  returned: when Cloudflare did not apply the requested Rules list fields
  type: list
  elements: dict
  contains:
    field:
      description: Name of the field.
      returned: always
      type: str
    requested:
      description: Requested value of the field.
      returned: always
      type: raw
    stored:
      description: Value Cloudflare stored for the field.
      returned: always
      type: raw
missing_items:
  description: Requested items that Cloudflare did not store.
  returned: when Cloudflare did not apply the requested items
  type: list
  elements: dict
unexpected_items:
  description: Stored items that were not requested, such as the form Cloudflare stored a requested item in.
  returned: when Cloudflare did not apply the requested items
  type: list
  elements: dict
message:
  returned: always
  type: str
  description:
  - Operation summary.

"""

import json
import re
import string
import time
from difflib import SequenceMatcher
from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.cloudflare.plugins.module_utils.cloudflare_utils import (
    cloudflare,
    cloudflare_client,
    cloudflare_error_context,
    create_once,
    ensure_resource_absent,
    find_resource,
    matching_resources,
    require_applied,
    require_mapping,
    resource_field,
    resource_id,
    serialize_resource,
    unsupported_fields,
    valid_dns_labels,
    values_differ,
    without_retries,
)

ITEMS_PER_PAGE = 500
OPERATION_POLL_SECONDS = 2

# Missing items the failure message pairs with a stored value; the rest are
# only returned in missing_items and unexpected_items.
MESSAGE_ITEMS = 10

ITEM_META_FIELDS = (
    "created_on",
    "id",
    "modified_on",
)

# Prefix lengths Cloudflare accepts in IP lists, by IP version:
# https://developers.cloudflare.com/waf/tools/lists/custom-lists/
IP_PREFIX_LENGTHS = {4: range(8, 33), 6: range(12, 129)}

# Field that identifies an item of each mapping-valued list kind; Cloudflare
# rejects two items with the same value even when their other fields differ.
IDENTITY_FIELDS = {
    "hostname": "url_hostname",
    "redirect": "source_url",
}

SOURCE_URL_SCHEMES = ("http", "https")
# A "%" not followed by two hexadecimal digits, which Cloudflare rejects in a
# redirect URL.
INVALID_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")
# Percent-escapes of "?", "#", and "%", which Cloudflare decodes in a redirect
# source URL and then rejects, so the stored form could never be requested.
DECODED_REJECTED_ESCAPE = re.compile(r"%(?:3F|23|25)", re.IGNORECASE)

# Characters the SDK documents for a hostname url_hostname (ASCII letters,
# digits, '*', and '-'), plus '.', '_', and uppercase letters, which
# Cloudflare also accepts.
HOSTNAME_CHARACTERS = frozenset(string.ascii_letters + string.digits + "*-._")

# Fields the SDK item models require inside each mapping-valued list kind.
REQUIRED_STRING_FIELDS = {
    "hostname": ("url_hostname",),
    "redirect": ("source_url", "target_url"),
}

# The SDK documents asn as a non-negative 32-bit integer.
MAX_ASN = 4294967295

REDIRECT_STATUS_CODES = (301, 302, 307, 308)

# Fields of the SDK HostnameParam and RedirectParam types, and those typed as
# booleans; Cloudflare rejects any other field or a non-boolean flag.
ITEM_VALUE_FIELDS = {
    "hostname": ("exclude_exact_hostname", "url_hostname"),
    "redirect": (
        "include_subdomains",
        "preserve_path_suffix",
        "preserve_query_string",
        "source_url",
        "status_code",
        "subpath_matching",
        "target_url",
    ),
}
BOOLEAN_ITEM_FIELDS = {
    "hostname": ("exclude_exact_hostname",),
    "redirect": ("include_subdomains", "preserve_path_suffix", "preserve_query_string", "subpath_matching"),
}

# Longest item comment Cloudflare accepts.
MAX_COMMENT_LENGTH = 500

# Cloudflare omits an empty list description.
LIST_DEFAULTS = {"description": ""}

REDIRECT_DEFAULTS = {
    "include_subdomains": False,
    "preserve_path_suffix": True,
    "preserve_query_string": False,
    "status_code": 301,
    "subpath_matching": False,
}


def canonical_ip(value):
    # Cloudflare stores addresses in canonical form, such as compressed IPv6,
    # and stores a full-length prefix, such as /32, as the bare address.
    address, separator, prefix = value.partition("/")
    try:
        parsed = ip_address(address)
    except ValueError:
        return value

    if prefix.isascii() and prefix.isdigit() and int(prefix) == parsed.max_prefixlen:
        return str(parsed)

    if prefix.isascii() and prefix.isdigit():
        prefix = str(int(prefix))

    return f"{parsed}{separator}{prefix}"


def canonical_item(item):
    return json.dumps(item, sort_keys=True, separators=(",", ":"))


def list_items(module, client, account_id, list_id):
    with cloudflare_error_context(
        "Cloudflare API request failed while gathering Rules list items",
        account_id=account_id,
        rules_list_id=list_id,
    ):
        items = [
            serialize_resource(item)
            for item in client.rules.lists.items.list(
                list_id,
                account_id=account_id,
                per_page=ITEMS_PER_PAGE,
            )
        ]

    for item in items:
        require_mapping(module, item, "Rules list item")

    return items


def pending_operation_error(exc):
    if getattr(exc, "status_code", None) not in (400, 409, 429):
        return False

    return "operation" in f"{exc} {getattr(exc, 'body', '')}".lower()


def transient_error(exc):
    if isinstance(exc, cloudflare.APIConnectionError):
        return True

    status_code = getattr(exc, "status_code", None)
    return status_code == 429 or (isinstance(status_code, int) and status_code >= 500)


def submit_items(module, client, account_id, list_id, items, deadline):
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            module.fail_json(msg="Timed out submitting the Rules list items operation", rules_list_id=list_id)

        try:
            with cloudflare_error_context(
                "Cloudflare API request failed while submitting the Rules list items",
                account_id=account_id,
                rules_list_id=list_id,
            ):
                operation = client.with_options(timeout=remaining, max_retries=0).rules.lists.items.update(
                    list_id,
                    account_id=account_id,
                    body=items,
                )
        except (cloudflare.APIConnectionError, cloudflare.APIStatusError) as exc:
            if (
                not (pending_operation_error(exc) or transient_error(exc))
                or deadline - time.monotonic() < OPERATION_POLL_SECONDS + 1
            ):
                raise

            time.sleep(OPERATION_POLL_SECONDS)
            continue

        # Cloudflare accepted the operation, so a response received after the
        # deadline is reported by wait_for_operation with its operation id.
        return serialize_resource(operation)


def wait_for_operation(module, client, account_id, operation, deadline):
    operation_id = None
    if isinstance(operation, dict):
        operation_id = operation.get("operation_id") or operation.get("id")

    if not isinstance(operation_id, str) or not operation_id.strip() or operation_id != operation_id.strip():
        module.fail_json(
            msg="Rules list items submission did not return an operation id",
            operation=operation,
        )

    status = {}
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            module.fail_json(
                msg="Timed out waiting for the Rules list items operation to complete",
                operation_id=operation_id,
                operation=status,
            )

        try:
            with cloudflare_error_context(
                "Cloudflare API request failed while waiting for the Rules list items operation",
                account_id=account_id,
                operation_id=operation_id,
            ):
                status = serialize_resource(
                    client.with_options(timeout=remaining, max_retries=0).rules.lists.bulk_operations.get(
                        operation_id,
                        account_id=account_id,
                    )
                )
        except (cloudflare.APIConnectionError, cloudflare.APIStatusError) as exc:
            if not transient_error(exc) or deadline - time.monotonic() <= 0:
                raise

            status = {}
            time.sleep(min(OPERATION_POLL_SECONDS, max(deadline - time.monotonic(), 0)))
            continue

        if not isinstance(status, dict) or not isinstance(status.get("status"), str):
            module.fail_json(
                msg="Cloudflare API returned malformed Rules list operation data",
                operation_id=operation_id,
            )

        if status.get("id") != operation_id:
            module.fail_json(
                msg="Cloudflare API returned the wrong Rules list operation",
                operation_id=operation_id,
                operation=status,
            )

        operation_status = status["status"]
        if operation_status == "completed":
            return status

        if operation_status == "failed":
            module.fail_json(
                msg="Rules list items operation failed",
                operation_id=operation_id,
                operation=status,
            )

        if operation_status not in ("pending", "running"):
            module.fail_json(
                msg="Cloudflare API returned an unknown Rules list operation status",
                operation_id=operation_id,
                operation=status,
            )

        time.sleep(min(OPERATION_POLL_SECONDS, max(deadline - time.monotonic(), 0)))


def normalize_items(items):
    normalized_items = {}
    for item in items or []:
        normalized = {}
        for key, value in item.items():
            if key in ITEM_META_FIELDS or value is None:
                continue

            if key == "comment" and value == "":
                continue

            normalized_value = value
            if key == "ip" and isinstance(normalized_value, str):
                normalized_value = canonical_ip(normalized_value)

            if key == "hostname" and isinstance(normalized_value, dict):
                hostname = {
                    hostname_key: hostname_value
                    for hostname_key, hostname_value in normalized_value.items()
                    if hostname_value is not None
                }

                if hostname.get("exclude_exact_hostname") is True:
                    hostname.pop("exclude_exact_hostname")

                normalized_value = hostname

            if key == "redirect" and isinstance(normalized_value, dict):
                normalized_value = {
                    redirect_key: redirect_value
                    for redirect_key, redirect_value in normalized_value.items()
                    if redirect_value is not None and values_differ(redirect_value, REDIRECT_DEFAULTS.get(redirect_key))
                }

            normalized[key] = normalized_value

        normalized_items[canonical_item(normalized)] = normalized

    return sorted(normalized_items.values(), key=canonical_item)


def checked_list(module, rules_list, name, kind, expected_id=None):
    rules_list = serialize_resource(rules_list)
    resource_id(module, rules_list, "Rules list", expected=expected_id)
    resource_field(module, rules_list, "name", "Rules list", expected=name)
    resource_field(module, rules_list, "kind", "Rules list", expected=kind)
    return rules_list


def valid_ip(value):
    """Return whether value is an IP address or a CIDR that Cloudflare accepts."""
    if not isinstance(value, str) or "%" in value:
        return False

    address, separator, prefix = value.partition("/")
    try:
        parsed = ip_address(address)
    except ValueError:
        return False

    if parsed.version == 6 and parsed.ipv4_mapped is not None:
        return False

    if not separator:
        return True

    if not (prefix.isascii() and prefix.isdigit() and int(prefix) in IP_PREFIX_LENGTHS[parsed.version]):
        return False

    try:
        ip_network(f"{parsed}/{int(prefix)}")
    except ValueError:
        return False

    return True


def valid_hostname(value):
    """Return whether value has only supported characters, `*` only as a single leading `*.` label, and valid labels."""
    if not set(value) <= HOSTNAME_CHARACTERS:
        return False

    host = value.removeprefix("*.")
    if "*" in host:
        return False

    # A single trailing dot is accepted and does not count toward the length.
    return valid_dns_labels(host.removesuffix("."))


def target_url_valid(value):
    """Return whether value is a URL with a scheme.

    The value must not start with whitespace or contain an ASCII control
    character or a "%" outside a percent-escape. The authority must not
    contain whitespace, and a port must be digits.
    """
    if (
        value[:1].isspace()
        or any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)
        or INVALID_PERCENT_ESCAPE.search(value)
    ):
        return False

    try:
        parts = urlsplit(value)
    except ValueError:
        return False

    if not parts.scheme:
        return False

    # urlsplit drops tabs and newlines, so read the authority from the value.
    authority = value.partition("://")[2]
    for delimiter in "/?#":
        authority = authority.partition(delimiter)[0]

    if any(character.isspace() for character in authority):
        return False

    # Parse the port text: Cloudflare stores an out-of-range port such as
    # 99999, for which urlsplit raises ValueError.
    port = authority.rpartition("@")[2].rpartition("]")[2].partition(":")[2]
    return not port or (port.isascii() and port.isdigit())


def source_url_error(value):
    """Return why a redirect source URL includes a component Cloudflare does not support, or None."""
    if "?" in value:
        return "must not include a query string"

    if "#" in value:
        return "must not include a fragment"

    if INVALID_PERCENT_ESCAPE.search(value):
        return "must use '%' only in a percent-escape such as %20"

    if DECODED_REJECTED_ESCAPE.search(value):
        return "must not contain %3F, %23, or %25, which Cloudflare decodes to characters it rejects"

    scheme, separator, rest = value.partition("://")
    if not separator or "/" in scheme:
        scheme, rest = None, value

    if scheme is not None and scheme.lower() not in SOURCE_URL_SCHEMES:
        return "must use the http or https scheme, or none"

    authority = rest.partition("/")[0]
    if not authority:
        return "must include a host"

    if "@" in authority:
        return "must not include userinfo"

    if authority.startswith("[") or authority.count(":") > 1:
        return "must not use an IPv6 address as its host"

    port = authority.rpartition(":")[2]
    if ":" in authority and ((port.isascii() and port.isdigit()) or (scheme is not None and port)):
        return "must not include a port"

    if scheme is None and ":" in authority:
        return "must use the http or https scheme followed by '://', or none"

    return None


def item_value(item, kind):
    """Return the value that identifies an item of the list kind."""
    value = item.get(kind)
    field = IDENTITY_FIELDS.get(kind)
    return value.get(field) if field and isinstance(value, dict) else value


def validate_elements(module, kind):
    """Fail when an element lacks the field that stores the list kind, has other keys, or holds an invalid value."""
    for index, element in enumerate(module.params.get("elements") or ()):
        if element.get(kind) is None:
            module.fail_json(msg=f"elements[{index}] must set {kind!r} for a Rules list of kind {kind!r}")

        unexpected = sorted(
            key
            for key, value in element.items()
            if key not in (kind, "comment", *ITEM_META_FIELDS) and value is not None
        )
        if unexpected:
            module.fail_json(
                msg=f"elements[{index}] supports only {kind!r} and 'comment' for a Rules list of kind {kind!r}",
                unexpected_keys=unexpected,
            )

        for field in REQUIRED_STRING_FIELDS.get(kind, ()):
            value = element[kind].get(field) if isinstance(element[kind], dict) else None
            if not isinstance(value, str) or not value:
                module.fail_json(msg=f"elements[{index}].{kind} must be a mapping with a non-empty string {field!r}")

        # A field set to null is not sent, so it counts as omitted.
        fields = (
            {key: value for key, value in element[kind].items() if value is not None}
            if kind in ITEM_VALUE_FIELDS
            else {}
        )
        unknown = unsupported_fields(fields, ITEM_VALUE_FIELDS.get(kind, ()), f"elements[{index}].{kind}")
        if unknown:
            module.fail_json(
                msg=f"elements[{index}].{kind} supports only {', '.join(ITEM_VALUE_FIELDS[kind])}",
                unsupported_fields=unknown,
            )

        not_boolean = [
            f"elements[{index}].{kind}.{field}"
            for field in BOOLEAN_ITEM_FIELDS.get(kind, ())
            if field in fields and not isinstance(fields[field], bool)
        ]
        if not_boolean:
            module.fail_json(msg=f"{', '.join(not_boolean)} must be true or false", invalid_fields=not_boolean)

        comment = element.get("comment")
        if comment is not None and (not isinstance(comment, str) or len(comment) > MAX_COMMENT_LENGTH):
            module.fail_json(
                msg=f"elements[{index}].comment must be a string of at most {MAX_COMMENT_LENGTH} characters",
                comment=comment,
            )

        asn = element.get("asn")
        if kind == "asn" and (not isinstance(asn, int) or isinstance(asn, bool) or not 1 <= asn <= MAX_ASN):
            module.fail_json(msg=f"elements[{index}].asn must be an integer from 1 to {MAX_ASN}", asn=asn)

        redirect = element.get("redirect") if kind == "redirect" else None
        status_code = redirect.get("status_code") if isinstance(redirect, dict) else None
        if status_code is not None and (
            not isinstance(status_code, int)
            or isinstance(status_code, bool)
            or status_code not in REDIRECT_STATUS_CODES
        ):
            module.fail_json(
                msg=f"elements[{index}].redirect.status_code must be one of 301, 302, 307, or 308",
                status_code=status_code,
            )

        source_url = redirect.get("source_url") if isinstance(redirect, dict) else None
        source_url_problem = source_url_error(source_url) if isinstance(source_url, str) else None
        if source_url_problem:
            module.fail_json(msg=f"elements[{index}].redirect.source_url {source_url_problem}", source_url=source_url)

        target_url = redirect.get("target_url") if isinstance(redirect, dict) else None
        if isinstance(target_url, str) and not target_url_valid(target_url):
            module.fail_json(
                msg=(
                    f"elements[{index}].redirect.target_url must start with a scheme, have "
                    "no whitespace in its authority, and only digits in its port, must not start with whitespace "
                    "or contain an ASCII control character, and may use '%' only in a percent-escape such as %20"
                ),
                target_url=target_url,
            )

        hostname = element.get("hostname") if kind == "hostname" else None
        url_hostname = hostname.get("url_hostname") if isinstance(hostname, dict) else None
        if isinstance(url_hostname, str) and not valid_hostname(url_hostname):
            module.fail_json(
                msg=(
                    f"elements[{index}].hostname.url_hostname may contain only ASCII letters, digits, "
                    "'.', '-', '_', and a '*' wildcard only as a single leading '*.' label, "
                    "each other label must have 1 to 63 characters and must not start or end with '-', "
                    "and the name must have at most 253 characters"
                ),
                url_hostname=url_hostname,
            )

        if (
            isinstance(url_hostname, str)
            and not url_hostname.startswith("*.")
            and hostname.get("exclude_exact_hostname") is False
        ):
            module.fail_json(
                msg=(
                    f"elements[{index}].hostname.exclude_exact_hostname may be false only for a wildcard "
                    "url_hostname such as '*.example.com'"
                ),
                url_hostname=url_hostname,
            )

        if kind == "ip" and not valid_ip(element["ip"]):
            module.fail_json(
                msg=(
                    f"elements[{index}].ip must be an IP address, or a CIDR with a prefix length "
                    "of 8 to 32 for IPv4 or 12 to 128 for IPv6 and no host bits set, "
                    "and must not be an IPv4-mapped or scoped IPv6 address"
                ),
                ip=element["ip"],
            )

    field = IDENTITY_FIELDS.get(kind)
    values = set()
    for item in normalize_items(module.params.get("elements")):
        value = item_value(item, kind)
        if canonical_item(value) in values:
            name = f"{kind}.{field}" if field else kind
            module.fail_json(msg=f"elements must not repeat the {name!r} value {value!r}", **{field or kind: value})

        values.add(canonical_item(value))

    # Cloudflare rejects a wildcard hostname alongside its exact apex hostname.
    if kind == "hostname":
        hostnames = {element["hostname"]["url_hostname"] for element in module.params.get("elements") or ()}
        for hostname in sorted(hostnames):
            if f"*.{hostname}" in hostnames:
                module.fail_json(
                    msg=f"elements must not set both 'url_hostname' values {'*.' + hostname!r} and {hostname!r}",
                    url_hostname=[f"*.{hostname}", hostname],
                )


def fail_not_applied(module, kind, desired_items, stored_items):
    """Fail, naming each requested value Cloudflare did not store next to the most similar stored value."""
    desired = {canonical_item(item) for item in desired_items}
    stored = {canonical_item(item) for item in stored_items}
    missing = [item for item in desired_items if canonical_item(item) not in stored]
    unexpected = [item for item in stored_items if canonical_item(item) not in desired]

    pairs = []
    remaining = [item_value(item, kind) for item in unexpected]
    for item in missing[:MESSAGE_ITEMS]:
        requested = item_value(item, kind)
        found = max(
            remaining, key=lambda value: SequenceMatcher(None, str(requested), str(value)).ratio(), default=None
        )
        if found is not None:
            remaining.remove(found)

        pairs.append(f"requested {requested!r}, stored {found!r}")

    if len(missing) > MESSAGE_ITEMS:
        pairs.append(f"{len(missing) - MESSAGE_ITEMS} more requested items are listed in missing_items")
    else:
        pairs.extend(f"stored {value!r}, not requested" for value in remaining[:MESSAGE_ITEMS])

    module.fail_json(
        msg=f"Cloudflare did not apply the requested Rules list items: {'; '.join(pairs)}",
        missing_items=missing,
        unexpected_items=unexpected,
    )


def ensure_present(module, client, current):
    params = module.params
    account_id = params["account_id"]
    lists = client.rules.lists

    if current is None:
        # Cloudflare rejects a new list without a kind.
        current_kind = params.get("kind")
    else:
        current_id = resource_id(module, current, "Rules list")
        current_kind = resource_field(module, current, "kind", "Rules list")
        if params.get("kind") is not None and params["kind"] != current_kind:
            module.fail_json(
                msg="An existing Rules list kind cannot be changed",
                rules_list=current,
            )

    if current_kind is not None:
        validate_elements(module, current_kind)

    changed = False
    created = False
    items_changed = False
    items_operation = None

    if current is None:
        if module.check_mode:
            module.exit_json(changed=True, message="Rules list would be created")

        payload = {
            "description": (params["name"] if params.get("description") is None else params["description"]),
            "kind": params["kind"],
            "name": params["name"],
        }
        with cloudflare_error_context(
            "Cloudflare API request failed while creating the Rules list",
            account_id=account_id,
            name=params["name"],
        ):
            rules_list = create_once(
                lambda: without_retries(client).rules.lists.create(account_id=account_id, **payload),
                lambda: matching_resources(lists.list(account_id=account_id), "name", params["name"]),
            )
            current = checked_list(module, rules_list, params["name"], params["kind"])

        require_applied(module, current, payload, "Rules list", LIST_DEFAULTS)
        current_id = current["id"]
        changed = True
        created = True
    else:
        desired_description = params.get("description")
        if desired_description is not None and current.get("description", "") != desired_description:
            if module.check_mode:
                module.exit_json(
                    changed=True,
                    message="Rules list would be updated",
                    rules_list=current,
                )

            with cloudflare_error_context(
                "Cloudflare API request failed while updating the Rules list",
                account_id=account_id,
                rules_list_id=current_id,
            ):
                current = checked_list(
                    module,
                    lists.update(current_id, account_id=account_id, description=desired_description),
                    params["name"],
                    current_kind,
                    expected_id=current_id,
                )

            require_applied(module, current, {"description": desired_description}, "Rules list", LIST_DEFAULTS)
            changed = True

    if params.get("elements") is not None:
        desired_items = normalize_items(params["elements"])
        current_count = current.get("num_items")

        if current_count is not None and (
            isinstance(current_count, bool)
            or not isinstance(current_count, (int, float))
            or current_count < 0
            or int(current_count) != current_count
        ):
            module.fail_json(msg="Cloudflare API returned malformed Rules list data")

        if current_count is not None and current_count != len(desired_items):
            items_changed = True
        else:
            items_changed = values_differ(
                normalize_items(list_items(module, client, account_id, current_id)),
                desired_items,
            )

        if module.check_mode and items_changed:
            module.exit_json(
                changed=True,
                message="Rules list items would be updated",
                rules_list=current,
            )

        if items_changed:
            deadline = time.monotonic() + params["operation_timeout"]
            items_operation = wait_for_operation(
                module,
                client,
                account_id,
                submit_items(module, client, account_id, current_id, desired_items, deadline),
                deadline,
            )

            with cloudflare_error_context(
                "Cloudflare API request failed while reading the updated Rules list",
                account_id=account_id,
                rules_list_id=current_id,
            ):
                current = checked_list(
                    module,
                    lists.get(current_id, account_id=account_id),
                    params["name"],
                    current_kind,
                    expected_id=current_id,
                )

            stored_items = normalize_items(list_items(module, client, account_id, current_id))
            if values_differ(stored_items, desired_items):
                fail_not_applied(module, current_kind, desired_items, stored_items)

    if not changed and not items_changed:
        module.exit_json(
            changed=False,
            message="Rules list already present",
            rules_list=current,
        )

    result = {
        "changed": True,
        "message": "Rules list created" if created else "Rules list updated",
        "rules_list": current,
    }
    if items_operation is not None:
        result["items_operation"] = items_operation

    module.exit_json(**result)


def run(module, client):
    params = module.params
    account_id = params["account_id"]
    lists = client.rules.lists

    if params["operation_timeout"] < 1:
        module.fail_json(msg="operation_timeout must be at least 1 second")

    with cloudflare_error_context(
        "Cloudflare API request failed while finding the Rules list",
        account_id=account_id,
        name=params["name"],
    ):
        current = find_resource(module, lists.list(account_id=account_id), "Rules list", "name", params["name"])

    if params["state"] == "absent":
        ensure_resource_absent(
            module,
            "rules_list",
            "Rules list",
            current,
            delete=lambda list_id: lists.delete(list_id, account_id=account_id),
            context={"account_id": account_id},
        )

    ensure_present(module, client, current)


def main():
    module = AnsibleModule(
        argument_spec={
            "account_id": {"required": True, "type": "str"},
            "api_token": {"required": True, "type": "str", "no_log": True},
            "name": {"required": True, "type": "str"},
            "kind": {"type": "str", "choices": ["ip", "redirect", "hostname", "asn"]},
            "description": {"type": "str"},
            "elements": {"type": "list", "elements": "dict"},
            "operation_timeout": {"type": "int", "default": 240},
            "state": {
                "type": "str",
                "choices": ["present", "absent"],
                "default": "present",
            },
        },
        supports_check_mode=True,
    )

    with cloudflare_client(module) as client:
        run(module, client)


if __name__ == "__main__":
    main()
