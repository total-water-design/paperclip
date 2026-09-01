# TWDS shared assistant contracts v1

This directory is the authoritative, application-neutral contract boundary for
TWDS assistants. Applications consume these files; they must not copy or fork
them locally.

The stable contract identifier is `twds.assistant/v1`. Additive changes may be
made without changing that identifier. Breaking changes require a new versioned
directory and contract identifier.

Files:

- `assistant-manifest.schema.json`: assistant identity, capabilities, and links
  to the registries it consumes.
- `assistant-response.schema.json`: structured, provenance-bearing responses
  and proposed actions.
- `semantic-target-registry.schema.json`: application-owned semantic targets;
  selectors remain implementation details outside this shared contract.
- `tool-registration.schema.json`: deterministic, side-effect-declared tool
  registrations with JSON Schema input and output contracts.
- `semantic-targets.json` and `tools.json`: the initial suite-wide registries.

Consumers must reject unknown major contract identifiers. A response action is
valid only when its `target_id` or `tool_id` resolves in the registries named by
the manifest. Tool execution is never implied by a response: the host remains
responsible for authorization, validation, and user confirmation.
