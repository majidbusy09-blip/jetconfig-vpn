<?php
/**
 * JetConfig App API
 * - ترجیحاً POST
 * - هدر X-Api-Key یا پارامتر api_key (مقدار APP_API_KEY در config)
 * - محدودیت درخواست ساده بر اساس IP
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Api-Key');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit();
}

require_once 'config.php';
if (is_readable(__DIR__ . '/test_offers_lib.php')) {
    require_once __DIR__ . '/test_offers_lib.php';
}

/** آیا کاربر هنوز حداقل یک تست دسته‌ای نگرفته؟ */
function api_can_claim_test(PDO $db, int $userId): bool
{
    if ($userId <= 0) {
        return false;
    }
    if (!api_is_feature_enabled($db, 'btn_test')) {
        return false;
    }
    // فقط کسانی که هنوز خرید دائم نکرده‌اند
    try {
        $st = $db->prepare('SELECT has_bought, has_used_test FROM users WHERE user_id = ? LIMIT 1');
        $st->execute([$userId]);
        $row = $st->fetch(PDO::FETCH_ASSOC);
        if ($row && (int)($row['has_bought'] ?? 0) === 1) {
            return false;
        }
    } catch (Throwable $e) {
    }
    try {
        $st = $db->prepare('SELECT plan_key, config_username, volume_gb, days FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 20');
        $st->execute([$userId]);
        foreach ($st->fetchAll(PDO::FETCH_ASSOC) as $or) {
            if (function_exists('api_order_is_test') && api_order_is_test($or)) {
                continue;
            }
            $pk = strtolower((string)($or['plan_key'] ?? ''));
            if (strpos($pk, 'test') !== false || $pk === 'test_free' || strpos($pk, 'test_offer_') === 0) {
                continue;
            }
            return false;
        }
    } catch (Throwable $e) {
    }
    if (function_exists('testOffersListVisible') && function_exists('testOfferUserHasUsed')) {
        try {
            $vis = testOffersListVisible($db);
            $any = false;
            foreach ($vis as $o) {
                $any = true;
                $oid = (int)($o['id'] ?? 0);
                if ($oid > 0 && !testOfferUserHasUsed($db, $userId, $oid)) {
                    return true;
                }
            }
            if ($any) {
                return false;
            }
        } catch (Throwable $e) {
        }
    }
    try {
        $st = $db->prepare('SELECT has_used_test FROM users WHERE user_id = ? LIMIT 1');
        $st->execute([$userId]);
        return ((int)$st->fetchColumn()) === 0;
    } catch (Throwable $e) {
        return false;
    }
}




/** اطلاع به ادمین‌های تلگرام (بدون وابستگی به bot.php) */
/** نام کاربری جدا برای تست وقتی اشتراک اصلی وجود دارد */
function api_make_secondary_test_username(string $base, int $offerId = 0): string
{
    $base = strtolower(preg_replace('/[^a-zA-Z0-9]/', '', $base) ?? '');
    if ($base === '') {
        $base = 'u';
    }
    $base = substr($base, 0, 10);
    $suf = $offerId > 0 ? (string)$offerId : substr(str_replace('.', '', uniqid('', true)), -4);
    return 't' . $base . $suf;
}

/** آیا این یوزرنیم روی پنل/سفارش، اشتراک غیرتست دارد؟ */
function api_username_has_paid_service(PDO $db, string $username, int $userId = 0): bool
{
    $username = trim($username);
    if ($username === '') {
        return false;
    }
    try {
        $st = $db->prepare(
            "SELECT plan_key, config_username, volume_gb, days FROM orders
             WHERE LOWER(config_username) = LOWER(?) OR (user_id = ? AND user_id > 0)
             ORDER BY id DESC LIMIT 15"
        );
        $st->execute([$username, $userId]);
        foreach ($st->fetchAll(PDO::FETCH_ASSOC) as $or) {
            if (function_exists('api_order_is_test') && api_order_is_test($or)) {
                continue;
            }
            $pk = strtolower((string)($or['plan_key'] ?? ''));
            $cn = strtolower((string)($or['config_username'] ?? ''));
            $isTest = (strpos($pk, 'test') !== false || $pk === 'test_free' || strpos($cn, 'test_') === 0 || strpos($cn, 't') === 0 && strpos($pk, 'test_offer_') === 0);
            // دقیق‌تر:
            $isTest = function_exists('api_order_is_test') ? api_order_is_test($or) : (
                strpos($pk, 'test') !== false || $pk === 'test_free' || strpos($cn, 'test_') === 0
            );
            if (!$isTest) {
                $vol = (float)($or['volume_gb'] ?? 0);
                $days = (int)($or['days'] ?? 0);
                // هر سفارش غیرتست (حجمی/زمانی/نامحدود)
                if ($vol > 0.2 || $days === 0 || $days > 1 || $pk !== '') {
                    return true;
                }
            }
        }
    } catch (Throwable $e) {
    }
    return false;
}


function api_notify_admins(PDO $db, string $text, $replyMarkup = null): void {
    if (!defined('BOT_TOKEN') || !BOT_TOKEN) {
        return;
    }
    $ids = [];
    if (defined('ADMIN_ID') && ADMIN_ID) {
        $ids[] = (int)ADMIN_ID;
    }
    try {
        $rows = $db->query('SELECT user_id FROM bot_admins')->fetchAll(PDO::FETCH_COLUMN) ?: [];
        foreach ($rows as $uid) {
            $uid = (int)$uid;
            if ($uid > 0) {
                $ids[] = $uid;
            }
        }
    } catch (Exception $e) {}
    $ids = array_values(array_unique(array_filter($ids)));
    if (!$ids) {
        return;
    }
    $bases = [];
    if (defined('WORKER_URL') && WORKER_URL) {
        $bases[] = rtrim((string)WORKER_URL, '/') . '/bot' . BOT_TOKEN;
    }
    $bases[] = 'https://api.telegram.org/bot' . BOT_TOKEN;
    foreach ($ids as $chatId) {
        $payload = [
            'chat_id' => $chatId,
            'text' => $text,
            'parse_mode' => 'HTML',
            'disable_web_page_preview' => true,
        ];
        if (is_array($replyMarkup)) {
            $payload['reply_markup'] = json_encode($replyMarkup, JSON_UNESCAPED_UNICODE);
        }
        foreach ($bases as $base) {
            $ch = curl_init(rtrim($base, '/') . '/sendMessage');
            curl_setopt_array($ch, [
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_POST => true,
                CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
                CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE),
                CURLOPT_TIMEOUT => 8,
                CURLOPT_SSL_VERIFYPEER => false,
            ]);
            $res = curl_exec($ch);
            $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            $j = json_decode((string)$res, true);
            if ($code >= 200 && $code < 300 && is_array($j) && !empty($j['ok'])) {
                break;
            }
        }
    }
}

function apiFail($msg, $code = 400) {
    http_response_code($code);
    echo json_encode(['ok' => false, 'msg' => $msg], JSON_UNESCAPED_UNICODE);
    exit();
}

/** ردیف پنل از جدول bot_panels یا fallback به config */
function api_default_panel_row() {
    return [
        'id' => 0,
        'name' => 'default',
        'type' => 'pasargad',
        'base_url' => defined('PANEL_URL') ? rtrim((string)PANEL_URL, '/') : '',
        'public_url' => defined('PANEL_URL') ? rtrim((string)PANEL_URL, '/') : '',
        'username' => defined('PANEL_USER') ? (string)PANEL_USER : '',
        'password' => defined('PANEL_PASS') ? (string)PANEL_PASS : '',
        'use_worker' => 1,
        'is_default' => 1,
        'is_active' => 1,
    ];
}


function api_get_setting(PDO $db, string $key, $default = '') {
    // ربات از setting_val استفاده می‌کند؛ بعضی نسخه‌ها setting_value دارند
    try {
        foreach (['setting_val', 'setting_value', 'value'] as $col) {
            try {
                $st = $db->prepare("SELECT {$col} FROM settings WHERE setting_key = ? LIMIT 1");
                $st->execute([$key]);
                $v = $st->fetchColumn();
                if ($v !== false && $v !== null && (string)$v !== '') {
                    return $v;
                }
            } catch (Exception $e) {
                continue;
            }
        }
        return $default;
    } catch (Exception $e) {
        return $default;
    }
}

function api_is_feature_enabled(PDO $db, string $key): bool {
    $v = api_get_setting($db, $key, '1');
    $v = is_string($v) ? trim($v) : $v;
    return ($v === '1' || $v === 1 || $v === true || $v === 'true' || $v === 'on');
}

function api_get_test_panel(PDO $db): array {
    $id = (int)api_get_setting($db, 'test_panel_id', '0');
    if ($id > 0) {
        return api_panel_by_id($db, $id);
    }
    return api_load_default_panel($db);
}

/** ساخت کاربر روی پنل (نسخه سبک برای تست اپ) */
function api_create_panel_user(PDO $db, array $panel, string $username, float $volume_gb, int $days): array {
    // getPanelToken تعریف بعداً در فایل است — از منطق توکن محلی استفاده می‌کنیم
    $user = (string)($panel['username'] ?? (defined('PANEL_USER') ? PANEL_USER : ''));
    $pass = (string)($panel['password'] ?? (defined('PANEL_PASS') ? PANEL_PASS : ''));
    if ($user === '') {
        return ['_error' => 'no_panel_user'];
    }
    $bases = api_panel_token_bases($panel);
    $token = null;
    $apiBase = '';
    foreach ($bases as $base) {
        foreach ([
            ['body' => json_encode(['username' => $user, 'password' => $pass], JSON_UNESCAPED_UNICODE), 'ct' => 'application/json'],
            ['body' => http_build_query(['username' => $user, 'password' => $pass]), 'ct' => 'application/x-www-form-urlencoded'],
        ] as $mode) {
            $ch = curl_init(rtrim($base, '/') . '/api/admin/token');
            curl_setopt_array($ch, [
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => $mode['body'],
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_HTTPHEADER => ['Content-Type: ' . $mode['ct']],
                CURLOPT_SSL_VERIFYPEER => false,
                CURLOPT_TIMEOUT => 20,
            ]);
            $res = curl_exec($ch);
            curl_close($ch);
            $decoded = json_decode((string)$res, true);
            $tok = is_array($decoded) ? ($decoded['access_token'] ?? $decoded['token'] ?? null) : null;
            if ($tok) {
                $token = $tok;
                $apiBase = rtrim($base, '/');
                break 2;
            }
        }
    }
    if (!$token) {
        return ['_error' => 'token_failed'];
    }
    $dataLimitBytes = ($volume_gb > 0) ? (int)round($volume_gb * 1024 * 1024 * 1024) : 0;
    $groupIds = [];
    try {
        $pid = (int)($panel['id'] ?? 0);
        $raw = '';
        // ۱) group_ids اختصاصی پنل (مثل ربات: panel_group_ids_{id})
        if ($pid > 0) {
            $raw = trim((string)api_get_setting($db, 'panel_group_ids_' . $pid, ''));
        }
        // ۲) سراسری پاسارگاد — همیشه، نه فقط پنل پیش‌فرض (فرق مهم با نسخهٔ قبلی)
        if ($raw === '' || $raw === '0') {
            $raw = trim((string)api_get_setting($db, 'pasargad_group_ids', ''));
        }
        // ۳) extra_json پنل
        if (($raw === '' || $raw === '0') && !empty($panel['extra_json'])) {
            $ex = json_decode((string)$panel['extra_json'], true);
            if (is_array($ex) && isset($ex['group_ids'])) {
                $raw = is_array($ex['group_ids']) ? implode(',', $ex['group_ids']) : (string)$ex['group_ids'];
            }
        }
        if ($raw !== '' && $raw !== '0') {
            $groupIds = array_map('intval', array_filter(array_map('trim', explode(',', $raw)), function ($v) {
                return $v !== '' && ctype_digit((string)$v);
            }));
            $groupIds = array_values(array_unique($groupIds));
        }
    } catch (Exception $e) {}
    // ۴) اگر هنوز خالی: همه گروه‌های پنل (همان انتخاب «همه» در UI پاسارگاد)
    if (empty($groupIds)) {
        try {
            foreach (['/api/groups', '/api/group'] as $gpath) {
                $chG = curl_init($apiBase . $gpath);
                curl_setopt_array($chG, [
                    CURLOPT_RETURNTRANSFER => true,
                    CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Accept: application/json'],
                    CURLOPT_SSL_VERIFYPEER => false,
                    CURLOPT_TIMEOUT => 12,
                ]);
                $resG = curl_exec($chG);
                $httpG = (int)curl_getinfo($chG, CURLINFO_HTTP_CODE);
                curl_close($chG);
                if ($httpG >= 400 || $resG === false) continue;
                $groups = json_decode((string)$resG, true);
                if (!is_array($groups)) continue;
                if (isset($groups['items']) && is_array($groups['items'])) {
                    $groups = $groups['items'];
                }
                foreach ($groups as $g) {
                    if (!is_array($g)) continue;
                    $gid = (int)($g['id'] ?? 0);
                    if ($gid > 0) $groupIds[] = $gid;
                }
                $groupIds = array_values(array_unique($groupIds));
                if (!empty($groupIds)) break;
            }
            // بعضی پنل‌ها id عددی کوچک می‌دهند — حداقل یک گروه بفرست
            if (empty($groupIds)) {
                // fallback ایمن: گروه ۱ و ۲ (در بسیاری از پاسارگادها موجود است)
                $groupIds = [1];
            }
        } catch (Exception $e) {
            if (empty($groupIds)) {
                $groupIds = [1];
            }
        }
    }
    // تضمین: هیچ‌وقت بدون group_ids نساز
    if (empty($groupIds)) {
        $groupIds = [1];
    }
    $payload = [
        'username' => $username,
        'data_limit' => $dataLimitBytes,
        'proxies' => ['vless' => new stdClass()],
        'inbounds' => new stdClass(),
    ];
    if ($days > 0) {
        $payload['status'] = 'on_hold';
        $payload['expire'] = 0;
        $payload['on_hold_expire_duration'] = $days * 86400;
    } else {
        $payload['expire'] = 0;
    }
    if (!empty($groupIds)) {
        $payload['group_ids'] = $groupIds;
    }
    $ch = curl_init($apiBase . '/api/user');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Content-Type: application/json'],
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_TIMEOUT => 20,
    ]);
    $res = curl_exec($ch);
    $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    $decoded = json_decode((string)$res, true);
    if (!is_array($decoded) || $http >= 400 || isset($decoded['detail']) || isset($decoded['message'])) {
        $msg = is_array($decoded) ? ($decoded['detail'] ?? $decoded['message'] ?? 'create_fail') : 'create_fail';
        if (is_array($msg)) {
            $msg = json_encode($msg, JSON_UNESCAPED_UNICODE);
        }
        return ['_error' => 'create_fail', 'detail' => (string)$msg, 'http' => $http];
    }
    // اگر ساخته شد ولی گروه نداشت، یک‌بار modify با group_ids
    if (!empty($groupIds)) {
        $hasLinks = !empty($decoded['links']) && is_array($decoded['links']) && count($decoded['links']) > 0;
        $hasSub = !empty($decoded['subscription_url']);
        if (!$hasLinks || !$hasSub) {
            try {
                $mod = $decoded;
                $mod['group_ids'] = $groupIds;
                if (empty($mod['proxies'])) {
                    $mod['proxies'] = ['vless' => new stdClass()];
                }
                $ch2 = curl_init($apiBase . '/api/user/' . rawurlencode($username));
                curl_setopt_array($ch2, [
                    CURLOPT_CUSTOMREQUEST => 'PUT',
                    CURLOPT_POSTFIELDS => json_encode($mod, JSON_UNESCAPED_UNICODE),
                    CURLOPT_RETURNTRANSFER => true,
                    CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Content-Type: application/json'],
                    CURLOPT_SSL_VERIFYPEER => false,
                    CURLOPT_TIMEOUT => 20,
                ]);
                $res2 = curl_exec($ch2);
                curl_close($ch2);
                $d2 = json_decode((string)$res2, true);
                if (is_array($d2) && empty($d2['detail'])) {
                    $decoded = $d2;
                }
            } catch (Exception $e) {}
        }
    }
    return $decoded;
}


function api_plan_cat(array $plan): string {
    $pCat = strtolower(trim((string)($plan['cat'] ?? '')));
    if ($pCat === '') {
        $pCat = ((int)($plan['days'] ?? 0) === 0) ? 'vip' : 'monthly';
    }
    return $pCat;
}

function api_order_is_test(array $ord): bool {
    $pk = strtolower((string)($ord['plan_key'] ?? ''));
    $cn = strtolower((string)($ord['config_username'] ?? ''));
    return (strpos($pk, 'test') !== false || $pk === 'test_free' || strpos($cn, 'test_') === 0);
}

