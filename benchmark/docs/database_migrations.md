# Confidentiality Notice

This document is internal to Acme Engineering. Do not share outside the
company without written approval from the engineering leadership team. All
recipients are bound by the terms of their employment agreement regarding
confidential and proprietary information.

# Database Migration Policy

Every schema migration must be backward compatible with the previous
release for at least one deploy cycle. Add columns as nullable first,
backfill in a separate job, then tighten constraints in a follow-up
migration once the backfill is confirmed complete.

Migrations run automatically in CI against a snapshot of production schema
before merge is allowed. Any migration that locks a table for more than one
second in the dry run is rejected and must be rewritten using an online
schema change tool.

# Document Revision History

Maintained by the Platform Engineering team. Last reviewed quarterly.
Report inaccuracies via the #docs-feedback Slack channel. This footer is
appended to all internal wiki exports automatically.
