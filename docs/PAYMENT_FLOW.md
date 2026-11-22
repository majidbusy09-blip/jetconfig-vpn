# JET VPN — Client-observed Purchase and Payment Flow

> Verified against client source at `main` `47949178016a6ef3e855a215550b06f4eae8378d`. Backend behavior remains unverified.

## New purchase

1. Client loads public plans via `GET /api.php?action=list_plans` (`_openPurchasePlans`, around 4356).
2. User selects a plan.
3. `_createInvoiceAndPay` sends `POST /api.php` with `action=create_invoice`, username, password, plan_key, and action_type.
4. Client reads a payment token and payment URL from the response and opens the payment URL.
5. Client stores the token in `SharedPreferences.pending_pay_token`.
6. `_watchPaymentStatus` sends `POST /api.php` with action `invoice_status`, current saved username/password, and the token.
7. On `approved`, the client clears the pending token and refreshes account data or activates an additional service profile. On expired/cancelled/rejected, it clears the token.

## Renewal

1. `_openRenewPlans` sends `list_renew_plans` with active username/password.
2. Selected `plan_key` is passed to `_createInvoiceAndPay` with `action_type='renew'`.
3. Remaining invoice/payment handling is shared with the new-purchase flow.

## Free test

1. `_claimFreeTest` requests `list_test_offers`.
2. Client filters offers by the client-observed `used` field.
3. User selects an offer (or the only available offer is selected automatically).
4. Client sends `claim_free_test` with credentials and optional `offer_id`.
5. Response may represent a new/additional service; the client may add a profile or refresh the active account.

## Important account-binding risk

- Token storage is global under `pending_pay_token`.
- `_watchPaymentStatus` combines the restored token with `savedUser` and `savedPass` at the time of checking.
- The token is not stored with its originating username or invoice metadata.
- `_activateProfile` switches active credentials and clears account/server caches, but does not visibly clear or rebind the pending payment token.

This establishes a client-side account-context mismatch risk. Whether the backend rejects mismatched ownership is unknown and must be tested from server source or a controlled test environment.

## Server-side questions before payment changes

- Is pay_token unique, unguessable, expiring, and bound to a single invoice/account?
- Is amount and plan identity recomputed on the server?
- Is approval idempotent under retries?
- Can one invoice be applied twice?
- Can a token be queried by another account?
- What is the exact payment URL and response schema?
- Are additional service and renewal flows atomic?

Never test payment changes against production without explicit user authorization and a safe test account.