/** نام پایدار پنل برای سرویس دوم بر اساس دسته */
function api_derive_panel_username(PDO $db, string $base, string $cat): string {
    $base = strtolower(preg_replace('/[^a-z0-9_]/i', '', $base) ?: 'user');
    if (strlen($base) > 20) {
        $base = substr($base, 0, 20);
    }
    $suffix = '';
    if (strpos($cat, 'vol') !== false || $cat === 'volume' || $cat === 'economic') {
        $suffix = '_v';
    } elseif (strpos($cat, 'vip') !== false || strpos($cat, 'unlim') !== false || $cat === 'premium') {
        $suffix = '_u';
    } elseif (strpos($cat, 'month') !== false) {
        $suffix = '_m';
    } else {
        $suffix = '_x';
    }
    $candidate = $base . $suffix;
    // اگر خالی یا تکراری با خود base برای دسته غیر اصلی
    for ($i = 0; $i < 8; $i++) {
        $try = $i === 0 ? $candidate : ($base . $suffix . $i);
        try {
            $st = $db->prepare('SELECT id FROM orders WHERE config_username = ? LIMIT 1');
            $st->execute([$try]);
            if (!$st->fetch()) {
                return $try;
            }
        } catch (Exception $e) {
            return $try;
        }
    }
    return $base . $suffix . substr(bin2hex(random_bytes(2)), 0, 4);
}



/** نام کانفیگ ساخته‌شده توسط ربات (نه ثبت‌نام اختصاصی اپ) */
function api_is_bot_panel_username(string $cn): bool {
    $cn = trim($cn);
    if ($cn === '') return false;
    // الگوهای رایج ربات: user_TELEGRAMID_xx / test_... / man_...
    if (preg_match('/^(user|test|man)_\d+/i', $cn)) return true;
    return false;
}

function api_synth_uid_from_name(string $cn): int {
    return 700000000000 + (abs(crc32(strtolower(trim($cn)))) % 999999999);
}

/**
 * تعیین صاحب منطقی حساب پس از احراز هویت
 * - کانفیگ ربات → user_id تلگرام از orders (اگر باشد)
 * - اکانت اپ → شناسه مصنوعی پایدار از نام ورود
 * خروجی: user_id, channel(telegram|app), login_name, is_bot_config
 */
function api_resolve_owner(PDO $db, string $username, $dbOrder = null, $appAccount = null): array {
    $username = trim($username);
    $loginName = $username;
    if (is_array($appAccount) && !empty($appAccount['config_username'])) {
        $loginName = trim((string)$appAccount['config_username']);
    }

    // نام پایه اگر سرویس مشتق باشد (m02_m → m02)
    $baseName = $username;
    if (strpos($username, '_') !== false && preg_match('/_[mvu]\d*$/i', $username)) {
        $baseName = preg_replace('/_[mvu]\d*$/i', '', $username);
    }

    $telegramUid = 0;
    $probeNames = array_unique(array_filter([$username, $baseName, $loginName]));

    // 1) از سفارش فعلی
    if (is_array($dbOrder) && !empty($dbOrder['user_id'])) {
        $uid = (int)$dbOrder['user_id'];
        if ($uid > 0 && $uid < 700000000000) {
            $telegramUid = $uid;
        }
    }

    // 2) جستجو در سفارش‌ها با نام کانفیگ
    if ($telegramUid <= 0) {
        foreach ($probeNames as $pn) {
            try {
                $st = $db->prepare('SELECT user_id FROM orders WHERE LOWER(config_username) = LOWER(?) ORDER BY id DESC LIMIT 8');
                $st->execute([$pn]);
                foreach ($st->fetchAll(PDO::FETCH_ASSOC) ?: [] as $row) {
                    $uid = (int)($row['user_id'] ?? 0);
                    if ($uid > 0 && $uid < 700000000000) {
                        $telegramUid = $uid;
                        break 2;
                    }
                }
            } catch (Exception $e) {}
        }
    }

    // 3) اگر هنوز پیدا نشد ولی الگوی ربات است، user_id تلگرام را از خود نام استخراج نکن — فقط orders
    $isBot = api_is_bot_panel_username($username) || api_is_bot_panel_username($baseName) || api_is_bot_panel_username($loginName);

    if ($telegramUid > 0) {
        return [
            'user_id' => $telegramUid,
            'channel' => 'telegram',
            'login_name' => $loginName !== '' ? $loginName : $username,
            'is_bot_config' => true,
            'base_name' => $baseName,
        ];
    }

    // اکانت اپ / ناشناس
    $appName = $loginName !== '' ? $loginName : ($baseName !== '' ? $baseName : $username);
    // اگر مشتق بود و base اکانت اپ است
    if (api_is_bot_panel_username($appName)) {
        // نام بات بدون سفارش تلگرام — synth از روی نام (نباید app_accounts شود)
        return [
            'user_id' => api_synth_uid_from_name($appName),
            'channel' => 'app',
            'login_name' => $appName,
            'is_bot_config' => true,
            'base_name' => $baseName,
        ];
    }
    return [
        'user_id' => api_synth_uid_from_name($appName),
        'channel' => 'app',
        'login_name' => $appName,
        'is_bot_config' => false,
        'base_name' => $baseName,
    ];
}


function api_panel_by_id(PDO $db, int $id): array {
    if ($id <= 0) {
        return api_load_default_panel($db);
    }
    try {
        $st = $db->prepare('SELECT * FROM bot_panels WHERE id = ? LIMIT 1');
        $st->execute([$id]);
        $row = $st->fetch(PDO::FETCH_ASSOC);
        if ($row) {
            return $row;
        }
    } catch (Exception $e) {
    }
    return api_load_default_panel($db);
}

function api_load_default_panel(PDO $db): array {
    try {
        $row = $db->query('SELECT * FROM bot_panels WHERE is_default = 1 AND is_active = 1 ORDER BY id ASC LIMIT 1')->fetch(PDO::FETCH_ASSOC);
        if ($row) {
            return $row;
        }
        $row = $db->query('SELECT * FROM bot_panels WHERE is_active = 1 ORDER BY id ASC LIMIT 1')->fetch(PDO::FETCH_ASSOC);
        if ($row) {
            return $row;
        }
    } catch (Exception $e) {
    }
    return api_default_panel_row();
}

function getPanelApiBase($panel = null) {
    if (!is_array($panel)) {
        $panel = api_default_panel_row();
    }
    $direct = rtrim((string)($panel['base_url'] ?? ''), '/');
    if ($direct === '' && defined('PANEL_URL')) {
        $direct = rtrim((string)PANEL_URL, '/');
    }
    // Worker فقط برای پنل پیش‌فرض که با PANEL_URL یکی است
    $useWorker = !empty($panel['use_worker']) || !empty($panel['is_default']);
    if ($useWorker && defined('WORKER_URL') && WORKER_URL) {
        $cfg = defined('PANEL_URL') ? rtrim((string)PANEL_URL, '/') : '';
        if (!empty($panel['is_default']) || $direct === '' || $direct === $cfg) {
            return rtrim((string)WORKER_URL, '/') . '/panel';
        }
    }
    return $direct;
}

function getPanelPublicBase($panel = null) {
    if (!is_array($panel)) {
        $panel = api_default_panel_row();
    }
    if (!empty($panel['public_url'])) {
        return rtrim((string)$panel['public_url'], '/');
    }
    if (!empty($panel['base_url'])) {
        return rtrim((string)$panel['base_url'], '/');
    }
    return defined('PANEL_URL') ? rtrim((string)PANEL_URL, '/') : '';
}

function api_panel_token_bases(array $panel): array {
    $bases = [];
    $direct = rtrim((string)($panel['base_url'] ?? ''), '/');
    if ($direct === '' && defined('PANEL_URL')) {
        $direct = rtrim((string)PANEL_URL, '/');
    }
    if ($direct !== '') {
        $bases[] = $direct;
    }
    $useWorker = !empty($panel['use_worker']) || !empty($panel['is_default']);
    if ($useWorker && defined('WORKER_URL') && WORKER_URL) {
        $cfg = defined('PANEL_URL') ? rtrim((string)PANEL_URL, '/') : '';
        if (!empty($panel['is_default']) || $direct === '' || $direct === $cfg) {
            $w = rtrim((string)WORKER_URL, '/') . '/panel';
            if (!in_array($w, $bases, true)) {
                $bases[] = $w;
            }
        }
    }
    return $bases;
}

function clientIp() {
    return $_SERVER['HTTP_CF_CONNECTING_IP']
        ?? $_SERVER['HTTP_X_FORWARDED_FOR']
        ?? $_SERVER['REMOTE_ADDR']
        ?? '0.0.0.0';
}

function rateLimitOrFail($max = 40, $window = 60) {
    $dir = sys_get_temp_dir() . '/jetconfig_api_rl';
    if (!is_dir($dir)) {
        @mkdir($dir, 0755, true);
    }
    $ip = preg_replace('/[^0-9a-fA-F:\.]/', '_', clientIp());
    $file = $dir . '/' . md5($ip) . '.json';
    $now = time();
    $data = ['t' => $now, 'c' => 0];
    if (is_file($file)) {
        $raw = @file_get_contents($file);
        $j = json_decode((string)$raw, true);
        if (is_array($j) && isset($j['t'], $j['c']) && ($now - (int)$j['t']) < $window) {
            $data = $j;
        }
    }
    if (($now - (int)$data['t']) >= $window) {
        $data = ['t' => $now, 'c' => 0];
    }
    $data['c'] = (int)$data['c'] + 1;
    @file_put_contents($file, json_encode($data), LOCK_EX);
    if ($data['c'] > $max) {
        apiFail('تعداد درخواست‌ها زیاد است. کمی بعد تلاش کنید.', 429);
    }
}

function readInput() {
    $username = '';
    $password = '';
    $apiKey = $_SERVER['HTTP_X_API_KEY'] ?? '';

    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
        $ct = $_SERVER['CONTENT_TYPE'] ?? $_SERVER['HTTP_CONTENT_TYPE'] ?? '';
        if (stripos($ct, 'application/json') !== false) {
            $body = json_decode((string)file_get_contents('php://input'), true) ?: [];
            $username = trim((string)($body['username'] ?? ''));
            $password = trim((string)($body['password'] ?? ''));
            if ($apiKey === '' && isset($body['api_key'])) {
                $apiKey = (string)$body['api_key'];
            }
        } else {
            $username = trim((string)($_POST['username'] ?? ''));
            $password = trim((string)($_POST['password'] ?? ''));
            if ($apiKey === '' && isset($_POST['api_key'])) {
                $apiKey = (string)$_POST['api_key'];
            }
            // body JSON بدون هدر درست
            if ($username === '' && $password === '') {
                $raw = file_get_contents('php://input');
                if ($raw) {
                    $body = json_decode((string)$raw, true);
                    if (is_array($body)) {
                        $username = trim((string)($body['username'] ?? ''));
                        $password = trim((string)($body['password'] ?? ''));
                        if ($apiKey === '' && isset($body['api_key'])) {
                            $apiKey = (string)$body['api_key'];
                        }
                    }
                }
            }
        }
    }

    // پشتیبان: query string (حتی روی POST) — اپ گاهی فقط URL می‌فرستد
    if ($username === '') {
        $username = trim((string)($_GET['username'] ?? ''));
    }
    if ($password === '') {
        $password = trim((string)($_GET['password'] ?? ''));
    }
    if ($apiKey === '' && isset($_GET['api_key'])) {
        $apiKey = (string)$_GET['api_key'];
    }

    return [$username, $password, trim($apiKey)];
}

list($username, $password, $apiKey) = readInput();

// اکشن‌های عمومی بدون نیاز به api_key (لیست پلن + تیکت پشتیبانی)
$actionQuick = '';
if (!empty($_GET['action'])) {
    $actionQuick = trim((string)$_GET['action']);
} elseif (!empty($_POST['action'])) {
    $actionQuick = trim((string)$_POST['action']);
}
$publicActions = ['list_plans', 'ticket_create', 'ticket_list', 'ticket_thread', 'ticket_reply'];
$isPublicAction = in_array($actionQuick, $publicActions, true);

rateLimitOrFail($isPublicAction ? 20 : 40, 60);

if (!$isPublicAction && defined('APP_API_KEY') && APP_API_KEY !== '') {
    if (!hash_equals((string)APP_API_KEY, (string)$apiKey)) {
        apiFail('دسترسی غیرمجاز', 401);
    }
}


// —— لیست پلن‌های قابل خرید (فاز B) — بدون لاگین
if ($actionQuick === 'list_plans') {
    try {
        $db = new PDO(
            "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4",
            DB_USER,
            DB_PASS,
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]
        );
        $rows = [];
        try {
            $rows = $db->query("SELECT plan_key, title, price, vol, days, cat, panel_id, sort_order, is_active FROM bot_plans WHERE is_active = 1 ORDER BY sort_order ASC, id ASC")->fetchAll();
        } catch (Exception $e) {
            try {
                $rows = $db->query("SELECT * FROM bot_plans WHERE is_active = 1 ORDER BY id ASC")->fetchAll();
            } catch (Exception $e2) {
                $rows = [];
            }
        }

        // دسته‌های فعال per-panel + متای سراسری
        $catActive = []; // "panelId|cat" => bool
        $catTitles = []; // "panelId|cat" => title
        try {
            foreach ($db->query('SELECT panel_id, cat_key, title, is_active FROM bot_plan_categories')->fetchAll() as $c) {
                $k = (int)$c['panel_id'] . '|' . strtolower(trim((string)$c['cat_key']));
                $catActive[$k] = ((int)($c['is_active'] ?? 1) === 1);
                if (!empty($c['title'])) {
                    $catTitles[$k] = (string)$c['title'];
                }
            }
        } catch (Exception $e) {}
        $metaEnabled = []; // cat_key => 0/1
        try {
            $st = $db->prepare("SELECT setting_value FROM settings WHERE setting_key = 'plan_category_meta' LIMIT 1");
            $st->execute();
            $raw = $st->fetchColumn();
            if ($raw) {
                $j = json_decode((string)$raw, true);
                if (is_array($j)) {
                    foreach ($j as $ck => $info) {
                        if (is_array($info) && array_key_exists('enabled', $info)) {
                            $metaEnabled[strtolower((string)$ck)] = (int)$info['enabled'];
                        }
                    }
                }
            }
        } catch (Exception $e) {}

        $out = [];
        foreach ($rows as $r) {
            if (isset($r['is_active']) && (int)$r['is_active'] !== 1) {
                continue;
            }
            $key = (string)($r['plan_key'] ?? '');
            if ($key === '') continue;
            $kl = strtolower($key);
            $title = (string)($r['title'] ?? $key);
            $tl = mb_strtolower($title);
            $vol = isset($r['vol']) ? (float)$r['vol'] : (float)($r['volume_gb'] ?? 0);
            $days = (int)($r['days'] ?? 0);
            if (strpos($kl, 'test') !== false || strpos($tl, 'تست') !== false || strpos($tl, 'آزمایش') !== false) {
                continue;
            }
            if ($vol > 0 && $vol <= 0.15 && $days > 0 && $days <= 2) {
                continue;
            }
            $price = (int)($r['price'] ?? 0);
            if ($price <= 0) continue;

            $cat = strtolower(trim((string)($r['cat'] ?? '')));
            $panelId = (int)($r['panel_id'] ?? 0);
            // دسته مخفی سراسری
            if ($cat !== '' && isset($metaEnabled[$cat]) && (int)$metaEnabled[$cat] === 0) {
                continue;
            }
            // دسته مخفی per-panel
            $ck = $panelId . '|' . $cat;
            if ($cat !== '' && array_key_exists($ck, $catActive) && $catActive[$ck] === false) {
                continue;
            }
            // اگر panel_id صفر بود، هر پنلی که این cat را مخفی کرده کافی است رد نشود مگر همه مخفی - ساده: فقط meta

            $catTitle = $catTitles[$ck] ?? '';
            if ($catTitle === '') {
                if (in_array($cat, ['monthly', 'month'], true) || strpos($cat, 'month') !== false) {
                    $catTitle = 'ماهانه';
                } elseif (in_array($cat, ['vip', 'unlimited'], true) || strpos($cat, 'vip') !== false || strpos($cat, 'unlim') !== false) {
                    $catTitle = 'نامحدود / VIP';
                } elseif (in_array($cat, ['volume', 'vol'], true) || strpos($cat, 'vol') !== false) {
                    $catTitle = 'حجمی';
                } elseif ($cat === 'economic' || strpos($cat, 'econ') !== false) {
                    $catTitle = 'اقتصادی';
                } elseif ($cat === 'premium' || strpos($cat, 'prem') !== false) {
                    $catTitle = 'پریمیوم';
                } elseif ($cat !== '') {
                    $catTitle = $cat;
                } else {
                    $catTitle = 'سایر';
                    $cat = 'other';
                }
            }

            $out[] = [
                'plan_key' => $key,
                'title' => $title,
                'price' => $price,
                'price_fmt' => number_format($price),
                'vol' => $vol,
                'days' => $days,
                'cat' => $cat !== '' ? $cat : 'other',
                'cat_title' => $catTitle,
                'label' => $title . ' — ' . number_format($price) . ' تومان',
            ];
        }
        $groups = [];
        foreach ($out as $pl) {
            $ck = $pl['cat'];
            if (!isset($groups[$ck])) {
                $groups[$ck] = ['cat' => $ck, 'title' => $pl['cat_title'], 'plans' => []];
            }
            $groups[$ck]['plans'][] = $pl;
        }
        $groupsList = array_values($groups);
        echo json_encode([
            'ok' => true,
            'plans' => $out,
            'groups' => $groupsList,
            'count' => count($out),
        ], JSON_UNESCAPED_UNICODE);
        exit();
    } catch (Exception $e) {
        apiFail('خطا در دریافت پلن‌ها', 500);
    }
}



