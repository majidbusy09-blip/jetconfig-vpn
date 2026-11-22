# JET VPN — Local Data Storage

> Verified against `main` `47949178016a6ef3e855a215550b06f4eae8378d`; primary source `lib/main.dart`.

## Storage mechanism

The client uses Flutter `SharedPreferences` for account profiles, active credentials, server cache, preferences, payment token, device ID, and native-stop coordination.

## Observed keys

| Key | Observed purpose | Sensitivity / notes |
|---|---|---|
| `app_profiles_json` | JSON array of profiles containing `username`, `password`, `label` | High: profile passwords stored as plaintext values in app preferences |
| `saved_username` | Active account username | Personal/account data |
| `saved_password` | Active account password | High: plaintext preference |
| `cached_user_json` | Cached account response | May contain account/subscription data |
| `cached_servers_json` | Cached server records/configs | Sensitive operational configuration |
| `cached_for_username` | Owner marker for cached account/server data | Account data |
| `pending_pay_token` | Pending invoice/payment token | High: no owner username stored alongside it |
| `last_server_id`, `last_server_config`, `last_server_name`, `last_server_host`, `last_server_port`, `last_server_index` | Last selected server state | Config/operational data |
| `pref_tunnel_mode`, `only_filtered_apps`, `pref_selected_vpn_packages` | Routing mode and selected apps | Preference |
| `pref_ui_theme` | Theme choice | Preference |
| `pref_auto_refresh_on_start`, `pref_auto_ping_on_start`, `pref_prefer_last_server` | Startup behavior | Preference |
| `pref_connection_mode_smart`, `pref_connection_mode_chosen`, `pref_prefer_stability` | Connection mode choices | Preference |
| `tunnel_bypass_json`, `tunnel_bypass_fetched_at` | Cached remote bypass rules and fetch time | Routing data |
| `app_device_id` | Generated/persisted device identifier | Device identifier |
| `v2ray_user_stop`, `flutter.v2ray_user_stop` | Native/user initiated stop coordination | Lifecycle state |
| `sub_alert_expired_<username>`, `sub_alert_warn_<username>` | Per-account subscription alert flags | Account preference |

Line references: profile serialization/migration `2450–2495`; active-session/profile switch `2515–2604`; preference loading `2605–2720`; server and routing preferences `2720–2840`; device ID `3264–3275`; payment token `3800–3822`.

## Confirmed design risks

1. Passwords are serialized in `app_profiles_json` and stored in `saved_password` without application-level encryption visible in this source. SharedPreferences is not a secure credential vault.
2. `pending_pay_token` is a single global key. The token is restored without an owner identifier; profile switching does not visibly bind the token to the account that created its invoice.
3. Cached server/account data has a `cached_for_username` owner key, which is a useful isolation pattern; payment token storage does not mirror it.

## Recommended future migration (not implemented)

- Use Android Keystore-backed encrypted storage for credentials/tokens.
- Define migration behavior for existing users before changing persistence.
- Preserve profile labels and active-account semantics.
- Bind pending invoices to owner username and creation time; consider multiple pending invoices.
- Define backup/restore policy for secrets and caches.
- Add migration tests and rollback handling before shipping.

No storage changes are made by this documentation PR.
