# JET VPN — Client-observed Purchase and Payment Flow

> Verified against the PR #14 client branch source. Backend behavior remains unverified.

## New purchase

1. Client loads public plans via `GET /api.php?action=list_plans` (`_openPurchasePlans`).
2. User selects a plan.
3. `_createInvoiceAndPay` sends `POST /api.php` with `action=create_invoice`, username, password, plan_key, and action_type.
4. Client reads the payment token and payment URL from the response and displays the invoice dialog.
5. When the user proceeds to payment, the client stores a `PendingPaymentRecord` in SharedPreferences under `pending_payment_json`: token, originating username, creation timestamp in milliseconds, and `pending` status.
6. `_watchPaymentStatus` sends `POST /api.php` with `action=invoice_status`, the stored token, and credentials for the active account—but only if the active username exactly matches the record owner.
7. Profile/account changes and password changes invalidate in-flight polls. A response arriving after invalidation or after the active account/credentials change is ignored.
8. On `approved`, the matching pending record is cleared and the client refreshes the originating account or activates an additional service profile. On expired/cancelled/rejected, the matching record is cleared.

## Renewal

1. `_openRenewPlans` sends `list_renew_plans` with active username/password.
2. Selected `plan_key` is passed to `_createInvoiceAndPay` with `action_type='renew'`.
3. Invoice ownership and status handling are shared with the new-purchase flow.

## Free test

1. `_claimFreeTest` requests `list_test_offers`.
2. Client filters offers by the client-observed `used` field.
3. User selects an offer (or the only available offer is selected automatically).
4. Client sends `claim_free_test` with credentials and optional `offer_id`.
5. Response may represent a new/additional service; the client may add a profile or refresh the active account.

## Account-binding safeguards

- The pending token is no longer stored as a standalone global string. Its record includes `owner_username`, `created_at_ms`, and `status='pending'`.
- Polling refuses to send a request if the active profile does not match the stored owner.
- Switching profiles, clearing the active session, changing account credentials, or changing the password invalidates outstanding polling generations.
- Results are revalidated after each network await so late responses cannot update the newly active account.
- Legacy `pending_pay_token` values contain no reliable owner metadata and are discarded on restore instead of being attached to the currently active profile. Users with such a legacy pending invoice may need to recreate it or ask support to reconcile it.
- Only one pending invoice is represented at a time. Multiple simultaneous pending invoices are not implemented.
- The token remains in SharedPreferences; this change does not add encryption.

## Server-side questions (not answered by client code)

- Is `pay_token` unique, unguessable, expiring, and bound immutably to one invoice/account?
- Does the backend reject a token queried with credentials for a different account?
- Is amount and plan identity recomputed on the server?
- Is approval idempotent under retries, and can one invoice be applied twice?
- Are additional-service and renewal operations atomic?

Never test payment changes against production without explicit authorization and a safe test account.