// —— تیکت پشتیبانی اپ (بدون لاگین اجباری)
if (in_array($actionQuick, ['ticket_create', 'ticket_list', 'ticket_thread', 'ticket_reply'], true)) {
    try {
        $db = new PDO(
            "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4",
            DB_USER,
            DB_PASS,
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]
        );
        $db->exec("CREATE TABLE IF NOT EXISTS app_tickets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            device_id VARCHAR(64) NOT NULL,
            username VARCHAR(64) NULL,
            email VARCHAR(120) NULL,
            subject VARCHAR(200) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'open',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_device (device_id),
            KEY idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
        $db->exec("CREATE TABLE IF NOT EXISTS app_ticket_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ticket_id INT NOT NULL,
            sender VARCHAR(16) NOT NULL,
            body TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            KEY idx_ticket (ticket_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

        $deviceId = '';
        if (!empty($_POST['device_id'])) $deviceId = trim((string)$_POST['device_id']);
        elseif (!empty($_GET['device_id'])) $deviceId = trim((string)$_GET['device_id']);
        $deviceId = preg_replace('/[^a-zA-Z0-9_\-]/', '', $deviceId);
        if (strlen($deviceId) < 8 || strlen($deviceId) > 64) {
            apiFail('شناسه دستگاه نامعتبر است');
        }

        if ($actionQuick === 'ticket_create') {
            $subject = trim((string)($_POST['subject'] ?? $_GET['subject'] ?? ''));
            $body = trim((string)($_POST['body'] ?? $_GET['body'] ?? ''));
            $uname = trim((string)($_POST['username'] ?? $_GET['username'] ?? ''));
            $email = trim((string)($_POST['email'] ?? $_GET['email'] ?? ''));
            if (mb_strlen($subject) < 3 || mb_strlen($subject) > 120) {
                apiFail('موضوع تیکت باید ۳ تا ۱۲۰ کاراکتر باشد');
            }
            if (mb_strlen($body) < 3 || mb_strlen($body) > 2000) {
                apiFail('متن پیام باید ۳ تا ۲۰۰۰ کاراکتر باشد');
            }
            if ($email !== '') {
                if (strpos($email, '@') !== false) {
                    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
                        apiFail('ایمیل نامعتبر است');
                    }
                } else {
                    $digits = preg_replace('/[^0-9+]/', '', $email);
                    if (strlen($digits) < 8) {
                        apiFail('شماره تماس نامعتبر است');
                    }
                }
            }
            if ($uname !== '' && !preg_match('/^[A-Za-z][A-Za-z0-9_]{2,31}$/', $uname)) {
                $uname = '';
            }
            // سقف ۳ تیکت باز در ۲۴ ساعت برای هر دستگاه
            $st = $db->prepare("SELECT COUNT(*) FROM app_tickets WHERE device_id = ? AND status IN ('open','answered') AND created_at >= (NOW() - INTERVAL 1 DAY)");
            $st->execute([$deviceId]);
            if ((int)$st->fetchColumn() >= 3) {
                apiFail('امروز بیش از ۳ تیکت باز ثبت کرده‌اید. منتظر پاسخ بمانید یا فردا دوباره تلاش کنید.', 429);
            }
            $db->prepare('INSERT INTO app_tickets (device_id, username, email, subject, status) VALUES (?,?,?,?,?)')
               ->execute([$deviceId, $uname !== '' ? $uname : null, $email !== '' ? $email : null, $subject, 'open']);
            $tid = (int)$db->lastInsertId();
            $db->prepare('INSERT INTO app_ticket_messages (ticket_id, sender, body) VALUES (?,?,?)')
               ->execute([$tid, 'user', $body]);
            // اطلاع به ادمین‌های تلگرام
            try {
                $unameShow = $uname !== '' ? $uname : '—';
                $mailShow = $email !== '' ? $email : '—';
                $preview = mb_substr($body, 0, 180);
                $adminText = "🎫 <b>تیکت جدید از اپ</b>\n"
                    . "━━━━━━━━━━━━━━\n"
                    . "🆔 تیکت: <code>#{$tid}</code>\n"
                    . "👤 کاربر: <code>{$unameShow}</code>\n"
                    . "📧 تماس: <code>{$mailShow}</code>\n"
                    . "📝 موضوع: " . htmlspecialchars($subject, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . "\n\n"
                    . "💬 " . htmlspecialchars($preview, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . "\n\n"
                    . "🖥 پاسخ در پنل وب:\n"
                    . "https://majid6064.ir/webadmin/tickets.php?id={$tid}";
                api_notify_admins($db, $adminText);
            } catch (Exception $e) {}
            echo json_encode(['ok' => true, 'ticket_id' => $tid, 'msg' => 'تیکت ثبت شد. پاسخ ادمین را از بخش پشتیبانی ببینید.'], JSON_UNESCAPED_UNICODE);
            exit();
        }

        if ($actionQuick === 'ticket_list') {
            $st = $db->prepare('SELECT id, subject, status, username, created_at, updated_at FROM app_tickets WHERE device_id = ? ORDER BY updated_at DESC LIMIT 50');
            $st->execute([$deviceId]);
            $rows = $st->fetchAll() ?: [];
            echo json_encode(['ok' => true, 'tickets' => $rows, 'count' => count($rows)], JSON_UNESCAPED_UNICODE);
            exit();
        }

        if ($actionQuick === 'ticket_thread' || $actionQuick === 'ticket_reply') {
            $tid = (int)($_POST['ticket_id'] ?? $_GET['ticket_id'] ?? 0);
            if ($tid <= 0) apiFail('شناسه تیکت نامعتبر');
            $st = $db->prepare('SELECT * FROM app_tickets WHERE id = ? AND device_id = ? LIMIT 1');
            $st->execute([$tid, $deviceId]);
            $ticket = $st->fetch();
            if (!$ticket) apiFail('تیکت یافت نشد', 404);

            if ($actionQuick === 'ticket_reply') {
                $body = trim((string)($_POST['body'] ?? ''));
                if (mb_strlen($body) < 2 || mb_strlen($body) > 2000) {
                    apiFail('متن پاسخ نامعتبر است');
                }
                if (($ticket['status'] ?? '') === 'closed') {
                    apiFail('این تیکت بسته شده است');
                }
                $db->prepare('INSERT INTO app_ticket_messages (ticket_id, sender, body) VALUES (?,?,?)')
                   ->execute([$tid, 'user', $body]);
                $db->prepare("UPDATE app_tickets SET status = 'open', updated_at = NOW() WHERE id = ?")->execute([$tid]);
                $ticket['status'] = 'open';
                try {
                    $unameShow = (string)($ticket['username'] ?? '—') ?: '—';
                    $preview = mb_substr($body, 0, 180);
                    $adminText = "💬 <b>پاسخ جدید کاربر روی تیکت اپ</b>\n"
                        . "🆔 تیکت: <code>#{$tid}</code>\n"
                        . "👤 <code>{$unameShow}</code>\n"
                        . "📝 " . htmlspecialchars($preview, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8') . "\n\n"
                        . "🖥 https://majid6064.ir/webadmin/tickets.php?id={$tid}";
                    api_notify_admins($db, $adminText);
                } catch (Exception $e) {}
            }

            $stM = $db->prepare('SELECT id, sender, body, created_at FROM app_ticket_messages WHERE ticket_id = ? ORDER BY id ASC LIMIT 200');
            $stM->execute([$tid]);
            $msgs = $stM->fetchAll() ?: [];
            echo json_encode([
                'ok' => true,
                'ticket' => [
                    'id' => (int)$ticket['id'],
                    'subject' => $ticket['subject'],
                    'status' => $ticket['status'],
                    'username' => $ticket['username'],
                    'created_at' => $ticket['created_at'],
                    'updated_at' => $ticket['updated_at'],
                ],
                'messages' => $msgs,
            ], JSON_UNESCAPED_UNICODE);
            exit();
        }
    } catch (Exception $e) {
        apiFail('خطا در سیستم تیکت', 500);
    }
}


if ($username === '') {
    apiFail('نام کاربری وارد نشده است');
}
if ($password === '') {
    apiFail('رمز عبور وارد نشده است');
}

try {
    $db = new PDO(
        "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4",
        DB_USER,
        DB_PASS,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
        ]
    );

    // panel_id و sub_link برای پنل درست (پاسارگاد / فرداد / …)
    try {
        $stmt = $db->prepare("SELECT password, volume_gb, days, panel_id, sub_link, config_username, user_id FROM orders WHERE LOWER(config_username) = LOWER(?) ORDER BY id DESC LIMIT 1");
        $stmt->execute([$username]);
        $dbOrder = $stmt->fetch();
    } catch (Exception $e) {
        // ستون panel_id ممکن است در نسخه‌های خیلی قدیمی نباشد
        $stmt = $db->prepare("SELECT password, volume_gb, days FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 1");
        $stmt->execute([$username]);
        $dbOrder = $stmt->fetch();
        if (is_array($dbOrder)) {
            $dbOrder['panel_id'] = null;
            $dbOrder['sub_link'] = null;
        }
    }

    // جدول حساب‌های ثبت‌نام‌شده از اپ (بدون ساخت پنل تا قبل از خرید)
    try {
        $db->exec(
            "CREATE TABLE IF NOT EXISTS app_accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                config_username VARCHAR(64) NOT NULL,
                password VARCHAR(64) NOT NULL,
                email VARCHAR(120) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login_at DATETIME NULL,
                UNIQUE KEY uq_app_user (config_username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        );
    } catch (Exception $e) {}
    try { $db->exec("ALTER TABLE app_accounts ADD COLUMN email VARCHAR(120) NULL"); } catch (Exception $e) {}

    $action = '';
    if (!empty($_GET['action'])) {
        $action = trim((string)$_GET['action']);
    } elseif (!empty($_POST['action'])) {
        $action = trim((string)$_POST['action']);
    } else {
        $rawBodyEarly = file_get_contents('php://input');
        if ($rawBodyEarly) {
            $jbEarly = json_decode($rawBodyEarly, true);
            if (is_array($jbEarly) && !empty($jbEarly['action'])) {
                $action = trim((string)$jbEarly['action']);
            }
        }
    }

    $appAccount = null;
    $appLoginUsername = $username; // یوزر ورود اپ (ممکن است با نام سرویس پنل فرق کند)
    try {
        $stApp = $db->prepare('SELECT id, config_username, password FROM app_accounts WHERE LOWER(config_username) = LOWER(?) LIMIT 1');
        $stApp->execute([$username]);
        $appAccount = $stApp->fetch(PDO::FETCH_ASSOC) ?: null;
    } catch (Exception $e) {
        $appAccount = null;
    }

    // سفارش این یوزرنیم (با حساسیت کمتر به حروف)
    if (empty($dbOrder) || empty($dbOrder['password'])) {
        try {
            $stO0 = $db->prepare('SELECT * FROM orders WHERE LOWER(config_username) = LOWER(?) ORDER BY id DESC LIMIT 1');
            $stO0->execute([$username]);
            $row0 = $stO0->fetch(PDO::FETCH_ASSOC);
            if ($row0) {
                $dbOrder = $row0;
            }
        } catch (Exception $e) {}
    }

    // سرویس مشتق (m02_m و ...) یا یوزر ربات بدون ردیف app_accounts
    $relatedOrderPasswords = [];
    if (is_array($dbOrder) && !empty($dbOrder['password'])) {
        $relatedOrderPasswords[] = (string)$dbOrder['password'];
    }
    try {
        $ordSec = null;
        if (is_array($dbOrder) && !empty($dbOrder['config_username'])) {
            $ordSec = $dbOrder;
        } else {
            $stO = $db->prepare('SELECT * FROM orders WHERE LOWER(config_username) = LOWER(?) ORDER BY id DESC LIMIT 1');
            $stO->execute([$username]);
            $ordSec = $stO->fetch(PDO::FETCH_ASSOC) ?: null;
        }
        if ($ordSec) {
            $uidSec = (int)($ordSec['user_id'] ?? 0);
            // همه سفارش‌های همین user_id → رمزهای قابل قبول
            if ($uidSec > 0) {
                try {
                    $stR = $db->prepare('SELECT config_username, password FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 30');
                    $stR->execute([$uidSec]);
                    foreach ($stR->fetchAll(PDO::FETCH_ASSOC) ?: [] as $rr) {
                        if (!empty($rr['password'])) {
                            $relatedOrderPasswords[] = (string)$rr['password'];
                        }
                    }
                } catch (Exception $e) {}
            }
            // base از نام مشتق (m02 از m02_m)
            $baseGuess = $username;
            if (strpos($username, '_') !== false) {
                $baseGuess = preg_replace('/_[a-z0-9]+$/i', '', $username);
            }
            if ($baseGuess !== '' && strcasecmp($baseGuess, $username) !== 0) {
                try {
                    $stB = $db->prepare('SELECT * FROM orders WHERE LOWER(config_username) = LOWER(?) ORDER BY id DESC LIMIT 5');
                    $stB->execute([$baseGuess]);
                    foreach ($stB->fetchAll(PDO::FETCH_ASSOC) ?: [] as $br) {
                        if (!empty($br['password'])) {
                            $relatedOrderPasswords[] = (string)$br['password'];
                        }
                    }
                } catch (Exception $e) {}
                if (!$appAccount) {
                    try {
                        $stBA = $db->prepare('SELECT id, config_username, password FROM app_accounts WHERE LOWER(config_username) = LOWER(?) LIMIT 1');
                        $stBA->execute([$baseGuess]);
                        $arB = $stBA->fetch(PDO::FETCH_ASSOC);
                        if ($arB) {
                            $appAccount = $arB;
                            $appLoginUsername = (string)$arB['config_username'];
                        }
                    } catch (Exception $e) {}
                }
            }
            // app_accounts با user_id مصنوعی یکسان
            if (!$appAccount && $uidSec >= 700000000000) {
                try {
                    $rowsA = $db->query('SELECT id, config_username, password FROM app_accounts')->fetchAll(PDO::FETCH_ASSOC) ?: [];
                    foreach ($rowsA as $ar) {
                        $su = 700000000000 + (abs(crc32(strtolower((string)$ar['config_username']))) % 999999999);
                        if ($su === $uidSec) {
                            $appAccount = $ar;
                            $appLoginUsername = (string)$ar['config_username'];
                            break;
                        }
                    }
                } catch (Exception $e) {}
            }
            if (empty($dbOrder)) {
                $dbOrder = $ordSec;
            }
        }
    } catch (Exception $e) {}
    $relatedOrderPasswords = array_values(array_unique(array_filter($relatedOrderPasswords)));

    // ثبت‌نام از اپ — فقط DB
    if ($action === 'register') {
        $uLen = mb_strlen($username);
        if ($uLen < 4 || $uLen > 32) {
            apiFail('نام کاربری باید ۴ تا ۳۲ کاراکتر باشد');
        }
        if (!preg_match('/^[A-Za-z][A-Za-z0-9_]*$/', $username)) {
            apiFail('نام کاربری با حرف انگلیسی شروع شود و فقط حرف، عدد و _ باشد');
        }
        $pLen = mb_strlen($password);
        if ($pLen < 5 || $pLen > 8) {
            apiFail('رمز باید ۵ تا ۸ کاراکتر باشد');
        }
        if (!preg_match('/^[A-Za-z0-9]+$/', $password)) {
            apiFail('رمز فقط حرف و عدد انگلیسی باشد');
        }
        $reserved = ['admin', 'root', 'test', 'support', 'jet', 'jetvpn', 'api', 'null', 'undefined'];
        if (in_array(strtolower($username), $reserved, true)) {
            apiFail('این نام کاربری مجاز نیست');
        }
        // یکتایی سخت: اپ + سفارش + پنل(ها)
        try {
            $stDup = $db->prepare('SELECT config_username FROM app_accounts WHERE LOWER(config_username) = LOWER(?) LIMIT 1');
            $stDup->execute([$username]);
            if ($stDup->fetch()) {
                apiFail('این نام کاربری قبلاً ثبت شده. وارد شوید یا نام دیگری انتخاب کنید.', 409);
            }
        } catch (Exception $e) {
            if ($appAccount) {
                apiFail('این نام کاربری قبلاً ثبت شده. وارد شوید.', 409);
            }
        }
        try {
            $stDup2 = $db->prepare('SELECT config_username FROM orders WHERE LOWER(config_username) = LOWER(?) LIMIT 1');
            $stDup2->execute([$username]);
            if ($stDup2->fetch() || $dbOrder) {
                apiFail('این نام کاربری قبلاً برای یک سرویس استفاده شده. نام دیگری انتخاب کنید.', 409);
            }
        } catch (Exception $e) {
            if ($dbOrder) {
                apiFail('این نام کاربری قبلاً ثبت شده. نام دیگری انتخاب کنید.', 409);
            }
        }
        // بررسی روی همه پنل‌های فعال (کوتاه؛ اگر پنل پاسخ نداد مانع ثبت‌نام نمی‌شود)
        try {
            $panels = [];
            try {
                $panels = $db->query('SELECT * FROM bot_panels WHERE is_active = 1 ORDER BY is_default DESC, id ASC')->fetchAll();
            } catch (Exception $e) {
                $panels = [api_load_default_panel($db)];
            }
            if (!$panels) {
                $panels = [api_load_default_panel($db)];
            }
            foreach ($panels as $panelProbe) {
                if (!is_array($panelProbe) || empty($panelProbe)) {
                    continue;
                }
                $tok = getPanelToken($panelProbe);
                if (!$tok) {
                    continue;
                }
                $apiBaseP = !empty($GLOBALS['_api_panel_base'])
                    ? (string)$GLOBALS['_api_panel_base']
                    : getPanelApiBase($panelProbe);
                $chp = curl_init(rtrim($apiBaseP, '/') . '/api/user/' . rawurlencode($username));
                curl_setopt_array($chp, [
                    CURLOPT_RETURNTRANSFER => true,
                    CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $tok, 'Accept: application/json'],
                    CURLOPT_SSL_VERIFYPEER => false,
                    CURLOPT_TIMEOUT => 8,
                ]);
                $rp = curl_exec($chp);
                curl_close($chp);
                $jp = json_decode((string)$rp, true);
                if (is_array($jp) && !empty($jp['username'])) {
                    apiFail('این نام کاربری روی سرور قبلاً گرفته شده. لطفاً نام دیگری انتخاب کنید.', 409);
                }
            }
        } catch (Exception $e) {}

        // تماس اختیاری: ایمیل یا شماره موبایل
        $email = '';
        if (!empty($_POST['email'])) $email = trim((string)$_POST['email']);
        elseif (!empty($_GET['email'])) $email = trim((string)$_GET['email']);
        elseif (!empty($_POST['contact'])) $email = trim((string)$_POST['contact']);
        elseif (!empty($_GET['contact'])) $email = trim((string)$_GET['contact']);
        if ($email !== '') {
            if (mb_strlen($email) > 120) {
                apiFail('اطلاعات تماس خیلی طولانی است');
            }
            if (strpos($email, '@') !== false) {
                if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
                    apiFail('ایمیل نامعتبر است. خالی بگذارید یا درست وارد کنید.');
                }
            } else {
                $digits = preg_replace('/[^0-9+]/', '', $email);
                if (strlen($digits) < 8 || strlen($digits) > 15) {
                    apiFail('شماره تماس نامعتبر است (۸ تا ۱۵ رقم).');
                }
            }
        }

        try {
            try {
                $ins = $db->prepare('INSERT INTO app_accounts (config_username, password, email) VALUES (?, ?, ?)');
                $ins->execute([$username, $password, $email !== '' ? $email : null]);
            } catch (Exception $eCol) {
                $ins = $db->prepare('INSERT INTO app_accounts (config_username, password) VALUES (?, ?)');
                $ins->execute([$username, $password]);
            }
        } catch (Exception $e) {
            apiFail('ثبت‌نام ناموفق بود. نام دیگری امتحان کنید.', 500);
        }

        // ردیف users برای دیده شدن در وب/ربات (user_id مصنوعی اپ)
        $synthUid = 700000000000 + (abs(crc32(strtolower($username))) % 999999999);
        try {
            $db->prepare('INSERT IGNORE INTO users (user_id, username, balance, has_bought, has_used_test) VALUES (?, ?, 0, 0, 0)')
               ->execute([$synthUid, $username]);
            try {
                $db->prepare("UPDATE users SET username = ? WHERE user_id = ? AND (username IS NULL OR username = '')")
                   ->execute([$username, $synthUid]);
            } catch (Exception $e) {}
        } catch (Exception $e) {
            try {
                $db->prepare('INSERT IGNORE INTO users (user_id, username) VALUES (?, ?)')->execute([$synthUid, $username]);
            } catch (Exception $e2) {}
        }

        echo json_encode([
            'ok' => true,
            'registered' => true,
            'has_subscription' => false,
            'has_used_test' => 0,
            'can_claim_test' => true,
            'can_renew' => false,
            'is_test_service' => false,
            'username' => $username,
            'status' => 'no_subscription',
            'panel_status' => 'no_subscription',
            'total_gb' => 0,
            'used_gb' => 0,
            'remaining_gb' => 0,
            'expire_days' => 'بدون اشتراک',
            'expire_ts' => 0,
            'servers' => [],
            'servers_count' => 0,
            'msg' => 'حساب ساخته شد. هنوز اشتراک فعالی ندارید.',
        ], JSON_UNESCAPED_UNICODE);
        exit();
    }

    // قبول رمز: app_accounts یا هر سفارش مرتبط (اصلی / مشتق / ربات)
    $passOk = false;
    if (!empty($appAccount['password']) && hash_equals((string)$appAccount['password'], $password)) {
        $passOk = true;
    }
    if (!$passOk) {
        foreach ($relatedOrderPasswords as $rp) {
            if ($rp !== '' && hash_equals($rp, $password)) {
                $passOk = true;
                break;
            }
        }
    }
    if (!$passOk && is_array($dbOrder) && !empty($dbOrder['password']) && hash_equals((string)$dbOrder['password'], $password)) {
        $passOk = true;
    }
    // حساب فقط-اپ بدون سفارش
    if (!$passOk && !empty($appAccount['password']) && empty($dbOrder)) {
        $passOk = hash_equals((string)$appAccount['password'], $password);
    }
    if (!$passOk) {
        // آخرین حلقه: اگر اصلاً سفارشی نیست و app_accounts نیست
        if (empty($appAccount) && empty($dbOrder)) {
            apiFail('نام کاربری یافت نشد. ثبت‌نام کنید یا از نام کاربری ربات/اپ استفاده کنید.', 404);
        }
        apiFail('رمز عبور وارد شده نادرست است', 403);
    }

    // همگام‌سازی app_accounts — فقط برای اکانت واقعی اپ (نه user_xxx / test_xxx ربات)
    try {
        $syncName = $appLoginUsername !== '' ? $appLoginUsername : $username;
        if (strpos($syncName, '_') !== false && preg_match('/_[a-z0-9]+$/i', $syncName)) {
            $baseSync = preg_replace('/_[a-z0-9]+$/i', '', $syncName);
            if ($baseSync !== '') {
                $stBs = $db->prepare('SELECT config_username FROM orders WHERE LOWER(config_username) = LOWER(?) LIMIT 1');
                $stBs->execute([$baseSync]);
                if ($stBs->fetch()) {
                    $syncName = $baseSync;
                }
            }
        }
        // یوزرنیم‌های پنل ربات: ورود OK است ولی لیست «اکانت‌های اپ» را شلوغ نکن
        $isBotPanelName = api_is_bot_panel_username($syncName);
        $stEx = $db->prepare('SELECT id, password, config_username FROM app_accounts WHERE LOWER(config_username) = LOWER(?) LIMIT 1');
        $stEx->execute([$syncName]);
        $ex = $stEx->fetch(PDO::FETCH_ASSOC);
        if ($ex) {
            try {
                $db->prepare('UPDATE app_accounts SET last_login_at = NOW() WHERE id = ?')->execute([(int)$ex['id']]);
            } catch (Exception $e) {}
            if (!$appAccount) {
                $appAccount = $ex;
                $appLoginUsername = (string)$ex['config_username'];
            }
        } elseif (!$isBotPanelName && $syncName !== '') {
            // اگر این نام کانفیگ متعلق به کاربر تلگرام است → app_accounts نساز
            $ownedByTelegram = false;
            try {
                $stTg = $db->prepare('SELECT user_id FROM orders WHERE LOWER(config_username) = LOWER(?) ORDER BY id DESC LIMIT 8');
                $stTg->execute([$syncName]);
                foreach ($stTg->fetchAll(PDO::FETCH_ASSOC) ?: [] as $tr) {
                    $tu = (int)($tr['user_id'] ?? 0);
                    if ($tu > 0 && $tu < 700000000000) {
                        $ownedByTelegram = true;
                        break;
                    }
                }
            } catch (Exception $e) {}
            if (!$ownedByTelegram) {
                try {
                    $db->prepare('INSERT INTO app_accounts (config_username, password, last_login_at) VALUES (?, ?, NOW())')
                       ->execute([$syncName, $password]);
                } catch (Exception $eIns) {
                    try {
                        $db->prepare('INSERT INTO app_accounts (config_username, password) VALUES (?, ?)')
                           ->execute([$syncName, $password]);
                    } catch (Exception $e2) {}
                }
                $appLoginUsername = $syncName;
            }
        }
    } catch (Exception $e) {}

    // صاحب منطقی حساب (تلگرام یا اپ) — برای خرید/تست/لیست سرویس
    $owner = api_resolve_owner($db, $username, is_array($dbOrder) ? $dbOrder : null, is_array($appAccount) ? $appAccount : null);
    $ownerUserId = (int)$owner['user_id'];
    $ownerChannel = (string)$owner['channel'];
    $ownerLoginName = (string)$owner['login_name'];
    $ownerIsBotConfig = !empty($owner['is_bot_config']);
    if ($ownerLoginName !== '') {
        $appLoginUsername = $ownerLoginName;
    }

    // —— تغییر رمز ورود اپ (۵ تا ۸ کاراکتر حرف/عدد)
    $action = '';
    if (!empty($_GET['action'])) {
        $action = trim((string)$_GET['action']);
    } elseif (!empty($_POST['action'])) {
        $action = trim((string)$_POST['action']);
    } else {
        $rawBody = file_get_contents('php://input');
        if ($rawBody) {
            $jb = json_decode($rawBody, true);
            if (is_array($jb) && !empty($jb['action'])) {
                $action = trim((string)$jb['action']);
            }
        }
    }
    if ($action === 'change_password') {
        $newPass = '';
        if (!empty($_POST['new_password'])) {
            $newPass = trim((string)$_POST['new_password']);
        } elseif (!empty($_GET['new_password'])) {
            $newPass = trim((string)$_GET['new_password']);
        } else {
            $rawBody = file_get_contents('php://input');
            if ($rawBody) {
                $jb = json_decode($rawBody, true);
                if (is_array($jb)) {
                    $newPass = trim((string)($jb['new_password'] ?? ''));
                }
            }
        }
        $len = mb_strlen($newPass);
        if ($len < 5 || $len > 8) {
            apiFail('رمز جدید باید ۵ تا ۸ کاراکتر باشد');
        }
        if (!preg_match('/^[A-Za-z0-9]+$/', $newPass)) {
            apiFail('رمز فقط حرف و عدد انگلیسی باشد (بدون فاصله و نماد)');
        }
        if (hash_equals($expectedPassword, $newPass)) {
            apiFail('رمز جدید نباید با رمز فعلی یکی باشد');
        }
        try {
            $up = $db->prepare('UPDATE orders SET password = ? WHERE config_username = ?');
            $up->execute([$newPass, $username]);
            $pwOk = $up->rowCount() > 0;
            try {
                $upA = $db->prepare('UPDATE app_accounts SET password = ? WHERE config_username = ?');
                $upA->execute([$newPass, $username]);
                if ($upA->rowCount() > 0) $pwOk = true;
            } catch (Exception $eA) {}
            if (!$pwOk) {
                $chk = $db->prepare('SELECT id FROM orders WHERE config_username = ? AND password = ? LIMIT 1');
                $chk->execute([$username, $newPass]);
                $chkA = false;
                try {
                    $stA = $db->prepare('SELECT id FROM app_accounts WHERE config_username = ? AND password = ? LIMIT 1');
                    $stA->execute([$username, $newPass]);
                    $chkA = (bool)$stA->fetch();
                } catch (Exception $eB) {}
                if (!$chk->fetch() && !$chkA) {
                    apiFail('به‌روزرسانی رمز ناموفق بود', 500);
                }
            }
        } catch (Exception $e) {
            apiFail('خطا در ذخیره رمز جدید', 500);
        }
        echo json_encode([
            'ok' => true,
            'msg' => 'رمز ورود اپ با موفقیت عوض شد',
            'password' => $newPass,
        ], JSON_UNESCAPED_UNICODE);
        exit();
    }
} catch (Exception $e) {
    apiFail('خطا در ارتباط با دیتابیس', 500);
}


    // —— وضعیت فاکتور خرید اپ (پولینگ)
    if ($action === 'invoice_status') {
        $token = '';
        if (!empty($_POST['pay_token'])) {
            $token = trim((string)$_POST['pay_token']);
        } elseif (!empty($_GET['pay_token'])) {
            $token = trim((string)$_GET['pay_token']);
        }
        if ($token === '' || strlen($token) < 16) {
            apiFail('توکن فاکتور نامعتبر است');
        }
        try {
            $st = $db->prepare('SELECT id, user_id, status, target_username, plan_key, price, expires_at, photo_file_id FROM payments WHERE pay_token = ? LIMIT 1');
            $st->execute([$token]);
            $pay = $st->fetch(PDO::FETCH_ASSOC);
        } catch (Exception $e) {
            apiFail('خطا در خواندن فاکتور', 500);
        }
        if (!$pay) {
            apiFail('فاکتور یافت نشد', 404);
        }
        $target = trim((string)($pay['target_username'] ?? ''));
        if ($target !== '' && strcasecmp($target, $username) !== 0) {
            apiFail('این فاکتور متعلق به این حساب نیست', 403);
        }
        $status = strtolower(trim((string)($pay['status'] ?? 'pending')));
        $expired = false;
        if (!empty($pay['expires_at']) && $status === 'pending') {
            try {
                if (strtotime((string)$pay['expires_at']) < time()) {
                    $expired = true;
                    $status = 'expired';
                }
            } catch (Exception $e) {}
        }
        $hasSub = false;
        if ($status === 'approved') {
            try {
                $c = $db->prepare('SELECT COUNT(*) FROM orders WHERE config_username = ? OR user_id = ?');
                $c->execute([$username, (int)$pay['user_id']]);
                $hasSub = ((int)$c->fetchColumn()) > 0;
            } catch (Exception $e) {}
            if (!$hasSub) {
                // شاید همین لحظه ساخته شده؛ هنوز has_subscription از لاگین بهتر است
                $hasSub = true;
            }
        }
        echo json_encode([
            'ok' => true,
            'payment_id' => (int)$pay['id'],
            'status' => $status,
            'expired' => $expired,
            'has_subscription' => $hasSub,
            'plan_key' => (string)($pay['plan_key'] ?? ''),
            'price' => (int)($pay['price'] ?? 0),
            'panel_username' => (string)($pay['target_username'] ?? ''),
            'login_username' => $username,
            'is_additional_service' => (strcasecmp((string)($pay['target_username'] ?? ''), $username) !== 0
                && strtolower((string)($pay['action_type'] ?? '')) === 'new'
                && $status === 'approved'),
            'msg' => $status === 'approved'
                ? (
                    (strcasecmp((string)($pay['target_username'] ?? ''), $username) !== 0
                        && strtolower((string)($pay['action_type'] ?? '')) === 'new')
                    ? ('سرویس جدید «' . (string)$pay['target_username'] . '» به حساب شما اضافه شد. می‌توانید از لیست اشتراک‌ها بین سرویس‌ها جابه‌جا شوید.')
                    : 'پرداخت تأیید شد و اشتراک فعال است'
                )
                : ($status === 'expired'
                    ? 'مهلت فاکتور تمام شده؛ دوباره خرید کنید'
                    : ($status === 'cancelled'
                        ? 'فاکتور لغو شده است'
                        : 'هنوز در انتظار تأیید پرداخت')),
        ], JSON_UNESCAPED_UNICODE);
        exit();
    }



    // —— لیست پیشنهادهای تست رایگان (چنددسته‌ای)
    if ($action === 'list_test_offers') {
        if (is_array($appAccount) && !empty($appAccount['config_username'])) {
            $username = (string)$appAccount['config_username'];
        }
        if (!isset($ownerUserId) || $ownerUserId <= 0) {
            $owner = api_resolve_owner($db, $username, is_array($dbOrder) ? $dbOrder : null, is_array($appAccount) ? $appAccount : null);
            $ownerUserId = (int)$owner['user_id'];
        }
        $synthUid = (int)$ownerUserId;
        if (!api_is_feature_enabled($db, 'btn_test')) {
            apiFail('تست رایگان فعلاً غیرفعال است', 403);
        }
        $offersOut = [];
        if (function_exists('testOffersListVisible')) {
            try {
                $vis = testOffersListVisible($db);
                foreach ($vis as $o) {
                    $oid = (int)($o['id'] ?? 0);
                    $used = function_exists('testOfferUserHasUsed')
                        ? testOfferUserHasUsed($db, $synthUid, $oid)
                        : false;
                    $offersOut[] = [
                        'id' => $oid,
                        'cat_key' => (string)($o['cat_key'] ?? ''),
                        'title' => (string)($o['title'] ?? ''),
                        'emoji' => (string)($o['emoji'] ?? '🎁'),
                        'description' => (string)($o['description'] ?? ''),
                        'volume_gb' => (float)($o['volume_gb'] ?? 0.1),
                        'days' => (int)($o['days'] ?? 1),
                        'panel_id' => (int)($o['panel_id'] ?? 0),
                        'used' => $used ? 1 : 0,
                    ];
                }
            } catch (Throwable $e) {
                $offersOut = [];
            }
        }
        // سازگاری: اگر هنوز offer تعریف نشده، یک گزینه پیش‌فرض
        if (!$offersOut) {
            $hasUsed = 0;
            try {
                $st = $db->prepare('SELECT has_used_test FROM users WHERE user_id = ? LIMIT 1');
                $st->execute([$synthUid]);
                $hasUsed = (int)$st->fetchColumn();
            } catch (Exception $e) {}
            $offersOut[] = [
                'id' => 0,
                'cat_key' => 'default',
                'title' => 'تست رایگان',
                'emoji' => '🎁',
                'description' => '۱۰۰ مگابایت / ۲۴ ساعت',
                'volume_gb' => 0.1,
                'days' => 1,
                'panel_id' => 0,
                'used' => $hasUsed ? 1 : 0,
            ];
        }
        echo json_encode([
            'ok' => true,
            'offers' => $offersOut,
            'msg' => 'هر نوع تست مربوط به یک دسته از پلن‌هاست تا همان کیفیت مسیر را ببینی.',
        ], JSON_UNESCAPED_UNICODE);
        exit();
    }

    // —— تست رایگان اپ (همان یوزر اپ، یک‌بار)
    if ($action === 'claim_free_test') {
        if (is_array($appAccount) && !empty($appAccount['config_username'])) {
            $username = (string)$appAccount['config_username'];
        }
        if (!isset($ownerUserId) || $ownerUserId <= 0) {
            $owner = api_resolve_owner($db, $username, is_array($dbOrder) ? $dbOrder : null, is_array($appAccount) ? $appAccount : null);
            $ownerUserId = (int)$owner['user_id'];
        }
        $synthUid = (int)$ownerUserId;
        if (!api_is_feature_enabled($db, 'btn_test')) {
            apiFail('تست رایگان فعلاً غیرفعال است', 403);
        }
        try {
            $stHb = $db->prepare('SELECT has_bought FROM users WHERE user_id = ? LIMIT 1');
            $stHb->execute([$synthUid]);
            if ((int)$stHb->fetchColumn() === 1) {
                apiFail('با داشتن سابقه خرید، تست رایگان فعال نیست', 409);
            }
        } catch (Throwable $e) {}
        if (function_exists('api_can_claim_test') && !api_can_claim_test($db, $synthUid)) {
            apiFail('تست رایگان برای این حساب در دسترس نیست', 409);
        }

        $offerId = (int)($_POST['offer_id'] ?? $_GET['offer_id'] ?? 0);
        $offer = null;
        $vol = 0.1;
        $days = 1;
        $panel = null;
        $catKey = 'default';
        $offerTitle = 'تست رایگان';

        if ($offerId > 0 && function_exists('testOfferGet')) {
            $offer = testOfferGet($db, $offerId);
            if (!$offer || !(int)($offer['is_active'] ?? 0)) {
                apiFail('این پیشنهاد تست فعال نیست', 404);
            }
            if (function_exists('testOfferUserHasUsed') && testOfferUserHasUsed($db, $synthUid, $offerId)) {
                apiFail('تست این دسته را قبلاً گرفته‌ای. برای تست دوباره با پشتیبانی هماهنگ کن.', 409);
            }
            $vol = (float)($offer['volume_gb'] ?? 0.1);
            if ($vol <= 0) { $vol = 0.1; }
            $days = (int)($offer['days'] ?? 1);
            if ($days < 0) { $days = 1; }
            $catKey = (string)($offer['cat_key'] ?? 'default');
            $offerTitle = trim((string)(($offer['emoji'] ?? '') . ' ' . ($offer['title'] ?? 'تست')));
            $pid = (int)($offer['panel_id'] ?? 0);
            $panel = $pid > 0 ? api_panel_by_id($db, $pid) : api_get_test_panel($db);
        } else {
            // مسیر قدیمی / تک‌پیشنهادی
            $hasUsed = 0;
            try {
                $st = $db->prepare('SELECT has_used_test FROM users WHERE user_id = ? LIMIT 1');
                $st->execute([$synthUid]);
                $hasUsed = (int)$st->fetchColumn();
            } catch (Exception $e) {}
            if ($hasUsed === 1) {
                apiFail('تست رایگان این حساب قبلاً استفاده شده است', 409);
            }
            // اگر فقط یک offer فعال باشد، همان را استفاده کن
            if (function_exists('testOffersListVisible')) {
                try {
                    $vis = testOffersListVisible($db);
                    $free = [];
                    foreach ($vis as $o) {
                        $oid = (int)($o['id'] ?? 0);
                        if ($oid > 0 && function_exists('testOfferUserHasUsed') && !testOfferUserHasUsed($db, $synthUid, $oid)) {
                            $free[] = $o;
                        }
                    }
                    if (count($free) === 1) {
                        $offer = $free[0];
                        $offerId = (int)$offer['id'];
                        $vol = (float)($offer['volume_gb'] ?? 0.1);
                        $days = (int)($offer['days'] ?? 1);
                        $catKey = (string)($offer['cat_key'] ?? 'default');
                        $offerTitle = trim((string)(($offer['emoji'] ?? '') . ' ' . ($offer['title'] ?? 'تست')));
                        $pid = (int)($offer['panel_id'] ?? 0);
                        $panel = $pid > 0 ? api_panel_by_id($db, $pid) : api_get_test_panel($db);
                    }
                } catch (Throwable $e) {}
            }
            if ($panel === null) {
                $panel = api_get_test_panel($db);
            }
        }

        if (!is_array($panel) || empty($panel)) {
            $panel = api_get_test_panel($db);
        }

        // مهم: اگر همین یوزر اشتراک غیرتست دارد، تست را روی نام کاربری جدا بساز
        // تا اشتراک اصلی (مثلاً نامحدود) روی پنل جایگزین/خراب نشود
        $loginUsername = $username;
        $panelUsername = $username;
        $isAdditional = false;
        $hasPaid = function_exists('api_username_has_paid_service')
            ? api_username_has_paid_service($db, $username, $synthUid)
            : false;
        // اگر روی پنل کاربر از قبل هست و حجم/مدت غیرتست دارد هم جدا بساز
        if (!$hasPaid) {
            try {
                $existing = null;
                // از وضعیت فعلی $user اگر همان یوزر لود شده
                // یا سفارش‌ها
                $st = $db->prepare("SELECT plan_key, volume_gb, days, config_username FROM orders WHERE LOWER(config_username)=LOWER(?) ORDER BY id DESC LIMIT 5");
                $st->execute([$username]);
                foreach ($st->fetchAll(PDO::FETCH_ASSOC) as $or) {
                    $pk = strtolower((string)($or['plan_key'] ?? ''));
                    if (strpos($pk, 'test') === false && $pk !== 'test_free') {
                        $volO = (float)($or['volume_gb'] ?? 0);
                        $daysO = (int)($or['days'] ?? -1);
                        if ($volO > 0.2 || $daysO === 0 || $daysO > 3) {
                            $hasPaid = true;
                            break;
                        }
                    }
                }
            } catch (Throwable $e) {}
        }

        if ($hasPaid) {
            $panelUsername = api_make_secondary_test_username($loginUsername, $offerId);
            $isAdditional = true;
        }

        $res = api_create_panel_user($db, $panel, $panelUsername, $vol, $days);
        if (!empty($res['_error'])) {
            $d = (string)($res['detail'] ?? $res['_error']);
            if (stripos($d, 'already') !== false || stripos($d, 'exist') !== false || stripos($d, 'duplicate') !== false) {
                // یک‌بار با پسوند تصادفی دوباره تلاش کن (فقط مسیر سرویس جدا)
                if ($isAdditional) {
                    $panelUsername = api_make_secondary_test_username($loginUsername, $offerId) . substr((string)mt_rand(10, 99), 0, 2);
                    $res = api_create_panel_user($db, $panel, $panelUsername, $vol, $days);
                }
            }
        }
        if (!empty($res['_error'])) {
            $d = (string)($res['detail'] ?? $res['_error']);
            if (stripos($d, 'already') !== false || stripos($d, 'exist') !== false || stripos($d, 'duplicate') !== false) {
                apiFail('ساخت تست ممکن نشد (نام تکراری). یک‌بار دیگر تلاش کن یا با پشتیبانی هماهنگ کن.', 409);
            }
            apiFail('ساخت تست ناموفق بود. کمی بعد دوباره امتحان کنید.', 502);
        }
        $subUrl = (string)($res['subscription_url'] ?? $res['sub_link'] ?? '');
        $passOrder = (string)($res['password'] ?? $res['pass'] ?? '');
        if ($passOrder === '' && $isAdditional) {
            // پسورد تصادفی برای سرویس تست جدا
            $passOrder = substr(str_replace(['+', '/', '='], '', base64_encode(random_bytes(9))), 0, 10);
        }
        $panelId = (int)($panel['id'] ?? 0);
        $planKeyStore = $offerId > 0 ? ('test_offer_' . $offerId) : 'test_free';
        $usernameForOrder = $panelUsername;

        try {
            $db->prepare('INSERT IGNORE INTO users (user_id, username, balance, has_bought, has_used_test) VALUES (?, ?, 0, 0, 0)')
               ->execute([$synthUid, $username]);
            $db->prepare('UPDATE users SET has_used_test = 1 WHERE user_id = ?')
               ->execute([$synthUid]);
        } catch (Exception $e) {
            try {
                $db->prepare('UPDATE users SET has_used_test = 1 WHERE user_id = ?')->execute([$synthUid]);
            } catch (Exception $e2) {}
        }

        $orderId = 0;
        try {
            $db->prepare('INSERT INTO orders (user_id, config_username, password, sub_link, volume_gb, days, panel_id, cat, plan_key) VALUES (?,?,?,?,?,?,?,?,?)')
               ->execute([$synthUid, $usernameForOrder, $passOrder, $subUrl, $vol, $days, $panelId > 0 ? $panelId : null, $catKey, $planKeyStore]);
            $orderId = (int)$db->lastInsertId();
        } catch (Exception $e) {
            try {
                $db->prepare('INSERT INTO orders (user_id, config_username, password, sub_link, volume_gb, days, panel_id, plan_key) VALUES (?,?,?,?,?,?,?,?)')
                   ->execute([$synthUid, $usernameForOrder, $passOrder, $subUrl, $vol, $days, $panelId > 0 ? $panelId : null, $planKeyStore]);
                $orderId = (int)$db->lastInsertId();
            } catch (Exception $e2) {
                try {
                    $db->prepare('INSERT INTO orders (user_id, config_username, password, sub_link, volume_gb, days) VALUES (?,?,?,?,?,?)')
                       ->execute([$synthUid, $usernameForOrder, $passOrder, $subUrl, $vol, $days]);
                    $orderId = (int)$db->lastInsertId();
                } catch (Exception $e3) {}
            }
        }

        if ($offerId > 0 && function_exists('testOfferMarkUsed')) {
            try {
                testOfferMarkUsed($db, $synthUid, $offerId, $catKey, $orderId > 0 ? $orderId : null);
            } catch (Throwable $e) {}
        }

        $volTxt = rtrim(rtrim(number_format($vol, 3, '.', ''), '0'), '.');
        $dayTxt = $days > 0 ? ($days . ' روز') : 'بدون محدودیت زمانی';
        $msg = 'تست رایگان فعال شد';
        if (trim($offerTitle) !== '') {
            $msg = '«' . trim($offerTitle) . '» فعال شد';
        }
        $msg .= " ({$volTxt} گیگ / {$dayTxt}). یک‌بار بروزرسانی کن.";

        if (!empty($isAdditional)) {
            $msg = 'تست به‌صورت اشتراک جدا اضافه شد';
            if (trim($offerTitle) !== '') {
                $msg = '«' . trim($offerTitle) . '» به‌صورت اشتراک جدا اضافه شد';
            }
            $volTxt = rtrim(rtrim(number_format($vol, 3, '.', ''), '0'), '.');
            $dayTxt = $days > 0 ? ($days . ' روز') : 'بدون محدودیت زمانی';
            $msg .= " ({$volTxt} گیگ / {$dayTxt}).\nاشتراک اصلی‌ات دست نخورده؛ از «اشتراک‌های من» می‌توانی بین آن‌ها جابه‌جا شوی.\nیوزر تست: {$panelUsername}";
        }

        echo json_encode([
            'ok' => true,
            'claimed' => true,
            'has_subscription' => true,
            'is_additional_service' => !empty($isAdditional),
            'username' => $loginUsername,
            'panel_username' => $panelUsername,
            'password' => $passOrder,
            'vol' => $vol,
            'days' => $days,
            'offer_id' => $offerId,
            'cat_key' => $catKey,
            'offer_title' => $offerTitle,
            'msg' => $msg,
        ], JSON_UNESCAPED_UNICODE);
        exit();
    }

    // —— پلن‌های قابل تمدید (هم‌دسته و هم‌پنل با سرویس فعلی)
    if ($action === 'list_renew_plans') {
        if (is_array($appAccount) && !empty($appAccount['config_username'])) {
            $username = (string)$appAccount['config_username'];
        }
        if (!isset($ownerUserId) || $ownerUserId <= 0) {
            $owner = api_resolve_owner($db, $username, is_array($dbOrder) ? $dbOrder : null, is_array($appAccount) ? $appAccount : null);
            $ownerUserId = (int)$owner['user_id'];
        }
        $synthUid = (int)$ownerUserId;
        $order = null;
        try {
            $st = $db->prepare('SELECT * FROM orders WHERE config_username = ? OR user_id = ? ORDER BY id DESC LIMIT 1');
            $st->execute([$username, $synthUid]);
            $order = $st->fetch(PDO::FETCH_ASSOC);
        } catch (Exception $e) {
            $st = $db->prepare('SELECT * FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 1');
            $st->execute([$username]);
            $order = $st->fetch(PDO::FETCH_ASSOC);
        }
        if (!$order) {
            apiFail('سرویس فعالی برای تمدید یافت نشد', 404);
        }
        $pk = strtolower((string)($order['plan_key'] ?? ''));
        $cn = strtolower((string)($order['config_username'] ?? ''));
        if (strpos($pk, 'test') !== false || strpos($cn, 'test_') === 0 || $pk === 'test_free') {
            apiFail('اشتراک تست قابل تمدید نیست. از خرید اشتراک استفاده کنید.', 409);
        }
        $svcCat = strtolower(trim((string)($order['cat'] ?? '')));
        if ($svcCat === '') {
            $svcCat = ((int)($order['days'] ?? 0) === 0) ? 'vip' : 'monthly';
        }
        $orderPanelId = (int)($order['panel_id'] ?? 0);
        $def = api_load_default_panel($db);
        $defId = (int)($def['id'] ?? 0);
        if ($orderPanelId <= 0) {
            $orderPanelId = $defId;
        }
        $rows = [];
        try {
            $rows = $db->query('SELECT * FROM bot_plans WHERE is_active = 1 ORDER BY sort_order ASC, id ASC')->fetchAll(PDO::FETCH_ASSOC);
        } catch (Exception $e) {
            try {
                $rows = $db->query('SELECT * FROM bot_plans WHERE is_active = 1')->fetchAll(PDO::FETCH_ASSOC);
            } catch (Exception $e2) {
                $rows = [];
            }
        }
        $out = [];
        foreach ($rows as $r) {
            $key = (string)($r['plan_key'] ?? '');
            if ($key === '') continue;
            $kl = strtolower($key);
            $title = (string)($r['title'] ?? $key);
            if (strpos($kl, 'test') !== false || mb_strpos($title, 'تست') !== false) continue;
            $pCat = strtolower(trim((string)($r['cat'] ?? '')));
            if ($pCat === '') {
                $pCat = ((int)($r['days'] ?? 0) === 0) ? 'vip' : 'monthly';
            }
            if ($pCat !== $svcCat) continue;
            $planPanelId = (int)($r['panel_id'] ?? 0);
            if ($planPanelId <= 0) $planPanelId = $defId;
            if ($orderPanelId > 0 && $planPanelId !== $orderPanelId) continue;
            $price = (int)($r['price'] ?? 0);
            if ($price <= 0) continue;
            $out[] = [
                'plan_key' => $key,
                'title' => $title,
                'price' => $price,
                'price_fmt' => number_format($price),
                'vol' => isset($r['vol']) ? (float)$r['vol'] : (float)($r['volume_gb'] ?? 0),
                'days' => (int)($r['days'] ?? 0),
                'cat' => $pCat,
                'label' => '🔄 ' . $title . ' — ' . number_format($price) . ' تومان',
            ];
        }
        echo json_encode([
            'ok' => true,
            'service' => (string)($order['config_username'] ?? $username),
            'cat' => $svcCat,
            'panel_id' => $orderPanelId,
            'plans' => $out,
            'count' => count($out),
            'hint' => 'فقط بسته‌های هم‌نوع با اشتراک فعلی. برای نوع دیگر از خرید اشتراک جدید استفاده کنید.',
            'msg' => count($out) ? 'بسته تمدید را انتخاب کنید' : 'بسته‌ای برای تمدید این سرویس فعال نیست',
        ], JSON_UNESCAPED_UNICODE);
        exit();
    }


    // —— لیست همه سرویس‌های حساب اپ
    if ($action === 'list_services') {
        $loginBase = !empty($appLoginUsername) ? $appLoginUsername : $username;
        if (!isset($ownerUserId) || $ownerUserId <= 0) {
            $owner = api_resolve_owner($db, $username, is_array($dbOrder) ? $dbOrder : null, is_array($appAccount) ? $appAccount : null);
            $ownerUserId = (int)$owner['user_id'];
        }
        $synthUid = (int)$ownerUserId;
        $rows = [];
        try {
            $st = $db->prepare('SELECT id, config_username, volume_gb, days, panel_id, cat, plan_key, sub_link, created_at FROM orders WHERE user_id = ? OR LOWER(config_username) = LOWER(?) ORDER BY id DESC LIMIT 30');
            $st->execute([$synthUid, $username]);
            $rows = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];
        } catch (Exception $e) {
            try {
                $st = $db->prepare('SELECT id, config_username, volume_gb, days, panel_id, sub_link, created_at FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 30');
                $st->execute([$username]);
                $rows = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];
            } catch (Exception $e2) {
                $rows = [];
            }
        }
        $out = [];
        foreach ($rows as $r) {
            $cn = (string)($r['config_username'] ?? '');
            if ($cn === '') continue;
            $isTest = api_order_is_test($r);
            $cat = strtolower(trim((string)($r['cat'] ?? '')));
            if ($cat === '') {
                $cat = ((int)($r['days'] ?? 0) === 0) ? 'vip' : 'monthly';
            }
            $catTitle = $cat;
            if (strpos($cat, 'month') !== false) $catTitle = 'ماهانه';
            elseif (strpos($cat, 'vol') !== false || $cat === 'economic') $catTitle = 'حجمی';
            elseif (strpos($cat, 'vip') !== false || strpos($cat, 'unlim') !== false) $catTitle = 'نامحدود / VIP';
            $out[] = [
                'id' => (int)($r['id'] ?? 0),
                'config_username' => $cn,
                'is_primary' => (strcasecmp($cn, $username) === 0),
                'is_test' => $isTest,
                'cat' => $cat,
                'cat_title' => $catTitle,
                'vol' => (float)($r['volume_gb'] ?? 0),
                'days' => (int)($r['days'] ?? 0),
                'plan_key' => (string)($r['plan_key'] ?? ''),
                'label' => ($isTest ? '🧪 تست · ' : '') . $catTitle . ' · ' . $cn,
            ];
        }
        echo json_encode([
            'ok' => true,
            'login_username' => $username,
            'services' => $out,
            'count' => count($out),
            'msg' => count($out) ? 'لیست سرویس‌ها' : 'سرویسی ثبت نشده',
        ], JSON_UNESCAPED_UNICODE);
        exit();
    }

    // —— ساخت فاکتور خرید از اپ (فاز B)
    if ($action === 'create_invoice') {
        // مبنای حساب اپ = اکانت اصلی نه نام مشتق سرویس
        if (is_array($appAccount) && !empty($appAccount['config_username'])) {
            $username = (string)$appAccount['config_username'];
        }
        $planKey = '';
        if (!empty($_POST['plan_key'])) {
            $planKey = trim((string)$_POST['plan_key']);
        } elseif (!empty($_GET['plan_key'])) {
            $planKey = trim((string)$_GET['plan_key']);
        }
        if ($planKey === '') {
            apiFail('پلن انتخاب نشده است');
        }
        $plan = null;
        try {
            $st = $db->prepare('SELECT * FROM bot_plans WHERE plan_key = ? AND is_active = 1 LIMIT 1');
            $st->execute([$planKey]);
            $plan = $st->fetch();
        } catch (Exception $e) {
            apiFail('پلن یافت نشد', 404);
        }
        if (!$plan) {
            apiFail('پلن فعال یافت نشد', 404);
        }
        $basePrice = (int)($plan['price'] ?? 0);
        if ($basePrice <= 0) {
            apiFail('قیمت پلن نامعتبر است');
        }

        // صورتحساب روی صاحب منطقی: تلگرام واقعی یا شناسه مصنوعی اپ
        if (!isset($ownerUserId) || $ownerUserId <= 0) {
            $owner = api_resolve_owner($db, $username, is_array($dbOrder) ? $dbOrder : null, is_array($appAccount) ? $appAccount : null);
            $ownerUserId = (int)$owner['user_id'];
            $ownerChannel = (string)$owner['channel'];
        }
        $synthUid = (int)$ownerUserId; // نام تاریخی متغیر؛ مقدار = صاحب حساب

        $invoiceAction = 'new';
        if (!empty($_POST['action_type'])) {
            $invoiceAction = strtolower(trim((string)$_POST['action_type']));
        } elseif (!empty($_GET['action_type'])) {
            $invoiceAction = strtolower(trim((string)$_GET['action_type']));
        }
        if ($invoiceAction !== 'renew') {
            $invoiceAction = 'new';
        }

        // برای تمدید: پلن باید هم‌دسته و هم‌پنل سرویس فعلی باشد
        if ($invoiceAction === 'renew') {
            $ord = null;
            try {
                $stO = $db->prepare('SELECT * FROM orders WHERE config_username = ? OR user_id = ? ORDER BY id DESC LIMIT 1');
                $stO->execute([$username, $synthUid]);
                $ord = $stO->fetch(PDO::FETCH_ASSOC);
            } catch (Exception $e) {}
            if (!$ord) {
                apiFail('سرویسی برای تمدید یافت نشد', 404);
            }
            $pk0 = strtolower((string)($ord['plan_key'] ?? ''));
            if (strpos($pk0, 'test') !== false || $pk0 === 'test_free') {
                apiFail('تست قابل تمدید نیست', 409);
            }
            $svcCat = strtolower(trim((string)($ord['cat'] ?? '')));
            if ($svcCat === '') {
                $svcCat = ((int)($ord['days'] ?? 0) === 0) ? 'vip' : 'monthly';
            }
            $pCat = strtolower(trim((string)($plan['cat'] ?? '')));
            if ($pCat === '') {
                $pCat = ((int)($plan['days'] ?? 0) === 0) ? 'vip' : 'monthly';
            }
            if ($pCat !== $svcCat) {
                apiFail('این بسته برای تمدید سرویس فعلی مناسب نیست. از خرید اشتراک برای نوع دیگر استفاده کنید.', 409);
            }
            $orderPanelId = (int)($ord['panel_id'] ?? 0);
            $planPanelId = (int)($plan['panel_id'] ?? 0);
            $defId = (int)(api_load_default_panel($db)['id'] ?? 0);
            if ($orderPanelId <= 0) $orderPanelId = $defId;
            if ($planPanelId <= 0) $planPanelId = $defId;
            if ($orderPanelId > 0 && $planPanelId !== $orderPanelId) {
                apiFail('این بسته مربوط به پنل دیگری است و برای تمدید مجاز نیست.', 409);
            }
        }

        // تخفیف اولین خرید ۱۰٪ — فقط خرید جدید، نه تمدید
        $discountPct = 0;
        $couponCode = null;
        // هدف پنل برای خرید جدید: اگر سرویس فعال ناهم‌نوع دارد → نام مشتق (سرویس دوم)
        $panelTarget = $username;
        $isAdditionalService = false;
        $additionalNote = '';
        if ($invoiceAction === 'new') {
            $newCat = api_plan_cat($plan);
            $existing = [];
            try {
                $stE = $db->prepare('SELECT * FROM orders WHERE user_id = ? OR config_username = ? ORDER BY id DESC LIMIT 20');
                $stE->execute([$synthUid, $username]);
                $existing = $stE->fetchAll(PDO::FETCH_ASSOC) ?: [];
            } catch (Exception $e) {
                try {
                    $stE = $db->prepare('SELECT * FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 20');
                    $stE->execute([$username]);
                    $existing = $stE->fetchAll(PDO::FETCH_ASSOC) ?: [];
                } catch (Exception $e2) {}
            }
            $hasOtherActive = false;
            $sameNameExists = false;
            foreach ($existing as $ex) {
                if (api_order_is_test($ex)) {
                    continue;
                }
                $exCn = (string)($ex['config_username'] ?? '');
                if (strcasecmp($exCn, $username) === 0) {
                    $sameNameExists = true;
                }
                $exCat = strtolower(trim((string)($ex['cat'] ?? '')));
                if ($exCat === '') {
                    $exCat = ((int)($ex['days'] ?? 0) === 0) ? 'vip' : 'monthly';
                }
                // اگر هر سرویس غیرتست هم‌نام یا ناهم‌نوع باشد، خرید نوع جدید روی نام اصلی خطرناک است
                if ($exCat !== $newCat || strcasecmp($exCn, $username) === 0) {
                    // ناهم‌نوع → حتماً سرویس دوم
                    if ($exCat !== $newCat) {
                        $hasOtherActive = true;
                    }
                    // هم‌نوع روی همان نام → باید تمدید کند نه خرید جدید؛ ولی اگر کاربر خرید زد، سرویس دوم با پسوند
                    if ($exCat === $newCat && strcasecmp($exCn, $username) === 0) {
                        $hasOtherActive = true; // جلوگیری از دوبل روی همان یوزر پنل
                    }
                }
            }
            // اگر روی پنل همان یوزر قبلاً هست (حتی هم‌نوع)، نام مشتق
            if ($sameNameExists || $hasOtherActive) {
                // اگر فقط هم‌نوع و همان نام: بهتر تمدید — ولی برای نوع دیگر مشتق
                $needDerive = false;
                foreach ($existing as $ex) {
                    if (api_order_is_test($ex)) continue;
                    $exCat = strtolower(trim((string)($ex['cat'] ?? '')));
                    if ($exCat === '') {
                        $exCat = ((int)($ex['days'] ?? 0) === 0) ? 'vip' : 'monthly';
                    }
                    $exCn = (string)($ex['config_username'] ?? '');
                    if ($exCat !== $newCat) {
                        $needDerive = true;
                        break;
                    }
                    if (strcasecmp($exCn, $username) === 0 && $exCat === $newCat) {
                        // خرید دوباره هم‌نوع روی همان نام → کاربر را به تمدید هدایت نکن اینجا؛ مشتق بساز تا پنل نترکد
                        $needDerive = true;
                        break;
                    }
                }
                if ($needDerive) {
                    $panelTarget = api_derive_panel_username($db, $username, $newCat);
                    $isAdditionalService = (strcasecmp($panelTarget, $username) !== 0);
                    $additionalNote = $isAdditionalService
                        ? ('سرویس جدید با نام «' . $panelTarget . '» به حساب شما اضافه می‌شود؛ اشتراک قبلی سر جایش می‌ماند.')
                        : '';
                }
            }
        }

        if ($invoiceAction !== 'renew') {
        try {
            // سفارش تست رایگان نباید مانع تخفیف اولین خرید شود
            $c1 = $db->prepare(
                "SELECT COUNT(*) FROM orders
                 WHERE (config_username = ? OR user_id = ?)
                   AND COALESCE(plan_key, '') NOT LIKE '%test%'
                   AND COALESCE(plan_key, '') <> 'test_free'
                   AND COALESCE(config_username, '') NOT LIKE 'test_%'"
            );
            $c1->execute([$username, $synthUid]);
            $c2 = $db->prepare(
                "SELECT COUNT(*) FROM payments
                 WHERE status = 'approved'
                   AND (target_username = ? OR user_id = ?)
                   AND COALESCE(plan_key, '') NOT LIKE '%test%'
                   AND COALESCE(plan_key, '') <> 'test_free'
                   AND COALESCE(coupon_code, '') <> 'TEST_FREE'"
            );
            $c2->execute([$username, $synthUid]);
            $hasPaidOrder = (int)$c1->fetchColumn() > 0;
            $hasApprovedPay = (int)$c2->fetchColumn() > 0;
            // has_bought فقط برای خرید واقعی
            $hb = 0;
            try {
                $stHb = $db->prepare('SELECT has_bought FROM users WHERE user_id = ? LIMIT 1');
                $stHb->execute([$synthUid]);
                $hb = (int)$stHb->fetchColumn();
            } catch (Exception $e) {}
            if (!$hasPaidOrder && !$hasApprovedPay && $hb === 0) {
                $discountPct = 10;
                $couponCode = 'FIRST10';
            }
        } catch (Exception $e) {}
        }

        if ($discountPct > 0) {
            $basePrice = (int)round($basePrice * (1 - $discountPct / 100));
        }
        $discountRand = random_int(10, 190);
        $finalPrice = max(1000, $basePrice - $discountRand);
        $finalPriceRial = $finalPrice * 10;

        try {
            $cols = $db->query('SHOW COLUMNS FROM payments')->fetchAll(PDO::FETCH_COLUMN);
            $cols = array_map('strtolower', $cols ?: []);
            if (!in_array('pay_token', $cols, true)) {
                $db->exec("ALTER TABLE payments ADD COLUMN pay_token VARCHAR(64) NULL DEFAULT NULL");
            }
            if (!in_array('expires_at', $cols, true)) {
                $db->exec("ALTER TABLE payments ADD COLUMN expires_at DATETIME NULL DEFAULT NULL");
            }
        } catch (Exception $e) {}

        $token = bin2hex(random_bytes(24));
        $ttl = defined('INVOICE_TTL_SEC') ? (int)INVOICE_TTL_SEC : 1200;
        $expiresAt = date('Y-m-d H:i:s', time() + $ttl);

        // اطمینان از ردیف users برای لیست کاربران وب
        try {
            $db->prepare('INSERT IGNORE INTO users (user_id, username, balance, has_bought, has_used_test) VALUES (?, ?, 0, 0, 0)')
               ->execute([$synthUid, $username]);
        } catch (Exception $e) {
            try {
                $db->prepare('INSERT IGNORE INTO users (user_id, username) VALUES (?, ?)')->execute([$synthUid, $username]);
            } catch (Exception $e2) {}
        }

        // لغو پیش‌فاکتورهای قبلی همین حساب اپ
        try {
            $db->prepare("UPDATE payments SET status = 'cancelled' WHERE user_id = ? AND status = 'pending' AND photo_file_id = 'AWAITING_RECEIPT'")
               ->execute([$synthUid]);
        } catch (Exception $e) {}

        // users ردیف صاحب حساب؛ app_accounts فقط برای اکانت اختصاصی اپ (نه کانفیگ ربات)
        try {
            $db->prepare('INSERT IGNORE INTO users (user_id, username, balance, has_bought, has_used_test) VALUES (?, ?, 0, 0, 0)')
               ->execute([$synthUid, $username]);
        } catch (Exception $e) {
            try {
                $db->prepare('INSERT IGNORE INTO users (user_id, username) VALUES (?, ?)')->execute([$synthUid, $username]);
            } catch (Exception $e2) {}
        }
        $canWriteAppAcc = empty($ownerIsBotConfig) && !api_is_bot_panel_username($username);
        if (!empty($ownerChannel) && $ownerChannel === 'telegram') {
            $canWriteAppAcc = false;
        }
        if ($canWriteAppAcc) {
            try {
                $stA = $db->prepare('SELECT id FROM app_accounts WHERE LOWER(config_username) = LOWER(?) LIMIT 1');
                $stA->execute([$username]);
                if (!$stA->fetch()) {
                    try {
                        $db->prepare('INSERT INTO app_accounts (config_username, password, last_login_at) VALUES (?, ?, NOW())')
                           ->execute([$username, $password]);
                    } catch (Exception $eIns) {
                        try {
                            $db->prepare('INSERT INTO app_accounts (config_username, password) VALUES (?, ?)')
                               ->execute([$username, $password]);
                        } catch (Exception $e2) {}
                    }
                } else {
                    try {
                        $db->prepare('UPDATE app_accounts SET last_login_at = NOW() WHERE LOWER(config_username) = LOWER(?)')->execute([$username]);
                    } catch (Exception $e) {}
                }
            } catch (Exception $e) {}
        }

        try {
            $db->prepare("INSERT INTO payments (user_id, plan_key, price, photo_file_id, target_username, action_type, coupon_code, status, pay_token, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)")
               ->execute([$synthUid, $planKey, $finalPrice, 'AWAITING_RECEIPT', $panelTarget, $invoiceAction, $couponCode, $token, $expiresAt]);
        } catch (Exception $e) {
            try {
                $db->prepare("INSERT INTO payments (user_id, plan_key, price, photo_file_id, target_username, action_type, coupon_code, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')")
                   ->execute([$synthUid, $planKey, $finalPrice, 'AWAITING_RECEIPT', $panelTarget, $invoiceAction, $couponCode]);
                $token = '';
            } catch (Exception $e2) {
                apiFail('ساخت فاکتور ناموفق بود', 500);
            }
        }
        $paymentId = (int)$db->lastInsertId();

        $cardNum = '';
        $cardHolder = 'جت‌کانفیگ';
        $bankName = '';
        try {
            $card = $db->query("SELECT * FROM bank_cards WHERE is_active = 1 ORDER BY RAND() LIMIT 1")->fetch();
            if ($card) {
                $cardNum = (string)($card['card_number'] ?? '');
                $cardHolder = (string)($card['card_holder'] ?? $cardHolder);
                $bankName = (string)($card['bank_name'] ?? '');
            }
        } catch (Exception $e) {}

        $payUrl = '';
        if ($token !== '') {
            $basePay = defined('PAY_PAGE_DEFAULT') ? PAY_PAGE_DEFAULT : 'https://majid6064.ir/pay.php';
            try {
                $sv = api_get_setting($db, 'pay_page_url', '');
                if ($sv !== '' && $sv !== null) {
                    $basePay = rtrim((string)$sv, '?&');
                }
            } catch (Exception $e) {}
            $sep = (strpos($basePay, '?') !== false) ? '&' : '?';
            $payUrl = $basePay . $sep . 't=' . urlencode($token);
        }

        echo json_encode([
            'ok' => true,
            'payment_id' => $paymentId,
            'plan_key' => $planKey,
            'plan_title' => (string)($plan['title'] ?? $planKey),
            'price' => $finalPrice,
            'price_fmt' => number_format($finalPrice),
            'price_rial' => $finalPriceRial,
            'price_rial_fmt' => number_format($finalPriceRial),
            'discount_first' => $discountPct > 0,
            'discount_pct' => $discountPct,
            'discount_note' => $discountPct > 0
                ? ('مبلغ پس از ' . $discountPct . '٪ تخفیف اولین خرید + کسر جزئی یکتا')
                : 'کسر جزئی تصادفی روی مبلغ برای تأیید خودکار واریز',
            'card_number' => $cardNum,
            'card_holder' => $cardHolder,
            'bank_name' => $bankName,
            'pay_url' => $payUrl,
            'pay_token' => $token,
            'expires_at' => $expiresAt,
            'ttl_sec' => $ttl,
            'target_username' => $panelTarget,
            'login_username' => $username,
            'is_additional_service' => !empty($isAdditionalService),
            'additional_note' => $additionalNote,
            'action_type' => $invoiceAction,
            'msg' => $invoiceAction === 'renew'
                ? 'فاکتور تمدید ساخته شد. مبلغ را دقیق واریز کنید تا تمدید خودکار شود.'
                : (!empty($isAdditionalService)
                    ? ('فاکتور ساخته شد. ' . $additionalNote)
                    : 'فاکتور ساخته شد. مبلغ را دقیق واریز کنید تا پرداخت به‌صورت خودکار تأیید شود.'),
        ], JSON_UNESCAPED_UNICODE);
        exit();
    }

