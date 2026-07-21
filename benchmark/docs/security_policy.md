# Confidentiality Notice

This document is internal to Acme Engineering. Do not share outside the
company without written approval from the engineering leadership team. All
recipients are bound by the terms of their employment agreement regarding
confidential and proprietary information.

# Security Policy

All production credentials must be rotated every 90 days and stored only
in the approved secrets manager, never in source control or environment
files committed to a repo. Any suspected credential leak must be reported
to #security-incidents immediately, regardless of confidence level.

Third-party dependencies are scanned nightly for known vulnerabilities.
Critical severity findings block the next deploy until patched or an
explicit, time-boxed exception is approved by the security team lead.

# Document Revision History

Maintained by the Platform Engineering team. Last reviewed quarterly.
Report inaccuracies via the #docs-feedback Slack channel. This footer is
appended to all internal wiki exports automatically.
