# Ansible SDK Plugins

Cloudflare SDK-specific standards for Python modules, lookup plugins, and
filter plugins under `plugins/`. Apply these with `ansible-plugins.md`.

## Dependency and API surface

- Use the supported `cloudflare` package range declared by the collection.
- Keep `requirements.txt` and plugin documentation requirements synchronized.
- Confirm SDK calls against the supported versions and the SDK's `api.md`.
- Use public clients, resources, models, exceptions, and response helpers.
- Do not import generated internals or depend on undocumented implementation
  details.
- Treat generated resource paths, method signatures, and static types as
  versioned interfaces that can change between SDK minor releases.
- Add or widen the dependency range only after tests pass at both boundaries.

## Clients and authentication

- Use `cloudflare_client(module)` instead of constructing clients in individual
  modules.
- Pass the Ansible `api_token` parameter explicitly to `Cloudflare`.
- Do not rely on SDK environment-variable authentication in a module.
- Keep API tokens under `no_log` and out of exceptions, results, and logging.
- Use the synchronous client for modules and lookup plugins.
- Keep filter plugins pure; they must not create a client or perform requests.
- Open one client context per plugin invocation so HTTP resources are closed.
- Reuse that client for every request in the invocation.
- Add another authentication scheme only for a concrete collection contract.

## Requests

- Prefer a generated resource method when it completely represents the
  documented Cloudflare API operation.
- Follow the generated resource namespace and documented method signature.
- Pass request parameters by their generated snake_case names.
- Pass nested request values as dictionaries matching the generated
  `TypedDict` shape.
- Omit unset optional values; pass `None` only when the API documents JSON null
  as meaningful.
- Use `client.with_options()` for an isolated timeout or retry override.
- Use `api_request` and the shared result helpers when the generated resource
  cannot represent a documented operation or response reliably.
- Keep raw requests on public `get`, `post`, `put`, `patch`, and `delete`
  methods and provide an explicit `cast_to` value.
- Encode path segments and query values; never interpolate untrusted values
  into an unescaped path.
- Do not duplicate SDK transport, authentication, or serialization behavior.

## Responses

- Convert SDK Pydantic models with `serialize_resource`.
- Return only JSON-serializable Ansible values, never SDK or HTTPX objects.
- Recursively serialize models nested in lists and dictionaries.
- Preserve stable documented fields and discard provider-only noise only when
  it would break the module contract or idempotence.
- Use `model_fields_set` only when missing and explicit null have different
  documented meanings.
- Use `model_extra` only for a documented API field missing from the generated
  model, and leave focused regression coverage.
- Validate required response fields and resource identities before reporting
  success.
- Re-read state after mutation when Cloudflare assigns or normalizes values.

## Pagination

- Iterate a generated list response to consume its auto-paginating iterator.
- Stop iteration as soon as a singular lookup finds its unique match.
- Do not read only the first page's `result` when the contract requires all
  items.
- Use server-side filters when the generated list method supports them.
- Use `iter_items` or `list_all` for raw request paths.
- Do not implement another page loop inside an individual plugin.
- Keep pagination output order only when the API documents it as stable.

## Failures, retries, and timeouts

- Let the shared client boundary convert SDK exceptions to Ansible failures.
- Catch the narrowest applicable public exception when local recovery is
  required.
- Treat `NotFoundError`, or status 404, as absence only when the operation's
  contract defines it that way.
- Preserve the operation, resource identifier, status code, and sanitized API
  response in actionable failures.
- Never expose request headers, authentication values, or secret response
  fields.
- Account for the SDK's default retries on connection errors and HTTP 408,
  409, 429, and 5xx responses.
- Do not stack an unbounded plugin retry loop on the SDK retry policy.
- Disable SDK retries when a module owns a bounded retry loop or a strict
  operation deadline.
- Apply a finite request timeout and count SDK retries, sleeps, and polling
  against the documented operation timeout.
- Use monotonic time for operation deadlines.

## Idempotence

- Compare serialized current state with only the fields managed by the module.
- Normalize documented Cloudflare defaults before deciding that state differs.
- Preserve unmanaged fields when an update API expects a complete object.
- Do not treat SDK-populated fields as user-requested configuration.
- Verify the postcondition after create, update, or delete operations.

## Verification

- Test generated model serialization with representative nested responses.
- Test generated pagination beyond one page when a plugin returns a full list.
- Test raw response envelopes separately from generated model responses.
- Test connection, timeout, status, not-found, and rate-limit handling used by
  the affected plugin.
- Test that explicit null and omitted values remain distinct when required.
- Run the plugin suite against the minimum and maximum supported SDK versions.
- Recheck generated resource paths and response types during every SDK update.