// نگهداری برای fallback بعدی (از جدول سفارش‌های ربات)
$orderDays = ($dbOrder && isset($dbOrder['days'])) ? (int)$dbOrder['days'] : 0;
$orderVolume = ($dbOrder && isset($dbOrder['volume_gb'])) ? (float)$dbOrder['volume_gb'] : 0;
$orderCreated = 0;
$orderSubLink = ($dbOrder && !empty($dbOrder['sub_link'])) ? trim((string)$dbOrder['sub_link']) : '';
$panelId = ($dbOrder && isset($dbOrder['panel_id'])) ? (int)$dbOrder['panel_id'] : 0;
$panel = api_panel_by_id($db, $panelId);

function getPanelToken($panel = null) {
    if (!is_array($panel)) {
        $panel = api_default_panel_row();
    }
    $user = (string)($panel['username'] ?? (defined('PANEL_USER') ? PANEL_USER : ''));
    $pass = (string)($panel['password'] ?? (defined('PANEL_PASS') ? PANEL_PASS : ''));
    if ($user === '') {
        return null;
    }
    $bases = api_panel_token_bases($panel);
    foreach ($bases as $base) {
        // JSON (مرزبان) سپس form (سازگاری)
        foreach ([
            ['body' => json_encode(['username' => $user, 'password' => $pass], JSON_UNESCAPED_UNICODE), 'ct' => 'application/json'],
            ['body' => http_build_query(['username' => $user, 'password' => $pass]), 'ct' => 'application/x-www-form-urlencoded'],
        ] as $mode) {
            $ch = curl_init(rtrim($base, '/') . '/api/admin/token');
            $opts = [
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => $mode['body'],
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_HTTPHEADER => ['Content-Type: ' . $mode['ct']],
                CURLOPT_SSL_VERIFYPEER => false,
                CURLOPT_SSL_VERIFYHOST => 0,
                CURLOPT_TIMEOUT => 20,
                CURLOPT_CONNECTTIMEOUT => 8,
                CURLOPT_FOLLOWLOCATION => true,
            ];
            if (defined('CURL_IPRESOLVE_V4')) {
                $opts[CURLOPT_IPRESOLVE] = CURL_IPRESOLVE_V4;
            }
            curl_setopt_array($ch, $opts);
            $res = curl_exec($ch);
            curl_close($ch);
            $decoded = json_decode((string)$res, true);
            $token = is_array($decoded) ? ($decoded['access_token'] ?? $decoded['token'] ?? null) : null;
            if ($token) {
                $GLOBALS['_api_panel_base'] = rtrim($base, '/');
                return $token;
            }
        }
    }
    return null;
}

