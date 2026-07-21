# Confidentiality Notice

This document is internal to Acme Engineering. Do not share outside the
company without written approval from the engineering leadership team. All
recipients are bound by the terms of their employment agreement regarding
confidential and proprietary information.

# API Design Guidelines

All internal APIs must be versioned in the URL path, e.g. /v1/resource.
Breaking changes require a new major version and a deprecation notice sent
to the #api-consumers channel at least 30 days in advance. Prefer
pagination via cursor tokens over offset-based pagination for any list
endpoint expected to grow past a few thousand rows.

Error responses should follow the standard envelope: a top-level `error`
object with `code`, `message`, and an optional `details` array. Never leak
internal stack traces or database error strings to API consumers.

# Document Revision History

Maintained by the Platform Engineering team. Last reviewed quarterly.
Report inaccuracies via the #docs-feedback Slack channel. This footer is
appended to all internal wiki exports automatically.
