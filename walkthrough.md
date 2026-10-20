# Release walkthrough — 20 October 2026

## Implemented

Updated sole-proprietor information, bank transfer details, prerequisite legal/about/contact pages, and official iyzico/PayTR artwork. Card payment simulation is blocked until real provider integration is implemented.

Added authenticated admin review search, recoverable removal and restoration; public review filtering and product rating recalculation; authoritative browser review synchronization.

Added persistent product-quality checkboxes and a workspace-agent review queue/report CLI. Product approval is bound to a fingerprint of the technical content and imagery. No real product has been marked verified by this release.

## Validation

The release checks include coupon security, coupon endpoints, payment readiness, review moderation and product-quality records. Tests use an isolated SQLite snapshot. UI checks use a separate preview database.

## Deployment

GitHub Pages serves the public storefront/admin assets. The Hetzner service uses `/var/www/pozitron` and `pozitron.service`. Back up the live database before deploying and preserve runtime data and secrets. A Git push alone does not deploy the Python API. Record the actual deployed revision and post-deployment checks in the delivery report.


## iyzico hosted checkout (20 October 2026)

Added TRY CheckoutForm initialization, environment-only credentials, verified callback retrieval and HMAC signatures, opaque customer result pages, and background recovery of missed callbacks. Unpaid sessions leave stock and coupons unchanged; successful payment consumes them atomically once. Paid orders with fulfillment conflicts require manual review. PayTR stays disabled. Updated privacy disclosure and admin payment states. Verification uses mocked provider contracts and a no-charge credential check; no live card charge was performed.