$token = getPanelToken($panel);
if (!$token) {
    apiFail('خطا در ارتباط با سرور پنل', 502);
}

$apiBase = !empty($GLOBALS['_api_panel_base'])
    ? (string)$GLOBALS['_api_panel_base']
    : getPanelApiBase($panel);

$ch = curl_init(rtrim($apiBase, '/') . '/api/user/' . rawurlencode($username));
$opts = [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Accept: application/json'],
    CURLOPT_SSL_VERIFYPEER => false,
    CURLOPT_SSL_VERIFYHOST => 0,
    CURLOPT_TIMEOUT => 25,
    CURLOPT_FOLLOWLOCATION => true,
];
if (defined('CURL_IPRESOLVE_V4')) {
    $opts[CURLOPT_IPRESOLVE] = CURL_IPRESOLVE_V4;
}
curl_setopt_array($ch, $opts);
$res = curl_exec($ch);
curl_close($ch);

$user = json_decode((string)$res, true);
if (!$user || !isset($user['username'])) {
    // اگر پنل API جواب نداد ولی لینک ساب در سفارش هست، با همان ادامه بده
    if ($orderSubLink !== '') {
        $user = [
            'username' => $username,
            'status' => 'active',
            'data_limit' => $orderVolume > 0 ? (int)round($orderVolume * 1024 * 1024 * 1024) : 0,
            'used_traffic' => 0,
            'expire' => 0,
            'subscription_url' => $orderSubLink,
            'links' => [],
        ];
    } elseif (!empty($appAccount)) {
            $hu = 0;
            try {
                $su = 700000000000 + (abs(crc32(strtolower($username))) % 999999999);
                $stHu = $db->prepare('SELECT has_used_test FROM users WHERE user_id = ? LIMIT 1');
                $stHu->execute([$su]);
                $hu = (int)$stHu->fetchColumn();
            } catch (Exception $e) {}
            $featTest = api_is_feature_enabled($db, 'btn_test');
            echo json_encode([
                'ok' => true,
                'has_subscription' => false,
                'has_used_test' => $hu,
                'can_claim_test' => ($featTest && api_can_claim_test($db, (int)$su)),
                'can_renew' => false,
                'is_test_service' => false,
                'username' => $username,
                'status' => 'no_subscription',
                'panel_status' => 'no_subscription',
                'total_gb' => 0,
                'used_gb' => 0,
                'remaining_gb' => 0,
                'expire_days' => 'بدون اشتراک',
                'expire_ts' => 0,
                'servers' => [],
                'servers_count' => 0,
                'msg' => 'وارد شدید. هنوز اشتراک فعالی روی این حساب نیست.',
            ], JSON_UNESCAPED_UNICODE);
            exit();
        } else {
            apiFail('کاربری با این نام کاربری یافت نشد', 404);
        }
}


