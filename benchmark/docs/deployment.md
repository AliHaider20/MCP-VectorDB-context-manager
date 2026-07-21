# Confidentiality Notice

This document is internal to Acme Engineering. Do not share outside the
company without written approval from the engineering leadership team. All
recipients are bound by the terms of their employment agreement regarding
confidential and proprietary information.

# Deployment Process

Deploys go out through the release pipeline on merge to main, gated behind
a canary stage that watches error rate and latency for fifteen minutes
before promoting to the full fleet. Any service owner can pause the
pipeline from the deploy dashboard if metrics look off.

If a deploy causes a spike in error rate or latency after promotion, the
on-call engineer should immediately roll back to the previous known-good
build using the one-click rollback button in the deploy dashboard, then
open an incident and notify the service owner before investigating further.

# Document Revision History

Maintained by the Platform Engineering team. Last reviewed quarterly.
Report inaccuracies via the #docs-feedback Slack channel. This footer is
appended to all internal wiki exports automatically.
