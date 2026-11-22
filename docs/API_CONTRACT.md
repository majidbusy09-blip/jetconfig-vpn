# JET VPN — Client-observed API Contract

> Source baseline: `main` `47949178016a6ef3e855a215550b06f4eae8378d`; all details below are observed in Flutter client source. **Server implementation and validation semantics are not verified.**

## Base endpoints

| Endpoint | Client use | Evidence |
|---|---|---|
| `POST https://majid6064.ir/api.php` | Most account, ticket, subscription, and payment actions | `lib/main.dart` action methods |
| `GET https://majid6064.ir/api.php?username=...&password=...` | Account/server fetch | `_fetchUserData`, lines 4594–4613 |
| `GET https://majid6064.ir/api.php?...&action=change_password&new_password=...` | Password change | `_changeAppPassword`, lines 7620–7697 |
| `GET https://majid6064.ir/api.php?action=list_plans` | Public plan catalogue | `_openPurchasePlans`, lines 4348–4364 |
| `POST https://majid6064.ir/sos_api.php` | SOS support flow | `_requestSosEmergency`, around line 2004 |
| `GET app_version.json` | Update metadata | constant at line 28; update methods around 7126 |
| `GET tunnel_bypass.json` | Routing bypass metadata | constant at line 29; methods around 1256–1320 |

## Observed action inventory

All POST actions use form-encoded request bodies in the client. The table lists only fields visible in the client; it is not a server-side schema guarantee.

| Action | Client-sent fields | Client handler / source |
|---|---|---|
| `ticket_list` | `device_id` | `_loadTickets`, 3276–3300 |
| `ticket_create` | `device_id`, `subject`, `body`; optional `username`, `email` | `_createTicket`, 3301–3336 |
| `ticket_thread` | `device_id`, `ticket_id` | `_openTicketThread`, 3337 onward |
| `ticket_reply` | `device_id`, `ticket_id`, `body` | `_openTicketThread`, 3466–3485 |
| `list_services` | `username`, `password` | `_syncAppServicesFromApi`, 3707–3734 |
| `register` | `username`, `password`; optional `email` | `_registerAppAccount`, 3735–3781 |
| `invoice_status` | `username`, `password`, `pay_token` | `_watchPaymentStatus`, 3988–4091 |
| `list_test_offers` | `username`, `password` | `_claimFreeTest`, 4092 onward |
| `claim_free_test` | `username`, `password`; optional `offer_id` | `_claimFreeTest`, around 4194 |
| `list_renew_plans` | `username`, `password` | `_openRenewPlans`, 4236–4347 |
| `create_invoice` | `username`, `password`, `plan_key`, `action_type` | `_createInvoiceAndPay`, 4500–4593 |

## Client-observed response fields

- Account fetch: expects `ok`, `servers`; uses subscription fields including `has_subscription`, `status`, `remaining_gb`, `total_gb`, `expire_days`, and optional message fields.
- Ticket list: expects `ok`, `tickets`.
- Ticket thread: expects `ok`, `ticket`, `messages`.
- Registration: expects `ok`, optional `msg`.
- Payment status: expects `ok`, `status`; on approval may read `panel_username`, `is_additional_service`, and `msg`.
- Free-test offers: expects `ok`, `offers`; each offer is inspected for `id`, `used`, `emoji`, `title`.
- Plan lists: expects `plans` and, in purchase catalogue, optionally grouped plan data.
- Invoice creation: client reads `pay_url`, `price_fmt` or `price`, `discount_note`, `additional_note`, `is_additional_service`, and `pay_token` (`_createInvoiceAndPay`, 4524–4558).

## Authentication and transport observations

- Several POST actions transmit username/password in form-encoded body.
- `_fetchUserData` sends username/password in a GET query string.
- `_changeAppPassword` sends current and new password in a GET query string.
- HTTPS protects transport in transit but does not prevent query strings from being recorded by server/proxy/access logs.
- The client uses timeouts and inconsistent error handling across actions; do not assume a uniform error envelope.

## Explicit server-unverified questions

- Are all actions authenticated and authorized server-side?
- Are ticket actions scoped to the supplied device ID/account?
- Is invoice ownership bound to a specific account and immutable server-side?
- Are invoice approvals idempotent and replay-resistant?
- Is amount/plan price calculated server-side rather than trusted from client input?
- Are free-test eligibility and service limits enforced server-side?
- Are password changes rate-limited and atomic?
- Are error codes, HTTP status codes, and response schemas stable?

Do not claim any of these are secure or insecure without inspecting the backend source and tests.