// can_claim_test بر اساس تست‌های باقی‌ماندهٔ دسته‌ای
try {
    $uidClaim = (isset($ownerUserId) && (int)$ownerUserId > 0) ? (int)$ownerUserId : 0;
    if ($uidClaim > 0 && function_exists('api_can_claim_test')) {
        $apiCanClaimTest = api_can_claim_test($db, $uidClaim);
    } elseif ($uidClaim > 0) {
        $stHu2 = $db->prepare('SELECT has_used_test FROM users WHERE user_id = ? LIMIT 1');
        $stHu2->execute([$uidClaim]);
        $apiCanClaimTest = ((int)$stHu2->fetchColumn() === 0) && api_is_feature_enabled($db, 'btn_test');
    }
} catch (Throwable $e) {
    $apiCanClaimTest = false;
}
// حجم پلن سفارش جاری (برای هشدار مصرف بعد از تمدید)
try {
    $stOv = $db->prepare("SELECT volume_gb FROM orders WHERE config_username = ? OR user_id = ? ORDER BY id DESC LIMIT 1");
    $stOv->execute([$username, isset($ownerUserId) ? (int)$ownerUserId : 0]);
    $apiPlanVolumeGb = (float)$stOv->fetchColumn();
} catch (Throwable $e) {
    $apiPlanVolumeGb = 0.0;
}

$totalBytes = (float)($user['data_limit'] ?? 0);
$usedBytes = (float)($user['used_traffic'] ?? 0);
$totalGB = $totalBytes > 0 ? round($totalBytes / (1024 * 1024 * 1024), 2) : 0;
$usedGB = round($usedBytes / (1024 * 1024 * 1024), 2);
$remainingGB = $totalBytes > 0 ? max(0, round($totalGB - $usedGB, 2)) : 0;
// بعد از تمدید انباشتی: مبنای نمایش/هشدار اپ = سقف و باقیماندهٔ زنده پنل
if ($totalGB > 0) {
    $apiPlanVolumeGb = $totalGB;
}

$status = $user['status'] ?? 'active';
// بعضی فورک‌ها/نسخه‌ها فیلد انقضا را با نام‌های مختلف می‌فرستند
$expireRaw = $user['expire']
    ?? $user['expire_at']
    ?? $user['expired_at']
    ?? $user['expire_date']
    ?? $user['expiry']
    ?? null;
$expireTimestamp = $expireRaw;
$onHoldDuration = (int)($user['on_hold_expire_duration'] ?? $user['onhold_expire_duration'] ?? 0);

// نرمال‌سازی timestamp (ثانیه / میلی‌ثانیه / رشته عددی / ISO)
if (is_string($expireTimestamp) && !is_numeric($expireTimestamp)) {
    $parsed = strtotime($expireTimestamp);
    $expireTimestamp = $parsed !== false ? $parsed : null;
}
if (is_string($expireTimestamp) && is_numeric($expireTimestamp)) {
    $expireTimestamp = (float)$expireTimestamp;
}
if (is_numeric($expireTimestamp) && (float)$expireTimestamp > 10000000000) {
    $expireTimestamp = (int)((float)$expireTimestamp / 1000);
} elseif (is_numeric($expireTimestamp) && (float)$expireTimestamp > 0) {
    $expireTimestamp = (int)$expireTimestamp;
} else {
    $expireTimestamp = null;
}

$now = time();
$expireDays = 'نامحدود';

// اولویت با وضعیت پنل
if ($status === 'expired') {
    $expireDays = 'منقضی شده';
} elseif ($status === 'limited') {
    $expireDays = 'پایان حجم';
} elseif ($status === 'on_hold') {
    if ($onHoldDuration > 0) {
        // کمتر از ۴۸ ساعت را ساعتی نشان بده (تست ۲۴ ساعته و مشابه)
        if ($onHoldDuration < 172800) {
            $hours = max(1, (int)ceil($onHoldDuration / 3600));
            $expireDays = $hours . " ساعت (شروع از اتصال)";
        } else {
            $days = max(1, (int)ceil($onHoldDuration / 86400));
            $expireDays = $days . " روز (شروع از اتصال)";
        }
    } else {
        $expireDays = 'شروع پس از اتصال';
    }
} elseif (!empty($expireTimestamp) && $expireTimestamp > 0) {
    $diff = (int)$expireTimestamp - $now;
    if ($diff <= 0) {
        $expireDays = 'منقضی شده';
    } elseif ($diff < 3600) {
        $mins = max(1, (int)ceil($diff / 60));
        $expireDays = $mins . " دقیقه مانده";
    } elseif ($diff < 172800) {
        // تا ۴۸ ساعت: ساعتی (جلوگیری از «۱ روز» گمراه‌کننده برای ۲۴ ساعت)
        $hours = max(1, (int)ceil($diff / 3600));
        $expireDays = $hours . " ساعت مانده";
    } else {
        $days = (int)ceil($diff / 86400);
        $expireDays = $days . " روز مانده";
    }
} elseif ($usedBytes == 0 && $onHoldDuration > 0) {
    if ($onHoldDuration < 172800) {
        $hours = max(1, (int)ceil($onHoldDuration / 3600));
        $expireDays = $hours . " ساعت (شروع از اتصال)";
    } else {
        $days = max(1, (int)ceil($onHoldDuration / 86400));
        $expireDays = $days . " روز (شروع از اتصال)";
    }
} elseif (empty($expireTimestamp) || $expireTimestamp == 0) {
    // نه تاریخ انقضا دارد نه on_hold — واقعاً نامحدود زمانی
    $expireDays = 'نامحدود';
}


// فقط وقتی پنل هیچ expire معتبری نداد از سفارش ربات استفاده کن
if (($expireDays === 'نامحدود' || $expireDays === 'نامحدود (VIP)') && $orderDays > 0 && empty($expireTimestamp)) {
    $expireDays = $orderDays . " روز (بر اساس سفارش)";
}

$subUrl = $user['subscription_url'] ?? '';
if ($subUrl === '' && $orderSubLink !== '') {
    $subUrl = $orderSubLink;
}
if (!empty($subUrl) && strpos($subUrl, 'http') !== 0) {
    $subUrl = rtrim(getPanelPublicBase($panel), '/') . '/' . ltrim($subUrl, '/');
}

$rawContent = '';
if (!empty($subUrl)) {
    // ترجیح: خودِ لینک عمومی ساب (مثلاً fardad-sub) — معمولاً مستقیم در دسترس است
    $fetchUrl = $subUrl;
    $publicBase = getPanelPublicBase($panel);
    $apiBaseNow = !empty($GLOBALS['_api_panel_base']) ? (string)$GLOBALS['_api_panel_base'] : getPanelApiBase($panel);
    // اگر ساب روی همان دامنه API است، از base موفق توکن استفاده کن
    if ($publicBase !== '' && strpos($subUrl, $publicBase) === 0 && $apiBaseNow !== '' && $publicBase !== $apiBaseNow) {
        // ساب عمومی جدا (مثل *-sub.*) — همان URL عمومی را بگیر
        $fetchUrl = $subUrl;
    } elseif ($publicBase !== '' && strpos($subUrl, $publicBase) === 0) {
        $path = substr($subUrl, strlen($publicBase));
        $fetchUrl = rtrim($apiBaseNow, '/') . $path;
    }

    $ch = curl_init($fetchUrl);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_TIMEOUT => 25,
        CURLOPT_HTTPHEADER => ['Accept: */*', 'User-Agent: JetConfig/1.9.8 (Server-API)']
    ]);
    $rawContent = trim((string)curl_exec($ch));
    curl_close($ch);
}

$servers = [];

if ($rawContent !== '') {
    $jsonArr = json_decode($rawContent, true);
    if (is_array($jsonArr) && !empty($jsonArr)) {
        foreach ($jsonArr as $index => $item) {
            if (!is_array($item)) {
                continue;
            }
            $serverName = $item['remarks'] ?? ('سرور ' . ($index + 1));
            $host = '';
            $port = 443;
            $protocol = 'V2RAY';

            if (!empty($item['outbounds']) && is_array($item['outbounds'])) {
                foreach ($item['outbounds'] as $out) {
                    $p = strtolower($out['protocol'] ?? '');
                    if (in_array($p, ['vless', 'vmess', 'trojan', 'shadowsocks', 'ss', 'hysteria', 'hysteria2', 'tuic'], true)) {
                        $protocol = strtoupper($p);
                        if (!empty($out['tag'])) {
                            $serverName = $out['tag'];
                        }
                        $settings = $out['settings'] ?? [];
                        if (!empty($settings['vnext'][0])) {
                            $host = $settings['vnext'][0]['address'] ?? '';
                            $port = (int)($settings['vnext'][0]['port'] ?? 443);
                        } elseif (!empty($settings['servers'][0])) {
                            $host = $settings['servers'][0]['address'] ?? '';
                            $port = (int)($settings['servers'][0]['port'] ?? 443);
                        }
                        break;
                    }
                }
            }

            $servers[] = [
                'name'     => $serverName,
                'host'     => $host,
                'port'     => $port,
                'protocol' => $protocol,
                'config'   => json_encode($item, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)
            ];
        }
    }
}

// اول لینک‌های مستقیم پنل (بدون وابستگی به دامنه ساب)
if (empty($servers) && !empty($user['links']) && is_array($user['links'])) {
    $candidatesEarly = [];
    foreach ($user['links'] as $lk) {
        if (is_string($lk) && $lk !== '') $candidatesEarly[] = $lk;
    }
    foreach (array_unique($candidatesEarly) as $urlItem) {
        $urlItem = trim($urlItem);
        $name = 'سرور پرسرعت';
        $host = '';
        $port = 443;
        $protocol = 'VPN';
        if (preg_match('/^(vless|trojan|ss):\/\//i', $urlItem)) {
            $parsed = parse_url($urlItem);
            $protocol = strtoupper($parsed['scheme'] ?? 'VPN');
            $host = $parsed['host'] ?? '';
            $port = (int)($parsed['port'] ?? 443);
            if (!empty($parsed['fragment'])) $name = urldecode($parsed['fragment']);
        } elseif (preg_match('/^vmess:\/\//i', $urlItem)) {
            $protocol = 'VMESS';
            $b = substr($urlItem, 8);
            $dec = @base64_decode($b);
            if ($dec) {
                $j = json_decode($dec, true);
                $name = $j['ps'] ?? 'سرور VMess';
                $host = $j['add'] ?? '';
                $port = (int)($j['port'] ?? 443);
            }
        }
        $servers[] = [
            'name' => $name, 'host' => $host, 'port' => $port,
            'protocol' => $protocol, 'config' => $urlItem,
        ];
    }
}

if (empty($servers) && $rawContent === '' && !empty($subUrl)) {
    // تلاش دوم با User-Agentهای رایج کلاینت
    foreach (['Happ/1.0', 'v2rayNG/1.8', 'Mozilla/5.0'] as $ua) {
        $ch = curl_init($subUrl);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_SSL_VERIFYHOST => 0,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_TIMEOUT => 20,
            CURLOPT_HTTPHEADER => ['Accept: */*', 'User-Agent: ' . $ua],
        ]);
        $rawContent = trim((string)curl_exec($ch));
        curl_close($ch);
        if ($rawContent !== '') break;
    }
}

if (empty($servers)) {
    $candidates = [];
    if (!empty($user['links']) && is_array($user['links'])) {
        $candidates = array_merge($candidates, $user['links']);
    }
    if ($rawContent !== '') {
        if (preg_match_all('/(?:vless|vmess|trojan|ss|hysteria2?|tuic):\/\/[^\s<>"\'`]+/i', $rawContent, $m)) {
            $candidates = array_merge($candidates, $m[0]);
        }
        $cleanB64 = strtr(preg_replace('/[^a-zA-Z0-9+\/=_\\-]/', '', $rawContent), '-_', '+/');
        while (strlen($cleanB64) % 4 !== 0) {
            $cleanB64 .= '=';
        }
        $dec = @base64_decode($cleanB64);
        if ($dec !== false && preg_match_all('/(?:vless|vmess|trojan|ss|hysteria2?|tuic):\/\/[^\s<>"\'`]+/i', $dec, $m2)) {
            $candidates = array_merge($candidates, $m2[0]);
        }
    }

    foreach (array_unique($candidates) as $urlItem) {
        $urlItem = trim($urlItem);
        $name = 'سرور پرسرعت';
        $host = '';
        $port = 443;
        $protocol = 'VPN';

        if (preg_match('/^(vless|trojan|ss):\\/\\//i', $urlItem)) {
            $parsed = parse_url($urlItem);
            $protocol = strtoupper($parsed['scheme'] ?? 'VPN');
            $host = $parsed['host'] ?? '';
            $port = (int)($parsed['port'] ?? 443);
            if (!empty($parsed['fragment'])) {
                $name = urldecode($parsed['fragment']);
            }
        } elseif (preg_match('/^vmess:\\/\\//i', $urlItem)) {
            $protocol = 'VMESS';
            $b = substr($urlItem, 8);
            $dec = base64_decode($b);
            if ($dec) {
                $j = json_decode($dec, true);
                $name = $j['ps'] ?? 'سرور VMess';
                $host = $j['add'] ?? '';
                $port = (int)($j['port'] ?? 443);
            }
        }

        $servers[] = [
            'name'     => $name,
            'host'     => $host,
            'port'     => $port,
            'protocol' => $protocol,
            'config'   => $urlItem
        ];
    }
}

// تشخیص تست / تمدیدپذیر بودن
$apiIsTestSvc = false;
$apiCanRenew = false;
$apiHasUsedTest = 0;
try {
    $suFlag = (isset($ownerUserId) && $ownerUserId > 0)
        ? (int)$ownerUserId
        : (700000000000 + (abs(crc32(strtolower($username))) % 999999999));
    $stHu = $db->prepare('SELECT has_used_test FROM users WHERE user_id = ? LIMIT 1');
    $stHu->execute([$suFlag]);
    $apiHasUsedTest = (int)$stHu->fetchColumn();
} catch (Exception $e) {}
try {
    $ordFlag = $dbOrder;
    if (!$ordFlag) {
        $stOf = $db->prepare('SELECT * FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 1');
        $stOf->execute([$username]);
        $ordFlag = $stOf->fetch(PDO::FETCH_ASSOC) ?: null;
    }
    if (is_array($ordFlag)) {
        $pkf = strtolower((string)($ordFlag['plan_key'] ?? ''));
        $cnf = strtolower((string)($ordFlag['config_username'] ?? ''));
        $apiIsTestSvc = (strpos($pkf, 'test') !== false || $pkf === 'test_free' || strpos($cnf, 'test_') === 0);
        // حجم بستهٔ آخر (نه سقف انباشتی) برای درصد مصرف و اخطار اپ
        if (isset($ordFlag['volume_cycle_gb']) && (float)$ordFlag['volume_cycle_gb'] > 0) {
            $apiVolumeCycleGb = (float)$ordFlag['volume_cycle_gb'];
        }
        if (isset($ordFlag['last_renew_gb']) && (float)$ordFlag['last_renew_gb'] > 0) {
            $apiPlanVolumeGb = (float)$ordFlag['last_renew_gb'];
        } else {
            // بک‌فیل از آخرین پرداخت تمدید/خرید این نام‌کاربری
            try {
                $stPk = $db->prepare("SELECT plan_key FROM payments WHERE status = 'approved' AND action_type IN ('renew','new') AND (target_username = ? OR ((target_username IS NULL OR target_username = '') AND user_id = ?)) ORDER BY id DESC LIMIT 1");
                $uidO = (int)($ordFlag['user_id'] ?? 0);
                $stPk->execute([(string)($ordFlag['config_username'] ?? $username), $uidO]);
                $pkLast = (string)($stPk->fetchColumn() ?: '');
                if ($pkLast !== '' && function_exists('getPlanByKey')) {
                    $pl = getPlanByKey($db, $pkLast);
                    if (!$pl && function_exists('api_get_plan')) {
                        $pl = null;
                    }
                }
                // plans table direct
                if ($pkLast !== '') {
                    $stPl = $db->prepare('SELECT vol, volume_gb FROM bot_plans WHERE plan_key = ? LIMIT 1');
                    try {
                        $stPl->execute([$pkLast]);
                        $plRow = $stPl->fetch(PDO::FETCH_ASSOC);
                    } catch (Throwable $e2) {
                        $stPl = $db->prepare('SELECT volume_gb AS vol FROM bot_plans WHERE plan_key = ? LIMIT 1');
                        try {
                            $stPl->execute([$pkLast]);
                            $plRow = $stPl->fetch(PDO::FETCH_ASSOC);
                        } catch (Throwable $e3) {
                            $plRow = null;
                        }
                    }
                    if ($plRow) {
                        $v = (float)($plRow['vol'] ?? $plRow['volume_gb'] ?? 0);
                        if ($v > 0) {
                            $apiPlanVolumeGb = $v;
                            try {
                                $db->exec('ALTER TABLE orders ADD COLUMN last_renew_gb DOUBLE NULL DEFAULT NULL');
                            } catch (Throwable $e4) {}
                            try {
                                $db->prepare('UPDATE orders SET last_renew_gb = ? WHERE id = ?')->execute([$v, (int)$ordFlag['id']]);
                            } catch (Throwable $e5) {}
                        }
                    }
                }
            } catch (Throwable $e) {}
            if ($apiPlanVolumeGb <= 0 && isset($ordFlag['volume_gb']) && (float)$ordFlag['volume_gb'] > 0) {
                $apiPlanVolumeGb = (float)$ordFlag['volume_gb'];
            }
        }
    }
    // اگر از سفارش معلوم نشد ولی حجم خیلی کم + on_hold یک‌روزه است، تست حساب کن
    if (!$apiIsTestSvc && $totalGB > 0 && $totalGB <= 0.15 && $onHoldDuration > 0 && $onHoldDuration <= 90000) {
        $apiIsTestSvc = true;
    }
    // can_renew در API = غیرتست؛ نمایش دکمه در اپ با قانون «رو به اتمام» کنترل می‌شود
    $apiCanRenew = !$apiIsTestSvc;
} catch (Exception $e) {
    $apiCanRenew = true;
    $apiIsTestSvc = false;
}
// محاسبه نهایی can_claim (بعد از owner) — بازنویسی نشود
try {
    $uidClaim = (isset($ownerUserId) && (int)$ownerUserId > 0)
        ? (int)$ownerUserId
        : ((isset($suFlag) && (int)$suFlag > 0) ? (int)$suFlag : 0);
    $apiCanClaimTest = ($uidClaim > 0) ? api_can_claim_test($db, $uidClaim) : false;
} catch (Throwable $e) {
    $apiCanClaimTest = false;
}


// ——— حجم دوره نمایش (Source of Truth برای اپ) ———
// volume_cycle_gb فقط وقتی در تمدید/خرید به‌صورت اتمیک ذخیره شده معتبر است.
// سقف انباشتی پنل (total_gb) هرگز جایگزین چرخه نمی‌شود.
// مقدار حدسی در دیتابیس نوشته نمی‌شود.
$apiCycleKnown = false;
$apiVolumeCycleGb = 0.0;
$apiPlanVolumeGb = isset($apiPlanVolumeGb) ? (float)$apiPlanVolumeGb : 0.0;
$apiDisplayTotalGb = 0.0;
$apiUsedCyclePct = 0;
$apiCycleSource = 'none';

try {
    // 1) snapshot قطعی از سفارش
    if (isset($ordFlag) && is_array($ordFlag)) {
        if (isset($ordFlag['volume_cycle_gb']) && (float)$ordFlag['volume_cycle_gb'] > 0) {
            $apiVolumeCycleGb = (float)$ordFlag['volume_cycle_gb'];
            $apiCycleKnown = true;
            $apiCycleSource = 'order.volume_cycle_gb';
        }
        if ($apiPlanVolumeGb <= 0 && isset($ordFlag['last_renew_gb']) && (float)$ordFlag['last_renew_gb'] > 0) {
            $apiPlanVolumeGb = (float)$ordFlag['last_renew_gb'];
        }
    }
    // 2) last_renew از سفارش یا از آخرین پرداخت (فقط اندازه بسته؛ نه چرخه کامل)
    if ($apiPlanVolumeGb <= 0 && isset($db) && isset($username)) {
        try {
            $cfgName = (string)(isset($ordFlag['config_username']) ? $ordFlag['config_username'] : $username);
            $stPk2 = $db->prepare("SELECT p.plan_key FROM payments p WHERE p.status='approved' AND p.action_type IN ('renew','new') AND (p.target_username = ? OR p.target_username = ?) ORDER BY p.id DESC LIMIT 1");
            $stPk2->execute([(string)$username, $cfgName]);
            $pk2 = (string)($stPk2->fetchColumn() ?: '');
            if ($pk2 !== '') {
                $v2 = 0.0;
                try {
                    $stPl2 = $db->prepare('SELECT COALESCE(vol, volume_gb, 0) AS v FROM bot_plans WHERE plan_key = ? LIMIT 1');
                    $stPl2->execute([$pk2]);
                    $v2 = (float)($stPl2->fetchColumn() ?: 0);
                } catch (Throwable $ePl) {
                    try {
                        $stPl2 = $db->prepare('SELECT volume_gb FROM bot_plans WHERE plan_key = ? LIMIT 1');
                        $stPl2->execute([$pk2]);
                        $v2 = (float)($stPl2->fetchColumn() ?: 0);
                    } catch (Throwable $ePl2) {}
                }
                if ($v2 > 0) {
                    $apiPlanVolumeGb = $v2;
                }
            }
        } catch (Throwable $ePay) {}
    }

    $remNow = isset($remainingGB) ? (float)$remainingGB : 0.0;

    // 3) فقط یک استنتاج امن و محدود — بدون نوشتن در DB:
    // اگر snapshot نداریم ولی last_renew داریم و مانده ≤ بستهٔ آخر (+۲٪ تلورانس)،
    // تقریباً مطمئنیم مانده قبلی صفر بوده و چرخه = بستهٔ آخر (سناریوی ۵۰ تمام + خرید ۱۰).
    // اگر مانده > بستهٔ آخر، چرخه را حدس نمی‌زنیم (مثال ۲۸ با مانده ۲۵ و خرید ۱۰).
    if (!$apiCycleKnown && $apiPlanVolumeGb > 0) {
        $tol = max(0.05, $apiPlanVolumeGb * 0.02);
        if ($remNow <= ($apiPlanVolumeGb + $tol)) {
            $apiVolumeCycleGb = $apiPlanVolumeGb;
            $apiCycleKnown = true;
            $apiCycleSource = 'inferred_last_renew_safe';
        }
        // else: unknown — نمایش فقط remaining، بدون درصد جعلی از total پنل
    }

    // 4) نمایش
    if ($apiCycleKnown && $apiVolumeCycleGb > 0) {
        $apiDisplayTotalGb = $apiVolumeCycleGb;
        $usedC = max(0.0, $apiVolumeCycleGb - max(0.0, $remNow));
        // اگر به هر دلیل remaining > cycle (نادر)، درصد را ۰ نشان بده نه منفی
        if ($remNow > $apiVolumeCycleGb) {
            $apiUsedCyclePct = 0;
        } else {
            $apiUsedCyclePct = (int)round(min(100.0, max(0.0, ($usedC / $apiVolumeCycleGb) * 100.0)));
        }
    } else {
        // نامشخص: total پنل را به اپ به عنوان چرخه نده
        $apiDisplayTotalGb = 0;
        $apiUsedCyclePct = 0;
        $apiCycleSource = $apiCycleSource === 'none' ? 'unknown' : $apiCycleSource;
    }
} catch (Throwable $eCyc) {
    $apiCycleKnown = false;
    $apiDisplayTotalGb = 0;
    $apiUsedCyclePct = 0;
    $apiCycleSource = 'error';
}

// اخطار حجم برای اپ: بر اساس چرخه معتبر؛ وگرنه آستانه مطلق روی remaining
$apiShouldWarnVol = false;
try {
    $remW = isset($remainingGB) ? (float)$remainingGB : -1.0;
    if ($remW >= 0) {
        if (!empty($apiCycleKnown) && $apiVolumeCycleGb > 0) {
            $cycW = (float)$apiVolumeCycleGb;
            if ($cycW <= 15.0) {
                $apiShouldWarnVol = ($remW / $cycW) <= 0.20;
            } else {
                $apiShouldWarnVol = ($remW <= 5.0);
            }
        } else {
            // بدون چرخه معتبر: فقط آستانه مطلق مانده (نه درصد از سقف انباشتی)
            $apiShouldWarnVol = ($remW > 0 && $remW <= 5.0);
        }
    }
} catch (Throwable $e) {
    $apiShouldWarnVol = false;
}

echo json_encode([
    'ok'            => true,
    'has_subscription' => true,
    'has_used_test' => isset($apiHasUsedTest) ? (int)$apiHasUsedTest : 0,
    'can_claim_test'=> !empty($apiCanClaimTest),
    'can_renew'     => !empty($apiCanRenew),
    'is_test_service'=> !empty($apiIsTestSvc),
    'account_channel'=> isset($ownerChannel) ? $ownerChannel : 'app',
    'account_uid'   => isset($ownerUserId) ? (int)$ownerUserId : 0,
    'username'      => $user['username'],
    'status'        => $status,
    'total_gb'      => $totalGB,
    'used_gb'       => $usedGB,
    'remaining_gb'  => $remainingGB,
    'plan_volume_gb'=> isset($apiPlanVolumeGb) ? round((float)$apiPlanVolumeGb, 3) : 0,
    'last_renew_gb' => isset($apiPlanVolumeGb) ? round((float)$apiPlanVolumeGb, 3) : 0,
    'volume_cycle_gb' => (!empty($apiCycleKnown) && isset($apiVolumeCycleGb) && (float)$apiVolumeCycleGb > 0) ? round((float)$apiVolumeCycleGb, 3) : 0,
    'display_total_gb' => (!empty($apiCycleKnown) && isset($apiDisplayTotalGb) && (float)$apiDisplayTotalGb > 0) ? round((float)$apiDisplayTotalGb, 3) : 0,
    'used_cycle_percent' => (!empty($apiCycleKnown) && isset($apiUsedCyclePct)) ? (int)$apiUsedCyclePct : 0,
    'cycle_known' => !empty($apiCycleKnown),
    'cycle_source' => isset($apiCycleSource) ? (string)$apiCycleSource : 'none',
    'should_warn_volume' => !empty($apiShouldWarnVol),
    'expire_days'   => $expireDays,
    'expire_ts'     => $expireTimestamp ?: 0,
    'on_hold_sec'   => $onHoldDuration,
    'panel_status'  => $status,
    'raw_expire'    => $expireRaw,
    'order_days'    => $orderDays,
    'data_limit'    => $totalBytes,
    'used_traffic'  => $usedBytes,
    'subscription_url' => $subUrl ?? '',
    'servers_count' => count($servers),
    'servers'       => $servers
], JSON_UNESCAPED_UNICODE);
