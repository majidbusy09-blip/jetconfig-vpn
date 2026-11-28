<?php
// پاسخ استاندارد وب‌هوک
http_response_code(200);

require_once 'config.php';
if (is_readable(__DIR__ . '/plans_lib.php')) {
    require_once __DIR__ . '/plans_lib.php';
} elseif (is_readable('plans_lib.php')) {
    require_once 'plans_lib.php';
}

require_once __DIR__ . '/support_ai.php';
require_once __DIR__ . '/wallet_ledger.php';
require_once __DIR__ . '/accounting.php';
if (is_readable(__DIR__ . '/reseller_lib.php')) {
    require_once __DIR__ . '/reseller_lib.php';
}
if (is_readable(__DIR__ . '/test_offers_lib.php')) {
    require_once __DIR__ . '/test_offers_lib.php';
}

/** لینک‌های دانلود اندروید از هاست */
function appAndroidDownloadHtml() {
    $page = defined('APP_DOWNLOAD_PAGE') ? APP_DOWNLOAD_PAGE : 'https://majid6064.ir/download/';
    return "• اندروید (JET / Happ / v2rayNG): <a href=\"{$page}\">دانلود از majid6064.ir/download</a>\n"
         . "• آیفون: <a href=\"https://apps.apple.com/app/streisand/id6450534064\">Streisand</a> · <a href=\"https://apps.apple.com/app/happ-proxy-utility/id6504287215\">Happ</a>\n"
         . "• ویندوز: <a href=\"https://github.com/2dust/v2rayN/releases\">v2rayN</a> · <a href=\"https://github.com/Happ-proxy/happ-desktop/releases\">Happ</a>";
}



// دانلود مستقیم از هاست (پوشه public_html/download)
const APP_HOST_BASE = 'https://majid6064.ir/download';
// از download.php استفاده می‌شود تا دانلود کامل و قابل‌ادامه باشد (نه لینک خام apk)
const DIRECT_DOWNLOAD_URL = 'https://majid6064.ir/download/';
const HAPP_APK_URL = 'https://majid6064.ir/download/';
const V2RAYNG_APK_URL = 'https://majid6064.ir/download/';
const APP_DOWNLOAD_PAGE = APP_HOST_BASE . '/';
// گیت‌هاب فقط به‌عنوان پشتیبان (اگر لازم شد)
const GITHUB_RELEASES_URL = 'https://github.com/majidbusy09-blip/jetconfig-vpn/releases';
/** مهلت فاکتور کارت‌به‌کارت (ثانیه) */
const INVOICE_TTL_SEC = 1200; // ۲۰ دقیقه
/** آدرس صفحه پرداخت وب (می‌توانی در settings با کلید pay_page_url عوض کنی) */
const PAY_PAGE_DEFAULT = 'https://majid6064.ir/pay.php';

// تست سلامت در مرورگر
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    header("Content-Type: text/html; charset=utf-8");
    echo "<div style='font-family:tahoma; padding:30px; text-align:center;'>";
    echo "<h2>🚀 سرور ربات JetConfig فعال و آنلاین است!</h2>";
    try {
        $dbTest = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4", DB_USER, DB_PASS);
        echo "<p style='color:green;'>✅ اتصال دیتابیس کاملاً برقرار است.</p>";
    } catch (Exception $e) {
        echo "<p style='color:red;'>❌ خطای دیتابیس: " . $e->getMessage() . "</p>";
    }
    echo "</div>";
    exit();
}

$rawInput = file_get_contents('php://input');
$update = json_decode($rawInput, true);
if (!$update) exit();

// اتصال به دیتابیس
try {
    $db = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";charset=utf8mb4", DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
    ]);
} catch (Exception $e) {
    exit();
}
$GLOBALS['db'] = $db;
ensureMultiPanelSchema($db);

/**
 * منوی دستورات تلگرام:
 * - همه: فقط /start + دکمه منو
 * - ادمین: /start و /admin
 * رفرش: /setupmenu (فقط ادمین)
 * @return array خلاصه نتیجه برای لاگ/نمایش
 */
function ensureBotMenuCommands($db, $force = false) {
    $report = [];
    try {
        if (!$force && getSetting($db, 'bot_menu_cmds_v2', '') === '1') {
            return ['skipped' => true];
        }

        $cmdStart = json_encode([
            ['command' => 'start', 'description' => 'شروع و منوی اصلی'],
        ], JSON_UNESCAPED_UNICODE);

        $cmdAdmin = json_encode([
            ['command' => 'start', 'description' => 'شروع و منوی اصلی'],
            ['command' => 'admin', 'description' => 'پنل مدیریت'],
        ], JSON_UNESCAPED_UNICODE);

        // 1) بدون scope = پیش‌فرض رسمی برای همه
        $r1 = sendTelegram('setMyCommands', ['commands' => $cmdStart]);
        $report['default_no_scope'] = $r1['ok'] ?? false;

        // 2) صریح default
        $r2 = sendTelegram('setMyCommands', [
            'commands' => $cmdStart,
            'scope' => json_encode(['type' => 'default']),
        ]);
        $report['scope_default'] = $r2['ok'] ?? false;
        if (!($r2['ok'] ?? false)) {
            $report['scope_default_err'] = $r2['description'] ?? $r2;
        }

        // 3) همه چت‌های خصوصی
        $r3 = sendTelegram('setMyCommands', [
            'commands' => $cmdStart,
            'scope' => json_encode(['type' => 'all_private_chats']),
        ]);
        $report['all_private'] = $r3['ok'] ?? false;
        if (!($r3['ok'] ?? false)) {
            $report['all_private_err'] = $r3['description'] ?? $r3;
        }

        // 4) ادمین: start + admin برای مالک و ادمین‌های جدول
        $adminIds = [];
        if (defined('ADMIN_ID') && ADMIN_ID) {
            $adminIds[] = (int)ADMIN_ID;
        }
        try {
            ensureBotAdminsTable($db);
            foreach (getExtraAdmins($db) as $row) {
                $adminIds[] = (int)$row['user_id'];
            }
        } catch (Throwable $e) {}
        $adminIds = array_values(array_unique(array_filter($adminIds)));
        $okAdmin = 0;
        foreach ($adminIds as $aid) {
            $r4 = sendTelegram('setMyCommands', [
                'commands' => $cmdAdmin,
                'scope' => json_encode(['type' => 'chat', 'chat_id' => $aid]),
            ]);
            if ($r4['ok'] ?? false) {
                $okAdmin++;
            }
            sendTelegram('setChatMenuButton', [
                'chat_id' => $aid,
                'menu_button' => json_encode(['type' => 'commands']),
            ]);
        }
        $report['admin_chat_count'] = $okAdmin;

        // 5) دکمه منو برای همه (پیش‌فرض ربات)
        $r6 = sendTelegram('setChatMenuButton', [
            'menu_button' => json_encode(['type' => 'commands']),
        ]);
        $report['default_menu_btn'] = $r6['ok'] ?? false;
        if (!($r6['ok'] ?? false)) {
            $report['default_menu_btn_err'] = $r6['description'] ?? $r6;
        }

        setSetting($db, 'bot_menu_cmds_v2', '1');
        setSetting($db, 'bot_menu_cmds_v1', '1');
    } catch (Throwable $e) {
        $report['exception'] = $e->getMessage();
        @file_put_contents(__DIR__ . '/bot_error.log', date('c') . ' menu_cmds ' . $e->getMessage() . "\n", FILE_APPEND);
    }
    return $report;
}



function telegramApiBases() {
    $bases = [];
    if (defined('WORKER_URL') && WORKER_URL && defined('BOT_TOKEN') && BOT_TOKEN) {
        $bases[] = rtrim(WORKER_URL, '/') . '/bot' . BOT_TOKEN;
    }
    if (defined('BOT_TOKEN') && BOT_TOKEN) {
        $direct = 'https://api.telegram.org/bot' . BOT_TOKEN;
        if (!in_array($direct, $bases, true)) {
            $bases[] = $direct;
        }
    }
    return $bases;
}



/**
 * کاتالوگ دکمه‌های ربات برای کنترل رنگ از پنل وب
 * default: primary|success|danger
 * match: text / text_contains / cb / cb_prefix
 */


/** دکمه‌های پنل ادمین از رنگ‌بندی کاربر خارج‌اند */
function tgButtonIsAdminOnly(array $btn) {
    $cb = (string)($btn['callback_data'] ?? '');
    if ($cb !== '' && (strpos($cb, 'adm_') === 0 || strpos($cb, 'admin_') === 0)) {
        return true;
    }
    return false;
}

/**
 * نقش معنایی دکمه کاربر — دکمه‌های جدید خودکار در یکی از این نقش‌ها جا می‌گیرند
 * positive | cancel | nav | test | wallet
 */
function tgButtonRole(array $btn) {
    $cb = (string)($btn['callback_data'] ?? '');
    $text = (string)($btn['text'] ?? '');
    $t = mb_strtolower($text);

    // انصراف / بازگشت خطرناک
    if ($cb === 'cancel_order' || $cb === 'my_wallet' || $cb === 'my_services_list') {
        if (mb_strpos($text, 'بازگشت') !== false || $cb === 'cancel_order') {
            // my_wallet گاهی «بازگشت به کیف» است → cancel
            if ($cb === 'cancel_order' || mb_strpos($text, 'انصراف') !== false || mb_strpos($text, 'بازگشت') !== false) {
                return 'cancel';
            }
        }
    }
    if ($cb === 'cancel_order' || mb_strpos($text, 'انصراف') !== false) {
        return 'cancel';
    }
    if (mb_strpos($text, 'بازگشت') !== false || mb_strpos($text, 'تغییر پلن') !== false) {
        return 'cancel';
    }
    if (isset($btn['style']) && strtolower((string)$btn['style']) === 'danger') {
        // اگر در کد danger گذاشته شده و ادمین نیست
        if (mb_strpos($text, 'حذف') === false) {
            // danger کاربر معمولاً بازگشت/انصراف
            return 'cancel';
        }
    }

    // تست
    if (mb_strpos($text, 'تست') !== false || strpos($cb, 'test') !== false) {
        return 'test';
    }

    // کیف پول / شارژ
    if ($cb === 'charge_wallet_menu' || $cb === 'transfer_balance_start' || $cb === 'my_wallet') {
        return 'wallet';
    }
    if (mb_strpos($text, 'کیف پول') !== false || mb_strpos($text, 'شارژ') !== false) {
        return 'wallet';
    }
    if (strpos($cb, 'pay_wallet:') === 0) {
        return 'positive';
    }

    // اقدام مثبت: خرید، تمدید، تأیید عضویت، پرداخت
    if (strpos($cb, 'ren_srv:') === 0 || strpos($cb, 'pay_wallet:') === 0) {
        return 'positive';
    }
    if ($cb === 'check_channel_join' || $cb === 'main_categories') {
        // main_categories = شروع خرید → positive-ish but often nav; treat buy entry as positive
        if ($cb === 'main_categories' || mb_strpos($text, 'خرید') !== false) {
            return 'positive';
        }
        return 'positive';
    }
    if (mb_strpos($text, 'خرید') !== false || mb_strpos($text, 'تمدید') !== false) {
        return 'positive';
    }
    if (mb_strpos($text, 'عضو شدم') !== false || mb_strpos($text, 'پرداخت') !== false) {
        return 'positive';
    }
    if (isset($btn['style']) && strtolower((string)$btn['style']) === 'success') {
        return 'positive';
    }

    // ناوبری: دسته‌ها، پلن‌ها، راهنما، کانال، پشتیبانی، کپی کارت، …
    return 'nav';
}

/** نقشه نقش → رنگ (primary|success|danger) از settings */
function getTgRoleStyleMap() {
    global $db;
    $defaults = [
        'positive' => 'success', // سبز — خرید و اقدام اصلی
        'cancel' => 'danger',    // قرمز — انصراف/بازگشت
        'nav' => 'primary',      // آبی — منو و انتخاب
        'test' => 'primary',     // آبی — تست
        'wallet' => 'success',   // سبز — کیف پول
    ];
    if (!$db) {
        return $defaults;
    }
    try {
        $raw = getSetting($db, 'tg_btn_roles', '');
        if ($raw === '') {
            return $defaults;
        }
        $j = json_decode($raw, true);
        if (!is_array($j)) {
            return $defaults;
        }
        $allowed = ['primary', 'success', 'danger', 'none'];
        foreach ($defaults as $role => $def) {
            $v = strtolower(trim((string)($j[$role] ?? $def)));
            if ($v === 'gray' || $v === 'grey') $v = 'none';
            $defaults[$role] = in_array($v, $allowed, true) ? $v : $def;
        }
    } catch (Throwable $e) {
    }
    return $defaults;
}

function resolveTgButtonStyle($style) {
    $style = strtolower(trim((string)$style));
    if ($style === '' || $style === 'default') {
        return null;
    }
    if ($style === 'blue') {
        $style = 'primary';
    }
    if ($style === 'green') {
        $style = 'success';
    }
    if ($style === 'red') {
        $style = 'danger';
    }
    if (!in_array($style, ['primary', 'success', 'danger'], true)) {
        return null;
    }
    return $style;
}

function getTgHighlightTargets() {
    static $c = null;
    if ($c !== null) return $c;
    $c = [];
    $tree = __DIR__ . '/tg_menu_tree.php';
    if (is_readable($tree)) {
        require_once $tree;
        if (function_exists('jet_tg_menu_flat_targets')) {
            global $db;
            $c = jet_tg_menu_flat_targets($db instanceof PDO ? $db : null);
        }
    }
    $path = __DIR__ . '/tg_button_highlights.php';
    if (is_readable($path)) {
        require_once $path;
        if (function_exists('jet_tg_highlight_targets')) {
            foreach (jet_tg_highlight_targets() as $id => $meta) {
                if (!isset($c[$id])) {
                    $c[$id] = $meta;
                }
            }
        }
    }
    return $c;
}

function getTgHighlightOverrides() {
    global $db;
    static $cache = null;
    static $loadedWithDb = false;
    // اگر قبلاً بدون DB کش خالی شده بود، با آمدن DB دوباره بخوان
    if ($cache !== null && ($loadedWithDb || !$db)) {
        return $cache;
    }
    $cache = [];
    $loadedWithDb = (bool)$db;
    if (!$db) {
        return $cache;
    }
    try {
        $raw = getSetting($db, 'tg_btn_highlights', '');
        if ($raw === '' || $raw === false) {
            return $cache;
        }
        $j = json_decode((string)$raw, true);
        if (!is_array($j)) {
            return $cache;
        }
        foreach ($j as $id => $style) {
            $style = strtolower(trim((string)$style));
            // role/default = از نقشه نقش؛ none/gray = بدون style تلگرام (خاکستری پیش‌فرض)
            if ($style === '' || $style === 'role' || $style === 'default') {
                continue;
            }
            if (in_array($style, ['primary', 'success', 'danger', 'none', 'gray', 'grey'], true)) {
                if ($style === 'gray' || $style === 'grey') {
                    $style = 'none';
                }
                $cache[(string)$id] = $style;
            }
        }
    } catch (Throwable $e) {
    }
    return $cache;
}

function jet_tg_normalize_btn_text($text) {
    $text = (string)$text;
    // حذف علائم تزئینی رایج برای تطبیق پایدارتر
    $text = preg_replace('/[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}\x{FE0F}\x{200D}]/u', '', $text);
    $text = preg_replace('/\s+/u', ' ', $text);
    return trim($text);
}

function matchTgHighlightId(array $btn) {
    $text = (string)($btn['text'] ?? '');
    $textNorm = jet_tg_normalize_btn_text($text);
    $cb = (string)($btn['callback_data'] ?? '');
    $targets = getTgHighlightTargets();
    // callback دقیق
    if ($cb !== '') {
        foreach ($targets as $id => $meta) {
            $m = $meta['match'] ?? [];
            if (!empty($m['cb']) && $cb === $m['cb']) return $id;
        }
        foreach ($targets as $id => $meta) {
            $m = $meta['match'] ?? [];
            if (!empty($m['cb_prefix']) && strpos($cb, $m['cb_prefix']) === 0) return $id;
        }
    }
    foreach ($targets as $id => $meta) {
        $m = $meta['match'] ?? [];
        if (empty($m['text_contains']) || $text === '') continue;
        $needle = (string)$m['text_contains'];
        if (mb_strpos($text, $needle) !== false) {
            return $id;
        }
        $needleNorm = jet_tg_normalize_btn_text($needle);
        if ($needleNorm !== '' && mb_strpos($textNorm, $needleNorm) !== false) {
            return $id;
        }
    }
    return null;
}

function styleForTgButton(array $btn) {
    if (tgButtonIsAdminOnly($btn)) {
        return isset($btn['style']) ? resolveTgButtonStyle($btn['style']) : null;
    }
    // استایل صریح روی دکمه اولویت دارد (مثلاً عنوان دسته: none = بی‌رنگ)
    if (isset($btn['style'])) {
        $raw = strtolower(trim((string)$btn['style']));
        if ($raw === 'none' || $raw === 'gray' || $raw === 'grey') {
            return null;
        }
        $explicit = resolveTgButtonStyle($btn['style']);
        if ($explicit !== null) {
            return $explicit;
        }
    }
    // ۱) برجسته‌سازی صریح (زیرمنو / دکمه خاص)
    $hid = matchTgHighlightId($btn);
    if ($hid !== null) {
        $hl = getTgHighlightOverrides();
        if (isset($hl[$hid])) {
            if ($hl[$hid] === 'none') {
                return null; // بدون رنگ اختصاصی تلگرام
            }
            return $hl[$hid];
        }
    }
    // ۲) نقش عمومی — مقدار none در نقشه نقش = بی‌رنگ
    $role = tgButtonRole($btn);
    $map = getTgRoleStyleMap();
    $style = $map[$role] ?? 'primary';
    if ($style === 'none' || $style === 'gray' || $style === 'grey') {
        return null;
    }
    return resolveTgButtonStyle($style) ?: 'primary';
}

function applyTgButtonStylesToMarkup($markup) {
    $wasJson = false;
    if (is_string($markup)) {
        $decoded = json_decode($markup, true);
        if (!is_array($decoded)) {
            return $markup;
        }
        $markup = $decoded;
        $wasJson = true;
    }
    if (!is_array($markup)) {
        return $markup;
    }
    foreach (['inline_keyboard', 'keyboard'] as $key) {
        if (empty($markup[$key]) || !is_array($markup[$key])) {
            continue;
        }
        foreach ($markup[$key] as $ri => $row) {
            if (!is_array($row)) {
                continue;
            }
            foreach ($row as $ci => $btn) {
                if (!is_array($btn)) {
                    continue;
                }
                $resolved = styleForTgButton($btn);
                if ($resolved === null) {
                    unset($markup[$key][$ri][$ci]['style']);
                } else {
                    $markup[$key][$ri][$ci]['style'] = $resolved;
                }
            }
        }
    }
    return $wasJson ? json_encode($markup, JSON_UNESCAPED_UNICODE) : $markup;
}

function sendTelegram($method, $data = []) {
    if (is_array($data) && !empty($data['reply_markup'])) {
        $data['reply_markup'] = applyTgButtonStylesToMarkup($data['reply_markup']);
    }
    $last = [];
    foreach (telegramApiBases() as $base) {
        $ch = curl_init();
        $opts = [
            CURLOPT_URL => rtrim($base, '/') . '/' . ltrim($method, '/'),
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $data,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_SSL_VERIFYPEER => false,
            CURLOPT_SSL_VERIFYHOST => 0,
            CURLOPT_TIMEOUT => 18,
            CURLOPT_CONNECTTIMEOUT => 8,
            CURLOPT_FOLLOWLOCATION => true,
        ];
        if (defined('CURL_IPRESOLVE_V4')) {
            $opts[CURLOPT_IPRESOLVE] = CURL_IPRESOLVE_V4;
        }
        curl_setopt_array($ch, $opts);
        $res = curl_exec($ch);
        $cerr = curl_error($ch);
        $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        $j = json_decode((string)$res, true);
        if (!is_array($j)) {
            $j = [];
        }
        $last = $j;
        if (!empty($j['ok'])) {
            return $j;
        }
        // خطای منطقی تلگرام (چت نامعتبر و …) — مسیر بعدی همان را برنمی‌گرداند
        if ($http >= 200 && $http < 500 && isset($j['description']) && $cerr === '') {
            $desc = (string)$j['description'];
            if (stripos($desc, 'chat not found') !== false
                || stripos($desc, 'blocked') !== false
                || stripos($desc, 'deactivated') !== false
                || stripos($desc, 'user is deactivated') !== false) {
                return $j;
            }
        }
        // Worker/شبکه fail → مسیر بعدی
    }
    return is_array($last) ? $last : [];
}

/**
 * اگر پیام فعلی عکس باشد editMessageText کار نمی‌کند → پیام متنی جدید می‌فرستد.
 */
function adminSendOrEditText($chat_id, $update, $text, $replyMarkup = null) {
    $msg = $update['callback_query']['message'] ?? [];
    $mid = $msg['message_id'] ?? null;
    $hasPhoto = !empty($msg['photo']);
    $payload = [
        'chat_id' => $chat_id,
        'text' => $text,
        'parse_mode' => 'HTML',
    ];
    if ($replyMarkup !== null) {
        $payload['reply_markup'] = is_string($replyMarkup) ? $replyMarkup : json_encode($replyMarkup, JSON_UNESCAPED_UNICODE);
    }
    if ($hasPhoto || !$mid) {
        if (!empty($update['callback_query']['id'])) {
            sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
        }
        return sendTelegram('sendMessage', $payload);
    }
    $payload['message_id'] = $mid;
    $res = sendTelegram('editMessageText', $payload);
    if (empty($res['ok'])) {
        if (!empty($update['callback_query']['id'])) {
            sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
        }
        return sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => $text,
            'parse_mode' => 'HTML',
            'reply_markup' => $payload['reply_markup'] ?? null,
        ]);
    }
    return $res;
}

function getQRCodeUrl($text) {
    return "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" . urlencode($text);
}

function ensureSettingsTable($db) {
    static $done = false;
    if ($done || !($db instanceof PDO)) {
        return;
    }
    try {
        $db->exec("CREATE TABLE IF NOT EXISTS settings (
            setting_key VARCHAR(191) NOT NULL,
            setting_val TEXT NULL,
            PRIMARY KEY (setting_key)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    } catch (Exception $e) {}
    // اگر جدول قدیمی بدون کلید یکتا باشد، آپدیت‌ها ذخیره نمی‌شوند
    try {
        $idx = $db->query("SHOW INDEX FROM settings WHERE Key_name = 'PRIMARY' OR Column_name = 'setting_key'")->fetchAll();
        $hasUnique = false;
        foreach ($idx as $row) {
            if ((int)($row['Non_unique'] ?? 1) === 0) {
                $hasUnique = true;
                break;
            }
        }
        if (!$hasUnique) {
            // حذف ردیف‌های تکراری (قدیمی‌ترها)
            $db->exec("DELETE s1 FROM settings s1
                INNER JOIN settings s2
                WHERE s1.setting_key = s2.setting_key AND s1.setting_val < s2.setting_val");
            try {
                $db->exec("ALTER TABLE settings ADD PRIMARY KEY (setting_key)");
            } catch (Exception $e2) {
                try {
                    $db->exec("ALTER TABLE settings ADD UNIQUE KEY uq_setting_key (setting_key)");
                } catch (Exception $e3) {}
            }
        }
    } catch (Exception $e) {}
    $done = true;
}

/** کش مشترک get/set تا بعد از تغییر، همان درخواست مقدار جدید ببیند */
function &settingsCacheRef() {
    static $cache = [];
    return $cache;
}

function getSetting($db, $key, $default = '') {
    $cache = &settingsCacheRef();
    if (array_key_exists($key, $cache)) {
        return $cache[$key];
    }
    try {
        ensureSettingsTable($db);
        $stmt = $db->prepare("SELECT setting_val FROM settings WHERE setting_key = ? LIMIT 1");
        $stmt->execute([$key]);
        $res = $stmt->fetchColumn();
        $val = $res !== false ? (string)$res : $default;
        $cache[$key] = $val;
        return $val;
    } catch (Exception $e) {
        return $default;
    }
}

function setSetting($db, $key, $val) {
    $val = (string)$val;
    try {
        ensureSettingsTable($db);
        $stmt = $db->prepare("INSERT INTO settings (setting_key, setting_val) VALUES (?, ?) ON DUPLICATE KEY UPDATE setting_val = VALUES(setting_val)");
        $stmt->execute([$key, $val]);
    } catch (Exception $e) {}
    $cache = &settingsCacheRef();
    $cache[$key] = $val;
}



/** کلید ذخیره group_ids اختصاصی هر پنل */
function panelGroupIdsSettingKey($panelId) {
    return 'panel_group_ids_' . (int)$panelId;
}

/** خواندن group_ids یک پنل */
function getPanelGroupIdsSetting($db, $panelId) {
    $pid = (int)$panelId;
    if ($pid > 0) {
        $v = trim((string)getSetting($db, panelGroupIdsSettingKey($pid), ''));
        if ($v !== '') {
            return $v;
        }
        try {
            $p = function_exists('getPanelById') ? getPanelById($pid, $db) : null;
            if (is_array($p) && !empty($p['is_default'])) {
                return trim((string)getSetting($db, 'pasargad_group_ids', ''));
            }
        } catch (Exception $e) {}
        return '';
    }
    return trim((string)getSetting($db, 'pasargad_group_ids', ''));
}

/** ذخیره group_ids برای یک پنل */
function setPanelGroupIdsSetting($db, $panelId, $val) {
    $val = preg_replace('/[^0-9,]/', '', (string)$val);
    $pid = (int)$panelId;
    if ($pid > 0) {
        setSetting($db, panelGroupIdsSettingKey($pid), $val === '' ? '0' : $val);
        try {
            $p = function_exists('getPanelById') ? getPanelById($pid, $db) : null;
            if (is_array($p) && !empty($p['is_default'])) {
                setSetting($db, 'pasargad_group_ids', $val === '' ? '0' : $val);
            }
        } catch (Exception $e) {}
        return;
    }
    setSetting($db, 'pasargad_group_ids', $val === '' ? '0' : $val);
}

function parseGroupIdsList($raw) {
    $raw = trim((string)$raw);
    if ($raw === '' || $raw === '0') {
        return [];
    }
    $ids = [];
    foreach (explode(',', $raw) as $p) {
        $p = trim($p);
        if ($p !== '' && $p !== '0' && ctype_digit($p)) {
            $ids[] = (int)$p;
        }
    }
    return array_values(array_unique($ids));
}


function isFeatureEnabled($db, $key) {
    // پرچم دکمه‌ها همیشه تازه از دیتابیس (بدون کش کهنه)
    $key = (string)$key;
    if (strpos($key, 'btn_') === 0) {
        $cache = &settingsCacheRef();
        unset($cache[$key]);
    }
    $v = getSetting($db, $key, '1');
    $v = is_string($v) ? trim($v) : $v;
    return ($v === '1' || $v === 1 || $v === true || $v === 'true' || $v === 'on');
}

/** مالک اصلی تعریف‌شده در config.php */
function isBotOwner($userId) {
    return defined('ADMIN_ID') && ADMIN_ID && (int)$userId === (int)ADMIN_ID;
}

function ensureBotAdminsTable($db) {
    try {
        $db->exec("CREATE TABLE IF NOT EXISTS bot_admins (
            user_id BIGINT NOT NULL PRIMARY KEY,
            added_by BIGINT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    } catch (Exception $e) {}
}

/** مالک اصلی یا ادمین اضافه‌شده در جدول bot_admins */
function isBotAdmin($userId) {
    if (isBotOwner($userId)) {
        return true;
    }
    global $db;
    if (!$db) {
        return false;
    }
    try {
        ensureBotAdminsTable($db);
        $st = $db->prepare("SELECT 1 FROM bot_admins WHERE user_id = ? LIMIT 1");
        $st->execute([(int)$userId]);
        return (bool)$st->fetchColumn();
    } catch (Exception $e) {
        return false;
    }
}

/**
 * step خالی = کاربر در منوی آزاد است
 * هر step دیگر یعنی منتظر ورودی متن/عکس هستیم و منو نباید متن را بدزدد
 */
function isIdleStep($userOrStep) {
    if (is_array($userOrStep)) {
        $s = trim((string)($userOrStep['step'] ?? 'none'));
    } else {
        $s = trim((string)$userOrStep);
    }
    return ($s === '' || $s === 'none');
}

/**
 * تشخیص دکمه منو: فقط پیام‌های کوتاه (نه متن طولانی ادمین/پشتیبانی/همگانی)
 */
function isMenuKeywordHit($text, $keyword, $maxLen = 48) {
    $text = trim((string)$text);
    if ($text === '' || mb_strlen($text) > $maxLen) {
        return false;
    }
    return (mb_strpos($text, (string)$keyword) !== false);
}

/**
 * اگر کاربر روی دکمه منوی اصلی زد ولی step گیر کرده بود،
 * step را آزاد می‌کند تا مجبور به /start نباشد.
 */
function tryRecoverMainMenuStep($db, &$currentUser, $user_id, $text, $callback_data = '') {
    if ($callback_data) {
        return false;
    }
    $text = trim((string)$text);
    if ($text === '' || mb_strlen($text) > 48) {
        return false;
    }
    // دستورات صریح
    if (strpos($text, '/start') === 0 || strpos($text, '/admin') === 0 || strpos($text, '/menu') === 0) {
        return false;
    }
    if (isIdleStep($currentUser)) {
        return false;
    }
    $keywords = [
        'خرید اشتراک',
        'سرویس‌های من',
        'سرویس های من',
        'تست رایگان',
        'کیف پول',
        'پشتیبانی',
        'زیرمجموعه',
        'دعوت دوست',
        'اپ و راهنمای اتصال',
        'دانلود اپلیکیشن',
        'دانلود اپ',
        'راهنمای اتصال',
        'کانال آموزش',
        'اطلاع‌رسانی',
        'اطلاع رسانی',
        'شماره کارت',
        'منوی اصلی',
        'منو اصلی',
        'درخواست نمایندگی',
        'پنل نمایندگی',
        'نمایندگی',
    ];
    $hit = false;
    foreach ($keywords as $kw) {
        if (isMenuKeywordHit($text, $kw)) {
            $hit = true;
            break;
        }
    }
    if (!$hit) {
        return false;
    }
    try {
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([(int)$user_id]);
    } catch (Exception $e) {
        return false;
    }
    if (is_array($currentUser)) {
        $currentUser['step'] = 'none';
    }
    return true;
}




/** لیست ادمین‌های اضافه (بدون مالک اصلی) */
function getExtraAdmins($db) {
    ensureBotAdminsTable($db);
    try {
        return $db->query("SELECT user_id, added_by, created_at FROM bot_admins ORDER BY created_at ASC")->fetchAll(PDO::FETCH_ASSOC);
    } catch (Exception $e) {
        return [];
    }
}

/** همه آیدی‌های ادمین (مالک + جدول) */
function getAllAdminIds($db) {
    $ids = [];
    if (defined('ADMIN_ID') && ADMIN_ID) {
        $ids[] = (int)ADMIN_ID;
    }
    foreach (getExtraAdmins($db) as $row) {
        $ids[] = (int)$row['user_id'];
    }
    return array_values(array_unique(array_filter($ids)));
}

/** ارسال پیام به همه ادمین‌ها */
function ensureAdminBroadcastTable($db) {
    static $done = false;
    if ($done || !$db) return;
    try {
        $db->exec("CREATE TABLE IF NOT EXISTS admin_broadcast_msgs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            kind VARCHAR(32) NOT NULL,
            ref_id VARCHAR(64) NOT NULL,
            admin_id BIGINT NOT NULL,
            message_id BIGINT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_kind_ref (kind, ref_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
        $done = true;
    } catch (Exception $e) {}
}

/**
 * ارسال به همه ادمین‌ها و در صورت نیاز ذخیره message_id برای پاک‌سازی بعدی
 * $kind / $refId مثلاً support + user_id یا payment + payment_id
 */
function notifyAdminsLog($msg) {
    @file_put_contents(__DIR__ . '/bot_error.log', '[' . date('Y-m-d H:i:s') . '] notifyAdmins ' . $msg . "\n", FILE_APPEND | LOCK_EX);
}

function notifyAdmins($text, $replyMarkup = null, $photoFileId = null, $kind = null, $refId = null) {
    global $db;
    $ids = getAllAdminIds($db);
    if (!$ids) {
        notifyAdminsLog('no admin ids');
        return;
    }
    $kind = $kind ? (string)$kind : null;
    $refId = ($refId !== null && $refId !== '') ? (string)$refId : null;
    if ($db && $kind && $refId !== null) {
        ensureAdminBroadcastTable($db);
        try {
            $db->prepare("DELETE FROM admin_broadcast_msgs WHERE kind = ? AND ref_id = ?")->execute([$kind, $refId]);
        } catch (Exception $e) {}
    }
    $okN = 0;
    $failN = 0;
    $n = count($ids);
    foreach ($ids as $i => $id) {
        $id = (int)$id;
        if ($id <= 0) {
            continue;
        }
        if ($photoFileId) {
            $payload = [
                'chat_id' => $id,
                'photo' => $photoFileId,
                'caption' => $text,
                'parse_mode' => 'HTML',
            ];
            if ($replyMarkup) {
                $payload['reply_markup'] = $replyMarkup;
            }
            $res = sendTelegram('sendPhoto', $payload);
        } else {
            $payload = [
                'chat_id' => $id,
                'text' => $text,
                'parse_mode' => 'HTML',
            ];
            if ($replyMarkup) {
                $payload['reply_markup'] = $replyMarkup;
            }
            $res = sendTelegram('sendMessage', $payload);
        }
        $mid = (int)($res['result']['message_id'] ?? 0);
        if (!empty($res['ok']) && $mid > 0) {
            $okN++;
            if ($db && $kind && $refId !== null) {
                try {
                    $db->prepare("INSERT INTO admin_broadcast_msgs (kind, ref_id, admin_id, message_id) VALUES (?, ?, ?, ?)")
                       ->execute([$kind, $refId, $id, $mid]);
                } catch (Exception $e) {}
            }
        } else {
            $failN++;
            $why = (string)($res['description'] ?? 'no_ok');
            notifyAdminsLog("fail admin={$id} kind=" . ($kind ?: '-') . " ref=" . ($refId ?: '-') . " why={$why}");
        }
        // فاصله کوتاه تا Worker/تلگرام زیر فشار پشت‌سرهم کمتر fail شوند
        if ($i < $n - 1) {
            usleep(120000);
        }
    }
    if ($failN > 0) {
        notifyAdminsLog("summary ok={$okN} fail={$failN} total={$n} kind=" . ($kind ?: '-'));
    }
}

/**
 * پاک کردن (یا بی‌اثر کردن) پیام‌های broadcast برای بقیه ادمین‌ها
 * $exceptAdminId = ادمینی که کار را انجام داده (پیامش حذف نمی‌شود مگر $alsoExcept=true)
 */
function clearAdminBroadcastMessages($db, $kind, $refId, $exceptAdminId = null, $doneNote = null, $alsoExcept = false) {
    if (!$db || !$kind || $refId === null || $refId === '') return;
    ensureAdminBroadcastTable($db);
    try {
        $st = $db->prepare("SELECT admin_id, message_id FROM admin_broadcast_msgs WHERE kind = ? AND ref_id = ?");
        $st->execute([(string)$kind, (string)$refId]);
        $rows = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];
    } catch (Exception $e) {
        return;
    }
    foreach ($rows as $row) {
        $aid = (int)$row['admin_id'];
        $mid = (int)$row['message_id'];
        if ($mid <= 0) continue;
        if (!$alsoExcept && $exceptAdminId !== null && $aid === (int)$exceptAdminId) {
            continue;
        }
        $deleted = false;
        $del = sendTelegram('deleteMessage', ['chat_id' => $aid, 'message_id' => $mid]);
        if (!empty($del['ok'])) {
            $deleted = true;
        }
        if (!$deleted && $doneNote) {
            // اگر حذف ممکن نبود، دکمه را بردار و یادداشت بگذار
            sendTelegram('editMessageReplyMarkup', [
                'chat_id' => $aid,
                'message_id' => $mid,
                'reply_markup' => json_encode(['inline_keyboard' => []]),
            ]);
            $cap = sendTelegram('editMessageCaption', [
                'chat_id' => $aid,
                'message_id' => $mid,
                'caption' => $doneNote,
                'parse_mode' => 'HTML',
            ]);
            if (empty($cap['ok'])) {
                sendTelegram('editMessageText', [
                    'chat_id' => $aid,
                    'message_id' => $mid,
                    'text' => $doneNote,
                    'parse_mode' => 'HTML',
                ]);
            }
        }
    }
    try {
        $db->prepare("DELETE FROM admin_broadcast_msgs WHERE kind = ? AND ref_id = ?")->execute([(string)$kind, (string)$refId]);
    } catch (Exception $e) {}
}

/** لغو پیش‌فاکتورهای بدون فیش (AWAITING_RECEIPT) برای یک کاربر */
function cancelAwaitingInvoices($db, $userId) {
    try {
        $db->prepare("UPDATE payments SET status = 'cancelled' WHERE user_id = ? AND status = 'pending' AND photo_file_id = 'AWAITING_RECEIPT'")
           ->execute([(int)$userId]);
    } catch (Exception $e) {
        try {
            $db->prepare("UPDATE payments SET status = 'rejected' WHERE user_id = ? AND status = 'pending' AND photo_file_id = 'AWAITING_RECEIPT'")
               ->execute([(int)$userId]);
        } catch (Exception $e2) {}
    }
}

/** ستون‌های pay_token / expires_at برای صفحه پرداخت وب */
function ensurePaymentPayColumns($db) {
    static $done = false;
    if ($done) {
        return;
    }
    $done = true;
    try {
        $cols = $db->query("SHOW COLUMNS FROM payments")->fetchAll(PDO::FETCH_COLUMN);
        $cols = array_map('strtolower', $cols ?: []);
        if (!in_array('pay_token', $cols, true)) {
            $db->exec("ALTER TABLE payments ADD COLUMN pay_token VARCHAR(64) NULL DEFAULT NULL");
            try {
                $db->exec("CREATE INDEX idx_payments_pay_token ON payments (pay_token)");
            } catch (Exception $e) {
            }
        }
        if (!in_array('expires_at', $cols, true)) {
            $db->exec("ALTER TABLE payments ADD COLUMN expires_at DATETIME NULL DEFAULT NULL");
        }
        if (!in_array('invoice_msg_id', $cols, true)) {
            $db->exec("ALTER TABLE payments ADD COLUMN invoice_msg_id BIGINT NULL DEFAULT NULL");
        }
    } catch (Exception $e) {
    }
}

function rememberInvoiceMsg($db, $paymentId, $msgId) {
    $paymentId = (int)$paymentId;
    $msgId = (int)$msgId;
    if ($paymentId <= 0 || $msgId <= 0) {
        return;
    }
    try {
        ensurePaymentPayColumns($db);
        $db->prepare('UPDATE payments SET invoice_msg_id = ? WHERE id = ?')->execute([$msgId, $paymentId]);
    } catch (Exception $e) {
    }
}

function notifyInvoiceExpired($db, array $pay) {
    $uid = (int)($pay['user_id'] ?? 0);
    $pid = (int)($pay['id'] ?? 0);
    if ($uid <= 0) {
        return;
    }
    $mid = (int)($pay['invoice_msg_id'] ?? 0);
    $txt = "⏰ <b>مهلت فاکتور #{$pid} تمام شد.</b>\n\n"
         . "اگر هنوز پرداخت نکردی، از منو فاکتور جدید بساز.\n\n"
         . "اگر <b>پرداخت کردی</b> ولی هنوز خودکار تأیید نشد، روی «پرداخت کرده‌ام» بزن و <b>عکس فیش</b> را بفرست تا سریع بررسی شود.";
    if ($mid > 0) {
        $del = sendTelegram('deleteMessage', ['chat_id' => $uid, 'message_id' => $mid]);
        if (empty($del['ok'])) {
            sendTelegram('editMessageText', [
                'chat_id' => $uid,
                'message_id' => $mid,
                'text' => $txt,
                'parse_mode' => 'HTML',
            ]);
        }
    }
    sendTelegram('sendMessage', [
        'chat_id' => $uid,
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => '✅ پرداخت کرده‌ام — ارسال فیش', 'callback_data' => 'pay_claim:' . $pid, 'style' => 'success']],
                [['text' => '🛍 خرید اشتراک جدید', 'callback_data' => 'main_categories', 'style' => 'primary']],
                [['text' => '💰 شارژ کیف پول', 'callback_data' => 'wallet_menu', 'style' => 'primary']],
            ]
        ], JSON_UNESCAPED_UNICODE),
    ]);
    try {
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ? AND (step LIKE 'pay:%' OR step LIKE 'payid:%')")->execute([$uid]);
    } catch (Exception $e) {
    }
}

function generatePayToken() {
    try {
        return bin2hex(random_bytes(24));
    } catch (Exception $e) {
        return sha1(uniqid((string)mt_rand(), true) . microtime(true));
    }
}

function getPayPageBaseUrl($db = null) {
    if ($db instanceof PDO) {
        try {
            $u = trim((string)getSetting($db, 'pay_page_url', ''));
            if ($u !== '') {
                return rtrim($u, '?&');
            }
        } catch (Exception $e) {
        }
    }
    return defined('PAY_PAGE_DEFAULT') ? PAY_PAGE_DEFAULT : 'https://majid6064.ir/pay.php';
}

function buildPayPageLink($db, $token) {
    $base = getPayPageBaseUrl($db);
    $sep = (strpos($base, '?') !== false) ? '&' : '?';
    return $base . $sep . 't=' . urlencode($token);
}

/** منقضی کردن فاکتورهای pending قدیمی‌تر از مهلت + اطلاع به کاربر */
function expireStaleInvoices($db) {
    $ttl = defined('INVOICE_TTL_SEC') ? (int)INVOICE_TTL_SEC : 1200;
    ensurePaymentPayColumns($db);
    $rows = [];
    try {
        $st = $db->prepare(
            "SELECT * FROM payments
             WHERE status = 'pending' AND photo_file_id = 'AWAITING_RECEIPT'
               AND (
                 (expires_at IS NOT NULL AND expires_at < NOW())
                 OR (expires_at IS NULL AND created_at < DATE_SUB(NOW(), INTERVAL ? SECOND))
               )
             LIMIT 40"
        );
        $st->execute([$ttl]);
        $rows = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];
    } catch (Exception $e) {
        $rows = [];
    }
    foreach ($rows as $pay) {
        $pid = (int)$pay['id'];
        try {
            $db->prepare("UPDATE payments SET status = 'expired' WHERE id = ? AND status = 'pending'")->execute([$pid]);
        } catch (Exception $e) {
            try {
                $db->prepare("UPDATE payments SET status = 'rejected' WHERE id = ? AND status = 'pending'")->execute([$pid]);
            } catch (Exception $e2) {
            }
        }
        notifyInvoiceExpired($db, $pay);
    }
}

function isPaymentExpiredRow(array $pay) {
    if (($pay['status'] ?? '') === 'expired') {
        return true;
    }
    if (!empty($pay['expires_at'])) {
        $ts = strtotime((string)$pay['expires_at']);
        if ($ts && $ts < time()) {
            return true;
        }
    }
    $ttl = defined('INVOICE_TTL_SEC') ? (int)INVOICE_TTL_SEC : 1200;
    if (!empty($pay['created_at'])) {
        $c = strtotime((string)$pay['created_at']);
        if ($c && (time() - $c) > $ttl) {
            return true;
        }
    }
    return false;
}

/**
 * نمایش جزئیات پرداخت داخل تلگرام (مسیر فعلی — کپی کارت/مبلغ + فیش)
 */
function showTelegramPaymentDetails($chat_id, $paymentId, $db, $plans, $editMsgId = null) {
    ensurePaymentPayColumns($db);
    expireStaleInvoices($db);
    $st = $db->prepare('SELECT * FROM payments WHERE id = ? LIMIT 1');
    $st->execute([(int)$paymentId]);
    $pay = $st->fetch(PDO::FETCH_ASSOC);
    if (!$pay) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ فاکتور یافت نشد.']);
        return;
    }
    if (isPaymentExpiredRow($pay) || !in_array($pay['status'], ['pending'], true)) {
        if (($pay['status'] ?? '') === 'pending') {
            try {
                $db->prepare("UPDATE payments SET status = 'expired' WHERE id = ?")->execute([(int)$paymentId]);
            } catch (Exception $e) {
            }
        }
        $txt = "⏰ <b>مهلت این فاکتور تمام شد</b>\n\nلطفاً دوباره از منو خرید/شارژ را شروع کن تا فاکتور جدید ساخته شود.";
        if ($editMsgId) {
            sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $editMsgId, 'text' => $txt, 'parse_mode' => 'HTML']);
        } else {
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => $txt, 'parse_mode' => 'HTML']);
        }
        return;
    }

    $card = getActiveBankCard($db);
    $finalPrice = (int)$pay['price'];
    $finalPriceRial = $finalPrice * 10;
    $actionType = (string)$pay['action_type'];
    $planKey = (string)$pay['plan_key'];
    $targetUser = (string)$pay['target_username'];
    $couponCode = (string)($pay['coupon_code'] ?? '');
    $ttlMin = (int)ceil((defined('INVOICE_TTL_SEC') ? INVOICE_TTL_SEC : 1200) / 60);
    $expLabel = !empty($pay['expires_at']) ? date('H:i', strtotime($pay['expires_at'])) : '';

    $inlineButtons = [];
    if ($actionType === 'deposit') {
        $msg = "🧾 <b>پرداخت داخل تلگرام — شارژ کیف پول</b>\n"
             . "#️⃣ فاکتور: <code>#{$paymentId}</code>\n\n"
             . "💰 مبلغ: <b>" . number_format($finalPrice) . " تومان</b>\n"
             . "🔢 دقیقاً این مبلغ به ریال: <code>{$finalPriceRial}</code>\n\n"
             . "💳 کارت: <code>{$card['card_number']}</code>\n"
             . "👤 به نام: <b>{$card['card_holder']}</b> ({$card['bank_name']})\n\n"
             . "⏱ مهلت: <b>{$ttlMin} دقیقه</b>" . ($expLabel ? " (تا ساعت {$expLabel})" : '') . "\n\n"
             . "✅ مبلغ رو <b>دقیقاً همون عدد</b> واریز کن.\n"
             . "📌 معمولاً پرداخت <b>خودکار</b> تأیید می‌شه؛ اگر طول کشید، <b>عکس فیش</b> رو همین‌جا بفرست.";
        $inlineButtons[] = [['text' => "📋 کپی شماره کارت", 'copy_text' => ['text' => $card['card_number']], 'style' => 'primary']];
        $inlineButtons[] = [['text' => "🔢 کپی مبلغ ریال (" . number_format($finalPriceRial) . ")", 'copy_text' => ['text' => (string)$finalPriceRial], 'style' => 'primary']];
        $inlineButtons[] = [['text' => '📚 راهنمای پرداخت', 'callback_data' => 'help_payment_guide']];
        $inlineButtons[] = [['text' => '🔙 تغییر روش پرداخت', 'callback_data' => 'pay_methods:' . (int)$paymentId, 'style' => 'primary']];
        $inlineButtons[] = [['text' => '❌ انصراف', 'callback_data' => 'pay_cancel:' . (int)$paymentId, 'style' => 'danger']];
    } else {
        $p = $plans[$planKey] ?? null;
        $daysTxt = ($p && (int)$p['days'] > 0) ? "{$p['days']} روزه" : 'VIP بدون انقضا';
        $actionTitle = $actionType === 'renew' ? 'تمدید اشتراک' : 'خرید اشتراک جدید';
        $title = $p['title'] ?? $planKey;
        $stmt = $db->prepare('SELECT balance FROM users WHERE user_id = ?');
        $stmt->execute([(int)$pay['user_id']]);
        $bal = (int)$stmt->fetchColumn();

        $msg = "🧾 <b>پرداخت داخل تلگرام — {$actionTitle}</b>\n"
             . "#️⃣ فاکتور: <code>#{$paymentId}</code>\n\n"
             . "📦 پلن: {$title} ({$daysTxt})\n"
             . "👤 نام کاربری: <code>{$targetUser}</code>\n";
        if ($couponCode !== '') {
            $msg .= "🏷 کد تخفیف: <code>{$couponCode}</code>\n";
        }
        $msg .= "💰 مبلغ: <b>" . number_format($finalPrice) . " تومان</b>\n"
             . "🔢 دقیقاً این مبلغ به ریال: <code>{$finalPriceRial}</code>\n"
             . "💵 موجودی کیف: " . number_format($bal) . " تومان\n\n"
             . "💳 کارت: <code>{$card['card_number']}</code>\n"
             . "👤 به نام: <b>{$card['card_holder']}</b> ({$card['bank_name']})\n\n"
             . "⏱ مهلت: <b>{$ttlMin} دقیقه</b>" . ($expLabel ? " (تا ساعت {$expLabel})" : '') . "\n\n"
             . "✅ مبلغ رو <b>دقیقاً همون عدد</b> واریز کن.\n"
             . "📌 معمولاً پرداخت <b>خودکار</b> تأیید می‌شه؛ اگر طول کشید، <b>عکس فیش</b> رو همین‌جا بفرست.";

        if ($bal >= $finalPrice) {
            $inlineButtons[] = [['text' => '⚡️ پرداخت آنی از کیف پول', 'callback_data' => "pay_wallet:{$actionType}:{$planKey}:{$targetUser}:{$couponCode}", 'style' => 'success']];
        }
        $inlineButtons[] = [['text' => '📋 کپی شماره کارت', 'copy_text' => ['text' => $card['card_number']], 'style' => 'primary']];
        $inlineButtons[] = [['text' => '🔢 کپی مبلغ ریال (' . number_format($finalPriceRial) . ')', 'copy_text' => ['text' => (string)$finalPriceRial], 'style' => 'primary']];
        $helpRow = [];
        if ($couponCode === '') {
            $helpRow[] = ['text' => '🏷 کد تخفیف داری؟', 'callback_data' => "apply_coupon:{$actionType}:{$planKey}:{$targetUser}", 'style' => 'primary'];
        }
        $helpRow[] = ['text' => '📚 راهنما', 'callback_data' => 'help_payment_guide'];
        $inlineButtons[] = $helpRow;
        $inlineButtons[] = [['text' => '🔙 تغییر روش پرداخت', 'callback_data' => 'pay_methods:' . (int)$paymentId, 'style' => 'primary']];
        $inlineButtons[] = [['text' => '❌ انصراف', 'callback_data' => 'pay_cancel:' . (int)$paymentId, 'style' => 'danger']];
    }

    $keyboard = json_encode(['inline_keyboard' => $inlineButtons], JSON_UNESCAPED_UNICODE);
    if ($editMsgId) {
        sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $editMsgId, 'text' => $msg, 'parse_mode' => 'HTML', 'reply_markup' => $keyboard]);
        rememberInvoiceMsg($db, $paymentId, $editMsgId);
    } else {
        $sent = sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => $msg, 'parse_mode' => 'HTML', 'reply_markup' => $keyboard]);
        rememberInvoiceMsg($db, $paymentId, (int)($sent['result']['message_id'] ?? 0));
    }
}

function clearBotPlansCache() {
    // با ریست کردن از طریق getBotPlans(force)
    $GLOBALS['__bot_plans_cache'] = [];
}

function getBotPlans($db, $onlyActive = true) {
    if ($db instanceof PDO) {
        try { ensureMultiPanelSchema($db); } catch (Exception $e) {}
        try { ensurePlanCatalogSchema($db); } catch (Exception $e) {}
        try { if (function_exists('plans_ensure_schema')) plans_ensure_schema($db); } catch (Exception $e) {}
    }
    if (!isset($GLOBALS['__bot_plans_cache']) || !is_array($GLOBALS['__bot_plans_cache'])) {
        $GLOBALS['__bot_plans_cache'] = [];
    }
    $cache = &$GLOBALS['__bot_plans_cache'];
    $cacheKey = $onlyActive ? 'active' : 'all';
    if (isset($cache[$cacheKey])) {
        return $cache[$cacheKey];
    }
    try {
        $where = $onlyActive ? " WHERE is_active = 1" : "";
        try {
            $rows = $db->query("SELECT * FROM bot_plans{$where} ORDER BY sort_order ASC, id ASC")->fetchAll();
        } catch (Exception $e1) {
            $rows = $db->query("SELECT * FROM bot_plans{$where} ORDER BY id ASC")->fetchAll();
        }
        $plans = [];
        foreach ($rows as $r) {
            $plans[$r['plan_key']] = $r;
        }
        $cache[$cacheKey] = $plans;
        return $plans;
    } catch (Exception $e) {
        return [];
    }
}

function getPlanCategoryMeta($db) {
    $defaults = [
        'monthly' => ['title' => 'مدت‌دار / ماهانه', 'emoji' => '📅', 'desc' => 'حجم مشخص + اعتبار زمانی', 'sort' => 10, 'enabled' => 1],
        'vip'     => ['title' => 'حجمی بدون انقضا', 'emoji' => '💎', 'desc' => 'فقط با تمام شدن حجم تمام می‌شود', 'sort' => 20, 'enabled' => 1],
    ];
    $extra = json_decode((string)getSetting($db, 'plan_cat_labels', '{}'), true);
    if (!is_array($extra)) $extra = [];
    foreach ($extra as $k => $v) {
        if (!is_array($v)) continue;
        $base = $defaults[$k] ?? ['title' => $k, 'emoji' => '📦', 'desc' => '', 'sort' => 100, 'enabled' => 1];
        $defaults[$k] = [
            'title'   => $v['title']   ?? $base['title'],
            'emoji'   => $v['emoji']   ?? $base['emoji'],
            'desc'    => $v['desc']    ?? $base['desc'],
            'sort'    => isset($v['sort']) ? (int)$v['sort'] : (int)$base['sort'],
            'enabled' => isset($v['enabled']) ? (int)$v['enabled'] : (int)$base['enabled'],
        ];
    }
    return $defaults;
}

/** سازگاری با کد قبلی */
function getPlanCategoryLabels($db) {
    return getPlanCategoryMeta($db);
}

function savePlanCategoryMeta($db, $key, $fields) {
    $extra = json_decode((string)getSetting($db, 'plan_cat_labels', '{}'), true);
    if (!is_array($extra)) $extra = [];
    $cur = $extra[$key] ?? [];
    if (!is_array($cur)) $cur = [];
    foreach (['title', 'emoji', 'desc', 'sort', 'enabled'] as $f) {
        if (array_key_exists($f, $fields)) {
            $cur[$f] = $fields[$f];
        }
    }
    $extra[$key] = $cur;
    setSetting($db, 'plan_cat_labels', json_encode($extra, JSON_UNESCAPED_UNICODE));
}

function savePlanCategoryLabel($db, $key, $title, $emoji = '📦', $desc = '') {
    $meta = getPlanCategoryMeta($db);
    $prev = $meta[$key] ?? [];
    savePlanCategoryMeta($db, $key, [
        'title'   => $title,
        'emoji'   => $emoji,
        'desc'    => $desc,
        'sort'    => (int)($prev['sort'] ?? 100),
        'enabled' => (int)($prev['enabled'] ?? 1),
    ]);
}

function listPlanCategoriesInUse($db, $onlyActivePlans = true) {
    $plans = getBotPlans($db, $onlyActivePlans);
    $cats = [];
    foreach ($plans as $p) {
        $c = strtolower(trim((string)($p['cat'] ?? '')));
        if ($c !== '') $cats[$c] = true;
    }
    $cats['monthly'] = true;
    $cats['vip'] = true;
    return array_keys($cats);
}

/** دسته‌های قابل نمایش به مشتری، مرتب‌شده */
function getOrderedVisibleCategories($db, $activePlans) {
    $meta = getPlanCategoryMeta($db);
    $catsInUse = [];
    foreach ($activePlans as $ap) {
        if (isset($ap['is_active']) && (int)$ap['is_active'] === 0) {
            continue;
        }
        $c = strtolower(trim((string)($ap['cat'] ?? '')));
        if ($c === '') {
            continue;
        }
        $panelId = (int)($ap['panel_id'] ?? 0);
        // هم متای سراسری و هم وضعیت دسته روی پنل پلن
        if (!isPlanCategoryActiveForPanel($db, $panelId, $c)) {
            continue;
        }
        $catsInUse[$c] = true;
    }
    $list = [];
    foreach (array_keys($catsInUse) as $ck) {
        $m = $meta[$ck] ?? ['title' => $ck, 'emoji' => '📦', 'desc' => '', 'sort' => 999, 'enabled' => 1];
        if ((int)($m['enabled'] ?? 1) !== 1) {
            continue;
        }
        $list[] = ['key' => $ck, 'meta' => $m, 'sort' => (int)($m['sort'] ?? 999)];
    }
    usort($list, function ($a, $b) {
        if ($a['sort'] === $b['sort']) {
            return strcmp($a['key'], $b['key']);
        }
        return $a['sort'] <=> $b['sort'];
    });
    return $list;
}

function planDraftKey($user_id) {
    return 'plan_wiz_draft_' . $user_id;
}

function getPlanDraft($db, $user_id) {
    $d = json_decode((string)getSetting($db, planDraftKey($user_id), '{}'), true);
    return is_array($d) ? $d : [];
}

function setPlanDraft($db, $user_id, $draft) {
    setSetting($db, planDraftKey($user_id), json_encode($draft, JSON_UNESCAPED_UNICODE));
}

function clearPlanDraft($db, $user_id) {
    setSetting($db, planDraftKey($user_id), '');
}

function getActiveBankCard($db) {
    try {
        $mode = getSetting($db, 'card_mode', 'random');
        $fixedCardId = (int)getSetting($db, 'fixed_card_id', 0);

        if ($mode === 'fixed' && $fixedCardId > 0) {
            $stmt = $db->prepare("SELECT * FROM bank_cards WHERE id = ? AND is_active = 1");
            $stmt->execute([$fixedCardId]);
            $card = $stmt->fetch();
            if ($card) return $card;
        }

        if ($mode === 'sequential') {
            $cards = $db->query("SELECT * FROM bank_cards WHERE is_active = 1 ORDER BY id ASC")->fetchAll();
            if (!empty($cards)) {
                $lastId = (int)getSetting($db, 'last_card_id', 0);
                $chosenCard = $cards[0];
                foreach ($cards as $c) {
                    if ($c['id'] > $lastId) {
                        $chosenCard = $c;
                        break;
                    }
                }
                setSetting($db, 'last_card_id', $chosenCard['id']);
                return $chosenCard;
            }
        }

        $stmt = $db->query("SELECT * FROM bank_cards WHERE is_active = 1 ORDER BY RAND() LIMIT 1");
        $card = $stmt->fetch();
        if ($card) return $card;
    } catch (Exception $e) {}

    return [
        'card_number' => '5041721002069533',
        'card_holder' => 'مجید کریمی',
        'bank_name'   => 'بانک قرض‌الحسنه رسالت'
    ];
}

$plans = getBotPlans($db, false);
$activePlans = getBotPlans($db, true);

function isUserMember($userId) {
    if (!defined('CHANNEL_ID') || empty(CHANNEL_ID) || isBotAdmin($userId)) {
        return true;
    }
    $res = sendTelegram('getChatMember', [
        'chat_id' => CHANNEL_ID,
        'user_id' => $userId
    ]);
    if (!empty($res['ok']) && isset($res['result']['status'])) {
        return in_array($res['result']['status'], ['creator', 'administrator', 'member', 'restricted']);
    }
    return true;
}

function postOrderToLogChannel($planTitle, $actionType) {
    return;
}

function exportDatabaseSql($db) {
    $tables = ['users', 'orders', 'payments', 'coupons', 'settings', 'bot_plans', 'bank_cards'];
    $sql = "-- JetConfig Database Backup\n-- Date: " . date('Y-m-d H:i:s') . "\n\nSET FOREIGN_KEY_CHECKS=0;\n\n";

    foreach ($tables as $t) {
        try {
            $stmt = $db->query("SHOW CREATE TABLE `{$t}`");
            $row = $stmt->fetch(PDO::FETCH_NUM);
            if ($row) {
                $sql .= "DROP TABLE IF EXISTS `{$t}`;\n" . $row[1] . ";\n\n";
                $rows = $db->query("SELECT * FROM `{$t}`")->fetchAll(PDO::FETCH_ASSOC);
                if (!empty($rows)) {
                    foreach ($rows as $r) {
                        $keys = array_map(function($k) { return "`$k`"; }, array_keys($r));
                        $vals = array_map(function($v) use ($db) {
                            return ($v === null) ? 'NULL' : $db->quote($v);
                        }, array_values($r));
                        $sql .= "INSERT INTO `{$t}` (" . implode(', ', $keys) . ") VALUES (" . implode(', ', $vals) . ");\n";
                    }
                    $sql .= "\n";
                }
            }
        } catch (Exception $e) {}
    }
    $sql .= "SET FOREIGN_KEY_CHECKS=1;\n";
    return $sql;
}


// ===================== چندپنلی (زیرساخت) =====================
/**
 * جدول پنل‌ها + ستون panel_id روی پلن و سفارش
 * پنل پیش‌فرض = همان پاسارگاد config.php — رفتار قبلی حفظ می‌شود
 */
function ensureMultiPanelSchema($db) {
    static $done = false;
    if ($done) return;
    $done = true;
    // بعد از یک‌بار موفق، ALTER تکراری نزن (کندی منوی پنل)
    $schemaOk = false;
    try {
        $schemaOk = (getSetting($db, 'multipanel_schema_v1', '') === '1');
    } catch (Exception $e) {}
    if ($schemaOk) {
        return;
    }
    try {
        $db->exec("CREATE TABLE IF NOT EXISTS bot_panels (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(40) NOT NULL DEFAULT 'pasargad',
            base_url VARCHAR(255) NOT NULL,
            public_url VARCHAR(255) NULL,
            username VARCHAR(120) NOT NULL,
            password VARCHAR(255) NOT NULL,
            use_worker TINYINT(1) NOT NULL DEFAULT 0,
            is_default TINYINT(1) NOT NULL DEFAULT 0,
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            extra_json TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    } catch (Exception $e) { /* ignore */ }

    foreach (['bot_plans' => 'panel_id INT NULL DEFAULT NULL', 'orders' => 'panel_id INT NULL DEFAULT NULL'] as $table => $colDef) {
        try {
            $chk = $db->query("SHOW COLUMNS FROM `{$table}` LIKE 'panel_id'")->fetch();
            if (!$chk) {
                $db->exec("ALTER TABLE {$table} ADD COLUMN {$colDef}");
            }
        } catch (Exception $e) { /* ignore */ }
    }

    // seed پنل پیش‌فرض از config
    try {
        $cnt = (int)$db->query("SELECT COUNT(*) FROM bot_panels")->fetchColumn();
        if ($cnt === 0 && defined('PANEL_URL') && defined('PANEL_USER') && defined('PANEL_PASS')) {
            $useWorker = (defined('WORKER_URL') && WORKER_URL) ? 1 : 0;
            $st = $db->prepare("INSERT INTO bot_panels (name, type, base_url, public_url, username, password, use_worker, is_default, is_active)
                VALUES ('پاسارگاد اصلی', 'pasargad', ?, ?, ?, ?, ?, 1, 1)");
            $st->execute([
                rtrim(PANEL_URL, '/'),
                rtrim(PANEL_URL, '/'),
                PANEL_USER,
                PANEL_PASS,
                $useWorker,
            ]);
            $defId = (int)$db->lastInsertId();
            if ($defId > 0) {
                try {
                    $db->exec("UPDATE bot_plans SET panel_id = {$defId} WHERE panel_id IS NULL");
                } catch (Exception $e) {}
            }
        }
    } catch (Exception $e) { /* ignore */ }

    try {
        setSetting($db, 'multipanel_schema_v1', '1');
    } catch (Exception $e) {}
}

function getDefaultPanel($db = null) {
    $db = $db ?: ($GLOBALS['db'] ?? null);
    if (!$db) {
        return panelConfigFromConstants();
    }
    ensureMultiPanelSchema($db);
    try {
        $row = $db->query("SELECT * FROM bot_panels WHERE is_default = 1 AND is_active = 1 ORDER BY id ASC LIMIT 1")->fetch();
        if ($row) return $row;
        $row = $db->query("SELECT * FROM bot_panels WHERE is_active = 1 ORDER BY id ASC LIMIT 1")->fetch();
        if ($row) return $row;
    } catch (Exception $e) {}
    return panelConfigFromConstants();
}

function panelConfigFromConstants() {
    return [
        'id' => 0,
        'name' => 'پاسارگاد (config)',
        'type' => 'pasargad',
        'base_url' => defined('PANEL_URL') ? rtrim(PANEL_URL, '/') : '',
        'public_url' => defined('PANEL_URL') ? rtrim(PANEL_URL, '/') : '',
        'username' => defined('PANEL_USER') ? PANEL_USER : '',
        'password' => defined('PANEL_PASS') ? PANEL_PASS : '',
        'use_worker' => (defined('WORKER_URL') && WORKER_URL) ? 1 : 0,
        'is_default' => 1,
        'is_active' => 1,
    ];
}

/**
 * فاز A: دسته‌های per-panel + cat/plan_key روی orders
 * حذف فیزیکی پلن نداریم — فقط is_active
 */
function ensurePlanCatalogSchema($db) {
    static $done = false;
    if ($done || !($db instanceof PDO)) {
        return;
    }
    $done = true;
    try {
        if (getSetting($db, 'plan_catalog_schema_v1', '') === '1') {
            return;
        }
    } catch (Exception $e) {}

    try {
        $db->exec("CREATE TABLE IF NOT EXISTS bot_plan_categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            panel_id INT NOT NULL,
            cat_key VARCHAR(64) NOT NULL,
            title VARCHAR(120) NOT NULL,
            emoji VARCHAR(16) NOT NULL DEFAULT '📦',
            description VARCHAR(255) NOT NULL DEFAULT '',
            sort_order INT NOT NULL DEFAULT 0,
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uq_panel_cat (panel_id, cat_key),
            KEY idx_panel_active (panel_id, is_active)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    } catch (Exception $e) {}

    foreach ([
        'orders' => [
            'cat' => "VARCHAR(64) NULL DEFAULT NULL",
            'plan_key' => "VARCHAR(64) NULL DEFAULT NULL",
        ],
    ] as $table => $cols) {
        foreach ($cols as $col => $def) {
            try {
                $chk = $db->query("SHOW COLUMNS FROM `{$table}` LIKE '{$col}'")->fetch();
                if (!$chk) {
                    $db->exec("ALTER TABLE `{$table}` ADD COLUMN `{$col}` {$def}");
                }
            } catch (Exception $e) {}
        }
    }

    // مهاجرت دسته از plan_cat_labels + catهای موجود پلن‌ها — برای هر پنل
    try {
        ensureMultiPanelSchema($db);
        $panels = $db->query("SELECT id FROM bot_panels WHERE is_active = 1")->fetchAll(PDO::FETCH_COLUMN);
        if (!$panels) {
            $panels = $db->query("SELECT id FROM bot_panels")->fetchAll(PDO::FETCH_COLUMN);
        }
        $defId = 0;
        try {
            $defId = (int)$db->query("SELECT id FROM bot_panels WHERE is_default = 1 ORDER BY id ASC LIMIT 1")->fetchColumn();
        } catch (Exception $e) {}
        if ($defId <= 0 && !empty($panels)) {
            $defId = (int)$panels[0];
        }

        $labels = [];
        try {
            $raw = getSetting($db, 'plan_cat_labels', '{}');
            $labels = json_decode((string)$raw, true);
            if (!is_array($labels)) {
                $labels = [];
            }
        } catch (Exception $e) {}

        $meta = [
            'monthly' => ['title' => 'مدت‌دار / ماهانه', 'emoji' => '📅', 'desc' => 'حجم مشخص + اعتبار زمانی'],
            'vip' => ['title' => 'حجمی بدون انقضا', 'emoji' => '💎', 'desc' => 'فقط با اتمام حجم تمام می‌شود'],
        ];
        foreach ($labels as $k => $v) {
            if (!is_array($v)) {
                continue;
            }
            $meta[$k] = array_merge($meta[$k] ?? [], $v);
        }

        $catsFromPlans = [];
        try {
            $rows = $db->query("SELECT DISTINCT cat, panel_id FROM bot_plans WHERE cat IS NOT NULL AND cat != ''")->fetchAll(PDO::FETCH_ASSOC);
            foreach ($rows as $r) {
                $ck = strtolower(trim((string)$r['cat']));
                if ($ck === '') {
                    continue;
                }
                $pid = (int)($r['panel_id'] ?? 0);
                if ($pid <= 0) {
                    $pid = $defId;
                }
                $catsFromPlans[$pid][$ck] = true;
            }
        } catch (Exception $e) {}

        // حداقل monthly/vip برای هر پنل
        foreach ($panels as $pid) {
            $pid = (int)$pid;
            if ($pid <= 0) {
                continue;
            }
            foreach (['monthly', 'vip'] as $ck) {
                $catsFromPlans[$pid][$ck] = true;
            }
            if (!empty($catsFromPlans[$pid])) {
                // already
            }
        }

        $ins = $db->prepare("INSERT IGNORE INTO bot_plan_categories (panel_id, cat_key, title, emoji, description, sort_order, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)");
        foreach ($catsFromPlans as $pid => $keys) {
            $sort = 0;
            foreach (array_keys($keys) as $ck) {
                $sort += 10;
                $title = $meta[$ck]['title'] ?? $ck;
                $emoji = $meta[$ck]['emoji'] ?? '📦';
                $desc = $meta[$ck]['desc'] ?? ($meta[$ck]['description'] ?? '');
                try {
                    $ins->execute([(int)$pid, $ck, $title, $emoji, $desc, $sort]);
                } catch (Exception $e) {}
            }
        }

        // پلن‌های بدون panel_id → پیش‌فرض
        if ($defId > 0) {
            try {
                $db->exec("UPDATE bot_plans SET panel_id = {$defId} WHERE panel_id IS NULL OR panel_id = 0");
            } catch (Exception $e) {}
        }

        // backfill سفارش‌های قدیم: cat تقریبی از days
        try {
            $db->exec("UPDATE orders SET cat = 'vip' WHERE (cat IS NULL OR cat = '') AND days = 0");
            $db->exec("UPDATE orders SET cat = 'monthly' WHERE (cat IS NULL OR cat = '') AND (days IS NULL OR days > 0)");
        } catch (Exception $e) {}
    } catch (Exception $e) {}

    try {
        setSetting($db, 'plan_catalog_schema_v1', '1');
    } catch (Exception $e) {}
}



/** ثبت سفارش با cat و plan_key در صورت وجود ستون */

/** نمایش حجم برای کاربر — 0 = نامحدود */

/** تشخیص سرویس تست — فقط prefix test_ یا plan_key/cat تست */
function isTestServiceOrder($orderOrUsername, $volumeGb = null) {
    if (is_array($orderOrUsername)) {
        $uname = (string)($orderOrUsername['config_username'] ?? '');
        $pk = strtolower(trim((string)($orderOrUsername['plan_key'] ?? '')));
        $cat = strtolower(trim((string)($orderOrUsername['cat'] ?? '')));
    } else {
        $uname = (string)$orderOrUsername;
        $pk = '';
        $cat = '';
    }
    if (stripos($uname, 'test_') === 0) {
        return true;
    }
    if ($pk !== '' && in_array($pk, ['test_free', 'test', 'free_test'], true)) {
        return true;
    }
    if ($cat === 'test') {
        return true;
    }
    return false;
}

/** آیا دسته برای این پنل فعال است؟ */
function isPlanCategoryActiveForPanel($db, $panelId, $catKey) {
    $catKey = strtolower(trim((string)$catKey));
    $panelId = (int)$panelId;
    if ($catKey === '') {
        return true;
    }
    // ۱) متای سراسری (منوی ادمین «مدیریت دسته‌ها») — اگر خاموش باشد همه جا خاموش
    try {
        $meta = getPlanCategoryMeta($db);
        if (isset($meta[$catKey]) && array_key_exists('enabled', $meta[$catKey]) && (int)$meta[$catKey]['enabled'] === 0) {
            return false;
        }
    } catch (Exception $e) {}
    // ۲) جدول per-panel
    try {
        if ($panelId > 0) {
            $st = $db->prepare('SELECT is_active FROM bot_plan_categories WHERE panel_id = ? AND cat_key = ? LIMIT 1');
            $st->execute([$panelId, $catKey]);
            $row = $st->fetch(PDO::FETCH_ASSOC);
            if ($row !== false && $row !== null) {
                return (int)($row['is_active'] ?? 1) === 1;
            }
        }
    } catch (Exception $e) {}
    return true;
}


/** پلن نامحدود روی پنل غیرپیش‌فرض (فرداد/مرزبان) */
function planIsFardadUnlimited($plan, $panel = null) {
    $vol = (float)($plan['vol'] ?? 0);
    $cat = strtolower((string)($plan['cat'] ?? ''));
    $title = (string)($plan['title'] ?? '');
    $unlimVol = ($vol <= 0);
    $unlimCat = (strpos($cat, 'unlim') !== false || strpos($cat, 'vip') !== false
        || strpos($cat, 'namahdood') !== false || mb_strpos($title, 'نامحدود') !== false);
    if (!$unlimVol && !$unlimCat) {
        return false;
    }
    if ($panel === null && !empty($plan['panel_id']) && function_exists('getPanelById')) {
        $panel = getPanelById((int)$plan['panel_id']);
    }
    if (!is_array($panel) || empty($panel)) {
        return false;
    }
    if (!empty($panel['is_default'])) {
        return false;
    }
    $ty = strtolower((string)($panel['type'] ?? ''));
    $n = strtolower((string)($panel['name'] ?? ''));
    $nameRaw = (string)($panel['name'] ?? '');
    return ($ty === 'marzban' || strpos($n, 'fardad') !== false || strpos($n, 'marz') !== false
        || mb_strpos($nameRaw, 'فرداد') !== false);
}

function formatLimitIpLabel($n) {
    $n = (int)$n;
    if ($n <= 0) {
        return 'بدون محدودیت IP';
    }
    if ($n === 1) {
        return 'تک‌کاربره (۱ IP هم‌زمان)';
    }
    return $n . ' کاربر هم‌زمان';
}


function formatVolumeGb($gb, $withUnit = true) {
    $gb = (float)$gb;
    if ($gb <= 0) {
        return 'نامحدود';
    }
    if ($gb < 1) {
        $mb = (int)round($gb * 1000);
        return $withUnit ? ($mb . ' MB') : (string)$mb;
    }
    $s = rtrim(rtrim(number_format($gb, 2, '.', ''), '0'), '.');
    return $withUnit ? ($s . ' GB') : $s;
}


/** برچسب کوتاه زمان برای دکمهٔ فقط‌نمایشی */
function remainingTimeChipLabel($daysTxt) {
    $d = trim((string)$daysTxt);
    if ($d === '') {
        return '⏰ —';
    }
    if (mb_strpos($d, 'منقضی') !== false) {
        return '⏰ منقضی شده';
    }
    if (mb_strpos($d, 'بدون انقضا') !== false || stripos($d, 'VIP') !== false) {
        return '⏰ بدون انقضا';
    }
    if (preg_match('/(\d+)\s*روز مانده/u', $d, $m)) {
        return '⏰ ' . $m[1] . ' روز مانده';
    }
    if (mb_strpos($d, 'از اولین اتصال') !== false) {
        if (preg_match('/(\d+)\s*روز/u', $d, $m)) {
            return '⏰ از اتصال · ' . $m[1] . ' روز';
        }
        return '⏰ از اولین اتصال';
    }
    if (preg_match('/(\d+)\s*روزه/u', $d, $m)) {
        return '⏰ ' . $m[1] . ' روز';
    }
    if (preg_match('/(\d+)\s*روز/u', $d, $m)) {
        return '⏰ ' . $m[1] . ' روز';
    }
    if (mb_strpos($d, 'ساعت') !== false || mb_strpos($d, '۲۴') !== false) {
        return '⏰ ۲۴ ساعت';
    }
    $short = mb_strlen($d) > 40 ? (mb_substr($d, 0, 37) . '…') : $d;
    return '⏰ ' . $short;
}

/** برچسب حجم مانده برای دکمهٔ فقط‌نمایشی */
function remainingVolumeChipLabel($totalGb, $usedGb = 0) {
    $totalGb = (float)$totalGb;
    $usedGb = (float)$usedGb;
    if ($totalGb <= 0) {
        return '📦 نامحدود';
    }
    $remain = max(0.0, $totalGb - $usedGb);
    if ($totalGb <= 1.0 || $remain < 1.0) {
        $mb = round($remain * 1024, 1);
        if ($mb < 0.1) {
            $mb = 0;
        }
        // عدد تمیز
        $mbTxt = (abs($mb - (int)$mb) < 0.05) ? (string)(int)$mb : rtrim(rtrim(number_format($mb, 1, '.', ''), '0'), '.');
        return '📦 ' . $mbTxt . ' مگابایت مانده';
    }
    return '📦 ' . formatVolumeGb($remain) . ' مانده';
}

/**
 * یک ردیف دکمه فقط‌نمایشی (زمان | حجم)
 * با زدن هیچ عملی انجام نمی‌شود — callback: noop_status
 */
function serviceInfoChipRow($timeLabel, $volumeLabel) {
    $t = trim((string)$timeLabel);
    $v = trim((string)$volumeLabel);
    if ($t === '') {
        $t = '⏰ —';
    }
    if ($v === '') {
        $v = '📦 —';
    }
    if (mb_strpos($t, '⏰') === false && mb_strpos($t, '⏱') === false) {
        $t = '⏰ ' . $t;
    }
    if (mb_strpos($v, '📦') === false && mb_strpos($v, '📊') === false) {
        $v = '📦 ' . $v;
    }
    if (mb_strlen($t) > 60) {
        $t = mb_substr($t, 0, 57) . '…';
    }
    if (mb_strlen($v) > 60) {
        $v = mb_substr($v, 0, 57) . '…';
    }
    return [[
        ['text' => $t, 'callback_data' => 'noop_status'],
        ['text' => $v, 'callback_data' => 'noop_status'],
    ]];
}


function insertBotOrder($db, $userId, $configUsername, $password, $subLink, $volumeGb, $days, $panelId = null, $cat = null, $planKey = null) {
    $userId = (int)$userId;
    $days = (int)$days;
    $volumeGb = (float)$volumeGb;
    $panelId = $panelId !== null && (int)$panelId > 0 ? (int)$panelId : null;
    $cat = $cat !== null && $cat !== '' ? (string)$cat : null;
    $planKey = $planKey !== null && $planKey !== '' ? (string)$planKey : null;
    try {
        ensurePlanCatalogSchema($db);
    } catch (Exception $e) {}
    $oid = 0;
    try {
        $st = $db->prepare("INSERT INTO orders (user_id, config_username, password, sub_link, volume_gb, days, panel_id, cat, plan_key) VALUES (?,?,?,?,?,?,?,?,?)");
        $st->execute([$userId, $configUsername, $password, $subLink, $volumeGb, $days, $panelId, $cat, $planKey]);
        $oid = (int)$db->lastInsertId();
    } catch (Exception $e) {
        try {
            $st = $db->prepare("INSERT INTO orders (user_id, config_username, password, sub_link, volume_gb, days, panel_id) VALUES (?,?,?,?,?,?,?)");
            $st->execute([$userId, $configUsername, $password, $subLink, $volumeGb, $days, $panelId]);
            $oid = (int)$db->lastInsertId();
        } catch (Exception $e2) {
            $st = $db->prepare("INSERT INTO orders (user_id, config_username, password, sub_link, volume_gb, days) VALUES (?,?,?,?,?,?)");
            $st->execute([$userId, $configUsername, $password, $subLink, $volumeGb, $days]);
            $oid = (int)$db->lastInsertId();
        }
    }
    // ظرفیت دوره نمایش برای خرید جدید = حجم پلن
    if ($oid > 0 && $volumeGb > 0) {
        try {
            jet_ensure_last_renew_col($db);
            $db->prepare('UPDATE orders SET last_renew_gb = ?, volume_cycle_gb = ? WHERE id = ?')
               ->execute([$volumeGb, $volumeGb, $oid]);
        } catch (Throwable $e) {}
    }
    return $oid;
}

function getPanelById($id, $db = null) {
    $id = (int)$id;
    if ($id <= 0) return getDefaultPanel($db);
    $db = $db ?: ($GLOBALS['db'] ?? null);
    if (!$db) return getDefaultPanel($db);
    ensureMultiPanelSchema($db);
    try {
        $st = $db->prepare("SELECT * FROM bot_panels WHERE id = ? LIMIT 1");
        $st->execute([$id]);
        $row = $st->fetch();
        if ($row) return $row;
    } catch (Exception $e) {}
    return getDefaultPanel($db);
}

/** $panel: null | int id | array row */
function resolvePanelConfig($panel = null, $db = null) {
    if (is_array($panel) && !empty($panel['base_url'])) {
        return $panel;
    }
    if (is_numeric($panel) && (int)$panel > 0) {
        return getPanelById((int)$panel, $db);
    }
    return getDefaultPanel($db);
}

function listBotPanels($db = null, $onlyActive = true) {
    $db = $db ?: ($GLOBALS['db'] ?? null);
    if (!$db) return [];
    ensureMultiPanelSchema($db);
    try {
        $sql = "SELECT * FROM bot_panels" . ($onlyActive ? " WHERE is_active = 1" : "") . " ORDER BY is_default DESC, id ASC";
        return $db->query($sql)->fetchAll() ?: [];
    } catch (Exception $e) {
        return [];
    }
}

/**
 * پایه API: پنل پیش‌فرض می‌تواند از Worker برود؛ پنل‌های دیگر مستقیم base_url
 */
function getPanelApiBase($panel = null) {
    $p = resolvePanelConfig($panel);
    $useWorker = !empty($p['use_worker']) || (!empty($p['is_default']) && defined('WORKER_URL') && WORKER_URL);
    // فقط وقتی Worker تعریف شده و پنل اجازه داده
    if ($useWorker && defined('WORKER_URL') && WORKER_URL) {
        // Worker فعلی فقط یک origin دارد — برای پنل پیش‌فرض/هم‌آدرس با PANEL_URL
        $base = rtrim($p['base_url'] ?? '', '/');
        $cfg = defined('PANEL_URL') ? rtrim(PANEL_URL, '/') : '';
        if ($base === '' || $base === $cfg || !empty($p['is_default'])) {
            return rtrim(WORKER_URL, '/') . '/panel';
        }
    }
    return rtrim($p['base_url'] ?? (defined('PANEL_URL') ? PANEL_URL : ''), '/');
}

function getPanelPublicBase($panel = null) {
    $p = resolvePanelConfig($panel);
    if (!empty($p['public_url'])) {
        return rtrim($p['public_url'], '/');
    }
    if (!empty($p['base_url'])) {
        return rtrim($p['base_url'], '/');
    }
    return defined('PANEL_URL') ? rtrim(PANEL_URL, '/') : '';
}

function getPanelCreds($panel = null) {
    $p = resolvePanelConfig($panel);
    return [
        'username' => $p['username'] ?? (defined('PANEL_USER') ? PANEL_USER : ''),
        'password' => $p['password'] ?? (defined('PANEL_PASS') ? PANEL_PASS : ''),
    ];
}

/** panel_id از روی پلن */
function panelIdFromPlan($plan) {
    if (!is_array($plan)) return 0;
    return (int)($plan['panel_id'] ?? 0);
}

/** panel از سفارش؛ اگر نبود پیش‌فرض */
function panelFromOrder($order, $db = null) {
    if (is_array($order) && !empty($order['panel_id'])) {
        return getPanelById((int)$order['panel_id'], $db);
    }
    return getDefaultPanel($db);
}

/** پنل از نام کانفیگ (orders.panel_id) — برای ادمین/حذف/هدیه/کرون */
function panelFromUsername($username, $db = null) {
    $db = $db ?: ($GLOBALS['db'] ?? null);
    $username = trim((string)$username);
    if ($username === '' || !($db instanceof PDO)) {
        return getDefaultPanel($db);
    }
    try {
        $st = $db->prepare('SELECT panel_id FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 1');
        $st->execute([$username]);
        $pid = (int)($st->fetchColumn() ?: 0);
        if ($pid > 0) {
            return getPanelById($pid, $db);
        }
    } catch (Exception $e) {}
    return getDefaultPanel($db);
}


/** پنل تست رایگان (تنظیم test_panel_id؛ وگرنه پیش‌فرض) */
function getTestPanel($db = null) {
    $db = $db ?: ($GLOBALS['db'] ?? null);
    $pid = 0;
    try {
        if ($db instanceof PDO) {
            $pid = (int)getSetting($db, 'test_panel_id', '0');
        }
    } catch (Exception $e) {}
    if ($pid > 0) {
        return getPanelById($pid, $db);
    }
    return getDefaultPanel($db);
}


/** ریست تست کاربر (جدول جدید + فیلد قدیمی) */
function jetResetUserTests($db, $userId) {
    $userId = (int)$userId;
    if (function_exists('testOfferResetUser')) {
        testOfferResetUser($db, $userId, null);
    } else {
        try {
            $db->prepare("UPDATE users SET has_used_test = 0 WHERE user_id = ?")->execute([$userId]);
        } catch (Exception $e) {}
    }
}

/** لیست پنل‌های فعال برای دکمه‌های ادمین */
function listActivePanels($db = null) {
    $db = $db ?: ($GLOBALS['db'] ?? null);
    if (!$db) return [];
    try {
        return $db->query("SELECT id, name, type, is_default, public_url, base_url FROM bot_panels WHERE is_active = 1 ORDER BY is_default DESC, id ASC")->fetchAll(PDO::FETCH_ASSOC) ?: [];
    } catch (Exception $e) {
        return [];
    }
}

/** نرمال‌سازی لینک ساب نسبت به public_url پنل */
function normalizeSubscriptionUrl($subUrl, $panel = null) {
    $subUrl = trim((string)$subUrl);
    if ($subUrl === '') return '';
    if (strpos($subUrl, 'http://') === 0 || strpos($subUrl, 'https://') === 0) {
        return $subUrl;
    }
    $base = rtrim(getPanelPublicBase($panel), '/');
    if ($base === '') return $subUrl;
    return $base . '/' . ltrim($subUrl, '/');
}


/**
 * بکاپ‌پوینت: backups/panel_smart_20260925/
 * اتصال هوشمند پنل: چند مسیر + retry + کش توکن + IPv4
 */
function panelCurlBaseOpts($timeout = 12) {
    $opts = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_TIMEOUT => (int)$timeout,
        CURLOPT_CONNECTTIMEOUT => min(8, (int)$timeout),
        CURLOPT_FOLLOWLOCATION => true,
    ];
    if (defined('CURL_IPRESOLVE_V4')) {
        $opts[CURLOPT_IPRESOLVE] = CURL_IPRESOLVE_V4;
    }
    return $opts;
}

function panelCacheKey($panel) {
    $p = resolvePanelConfig($panel);
    $id = (int)($p['id'] ?? 0);
    $base = rtrim((string)($p['base_url'] ?? ''), '/');
    return $id . '|' . md5($base . '|' . (string)($p['username'] ?? ''));
}

/** لیست base: آخرین موفق → مستقیم → Worker */
function getPanelApiBasesList($panel = null) {
    $p = resolvePanelConfig($panel);
    $direct = rtrim((string)($p['base_url'] ?? (defined('PANEL_URL') ? PANEL_URL : '')), '/');
    $worker = '';
    $useWorker = !empty($p['use_worker']) || (!empty($p['is_default']) && defined('WORKER_URL') && WORKER_URL);
    if ($useWorker && defined('WORKER_URL') && WORKER_URL) {
        $cfg = defined('PANEL_URL') ? rtrim(PANEL_URL, '/') : '';
        $base = rtrim((string)($p['base_url'] ?? ''), '/');
        if ($base === '' || $base === $cfg || !empty($p['is_default'])) {
            $worker = rtrim(WORKER_URL, '/') . '/panel';
        }
    }

    $ck = 'panel_last_base_' . panelCacheKey($p);
    $last = '';
    try {
        if (isset($GLOBALS['db']) && $GLOBALS['db'] instanceof PDO && function_exists('getSetting')) {
            $last = trim((string)getSetting($GLOBALS['db'], $ck, ''));
        }
    } catch (Exception $e) {
        $last = '';
    }
    if ($last === '' && !empty($GLOBALS['_panel_last_base'][$ck])) {
        $last = (string)$GLOBALS['_panel_last_base'][$ck];
    }

    $bases = [];
    if ($last !== '') {
        $bases[] = $last;
    }
    if ($direct !== '' && !in_array($direct, $bases, true)) {
        $bases[] = $direct;
    }
    if ($worker !== '' && !in_array($worker, $bases, true)) {
        $bases[] = $worker;
    }
    try {
        $legacy = rtrim((string)getPanelApiBase($panel), '/');
        if ($legacy !== '' && !in_array($legacy, $bases, true)) {
            $bases[] = $legacy;
        }
    } catch (Exception $e) {
    }
    return array_values(array_filter($bases));
}

function rememberPanelApiBase($panel, $base) {
    $base = rtrim((string)$base, '/');
    if ($base === '') {
        return;
    }
    $ck = 'panel_last_base_' . panelCacheKey($panel);
    $GLOBALS['_panel_last_base'][$ck] = $base;
    try {
        if (isset($GLOBALS['db']) && $GLOBALS['db'] instanceof PDO && function_exists('setSetting')) {
            setSetting($GLOBALS['db'], $ck, $base);
        }
    } catch (Exception $e) {
    }
}

function getPanelApiBaseEffective($panel = null) {
    $ck = 'panel_last_base_' . panelCacheKey($panel);
    if (!empty($GLOBALS['_panel_last_base'][$ck])) {
        return rtrim((string)$GLOBALS['_panel_last_base'][$ck], '/');
    }
    try {
        if (isset($GLOBALS['db']) && $GLOBALS['db'] instanceof PDO && function_exists('getSetting')) {
            $b = trim((string)getSetting($GLOBALS['db'], $ck, ''));
            if ($b !== '') {
                return rtrim($b, '/');
            }
        }
    } catch (Exception $e) {
    }
    return rtrim((string)getPanelApiBase($panel), '/');
}

function panelInvalidateTokenCache($panel = null) {
    $ck = panelCacheKey($panel);
    if (isset($GLOBALS['_panel_token_cache'][$ck])) {
        unset($GLOBALS['_panel_token_cache'][$ck]);
    }
}

function getPasargadToken($debug = false, $panel = null) {
    $p = resolvePanelConfig($panel);
    $creds = getPanelCreds($p);
    $user = (string)($creds['username'] ?? '');
    $pass = (string)($creds['password'] ?? '');
    $ck = panelCacheKey($p);

    if (!$debug && !empty($GLOBALS['_panel_token_cache'][$ck])) {
        $ent = $GLOBALS['_panel_token_cache'][$ck];
        if (!empty($ent['token']) && !empty($ent['exp']) && (int)$ent['exp'] > time()) {
            if (!empty($ent['base'])) {
                rememberPanelApiBase($p, $ent['base']);
            }
            return $ent['token'];
        }
    }

    if ($user === '') {
        if ($debug) {
            return ['ok' => false, 'token' => null, 'http' => 0, 'curl_error' => 'empty_user', 'url' => '', 'body_preview' => ''];
        }
        return null;
    }

    $bases = getPanelApiBasesList($p);
    $debugParts = [];
    $postData = http_build_query(['username' => $user, 'password' => $pass]);

    foreach ($bases as $base) {
        $url = rtrim($base, '/') . '/api/admin/token';
        for ($try = 1; $try <= 2; $try++) {
            $ch = curl_init();
            $opts = panelCurlBaseOpts(12);
            $opts[CURLOPT_URL] = $url;
            $opts[CURLOPT_POST] = true;
            $opts[CURLOPT_POSTFIELDS] = $postData;
            $opts[CURLOPT_HTTPHEADER] = ['Content-Type: application/x-www-form-urlencoded'];
            curl_setopt_array($ch, $opts);
            $res = curl_exec($ch);
            $httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
            $curlErr = curl_error($ch);
            curl_close($ch);

            $decoded = json_decode((string)$res, true);
            $token = is_array($decoded) ? ($decoded['access_token'] ?? $decoded['token'] ?? null) : null;

            if (!empty($token)) {
                rememberPanelApiBase($p, $base);
                $GLOBALS['_panel_token_cache'][$ck] = [
                    'token' => $token,
                    'base' => rtrim($base, '/'),
                    'exp' => time() + 720,
                ];
                if ($debug) {
                    return [
                        'ok' => true,
                        'token' => $token,
                        'http' => $httpCode,
                        'curl_error' => $curlErr,
                        'url' => $url,
                        'body_preview' => mb_substr((string)$res, 0, 400),
                        'base' => $base,
                        'try' => $try,
                    ];
                }
                return $token;
            }
            $debugParts[] = $base . ' try' . $try . ' http=' . $httpCode . ($curlErr ? ' err=' . $curlErr : '');
            if ($try < 2) {
                usleep(350000);
            }
        }
    }

    if ($debug) {
        return [
            'ok' => false,
            'token' => null,
            'http' => 0,
            'curl_error' => implode(' | ', $debugParts),
            'url' => $bases ? (rtrim($bases[0], '/') . '/api/admin/token') : '',
            'body_preview' => '',
        ];
    }
    return null;
}

function getPasargadUser($username, $panel = null) {
    $token = getPasargadToken(false, $panel);
    if (!$token) return false;

    $url = getPanelApiBaseEffective($panel) . '/api/user/' . rawurlencode($username);
    $do = function ($token) use ($url) {
        $ch = curl_init();
        $opts = panelCurlBaseOpts(12);
        $opts[CURLOPT_URL] = $url;
        $opts[CURLOPT_HTTPHEADER] = ['Authorization: Bearer ' . $token];
        curl_setopt_array($ch, $opts);
        $res = curl_exec($ch);
        $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        return [$res, $http];
    };
    list($res, $http) = $do($token);
    if ($http === 401) {
        panelInvalidateTokenCache($panel);
        $token = getPasargadToken(false, $panel);
        if (!$token) return false;
        list($res, $http) = $do($token);
    }
    return json_decode((string)$res, true);
}

/**
 * حذف کاربر/سرویس از پنل پاسارگاد (Marzban-compatible)
 * @return array{ok:bool,http:int,detail:string}
 */
function deletePasargadUser($username, $panel = null) {
    $token = getPasargadToken(false, $panel);
    if (!$token) {
        return ['ok' => false, 'http' => 0, 'detail' => 'توکن پنل دریافت نشد'];
    }

    $url = getPanelApiBaseEffective($panel) . '/api/user/' . rawurlencode($username);
    $ch = curl_init();
    curl_setopt_array($ch, panelCurlBaseOpts(15) + [
        CURLOPT_URL => $url,
        CURLOPT_CUSTOMREQUEST => 'DELETE',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => [
            'Authorization: Bearer ' . $token,
            'Accept: application/json'
        ],
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_TIMEOUT => 15,
        CURLOPT_FOLLOWLOCATION => true
    ]);
    $res = curl_exec($ch);
    $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err = curl_error($ch);
    curl_close($ch);

    // 200 / 204 = موفقیت؛ 404 = از قبل نبود (برای ما کافی است)
    if ($http === 200 || $http === 204 || $http === 404) {
        return ['ok' => true, 'http' => $http, 'detail' => $http === 404 ? 'در پنل نبود' : 'حذف شد'];
    }
    $detail = $err ?: mb_substr((string)$res, 0, 200);
    return ['ok' => false, 'http' => $http, 'detail' => $detail];
}

/**
 * تبدیل فیلد expire پنل به unix timestamp (ثانیه)
 * پشتیبانی از: عدد ثانیه، میلی‌ثانیه، رشته ISO
 */
function parsePanelExpire($value) {
    if ($value === null || $value === '' || $value === false) {
        return 0;
    }
    // عدد خالص
    if (is_numeric($value)) {
        $n = (float)$value;
        if ($n <= 0) return 0;
        // میلی‌ثانیه
        if ($n > 10000000000) {
            return (int)floor($n / 1000);
        }
        return (int)$n;
    }
    // رشته تاریخ ISO یا قابل‌خواندن
    if (is_string($value)) {
        $trim = trim($value);
        if ($trim === '' || $trim === '0') return 0;
        if (is_numeric($trim)) {
            return parsePanelExpire((float)$trim);
        }
        $ts = strtotime($trim);
        if ($ts !== false && $ts > 0) {
            return (int)$ts;
        }
    }
    return 0;
}

function modifyPasargadUserDirect($username, $newVolumeGb = null, $addDays = null, $newStatus = null, $panel = null) {
    $token = getPasargadToken(false, $panel);
    if (!$token) return false;

    $currentUser = getPasargadUser($username, $panel);
    if (!$currentUser) return false;

    $payload = [];
    if ($newVolumeGb !== null) {
        $payload['data_limit'] = round($newVolumeGb * 1024 * 1024 * 1024);
    }
    if ($addDays !== null) {
        $currentExpire = parsePanelExpire($currentUser['expire'] ?? 0);
        $baseTime = ($currentExpire > time()) ? $currentExpire : time();
        $payload['expire'] = $baseTime + ($addDays * 86400);
    }
    if ($newStatus !== null) {
        $payload['status'] = $newStatus;
    }

    if (empty($payload)) return false;

    $editUrl = getPanelApiBaseEffective($panel) . '/api/user/' . rawurlencode($username);
    $ch = curl_init($editUrl);
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST => 'PUT',
        CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Content-Type: application/json'],
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_TIMEOUT => 10
    ]);
    $res = curl_exec($ch);
    curl_close($ch);
    return json_decode($res, true);
}

function createPasargadUser($username, $volume_gb, $days, $panel = null, $limitIp = 0) {
    $token = getPasargadToken(false, $panel);
    if (!$token) {
        return ['_error' => 'token_failed', 'detail' => 'دریافت توکن پنل ناموفق بود. PANEL_USER / PANEL_PASS / PANEL_URL را چک کنید.'];
    }

    $url = getPanelApiBaseEffective($panel) . '/api/user';
    $volume_gb = (float)$volume_gb;
    // 0 = حجم نامحدود در API مرزبان/پاسارگاد
    $dataLimitBytes = ($volume_gb > 0) ? (int)round($volume_gb * 1024 * 1024 * 1024) : 0;
    $days = (int)$days;

    // group_ids: اختصاصی هر پنل → بعد سراسری پیش‌فرض → در غیر این صورت خالی (API پنل ممکن است همه را بدهد)
    $groupIds = [];
    try {
        $panelCfg = resolvePanelConfig($panel);
        $ptype = strtolower((string)($panelCfg['type'] ?? 'pasargad'));
        $isDefault = !empty($panelCfg['is_default']);
        $panelRowId = (int)($panelCfg['id'] ?? 0);
        $groupIdsRaw = '';
        if (isset($GLOBALS['db']) && $GLOBALS['db'] instanceof PDO) {
            $groupIdsRaw = getPanelGroupIdsSetting($GLOBALS['db'], $panelRowId);
        }
        if ($groupIdsRaw === '' && !empty($panelCfg['extra_json'])) {
            $ex = json_decode((string)$panelCfg['extra_json'], true);
            if (is_array($ex) && isset($ex['group_ids'])) {
                $groupIdsRaw = is_array($ex['group_ids']) ? implode(',', $ex['group_ids']) : (string)$ex['group_ids'];
            }
        }
        $groupIds = function_exists('parseGroupIdsList') ? parseGroupIdsList($groupIdsRaw) : [];
        if (!$groupIds && $groupIdsRaw !== '') {
            $parsed = array_map('intval', array_filter(array_map('trim', explode(',', (string)$groupIdsRaw)), function($v) {
                return $v !== '' && $v !== '0';
            }));
            $groupIds = array_values($parsed);
        }
    } catch (Exception $e) {}

    // فقط پروتکل‌های فعال روی سرور — ارسال vmess روی پنل‌هایی که خاموش است خطا می‌دهد
    // تنظیم اختیاری: panel_proxy_types=vless,trojan (پیش‌فرض: فقط vless)
    $proxyTypes = ['vless'];
    try {
        if (isset($GLOBALS['db']) && $GLOBALS['db'] instanceof PDO) {
            $rawPx = trim((string)getSetting($GLOBALS['db'], 'panel_proxy_types', 'vless'));
            if ($rawPx !== '') {
                $allowed = ['vless', 'vmess', 'trojan', 'shadowsocks'];
                $parsed = [];
                foreach (preg_split('/[\s,;]+/', strtolower($rawPx)) as $p) {
                    $p = trim($p);
                    if (in_array($p, $allowed, true)) {
                        $parsed[$p] = true;
                    }
                }
                if ($parsed) {
                    $proxyTypes = array_keys($parsed);
                }
            }
        }
    } catch (Exception $e) {}
    $proxiesObj = [];
    foreach ($proxyTypes as $pt) {
        $proxiesObj[$pt] = new stdClass();
    }
    if (!$proxiesObj) {
        $proxiesObj['vless'] = new stdClass();
    }

    // پلن مدت‌دار: شروع از اولین اتصال (on_hold) — VIP بدون مدت مثل قبل
    $payload = [
        'username' => $username,
        'data_limit' => $dataLimitBytes,
        'proxies' => $proxiesObj,
        'inbounds' => new stdClass()
    ];
    if ($days > 0) {
        $payload['status'] = 'on_hold';
        $payload['expire'] = 0;
        $payload['on_hold_expire_duration'] = $days * 86400;
        // بدون on_hold_timeout: تا اولین اتصال منتظر می‌ماند و حذف خودکار نمی‌شود
    } else {
        $payload['expire'] = 0;
    }
    if (!empty($groupIds)) {
        $payload['group_ids'] = $groupIds;
    }
    $limitIp = max(0, (int)$limitIp);
    if ($limitIp > 0) {
        $payload['limit_ip'] = $limitIp;
    }

    $res = false;
    $httpCode = 0;
    $curlErr = '';
    for ($try = 1; $try <= 3; $try++) {
        if ($try >= 2) {
            panelInvalidateTokenCache($panel);
            $token = getPasargadToken(false, $panel);
            if (!$token) {
                break;
            }
            $url = getPanelApiBaseEffective($panel) . '/api/user';
            usleep(400000);
        }
        $ch = curl_init();
        $opts = panelCurlBaseOpts(14);
        $opts[CURLOPT_URL] = $url;
        $opts[CURLOPT_POST] = true;
        $opts[CURLOPT_POSTFIELDS] = json_encode($payload);
        $opts[CURLOPT_HTTPHEADER] = ['Authorization: Bearer ' . $token, 'Content-Type: application/json'];
        curl_setopt_array($ch, $opts);
        $res = curl_exec($ch);
        $httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curlErr = curl_error($ch);
        curl_close($ch);
        if ($res === false || $res === '') {
            continue;
        }
        // اگر پروتکل خاصی روی سرور خاموش است، حذف و یک‌بار دیگر تلاش
        $tmpDec = json_decode((string)$res, true);
        $errDetail = is_array($tmpDec) ? (string)($tmpDec['detail'] ?? '') : '';
        if ($httpCode >= 400 && preg_match('/ProxyTypes\.(\w+)\s+is\s+disabled/i', $errDetail, $mm)) {
            $bad = strtolower($mm[1]);
            if (isset($payload['proxies'][$bad])) {
                unset($payload['proxies'][$bad]);
                if (empty($payload['proxies'])) {
                    $payload['proxies'] = ['vless' => new stdClass()];
                }
                continue;
            }
        }
        break;
    }

    // اگر پاسخ شبکه خراب بود ولی کاربر ساخته شده باشد
    if ($res === false || $res === '') {
        $exists = getPasargadUser($username, $panel);
        if (is_array($exists) && !empty($exists['username'])) {
            return $exists;
        }
        return ['_error' => 'curl_failed', 'detail' => $curlErr ?: 'پاسخ خالی از پنل', 'http' => $httpCode];
    }

    $decoded = json_decode($res, true);
    if (!is_array($decoded)) {
        $exists = getPasargadUser($username, $panel);
        if (is_array($exists) && !empty($exists['username'])) {
            return $exists;
        }
        return ['_error' => 'invalid_json', 'detail' => substr((string)$res, 0, 300), 'http' => $httpCode];
    }

    // اگر پنل خطا برگرداند
    if (isset($decoded['detail']) || isset($decoded['message']) || $httpCode >= 400) {
        $msg = $decoded['detail'] ?? $decoded['message'] ?? json_encode($decoded, JSON_UNESCAPED_UNICODE);
        if (is_array($msg)) $msg = json_encode($msg, JSON_UNESCAPED_UNICODE);
        return ['_error' => 'panel_error', 'detail' => $msg, 'http' => $httpCode, 'raw' => $decoded];
    }

    return $decoded;
}

/** آیا پیام خطای پنل یعنی «نام کاربری از قبل هست»؟ */
function panelErrorIsUsernameTaken($detail) {
    $d = mb_strtolower((string)$detail);
    return (strpos($d, 'already exists') !== false
        || strpos($d, 'user exists') !== false
        || strpos($d, 'duplicate') !== false
        || strpos($d, 'وجود دارد') !== false
        || strpos($d, 'تکراری') !== false);
}

/**
 * نام‌های جایگزین نزدیک به درخواست کاربر
 * bahram → bahram1, bahram12, bahram123, bahram_123، … و در آخر user_{id}_xxxx
 */
function buildUsernameCandidates($preferredUsername, $userId = 0) {
    $preferredUsername = preg_replace('/[^a-zA-Z0-9_\-\.]/', '', (string)$preferredUsername);
    $uidPart = max(1, (int)$userId);
    if ($preferredUsername === '' || preg_match('/^user_\d+_\d+$/', $preferredUsername)) {
        $out = [];
        for ($i = 0; $i < 8; $i++) {
            $out[] = 'user_' . $uidPart . '_' . random_int(1000, 9999);
        }
        return array_values(array_unique($out));
    }
    $base = mb_substr($preferredUsername, 0, 24);
    $candidates = [$preferredUsername, $base];
    for ($n = 1; $n <= 9; $n++) {
        $candidates[] = $base . $n;
    }
    foreach ([12, 21, 99, 100, 123, 321, 2024, 2025, 2026] as $n) {
        $candidates[] = $base . $n;
        $candidates[] = $base . '_' . $n;
    }
    for ($i = 0; $i < 4; $i++) {
        $candidates[] = $base . random_int(10, 99);
        $candidates[] = $base . random_int(100, 999);
    }
    for ($i = 0; $i < 3; $i++) {
        $candidates[] = 'user_' . $uidPart . '_' . random_int(1000, 9999);
    }
    $out = [];
    foreach ($candidates as $c) {
        $c = preg_replace('/[^a-zA-Z0-9_\-\.]/', '', (string)$c);
        if ($c === '' || isset($out[$c])) {
            continue;
        }
        if (mb_strlen($c) > 32) {
            $c = mb_substr($c, 0, 32);
        }
        $out[$c] = $c;
    }
    return array_values($out);
}

/**
 * ساخت کاربر در پنل؛ اگر نام تکراری بود نام نزدیک به درخواست کاربر می‌سازد.
 * @return array نتیجه پنل + کلید _final_username
 */
function createPasargadUserUnique($preferredUsername, $volume_gb, $days, $panel = null, $userId = 0, $limitIp = 0) {
    $candidates = buildUsernameCandidates($preferredUsername, $userId);

    $last = ['_error' => 'no_attempt', 'detail' => 'نام کاربری خالی'];
    foreach ($candidates as $uname) {
        try {
            if (isset($GLOBALS['db']) && $GLOBALS['db'] instanceof PDO) {
                $st = $GLOBALS['db']->prepare('SELECT id FROM orders WHERE config_username = ? LIMIT 1');
                $st->execute([$uname]);
                if ($st->fetch()) {
                    continue;
                }
            }
        } catch (Exception $e) {
        }

        $res = createPasargadUser($uname, $volume_gb, $days, $panel, $limitIp);
        if (empty($res['_error'])) {
            $res['_final_username'] = $uname;
            return $res;
        }
        $last = $res;
        $detail = (string)($res['detail'] ?? $res['_error'] ?? '');
        if (!panelErrorIsUsernameTaken($detail)) {
            $last['_final_username'] = $uname;
            return $last;
        }
    }
    $last['_final_username'] = (string)($candidates[0] ?? $preferredUsername);
    return $last;
}

function renewPasargadUser($username, $volume_gb, $days, $panel = null) {
    /**
     * تمدید حجم:
     * - سقف جدید = سقف قبلی + حجم پلن (مصرف ریست نمی‌شود)
     * - اگر هنوز on_hold (وصل نشده): مدت به on_hold_expire_duration اضافه می‌شود
     * - اگر active: انقضا از تاریخ فعلی یا الان + روزها
     * - days=0 → VIP بدون انقضا
     */
    $token = getPasargadToken(false, $panel);
    if (!$token) return false;

    $current = getPasargadUser($username, $panel);
    $used = 0;
    $oldLimit = 0;
    $currentExpire = 0;
    $panelStatus = 'active';
    $holdDur = 0;
    if (is_array($current)) {
        $used = (float)($current['used_traffic'] ?? 0);
        $oldLimit = (float)($current['data_limit'] ?? 0);
        $currentExpire = parsePanelExpire($current['expire'] ?? 0);
        $panelStatus = (string)($current['status'] ?? 'active');
        $holdDur = (int)($current['on_hold_expire_duration'] ?? 0);
    }

    $remaining = 0;
    if ($oldLimit > 0) {
        $remaining = max(0, $oldLimit - $used);
    }

    $addBytes = (int)round((float)$volume_gb * 1024 * 1024 * 1024);
    if ($oldLimit > 0) {
        $newLimit = (int)round($oldLimit + $addBytes);
    } else {
        $newLimit = $addBytes;
    }
    $newVolGb = round($newLimit / (1024 * 1024 * 1024), 3);

    $days = (int)$days;
    $payload = [
        'data_limit' => $newLimit,
    ];
    $expireTime = 0;

    if ($days > 0 && $panelStatus === 'on_hold') {
        // هنوز اولین اتصال نخورده — مدت را به حالت انتظار اضافه کن
        $payload['status'] = 'on_hold';
        $payload['expire'] = 0;
        $payload['on_hold_expire_duration'] = max(0, $holdDur) + ($days * 86400);
        $expireTime = 0;
    } elseif ($days > 0) {
        $baseTime = ($currentExpire > time()) ? $currentExpire : time();
        $expireTime = $baseTime + ($days * 86400);
        $payload['expire'] = $expireTime;
        $payload['status'] = 'active';
    } else {
        $expireTime = 0;
        $payload['expire'] = 0;
        $payload['status'] = 'active';
    }

    $editUrl = getPanelApiBaseEffective($panel) . '/api/user/' . rawurlencode($username);
    $ch = curl_init($editUrl);
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST => 'PUT',
        CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Content-Type: application/json'],
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_TIMEOUT => 12
    ]);
    $res = curl_exec($ch);
    $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    $decoded = json_decode((string)$res, true);

    $ok = is_array($decoded) && empty($decoded['detail']) && $http >= 200 && $http < 300;
    // اگر پاسخ مبهم بود ولی سقف واقعاً بالا رفته
    if (!$ok && is_array($decoded) && isset($decoded['data_limit']) && (float)$decoded['data_limit'] >= $newLimit * 0.99) {
        $ok = true;
    }

    return [
        'ok' => $ok,
        'volume_gb' => $newVolGb,
        'expire' => $expireTime,
        'days_added' => (int)$days,
        'remaining_bytes' => (int)$remaining,
        'old_limit' => (int)$oldLimit,
        'used' => (int)$used,
        'http' => $http,
        'raw' => $decoded
    ];
}


/**
 * ستون حجم آخرین تمدید (برای نمایش/اخطار بر اساس بستهٔ آخر نه سقف انباشتی)
 */
function jet_ensure_last_renew_col(PDO $db): void {
    static $done = false;
    if ($done) {
        return;
    }
    $done = true;
    try {
        $db->exec('ALTER TABLE orders ADD COLUMN last_renew_gb DOUBLE NULL DEFAULT NULL');
    } catch (Throwable $e) {
        // already exists
    }
    try {
        $db->exec('ALTER TABLE orders ADD COLUMN volume_cycle_gb DOUBLE NULL DEFAULT NULL');
    } catch (Throwable $e) {
        // already exists
    }
}

/** اطمینان از وجود ستون ظرفیت دوره نمایش (مانده قبل تمدید + بسته جدید) */
function jet_ensure_volume_cycle_col(PDO $db): void {
    jet_ensure_last_renew_col($db);
}

/**
 * همگام‌سازی سفارش بعد از تمدید انباشتی — حجم کل پنل + روز مانده واقعی + ریست هشدارها
 * @param array|bool $ren خروجی renewPasargadUser
 * @param float $addedVol حجم همین تمدید (پلن خریداری‌شده) برای last_renew_gb
 * @return float حجم کل ذخیره‌شده
 */
function jet_sync_order_after_renew(PDO $db, string $configUsername, $ren, int $planDays, float $fallbackVol = 0.0, float $addedVol = 0.0): float {
    // فقط پس از موفقیت قطعی تمدید پنل Snapshot ثبت شود — در شکست، سفارش دست‌نخورده بماند
    if ($ren === false || $ren === null) {
        return 0.0;
    }
    if (!is_array($ren)) {
        return 0.0;
    }
    // renewPasargadUser همیشه آرایه با کلید ok برمی‌گرداند (به‌جز false برای نبود توکن)
    if (array_key_exists('ok', $ren) && empty($ren['ok'])) {
        return 0.0;
    }
    jet_ensure_last_renew_col($db);
    $newVol = 0.0;
    if (isset($ren['volume_gb']) && (float)$ren['volume_gb'] > 0) {
        $newVol = (float)$ren['volume_gb'];
    } elseif ($fallbackVol > 0) {
        // fallback فقط وقتی پاسخ موفق بوده ولی volume_gb خالی است (نادر)
        $newVol = $fallbackVol;
    }
    $exp = is_array($ren) && !empty($ren['expire']) ? (int)$ren['expire'] : 0;
    if ($planDays <= 0) {
        $daysStore = 0;
    } elseif ($exp > time()) {
        $daysStore = max($planDays, (int)ceil(($exp - time()) / 86400));
    } else {
        $daysStore = $planDays;
    }
    if ($newVol <= 0) {
        return $newVol;
    }
    $add = $addedVol > 0 ? $addedVol : 0.0;
    // ظرفیت دوره نمایش = مانده واقعی قبل از تمدید + حجم بسته تمدید
    $remainingBeforeGb = 0.0;
    if (is_array($ren) && isset($ren['remaining_bytes'])) {
        $remainingBeforeGb = max(0.0, (float)$ren['remaining_bytes'] / (1024 * 1024 * 1024));
    } elseif (is_array($ren) && isset($ren['remaining_before_gb'])) {
        $remainingBeforeGb = max(0.0, (float)$ren['remaining_before_gb']);
    }
    $cycleGb = ($add > 0) ? round($remainingBeforeGb + $add, 3) : 0.0;
    $orderId = 0;
    try {
        $stOid = $db->prepare('SELECT id FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 1');
        $stOid->execute([$configUsername]);
        $orderId = (int)($stOid->fetchColumn() ?: 0);
    } catch (Throwable $eOid) {}
    try {
        if ($orderId > 0) {
            if ($add > 0 && $cycleGb > 0) {
                $db->prepare("UPDATE orders SET volume_gb = ?, days = ?, last_renew_gb = ?, volume_cycle_gb = ?, warned_volume = 0, warned_expire = 0 WHERE id = ?")
                    ->execute([$newVol, $daysStore, $add, $cycleGb, $orderId]);
            } elseif ($add > 0) {
                $db->prepare("UPDATE orders SET volume_gb = ?, days = ?, last_renew_gb = ?, warned_volume = 0, warned_expire = 0 WHERE id = ?")
                    ->execute([$newVol, $daysStore, $add, $orderId]);
                error_log('[jet_sync] cycle snapshot skipped (no cycleGb) order_id=' . $orderId);
            } else {
                $db->prepare("UPDATE orders SET volume_gb = ?, days = ?, warned_volume = 0, warned_expire = 0 WHERE id = ?")
                    ->execute([$newVol, $daysStore, $orderId]);
            }
        } else {
            if ($add > 0 && $cycleGb > 0) {
                $db->prepare("UPDATE orders SET volume_gb = ?, days = ?, last_renew_gb = ?, volume_cycle_gb = ?, warned_volume = 0, warned_expire = 0 WHERE config_username = ?")
                    ->execute([$newVol, $daysStore, $add, $cycleGb, $configUsername]);
            } elseif ($add > 0) {
                $db->prepare("UPDATE orders SET volume_gb = ?, days = ?, last_renew_gb = ?, warned_volume = 0, warned_expire = 0 WHERE config_username = ?")
                    ->execute([$newVol, $daysStore, $add, $configUsername]);
            } else {
                $db->prepare("UPDATE orders SET volume_gb = ?, days = ?, warned_volume = 0, warned_expire = 0 WHERE config_username = ?")
                    ->execute([$newVol, $daysStore, $configUsername]);
            }
        }
    } catch (Throwable $e) {
        error_log('[jet_sync] orders update failed order_id=' . $orderId . ' err=' . $e->getMessage());
        try {
            if ($add > 0) {
                $db->prepare("UPDATE orders SET volume_gb = ?, days = ?, last_renew_gb = ?, warned_volume = 0, warned_expire = 0 WHERE config_username = ?")
                    ->execute([$newVol, $daysStore, $add, $configUsername]);
            } else {
                $db->prepare("UPDATE orders SET volume_gb = ?, days = ?, warned_volume = 0, warned_expire = 0 WHERE config_username = ?")
                    ->execute([$newVol, $daysStore, $configUsername]);
            }
        } catch (Throwable $e2) {
            try {
                $db->prepare("UPDATE orders SET volume_gb = ?, days = ? WHERE config_username = ?")
                    ->execute([$newVol, $daysStore, $configUsername]);
            } catch (Throwable $e3) {}
        }
    }
    return $newVol;
}

/**
 * پاداش دعوت — فقط اولین خرید واقعی
 * معرف: ۱۰٪ مبلغ فاکتور (سقف ۵۰٬۰۰۰ ت) به کیف پول
 * دعوت‌شده: ۵٪ حجم اضافه در لحظه ساخت سرویس (تابع inviteeVolumeWithBonus)
 */
function checkAndRewardReferral($buyerId, $db, $buyerUsername, $purchasePrice = 0) {
    try {
        $stmt = $db->prepare("SELECT inviter_id, has_bought FROM users WHERE user_id = ?");
        $stmt->execute([$buyerId]);
        $user = $stmt->fetch();

        if ($user && (int)$user['has_bought'] === 0 && !empty($user['inviter_id'])) {
            $inviterId = (int)$user['inviter_id'];
            $pct = (int)getSetting($db, 'ref_reward_percent', 10);
            $cap = (int)getSetting($db, 'ref_reward_cap', 50000);
            if ($pct < 1) {
                $pct = 10;
            }
            if ($cap < 1000) {
                $cap = 50000;
            }
            $price = (int)$purchasePrice;
            if ($price > 0) {
                $rewardAmount = (int)round($price * $pct / 100.0);
            } else {
                $rewardAmount = (int)getSetting($db, 'ref_reward', 20000);
            }
            $rewardAmount = max(0, min($rewardAmount, $cap));

            if ($rewardAmount > 0) {
                $adj = adjustWalletBalance($db, $inviterId, $rewardAmount, 'referral_reward', 'user', (string)$buyerId, 'پاداش دعوت');
                if (!empty($adj['ok'])) {
                    $db->prepare("UPDATE users SET total_ref_earned = total_ref_earned + ? WHERE user_id = ?")
                       ->execute([$rewardAmount, $inviterId]);
                }

                $notifMsg = "🎉 <b>آفرین! پاداش دعوتت نشست</b>\n"
                          . "──────────────────\n"
                          . "@{$buyerUsername} اولین خریدش رو زد.\n\n"
                          . "💰 <b>" . number_format($rewardAmount) . " تومان</b> ({$pct}٪ خرید، سقف " . number_format($cap) . ")\n"
                          . "رفت تو کیف پولت — می‌تونی باهاش خرید آنی بزنی ⚡️";

                sendTelegram('sendMessage', [
                    'chat_id' => $inviterId,
                    'text' => $notifMsg,
                    'parse_mode' => 'HTML'
                ]);
            }

            $db->prepare("UPDATE users SET has_bought = 1 WHERE user_id = ?")->execute([$buyerId]);
        } else {
            $db->prepare("UPDATE users SET has_bought = 1 WHERE user_id = ?")->execute([$buyerId]);
        }
    } catch (Exception $e) {}
}

/** ۵٪ حجم اضافه برای اولین خرید کسی که با لینک دعوت آمده */
function inviteeVolumeWithBonus($db, $userId, $volumeGb) {
    $vol = (float)$volumeGb;
    if ($vol <= 0 || $userId <= 0) {
        return $vol;
    }
    try {
        $stmt = $db->prepare("SELECT inviter_id, has_bought FROM users WHERE user_id = ? LIMIT 1");
        $stmt->execute([(int)$userId]);
        $u = $stmt->fetch(PDO::FETCH_ASSOC);
        if (!$u || empty($u['inviter_id']) || (int)$u['has_bought'] === 1) {
            return $vol;
        }
        $pct = (int)getSetting($db, 'ref_invitee_vol_percent', 5);
        if ($pct < 1) {
            $pct = 5;
        }
        return round($vol * (1 + $pct / 100.0), 3);
    } catch (Exception $e) {
        return $vol;
    }
}

/** یادآوری نرم بعد از خرید — لینک دعوت + دکمه اشتراک‌گذاری */
function sendReferralInviteNudge($db, $userId) {
    try {
        if (!isFeatureEnabled($db, 'btn_ref') && !isBotAdmin((int)$userId)) {
            return;
        }
        $botInfo = sendTelegram('getMe');
        $botUsername = $botInfo['result']['username'] ?? 'JetConfig1bot';
        $refLink = "https://t.me/{$botUsername}?start={$userId}";
        $pct = (int)getSetting($db, 'ref_reward_percent', 10);
        $cap = (int)getSetting($db, 'ref_reward_cap', 50000);
        $shareText = "🚀 اینترنت پرسرعت با JET — تست رایگان بگیر:\n{$refLink}";
        $shareUrl = 'https://t.me/share/url?url=' . rawurlencode($refLink) . '&text=' . rawurlencode($shareText);
        $kb = json_encode([
            'inline_keyboard' => [
                [['text' => '📤 ارسال برای دوست در تلگرام', 'url' => $shareUrl]],
                [['text' => '👥 جزئیات دعوت دوست', 'callback_data' => 'referral_menu', 'style' => 'primary']],
            ]
        ], JSON_UNESCAPED_UNICODE);
        $msg = "🎁 <b>دوستت هم وصل بشه، هر دو سود می‌برید</b>\n\n"
             . "با لینک تو اگه اولین خریدش رو بزنه:\n"
             . "• تو: <b>{$pct}٪</b> مبلغ خرید (سقف " . number_format($cap) . " ت) تو کیف پول\n"
             . "• دوستت: مثل همه <b>۱۰٪ تخفیف اولین خرید</b> + <b>۵٪ حجم بیشتر</b> هدیه دعوت 📦\n\n"
             . "لینک اختصاصیت:\n<code>{$refLink}</code>";
        sendTelegram('sendMessage', [
            'chat_id' => $userId,
            'text' => $msg,
            'parse_mode' => 'HTML',
            'reply_markup' => $kb,
            'disable_web_page_preview' => true,
        ]);
    } catch (Exception $e) {}
}

function getFinancialReport($db, $period = 'today') {
    $resetAt = getSetting($db, 'financial_reset_at', '2020-01-01 00:00:00');
    $whereTime = "";
    $title = "";

    switch ($period) {
        case 'today':
            $whereTime = "AND DATE(created_at) = CURDATE()";
            $title = "گزارش مالی امروز";
            break;
        case 'yesterday':
            $whereTime = "AND DATE(created_at) = SUBDATE(CURDATE(), 1)";
            $title = "گزارش مالی دیروز";
            break;
        case '7days':
            $whereTime = "AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)";
            $title = "گزارش مالی ۷ روز اخیر";
            break;
        case '30days':
            $whereTime = "AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)";
            $title = "گزارش مالی ۳۰ روز اخیر";
            break;
        default:
            $whereTime = "";
            $title = "گزارش مالی کل دوره";
            break;
    }

    $exUser = function_exists('accountingExcludeSql') ? accountingExcludeSql($db, 'user_id') : '';

    try {
        $stmt = $db->prepare("SELECT SUM(price) FROM payments WHERE status = 'approved' AND created_at >= ? {$whereTime}{$exUser}");
        $stmt->execute([$resetAt]);
        $totalIncome = (int)($stmt->fetchColumn() ?: 0);

        $stmt = $db->prepare("SELECT COUNT(*) FROM payments WHERE status = 'approved' AND created_at >= ? {$whereTime}{$exUser}");
        $stmt->execute([$resetAt]);
        $totalOrders = (int)($stmt->fetchColumn() ?: 0);

        $avgOrder = $totalOrders > 0 ? round($totalIncome / $totalOrders) : 0;

        // کارت به کارت (فیش واقعی)
        $stmt = $db->prepare("SELECT SUM(price) FROM payments WHERE status = 'approved' AND photo_file_id != 'WALLET_PAY' AND photo_file_id IS NOT NULL AND action_type != 'deposit' AND created_at >= ? {$whereTime}{$exUser}");
        $stmt->execute([$resetAt]);
        $cardPlanIncome = (int)($stmt->fetchColumn() ?: 0);

        // شارژ کیف پول با فیش
        $stmt = $db->prepare("SELECT SUM(price) FROM payments WHERE status = 'approved' AND action_type = 'deposit' AND created_at >= ? {$whereTime}{$exUser}");
        $stmt->execute([$resetAt]);
        $depositIncome = (int)($stmt->fetchColumn() ?: 0);

        // پرداخت از موجودی کیف پول
        $stmt = $db->prepare("SELECT SUM(price) FROM payments WHERE status = 'approved' AND photo_file_id = 'WALLET_PAY' AND created_at >= ? {$whereTime}{$exUser}");
        $stmt->execute([$resetAt]);
        $walletPayIncome = (int)($stmt->fetchColumn() ?: 0);

        $stmt = $db->prepare("SELECT COUNT(*) FROM users WHERE created_at >= ? {$whereTime}");
        $stmt->execute([$resetAt]);
        $newUsers = (int)($stmt->fetchColumn() ?: 0);

        $pendingCount = (int)($db->query("SELECT COUNT(*) FROM payments WHERE status = 'pending'")->fetchColumn() ?: 0);
        $pendingSum = (int)($db->query("SELECT SUM(price) FROM payments WHERE status = 'pending'")->fetchColumn() ?: 0);

        return "📊 <b>{$title}</b>\n\n"
             . "💰 درآمد کل: <b>" . number_format($totalIncome) . " تومان</b>\n"
             . "📦 سفارش موفق: <b>{$totalOrders}</b> عدد\n"
             . "📐 میانگین هر سفارش: <b>" . number_format($avgOrder) . " تومان</b>\n\n"
             . "💳 خرید پلن (کارت): <b>" . number_format($cardPlanIncome) . "</b>\n"
             . "➕ شارژ کیف پول: <b>" . number_format($depositIncome) . "</b>\n"
             . "⚡️ پرداخت از کیف پول: <b>" . number_format($walletPayIncome) . "</b>\n\n"
             . "👥 کاربر جدید: <b>{$newUsers}</b> نفر\n"
             . "⏳ فیش در انتظار: <b>{$pendingCount}</b> عدد (" . number_format($pendingSum) . " تومان)\n\n"
             . "📌 مبدا آمار: <code>" . substr($resetAt, 0, 16) . "</code>";
    } catch (Exception $e) {
        return "⚠️ خطا در دریافت گزارش مالی.";
    }
}



if (!function_exists('buildPaymentReviewInfo')) {
    /**
     * کارت کامل بررسی فیش برای ادمین (ربات + وب)
     * @return array{html:string,warn:bool,warn_text:string,fields:array}
     */
    function buildPaymentReviewInfo($db, array $pay) {
        $pid = (int)($pay['id'] ?? 0);
        $uid = (int)($pay['user_id'] ?? 0);
        $price = (int)($pay['price'] ?? 0);
        $act = strtolower(trim((string)($pay['action_type'] ?? 'new')));
        $planKey = trim((string)($pay['plan_key'] ?? ''));
        $coupon = trim((string)($pay['coupon_code'] ?? ''));
        $target = trim((string)($pay['target_username'] ?? ''));
        $created = (string)($pay['created_at'] ?? '');
        $fid = (string)($pay['photo_file_id'] ?? '');

        $actMap = [
            'new' => 'خرید جدید',
            'renew' => 'تمدید',
            'deposit' => 'شارژ کیف پول',
        ];
        $actLabel = $actMap[$act] ?? $act;

        $tgUser = '';
        $balance = 0;
        $hasBought = 0;
        $orderCount = 0;
        try {
            $st = $db->prepare('SELECT username, balance, has_bought FROM users WHERE user_id = ? LIMIT 1');
            $st->execute([$uid]);
            $u = $st->fetch(PDO::FETCH_ASSOC);
            if ($u) {
                $tgUser = ltrim((string)($u['username'] ?? ''), '@');
                $balance = (int)($u['balance'] ?? 0);
                $hasBought = (int)($u['has_bought'] ?? 0);
            }
        } catch (Exception $e) {}
        try {
            $st = $db->prepare('SELECT COUNT(*) FROM orders WHERE user_id = ?');
            $st->execute([$uid]);
            $orderCount = (int)$st->fetchColumn();
        } catch (Exception $e) {}

        $planTitle = '';
        $planPrice = 0;
        $planVol = null;
        $planDays = null;
        if ($act !== 'deposit' && $planKey !== '' && !is_numeric($planKey)) {
            try {
                $st = $db->prepare('SELECT title, price, vol, days FROM bot_plans WHERE plan_key = ? LIMIT 1');
                $st->execute([$planKey]);
                $pl = $st->fetch(PDO::FETCH_ASSOC);
                if ($pl) {
                    $planTitle = (string)($pl['title'] ?? '');
                    $planPrice = (int)($pl['price'] ?? 0);
                    $planVol = $pl['vol'] ?? null;
                    $planDays = $pl['days'] ?? null;
                }
            } catch (Exception $e) {}
        }

        $discountPct = 0;
        if ($coupon !== '') {
            if (strtoupper($coupon) === 'FIRST10') {
                $discountPct = 10;
            } else {
                try {
                    $st = $db->prepare('SELECT discount_percent FROM coupons WHERE code = ? LIMIT 1');
                    $st->execute([$coupon]);
                    $discountPct = (int)$st->fetchColumn();
                } catch (Exception $e) {}
            }
        }
        $afterDiscount = $planPrice > 0 && $discountPct > 0
            ? (int)round($planPrice * (1 - $discountPct / 100.0))
            : $planPrice;

        $source = 'عکس فیش';
        if ($fid === 'SMS_AUTO') $source = 'تأیید پیامکی';
        elseif ($fid === 'WALLET_PAY') $source = 'کیف پول';
        elseif ($fid === 'AWAITING_RECEIPT') $source = 'پیش‌فاکتور (بدون عکس)';
        elseif ($fid === 'ADMIN_CREDIT' || $fid === 'ADMIN_DEBIT') $source = 'دستی ادمین';
        elseif ($fid !== '' && strlen($fid) > 15) $source = 'عکس فیش';

        $createdFa = $created;
        if ($created !== '' && function_exists('formatJalaliDateTime')) {
            $createdFa = formatJalaliDateTime($created);
        } elseif (strlen($created) >= 16) {
            $createdFa = substr($created, 0, 16);
        }

        $warn = false;
        $warnText = '';
        if (in_array($act, ['new', 'renew'], true) && $planPrice >= 10000) {
            $ratio = $price / max(1, $planPrice);
            if ($ratio < 0.40) {
                $warn = true;
                $warnText = 'مبلغ فاکتور کمتر از ۴۰٪ قیمت پلن است — احتمال خطا یا فاکتور ناقص';
            } elseif ($ratio > 1.25) {
                $warn = true;
                $warnText = 'مبلغ فاکتور بیشتر از حد انتظار نسبت به قیمت پلن است';
            }
        }
        if ($act === 'deposit' && $price > 0 && is_numeric($planKey)) {
            $req = (int)$planKey;
            if ($req > 0 && $price < (int)($req * 0.5)) {
                $warn = true;
                $warnText = 'مبلغ یکتا با مبلغ درخواست شارژ هم‌خوانی ندارد';
            }
        }

        $customerLabel = $hasBought > 0 || $orderCount > 0 ? 'مشتری قبلی' : 'خرید اول / کاربر جدید';
        $tgLine = $tgUser !== '' ? '@' . $tgUser : '—';

        $h = function ($s) {
            return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8');
        };

        $lines = [];
        $lines[] = $warn ? '⚠️ <b>هشدار: مبلغ غیرعادی</b>' : '🔔 <b>فیش جدید برای بررسی</b>';
        if ($warn && $warnText !== '') {
            $lines[] = '❗️ ' . $h($warnText);
        }
        $lines[] = '';
        $lines[] = "#️⃣ فاکتور: <code>#{$pid}</code>";
        $lines[] = "👤 کاربر: {$h($tgLine)} (<code>{$uid}</code>)";
        $lines[] = "🏷 وضعیت: {$h($customerLabel)} | 💼 کیف: <b>" . number_format($balance) . "</b> ت";
        if ($orderCount > 0) {
            $lines[] = "📊 سرویس ثبت‌شده: <b>{$orderCount}</b>";
        }
        $lines[] = '';
        $lines[] = "📦 نوع: <b>{$h($actLabel)}</b>";
        if ($act === 'deposit') {
            $reqAmt = is_numeric($planKey) ? (int)$planKey : 0;
            if ($reqAmt > 0) {
                $lines[] = "💳 مبلغ درخواست شارژ: <b>" . number_format($reqAmt) . "</b> ت";
            }
        } else {
            if ($planTitle !== '') {
                $lines[] = "🏷 پلن: <b>{$h($planTitle)}</b>";
            }
            if ($planKey !== '') {
                $lines[] = "🔑 کد پلن: <code>{$h($planKey)}</code>";
            }
            if ($planPrice > 0) {
                $lines[] = "💰 قیمت پلن: <b>" . number_format($planPrice) . "</b> ت";
            }
            if ($planVol !== null || $planDays !== null) {
                $volTxt = ((float)$planVol <= 0) ? 'نامحدود' : (rtrim(rtrim(number_format((float)$planVol, 2, '.', ''), '0'), '.') . ' گیگ');
                $dayTxt = ((int)$planDays <= 0) ? 'بدون انقضا' : ((int)$planDays . ' روز');
                $lines[] = "📐 حجم/مدت: {$h($volTxt)} / {$h($dayTxt)}";
            }
        }
        if ($coupon !== '') {
            $cLine = "🎟 تخفیف: <code>{$h($coupon)}</code>";
            if ($discountPct > 0) {
                $cLine .= " ({$discountPct}٪)";
                if ($afterDiscount > 0) {
                    $cLine .= " → " . number_format($afterDiscount) . " ت";
                }
            }
            $lines[] = $cLine;
        } else {
            $lines[] = "🎟 تخفیف: —";
        }
        $lines[] = "🔢 مبلغ قابل پرداخت: <b>" . number_format($price) . "</b> ت";
        $lines[] = "💵 ریال: <code>" . number_format($price * 10) . "</code>";
        if ($target !== '' && $target !== 'wallet') {
            $lines[] = "👤 کانفیگ: <code>{$h($target)}</code>";
        }
        $lines[] = "📥 منبع: {$h($source)}";
        if ($createdFa !== '') {
            $lines[] = "⏱ زمان فاکتور: {$h($createdFa)}";
        }

        return [
            'html' => implode("\n", $lines),
            'warn' => $warn,
            'warn_text' => $warnText,
            'fields' => [
                'id' => $pid,
                'user_id' => $uid,
                'tg_username' => $tgUser,
                'balance' => $balance,
                'has_bought' => $hasBought,
                'order_count' => $orderCount,
                'customer_label' => $customerLabel,
                'action' => $act,
                'action_label' => $actLabel,
                'plan_key' => $planKey,
                'plan_title' => $planTitle,
                'plan_price' => $planPrice,
                'plan_vol' => $planVol,
                'plan_days' => $planDays,
                'coupon' => $coupon,
                'discount_pct' => $discountPct,
                'after_discount' => $afterDiscount,
                'price' => $price,
                'rial' => $price * 10,
                'target' => $target,
                'source' => $source,
                'created' => $created,
                'created_fa' => $createdFa,
            ],
        ];
    }
}


function ensureUsersStepWide($db) {
    static $done = false;
    if ($done) return;
    $done = true;
    try {
        $db->exec("ALTER TABLE users MODIFY step VARCHAR(255) NOT NULL DEFAULT 'none'");
    } catch (Exception $e) {
        try {
            $db->exec("ALTER TABLE users MODIFY COLUMN step VARCHAR(255) DEFAULT 'none'");
        } catch (Exception $e2) {}
    }
}

function issueDepositInvoice($chat_id, $user_id, $amount, $db, $editMsgId = null) {
    ensureUsersStepWide($db);
    ensurePaymentPayColumns($db);
    expireStaleInvoices($db);
    $discountRand = rand(10, 190);
    $finalAmount = max(1000, $amount - $discountRand);
    $finalAmountRial = $finalAmount * 10;
    $token = generatePayToken();
    $ttl = defined('INVOICE_TTL_SEC') ? (int)INVOICE_TTL_SEC : 1200;
    $expiresAt = date('Y-m-d H:i:s', time() + $ttl);
    $paymentId = 0;

    try {
        $db->prepare("UPDATE payments SET status = 'rejected' WHERE user_id = ? AND status = 'pending' AND photo_file_id = 'AWAITING_RECEIPT'")
           ->execute([$user_id]);
        $db->prepare("INSERT INTO payments (user_id, plan_key, price, photo_file_id, target_username, action_type, coupon_code, status, pay_token, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)")
           ->execute([$user_id, (string)$amount, $finalAmount, 'AWAITING_RECEIPT', 'wallet', 'deposit', null, $token, $expiresAt]);
        $paymentId = (int)$db->lastInsertId();
    } catch (Exception $e) {
        try {
            $db->prepare("INSERT INTO payments (user_id, plan_key, price, photo_file_id, target_username, action_type, coupon_code, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')")
               ->execute([$user_id, (string)$amount, $finalAmount, 'AWAITING_RECEIPT', 'wallet', 'deposit', null]);
            $paymentId = (int)$db->lastInsertId();
        } catch (Exception $e2) {
        }
    }

    if ($paymentId > 0) {
        $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["payid:{$paymentId}", $user_id]);
    } else {
        $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["pay:deposit:{$amount}:wallet::{$finalAmount}", $user_id]);
    }

    $ttlMin = (int)ceil($ttl / 60);
    $payLink = ($token !== '' && $paymentId > 0) ? buildPayPageLink($db, $token) : '';
    $msg = "🧾 <b>فاکتور شارژ کیف پول آماده‌ست</b>\n"
         . "#️⃣ شماره فاکتور: <code>#{$paymentId}</code>\n\n"
         . "💰 مبلغ: <b>" . number_format($finalAmount) . " تومان</b>\n"
         . "🔢 به ریال: <code>{$finalAmountRial}</code>\n"
         . "⏱ مهلت پرداخت: <b>{$ttlMin} دقیقه</b>\n\n"
         . "📌 معمولاً پرداخت <b>خودکار</b> تأیید می‌شه؛ اگر طول کشید، <b>عکس فیش</b> را بفرست.\n\n"
         . "👇 <b>چطور می‌خوای پرداخت کنی؟</b>";

    $inlineButtons = [];
    if ($payLink !== '') {
        $inlineButtons[] = [['text' => '🌐 پرداخت در صفحه امن', 'url' => $payLink]];
    } else {
        $inlineButtons[] = [['text' => '🌐 پرداخت در صفحه امن', 'callback_data' => 'pay_web:' . $paymentId, 'style' => 'primary']];
    }
    $inlineButtons[] = [['text' => '💬 پرداخت داخل تلگرام', 'callback_data' => 'pay_tg:' . $paymentId, 'style' => 'primary']];
    $inlineButtons[] = [['text' => '❌ انصراف', 'callback_data' => 'pay_cancel:' . $paymentId, 'style' => 'danger']];
    $keyboard = json_encode(['inline_keyboard' => $inlineButtons], JSON_UNESCAPED_UNICODE);

    if ($editMsgId) {
        sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $editMsgId, 'text' => $msg, 'parse_mode' => 'HTML', 'reply_markup' => $keyboard]);
        rememberInvoiceMsg($db, $paymentId, $editMsgId);
    } else {
        $sent = sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => $msg, 'parse_mode' => 'HTML', 'reply_markup' => $keyboard]);
        rememberInvoiceMsg($db, $paymentId, (int)($sent['result']['message_id'] ?? 0));
    }
}

function issueInvoice($chat_id, $user_id, $planKey, $targetUser, $actionType, $plans, $db, $editMsgId = null, $couponData = null) {
    ensureUsersStepWide($db);
    ensurePaymentPayColumns($db);
    expireStaleInvoices($db);
    $p = $plans[$planKey];
    $basePrice = $p['price'];
    $couponCode = $couponData['code'] ?? '';
    $firstPurchaseNote = false;
    // ۱۰٪ تخفیف اولین خرید (فقط خرید سرویس جدید، نه تمدید)
    $act = strtolower(trim((string)$actionType));
    if (!$couponData && $act !== 'renew' && $act !== 'deposit') {
        try {
            $stHb = $db->prepare('SELECT has_bought FROM users WHERE user_id = ? LIMIT 1');
            $stHb->execute([(int)$user_id]);
            $hb = (int)($stHb->fetchColumn() ?: 0);
            if ($hb === 0) {
                $couponData = ['code' => 'FIRST10', 'discount_percent' => 10];
                $couponCode = 'FIRST10';
                $firstPurchaseNote = true;
            }
        } catch (Exception $e) {}
    }
    if ($couponData) {
        $basePrice = round($p['price'] * (1 - ($couponData['discount_percent'] / 100)));
    }

    $discountRand = rand(10, 190);
    $finalPrice = max(1000, $basePrice - $discountRand);
    $finalPriceRial = $finalPrice * 10;
    $token = generatePayToken();
    $ttl = defined('INVOICE_TTL_SEC') ? (int)INVOICE_TTL_SEC : 1200;
    $expiresAt = date('Y-m-d H:i:s', time() + $ttl);
    $paymentId = 0;

    try {
        $db->prepare("UPDATE payments SET status = 'rejected' WHERE user_id = ? AND status = 'pending' AND photo_file_id = 'AWAITING_RECEIPT'")
           ->execute([$user_id]);
        $db->prepare("INSERT INTO payments (user_id, plan_key, price, photo_file_id, target_username, action_type, coupon_code, status, pay_token, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)")
           ->execute([$user_id, $planKey, $finalPrice, 'AWAITING_RECEIPT', $targetUser, $actionType, ($couponCode !== '' ? $couponCode : null), $token, $expiresAt]);
        $paymentId = (int)$db->lastInsertId();
    } catch (Exception $e) {
        try {
            $db->prepare("INSERT INTO payments (user_id, plan_key, price, photo_file_id, target_username, action_type, coupon_code, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')")
               ->execute([$user_id, $planKey, $finalPrice, 'AWAITING_RECEIPT', $targetUser, $actionType, ($couponCode !== '' ? $couponCode : null)]);
            $paymentId = (int)$db->lastInsertId();
        } catch (Exception $e2) {
        }
    }

    // step کوتاه و پایدار — مبلغ از جدول payments خوانده می‌شود (جلوگیری از قطع شدن VARCHAR)
    if ($paymentId > 0) {
        $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["payid:{$paymentId}", $user_id]);
    } else {
        $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["pay:{$actionType}:{$planKey}:{$targetUser}:{$couponCode}:{$finalPrice}", $user_id]);
    }
    $stmt = $db->prepare('SELECT balance FROM users WHERE user_id = ?');
    $stmt->execute([$user_id]);
    $bal = (int)$stmt->fetchColumn();

    $daysTxt = $p['days'] > 0 ? "{$p['days']} روزه" : 'VIP بدون انقضا';
    $actionTitle = $actionType === 'renew' ? 'تمدید اشتراک' : 'خرید اشتراک جدید';
    $ttlMin = (int)ceil($ttl / 60);

    $payLink = ($token !== '' && $paymentId > 0) ? buildPayPageLink($db, $token) : '';
    $invoice = "🧾 <b>فاکتور {$actionTitle} آماده‌ست</b>\n"
             . "#️⃣ شماره فاکتور: <code>#{$paymentId}</code>\n\n"
             . "📦 پلن: {$p['title']} ({$daysTxt})\n"
             . "👤 نام کاربری: <code>{$targetUser}</code>\n";
    if ($couponData) {
        if (!empty($firstPurchaseNote) || (($couponData['code'] ?? '') === 'FIRST10')) {
            $invoice .= "🎁 تخفیف اولین خرید: <b>{$couponData['discount_percent']}٪</b>\n";
        } else {
            $invoice .= "🏷 کد تخفیف: <code>{$couponData['code']}</code> ({$couponData['discount_percent']}%)\n";
        }
    }
    $invoice .= "💰 مبلغ: <b>" . number_format($finalPrice) . " تومان</b>\n"
             . "🔢 به ریال: <code>{$finalPriceRial}</code>\n"
             . "💵 موجودی کیف: " . number_format($bal) . " تومان\n"
             . "⏱ مهلت پرداخت: <b>{$ttlMin} دقیقه</b>\n\n"
             . "📌 معمولاً پرداخت <b>خودکار</b> تأیید می‌شه؛ اگر طول کشید، <b>عکس فیش</b> را بفرست.\n\n"
             . "👇 <b>چطور می‌خوای پرداخت کنی؟</b>";

    $inlineButtons = [];
    if ($bal >= $finalPrice) {
        $inlineButtons[] = [['text' => '⚡️ پرداخت آنی از کیف پول', 'callback_data' => "pay_wallet:{$actionType}:{$planKey}:{$targetUser}:{$couponCode}", 'style' => 'success']];
    }
    if ($payLink !== '') {
        $inlineButtons[] = [['text' => '🌐 پرداخت در صفحه امن', 'url' => $payLink]];
    } else {
        $inlineButtons[] = [['text' => '🌐 پرداخت در صفحه امن', 'callback_data' => 'pay_web:' . $paymentId, 'style' => 'primary']];
    }
    $inlineButtons[] = [['text' => '💬 پرداخت داخل تلگرام', 'callback_data' => 'pay_tg:' . $paymentId, 'style' => 'primary']];
    // حتی با FIRST10 بتوانند کد بهتر بزنند
    if (!$couponData || (!empty($firstPurchaseNote) || ($couponCode === 'FIRST10'))) {
        $inlineButtons[] = [['text' => '🏷 کد تخفیف داری؟', 'callback_data' => "apply_coupon:{$actionType}:{$planKey}:{$targetUser}", 'style' => 'primary']];
    }
    $inlineButtons[] = [['text' => '❌ انصراف', 'callback_data' => 'pay_cancel:' . $paymentId, 'style' => 'danger']];

    $keyboard = json_encode(['inline_keyboard' => $inlineButtons], JSON_UNESCAPED_UNICODE);
    if ($editMsgId) {
        sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $editMsgId, 'text' => $invoice, 'parse_mode' => 'HTML', 'reply_markup' => $keyboard]);
        rememberInvoiceMsg($db, $paymentId, $editMsgId);
    } else {
        $sent = sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => $invoice, 'parse_mode' => 'HTML', 'reply_markup' => $keyboard]);
        rememberInvoiceMsg($db, $paymentId, (int)($sent['result']['message_id'] ?? 0));
    }
}

// رنگ‌ها از وب هنگام sendTelegram اعمال می‌شوند
// کیبورد بر اساس وضعیت دکمه‌ها (تنظیمات ربات / وب) ساخته می‌شود

/** برچسب سفارشی دکمه‌ها از وب‌پنل (settings: tg_btn_labels) */
function jet_tg_label_overrides(?PDO $dbParam = null): array {
    static $cache = null;
    if ($cache !== null) return $cache;
    $cache = [];
    global $db;
    $use = $dbParam instanceof PDO ? $dbParam : (isset($db) && $db instanceof PDO ? $db : null);
    if (!$use) return $cache;
    try {
        if (function_exists('getSetting')) {
            $raw = getSetting($use, 'tg_btn_labels', '');
        } else {
            $st = $use->prepare("SELECT setting_val FROM settings WHERE setting_key = 'tg_btn_labels' LIMIT 1");
            $st->execute();
            $raw = (string)($st->fetchColumn() ?: '');
        }
        if ($raw === '') return $cache;
        $j = json_decode($raw, true);
        if (is_array($j)) {
            foreach ($j as $k => $v) {
                $v = trim((string)$v);
                if ($v !== '') $cache[(string)$k] = $v;
            }
        }
    } catch (Throwable $e) {}
    return $cache;
}
function jet_tg_btn_label(string $id, string $default, ?PDO $dbParam = null): string {
    $o = jet_tg_label_overrides($dbParam);
    return isset($o[$id]) && $o[$id] !== '' ? $o[$id] : $default;
}

function buildMainKeyboard($db, $forUserId = 0) {
    $rows = [];

    // ۱) خرید — بزرگ، بالای همه
    if (isFeatureEnabled($db, 'btn_buy')) {
        $rows[] = [['text' => jet_tg_btn_label('main.buy', '🛍 خرید اشتراک جدید 🚀', $db)]];
    }

    // ۲) سرویس‌های من + تست رایگان (کوچک)
    $row2 = [];
    $row2[] = ['text' => jet_tg_btn_label('main.services', '👤 سرویس‌های من + تمدید', $db)];
    if (isFeatureEnabled($db, 'btn_test')) {
        $row2[] = ['text' => jet_tg_btn_label('main.test', '🎁 تست رایگان', $db)];
    }
    $rows[] = $row2;

    // ۳) کیف پول + دعوت دوست
    $row3 = [];
    if (isFeatureEnabled($db, 'btn_wallet')) {
        $row3[] = ['text' => jet_tg_btn_label('main.wallet', '💰 کیف پول و تراکنش‌ها', $db)];
    }
    if (isFeatureEnabled($db, 'btn_ref')) {
        $row3[] = ['text' => jet_tg_btn_label('main.ref', '🎁 دعوت دوست', $db)];
    }
    if ($row3) {
        $rows[] = $row3;
    }

    // ۴) راهنمای اتصال + کانال (کوچک)
    $rows[] = [
        ['text' => jet_tg_btn_label('main.app', '📱 راهنمای اتصال', $db)],
        ['text' => jet_tg_btn_label('main.channel', '📢 کانال', $db)],
    ];

    // ۵) نمایندگی + پشتیبانی
    $tail = [];
    if (function_exists('reseller_system_enabled') && reseller_system_enabled($db)) {
        if ($forUserId > 0 && function_exists('reseller_is_active') && reseller_is_active($db, (int)$forUserId)) {
            $tail[] = ['text' => jet_tg_btn_label('main.reseller', '🏪 پنل نمایندگی', $db)];
        } else {
            $tail[] = ['text' => jet_tg_btn_label('main.reseller_apply', '🏪 درخواست نمایندگی', $db)];
        }
    }
    if (isFeatureEnabled($db, 'btn_support')) {
        $tail[] = ['text' => jet_tg_btn_label('main.support', '☎️ پشتیبانی', $db)];
    }
    if ($tail) {
        $rows[] = $tail;
    }

    return json_encode([
        'keyboard' => $rows,
        'resize_keyboard' => true,
    ], JSON_UNESCAPED_UNICODE);
}
$mainKeyboard = buildMainKeyboard($db, (int)($user_id ?? 0));

$chat_id = $update['message']['chat']['id'] ?? $update['callback_query']['message']['chat']['id'] ?? null;
$text = trim($update['message']['text'] ?? '');
// کپشن عکس/مدیا (تلگرام caption جدا از text است)
if ($text === '' && !empty($update['message']['caption'])) {
    $text = trim((string)$update['message']['caption']);
}
$user_id = $update['message']['from']['id'] ?? $update['callback_query']['from']['id'] ?? null;
$username = $update['message']['from']['username'] ?? 'User';
$callback_data = $update['callback_query']['data'] ?? null;
$photo = $update['message']['photo'] ?? null;

if (!$chat_id) exit();

// مدیریت کاربر
try {
    $stmt = $db->prepare("SELECT * FROM users WHERE user_id = ?");
    $stmt->execute([$user_id]);
    $currentUser = $stmt->fetch();

// کیبورد متناسب با نقش نماینده
if (function_exists('buildMainKeyboard') && !empty($user_id)) {
    $mainKeyboard = buildMainKeyboard($db, (int)$user_id);
}

    if (!$currentUser) {
        $inviterId = null;
        if (strpos($text, '/start') === 0) {
            $parts = explode(' ', $text);
            if (isset($parts[1]) && is_numeric($parts[1]) && $parts[1] != $user_id) {
                $inviterId = (int)$parts[1];
            }
        }

        $stmt = $db->prepare("INSERT INTO users (user_id, username, balance, inviter_id, has_bought, has_used_test, total_ref_earned, step) VALUES (?, ?, 0, ?, 0, 0, 0, 'none')");
        $stmt->execute([$user_id, $username, $inviterId]);
        $currentUser = ['user_id' => $user_id, 'username' => $username, 'balance' => 0, 'inviter_id' => $inviterId, 'has_bought' => 0, 'has_used_test' => 0, 'total_ref_earned' => 0, 'step' => 'none'];

        if ($inviterId) {
            $refPct = (int)getSetting($db, 'ref_reward_percent', 10);
            $refCap = number_format((int)getSetting($db, 'ref_reward_cap', 50000));
            sendTelegram('sendMessage', [
                'chat_id' => $inviterId,
                'text' => "🎉 یه نفر با لینک تو وارد ربات شد!\nبا اولین خریدش، <b>{$refPct}٪</b> مبلغ خرید (سقف {$refCap} ت) می‌ره تو کیف پولت 💰\nدوستت مثل بقیه <b>۱۰٪ تخفیف اولین خرید</b> داره + <b>۵٪ حجم بیشتر</b> هدیه دعوت 📦",
                'parse_mode' => 'HTML'
            ]);
        }
    }
} catch (Exception $e) {
    exit();
}

// ——— لایه نمایندگی (زود — callback ادمین و دکمه‌های منو) ———
if (is_readable(__DIR__ . '/reseller_bot_handlers.php')) {
    require_once __DIR__ . '/reseller_bot_handlers.php';
}

// تنظیم یک‌باره منوی دستورات تلگرام (/start برای همه، /admin فقط ادمین)
ensureBotMenuCommands($db, false);

// بررسی عضویت در کانال
if (!isUserMember($user_id)) {
    $joinKeyboard = json_encode([
        'inline_keyboard' => [
            [['text' => '📢 عضویت در کانال تلگرام 🚀', 'url' => CHANNEL_LINK]],
            [['text' => '✅ عضو شدم / ورود به ربات', 'callback_data' => 'check_channel_join', 'style' => 'success']]
        ]
    ]);

    $forceMsg = "👋 برای شروع، یک‌بار توی <b>کانال رسمی</b> عضو شو.\n\n"
              . "آنجا خبر سرورها، کد تخفیف و آپدیت‌ها اعلام می‌شه.\n\n"
              . "بعد از عضویت، دکمه زیر رو بزن تا وارد ربات بشی 👇";

    if ($callback_data === 'check_channel_join') {
        sendTelegram('answerCallbackQuery', [
            'callback_query_id' => $update['callback_query']['id'],
            'text' => 'هنوز عضو کانال نشدی — اول عضو شو، بعد دوباره بزن 🙂',
            'show_alert' => true
        ]);
    } else {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => $forceMsg,
            'parse_mode' => 'HTML',
            'reply_markup' => $joinKeyboard
        ]);
    }
    exit();
}

// ——— سدّ سراسری: دکمه‌های خاموش حتی از کیبورد قدیمی کار نکنند + منو تازه شود ———
if (!isBotAdmin($user_id)) {
    $mainKeyboard = buildMainKeyboard($db, (int)($user_id ?? 0)); // همیشه آخرین وضعیت دکمه‌ها
    $featDeny = null;
    if ($text !== '') {
        if (isMenuKeywordHit($text, 'تست رایگان') && !isFeatureEnabled($db, 'btn_test')) {
            $featDeny = "😊 تست رایگان الان موقتاً خاموشه. کمی بعد دوباره امتحان کن یا از خرید اشتراک استفاده کن.";
        } elseif (isMenuKeywordHit($text, 'خرید اشتراک') && !isFeatureEnabled($db, 'btn_buy')) {
            $featDeny = "😊 خرید اشتراک الان موقتاً خاموشه. کمی بعد دوباره سر بزن؛ اگه فوریه از پشتیبانی بگو.";
        } elseif ((isMenuKeywordHit($text, 'کیف پول') || isMenuKeywordHit($text, 'شارژ')) && !isFeatureEnabled($db, 'btn_wallet')) {
            // فقط اگر متن شبیه منوی اصلی کیف پول است نه هر شارژ
            if (isMenuKeywordHit($text, 'کیف پول و حساب') || isMenuKeywordHit($text, 'کیف پول')) {
                $featDeny = "😊 شارژ کیف پول الان موقتاً خاموشه.";
            }
        } elseif ((isMenuKeywordHit($text, 'دعوت دوست') || isMenuKeywordHit($text, 'زیرمجموعه')) && !isFeatureEnabled($db, 'btn_ref')) {
            $featDeny = "😊 بخش دعوت فعلاً خاموشه. کمی بعد دوباره چک کن.";
        } elseif (isMenuKeywordHit($text, 'پشتیبانی') && !isFeatureEnabled($db, 'btn_support')) {
            $featDeny = "😊 پشتیبانی الان خاموشه. کمی بعد دوباره سر بزن.";
        } elseif (isMenuKeywordHit($text, 'انتقال') && !isFeatureEnabled($db, 'btn_transfer')) {
            $featDeny = "😊 انتقال اعتبار الان خاموشه.";
        }
    }
    if ($callback_data) {
        if (($callback_data === 'get_free_test' || (is_string($callback_data) && strpos($callback_data, 'test_offer:') === 0)) && !isFeatureEnabled($db, 'btn_test')) {
            $featDeny = "😊 تست رایگان الان موقتاً خاموشه.";
        } elseif (in_array($callback_data, ['main_categories'], true) && !isFeatureEnabled($db, 'btn_buy')) {
            $featDeny = "😊 خرید اشتراک الان موقتاً خاموشه.";
        } elseif (in_array($callback_data, ['charge_wallet_menu', 'my_wallet'], true) && !isFeatureEnabled($db, 'btn_wallet')) {
            // my_wallet ممکن است فقط مشاهده باشد — فقط charge را ببند
            if ($callback_data === 'charge_wallet_menu') {
                $featDeny = "😊 شارژ کیف پول الان موقتاً خاموشه.";
            }
        } elseif (in_array($callback_data, ['referral_menu'], true) && !isFeatureEnabled($db, 'btn_ref')) {
            $featDeny = "😊 بخش دعوت فعلاً خاموشه.";
        } elseif (in_array($callback_data, ['start_support', 'support_human'], true) && !isFeatureEnabled($db, 'btn_support')) {
            $featDeny = "😊 پشتیبانی الان خاموشه.";
        }
    }
    if ($featDeny !== null) {
        if ($callback_data) {
            sendTelegram('answerCallbackQuery', [
                'callback_query_id' => $update['callback_query']['id'],
                'text' => 'این بخش موقتاً غیرفعال است',
                'show_alert' => true,
            ]);
        }
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => $featDeny,
            'reply_markup' => $mainKeyboard,
        ]);
        exit();
    }
}



if ($callback_data === 'check_channel_join') {
    sendTelegram('deleteMessage', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id']
    ]);
    $text = '/start';
}

// بازیابی خودکار منو: اگر step گیر کرده و کاربر دکمه منو را زد
try {
    tryRecoverMainMenuStep($db, $currentUser, $user_id, $text, $callback_data);
} catch (Exception $e) {}

// میانبر: /menu مثل start بدون متن خوش‌آمد طولانی
if (trim($text) === '/menu' || trim($text) === 'منوی اصلی' || trim($text) === 'منو اصلی') {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $text = '/start';
}

// منوی اصلی
if (strpos($text, '/start') === 0) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    $welcome = "سلام <b>" . htmlspecialchars($username) . "</b> 👋\n"
             . "به خانواده <b>JetConfig</b> خوش اومدی 🚀\n\n"
             . "اینجا قراره اینترنتت سریع، پایدار و بی‌دردسر باشه —\n"
             . "برای یوتیوب، گیم، کار و روزمره، روی همه اپراتورها.\n\n"
             . "🎁 برای <b>اولین خریدت ۱۰٪ تخفیف</b> خودکار اعمال می‌شه\n"
             . "🧪 اول می‌تونی <b>تست رایگان</b> بگیری و کیفیت رو خودت ببینی\n"
             . "🛍 یا مستقیم بری سراغ پلن‌های به‌صرفه با <b>تحویل آنی</b>\n\n"
             . "از منوی پایین شروع کن 👇\n"
             . "هر سوالی داشتی، پشتیبانی اینجاست 💬";

    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => $welcome,
        'parse_mode' => 'HTML',
        'reply_markup' => $mainKeyboard
    ]);
    exit();
}

// ===== پاسخ ادمین به کاربر (متن یا عکس — step پاک نمی‌شود) =====
if (($text || $photo) && isBotAdmin($user_id) && strpos((string)($currentUser['step'] ?? ''), 'admin_reply:') === 0) {
    $target = (int)str_replace('admin_reply:', '', $currentUser['step']);
    if (function_exists('openSupportTicket')) {
        openSupportTicket($db, $target);
        if (function_exists('assignSupportTicket')) {
            assignSupportTicket($db, $target, $user_id);
        }
    }
    $userKb = function_exists('supportUserOpenKeyboard') ? supportUserOpenKeyboard() : null;
    $sendRes = null;

    if ($photo) {
        $fid = end($photo)['file_id'];
        $logTxt = $text !== '' ? $text : '[تصویر ادمین]';
        if (function_exists('logSupportHumanMessage')) {
            logSupportHumanMessage($db, $target, 'admin', $logTxt, $user_id, $fid);
        }
        if (function_exists('touchSupportTicket')) {
            touchSupportTicket($db, $target);
        }
        $cap = "👨‍💼 پشتیبانی JET VPN";
        if ($text !== '') {
            $cap .= "\n\n" . $text;
        }
        if (mb_strlen($cap) > 1000) {
            $cap = mb_substr($cap, 0, 1000) . "\n…";
        }
        $payload = [
            'chat_id' => $target,
            'photo' => $fid,
            'caption' => $cap,
        ];
        if ($userKb) {
            $payload['reply_markup'] = $userKb;
        }
        $sendRes = sendTelegram('sendPhoto', $payload);
    } else {
        if (function_exists('logSupportHumanMessage')) {
            logSupportHumanMessage($db, $target, 'admin', $text, $user_id, null);
        }
        if (function_exists('touchSupportTicket')) {
            touchSupportTicket($db, $target);
        }
        $replyHtml = "👨‍💼 <b>پشتیبانی JET VPN</b>\n\n" . htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
        if (mb_strlen($replyHtml) > 4000) {
            $replyHtml = mb_substr($replyHtml, 0, 4000) . "\n…";
        }
        $payload = [
            'chat_id' => $target,
            'text' => $replyHtml,
            'parse_mode' => 'HTML',
            'disable_web_page_preview' => false,
        ];
        if ($userKb) {
            $payload['reply_markup'] = $userKb;
        }
        $sendRes = sendTelegram('sendMessage', $payload);
        if (empty($sendRes['ok'])) {
            $plain = "👨‍💼 پشتیبانی JET VPN\n\n" . $text;
            if (mb_strlen($plain) > 4000) {
                $plain = mb_substr($plain, 0, 4000) . "\n…";
            }
            $payload2 = ['chat_id' => $target, 'text' => $plain];
            if ($userKb) {
                $payload2['reply_markup'] = $userKb;
            }
            $sendRes = sendTelegram('sendMessage', $payload2);
        }
    }

    if (function_exists('clearAdminBroadcastMessages')) {
        clearAdminBroadcastMessages(
            $db,
            'support',
            $target,
            $user_id,
            "🎫 تیکت کاربر <code>{$target}</code>\n\n✅ پاسخ ارسال شد — گفتگو باز است"
        );
    }
    $adminKb = function_exists('supportAdminReplyModeKeyboard')
        ? supportAdminReplyModeKeyboard($target)
        : json_encode(['inline_keyboard' => [[['text' => '⏸ ترک پاسخ (تیکت باز بماند)', 'callback_data' => 'adm_sup_leave_reply']]]]);
    if (!empty($sendRes['ok'])) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ ارسال شد به <code>{$target}</code>\nگفتگو باز است — می‌تونی ادامه بدی یا تیکت را ببندی.",
            'parse_mode' => 'HTML',
            'reply_markup' => $adminKb,
        ]);
    } else {
        $err = $sendRes['description'] ?? 'unknown';
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "⚠️ ارسال ناموفق:\n<code>" . htmlspecialchars((string)$err, ENT_QUOTES, 'UTF-8') . "</code>",
            'parse_mode' => 'HTML',
            'reply_markup' => $adminKb,
        ]);
    }
    exit();
}

// ===== پیام ادمین به کاربر خاص / همگانی (قبل از منو) =====
if (($text || $photo) && isBotAdmin($user_id) && strpos((string)($currentUser['step'] ?? ''), 'adm_msg_user|') === 0) {
    $targetUid = (int)str_replace('adm_msg_user|', '', $currentUser['step']);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if ($targetUid <= 0) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ کاربر نامعتبر.']);
        exit();
    }
    $ok = false;
    if ($photo) {
        $fid = end($photo)['file_id'];
        $cap = $text !== '' ? $text : '📨 پیام پشتیبانی';
        if (mb_strlen($cap) > 1000) $cap = mb_substr($cap, 0, 1000) . "\n…";
        $sendRes = sendTelegram('sendPhoto', [
            'chat_id' => $targetUid,
            'photo' => $fid,
            'caption' => $cap,
        ]);
        $ok = !empty($sendRes['ok']);
        if (function_exists('logSupportHumanMessage')) {
            logSupportHumanMessage($db, $targetUid, 'admin', $text !== '' ? $text : '[تصویر]', $user_id, $fid);
        }
    } else {
        $body = trim((string)$text);
        if ($body === '') {
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ پیام خالی.']);
            exit();
        }
        $msg = "📨 <b>پیام پشتیبانی</b>\n──────────────────\n" . htmlspecialchars($body, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
        if (function_exists('notifyUserFromBot')) {
            $ok = notifyUserFromBot($targetUid, $msg, [
                'inline_keyboard' => [[['text' => '💬 پشتیبانی', 'callback_data' => 'start_support']]]
            ]);
            if (!$ok) $ok = notifyUserFromBot($targetUid, $msg);
        } else {
            $sendRes = sendTelegram('sendMessage', ['chat_id' => $targetUid, 'text' => $msg, 'parse_mode' => 'HTML']);
            $ok = !empty($sendRes['ok']);
        }
        if ($ok && function_exists('logSupportHumanMessage')) {
            logSupportHumanMessage($db, $targetUid, 'admin', $body, $user_id, null);
        }
    }
    if ($ok) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ پیام برای کاربر <code>{$targetUid}</code> ارسال شد.",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '👤 بازگشت به کاربر', 'callback_data' => 'adm_user_view:' . $targetUid, 'style' => 'primary']],
                [['text' => '✉️ پیام دیگر', 'callback_data' => 'adm_msg_user:' . $targetUid]],
            ]], JSON_UNESCAPED_UNICODE)
        ]);
    } else {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "⚠️ ارسال ناموفق بود (کاربر ممکن است ربات را بلاک کرده باشد).",
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '👤 بازگشت به کاربر', 'callback_data' => 'adm_user_view:' . $targetUid]],
            ]], JSON_UNESCAPED_UNICODE)
        ]);
    }
    exit();
}

if ($text && isBotAdmin($user_id) && (string)($currentUser['step'] ?? '') === 'admin_broadcast') {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $all = $db->query("SELECT user_id FROM users")->fetchAll(PDO::FETCH_COLUMN);
    $okN = 0;
    $failN = 0;
    foreach ($all as $u) {
        $res = sendTelegram('sendMessage', [
            'chat_id' => $u,
            'text' => "🔔 <b>اطلاعیه:</b>\n\n" . htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'),
            'parse_mode' => 'HTML',
        ]);
        if (!empty($res['ok'])) $okN++; else $failN++;
        usleep(35000);
    }
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ همگانی ارسال شد.\nموفق: <b>{$okN}</b> | ناموفق: <b>{$failN}</b>",
        'parse_mode' => 'HTML',
    ]);
    exit();
}

// دکمه ترکیبی: اپ + راهنمای اتصال
if (isIdleStep($currentUser) && (
    isMenuKeywordHit($text, 'اپ و راهنمای اتصال')
    || isMenuKeywordHit($text, 'دانلود اپلیکیشن')
    || isMenuKeywordHit($text, 'دانلود اپ')
    || isMenuKeywordHit($text, 'راهنمای اتصال')
    || isMenuKeywordHit($text, 'راهنما', 40)
)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $app_text = "📱 <b>اپ و راهنمای اتصال</b>\n\n"
              . "<b>۱) روش پیشنهادی — JET VPN</b>\n"
              . "• از دکمه زیر آخرین نسخه را بگیر و نصب کن\n"
              . "• نام کاربری و رمز را از «سرویس‌های من» کپی کن\n"
              . "• در اپ وارد شو و با یک لمس وصل شو ⚡️\n\n"
              . "<b>۲) با اپ‌های دیگر (لینک ساب → Import)</b>\n\n"
              . "🤖 <b>اندروید</b> (گوگل‌پلی)\n"
              . "• <a href=\"https://majid6064.ir/download/\">v2rayNG</a>\n"
              . "• <a href=\"https://play.google.com/store/apps/details?id=app.hiddify.com\">Hiddify</a>\n"
              . "• <a href=\"https://majid6064.ir/download/\">Happ</a>\n"
              . "• <a href=\"https://play.google.com/store/apps/details?id=dev.hexasoftware.v2box\">V2Box</a>\n\n"
              . "🍎 <b>آیفون</b> (اپ‌استور — Streisand پیشنهادی)\n"
              . "• <a href=\"https://apps.apple.com/app/streisand/id6450534064\">Streisand</a>\n"
              . "• <a href=\"https://apps.apple.com/app/shadowrocket/id932747118\">Shadowrocket</a>\n"
              . "• <a href=\"https://apps.apple.com/app/happ-proxy-utility/id6504287215\">Happ</a>\n"
              . "• <a href=\"https://apps.apple.com/us/app/v2box-v2ray-client/id6446814690\">V2Box</a>\n\n"
              . "💻 <b>ویندوز</b> (گیت‌هاب)\n"
              . "• <a href=\"https://github.com/2dust/v2rayN/releases\">v2rayN</a>\n"
              . "• <a href=\"https://github.com/hiddify/hiddify-app/releases\">Hiddify</a>\n"
              . "• <a href=\"https://github.com/Happ-proxy/happ-desktop/releases\">Happ</a>\n\n"
              . "اگه گیر کردی، از منو <b>پشتیبانی</b> بزن — کمکت می‌کنیم 💬";

    $inline = [
        [['text' => '📥 دانلود اپ‌ها', 'url' => DIRECT_DOWNLOAD_URL]],
        [['text' => '📢 کانال رسمی اطلاع‌رسانی', 'url' => 'https://t.me/jetconfig11']]
    ];

    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => $app_text,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $inline], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if (isIdleStep($currentUser) && (
    isMenuKeywordHit($text, 'کانال آموزش')
    || isMenuKeywordHit($text, 'اطلاع‌رسانی')
    || isMenuKeywordHit($text, 'اطلاع رسانی')
    || isMenuKeywordHit($text, 'کانال')
)) {
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "📢 <b>کانال آموزش و اطلاع‌رسانی JetConfig</b>\n\n"
                . "آخرین اخبار سرورها، آموزش اتصال و تخفیف‌ها رو از کانال دنبال کن 👇",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '📢 عضویت در کانال', 'url' => 'https://t.me/jetconfig11']],
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

// شماره کارت از منوی اصلی حذف شد؛ در صورت تایپ دستی همچنان نمایش داده می‌شود
if (isIdleStep($currentUser) && isMenuKeywordHit($text, 'شماره کارت')) {
    $card = getActiveBankCard($db);
    $cardInfo = "💳 <b>کارت واریز</b>\n\n"
              . "▫️ شماره کارت: <code>{$card['card_number']}</code> (برای کپی لمس کن)\n"
              . "▫️ به نام: <b>{$card['card_holder']}</b>\n"
              . "▫️ بانک: <b>{$card['bank_name']}</b>\n\n"
              . "💡 برای خرید یا شارژ کیف پول از منوی اصلی اقدام کن. مبلغ رو دقیقاً همون عددی بزن که ربات می‌گه.";
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => $cardInfo,
        'parse_mode' => 'HTML'
    ]);
    exit();
}

if ((isIdleStep($currentUser) && isMenuKeywordHit($text, 'پشتیبانی')) || $callback_data === 'start_support') {
    if (!isFeatureEnabled($db, 'btn_support') && !isBotAdmin($user_id)) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "😊 پشتیبانی الان خاموشه. کمی بعد دوباره سر بزن.", 'reply_markup' => $mainKeyboard]);
        exit();
    }
    $db->prepare("UPDATE users SET step = 'support_message' WHERE user_id = ?")->execute([$user_id]);
    $supportKb = json_encode(['inline_keyboard' => [
        [['text' => '👨‍💼 پشتیبانی انسانی', 'callback_data' => 'support_human', 'style' => 'primary']],
        [['text' => '❌ انصراف', 'callback_data' => 'cancel_order', 'style' => 'danger']]
    ]], JSON_UNESCAPED_UNICODE);

    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "🤖 <b>پشتیبانی JET VPN</b>\n\n"
            . "سوالت رو همین‌جا بفرست تا دستیار جواب بده.\n"
            . "برای موضوع مالی یا پیگیری خاص، <b>پشتیبانی انسانی</b> رو بزن.\n\n"
            . "متن یا عکس فیش/مدرک هم می‌تونی بفرستی.",
        'parse_mode' => 'HTML',
        'reply_markup' => $supportKb
    ]);
    exit();
}

if ((isIdleStep($currentUser) && (isMenuKeywordHit($text, 'زیرمجموعه') || isMenuKeywordHit($text, 'دعوت دوست'))) || $callback_data === 'referral_menu') {
    if (!isFeatureEnabled($db, 'btn_ref') && !isBotAdmin($user_id)) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "😊 بخش دعوت فعلاً خاموشه. کمی بعد دوباره چک کن.", 'reply_markup' => $mainKeyboard]);
        exit();
    }
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    $stmt = $db->prepare("SELECT COUNT(*) FROM users WHERE inviter_id = ?");
    $stmt->execute([$user_id]);
    $totalInvited = $stmt->fetchColumn();

    $stmt = $db->prepare("SELECT COUNT(*) FROM users WHERE inviter_id = ? AND has_bought = 1");
    $stmt->execute([$user_id]);
    $boughtCount = $stmt->fetchColumn();

    $refPct = (int)getSetting($db, 'ref_reward_percent', 10);
    $refCap = (int)getSetting($db, 'ref_reward_cap', 50000);
    $inviteeVolPct = (int)getSetting($db, 'ref_invitee_vol_percent', 5);
    $totalEarned = (int)($currentUser['total_ref_earned'] ?? 0);

    $botInfo = sendTelegram('getMe');
    $botUsername = $botInfo['result']['username'] ?? 'JetConfig1bot';
    $refLink = "https://t.me/{$botUsername}?start={$user_id}";
    $shareText = "🚀 اینترنت پرسرعت با JET — تست رایگان بگیر:\n{$refLink}";
    $shareUrl = 'https://t.me/share/url?url=' . rawurlencode($refLink) . '&text=' . rawurlencode($shareText);

    $refMsg = "🎁 <b>دعوت دوست + هدیه</b>\n\n"
            . "دوستت با لینک تو بیاد و <b>اولین خرید</b> رو بزنه:\n"
            . "• <b>تو:</b> {$refPct}٪ مبلغ همون خرید (سقف " . number_format($refCap) . " ت) تو کیف پول 💰\n"
            . "• <b>دوستت:</b> مثل همه <b>۱۰٪ تخفیف اولین خرید</b> + <b>{$inviteeVolPct}٪ حجم بیشتر</b> هدیه مخصوص دعوت 📦\n\n"
            . "📊 آمار تو:\n"
            . "• دعوت‌شده‌ها: <b>{$totalInvited}</b> نفر\n"
            . "• خرید موفق: <b>{$boughtCount}</b> نفر\n"
            . "• درآمد کل: <b>" . number_format($totalEarned) . "</b> تومان\n\n"
            . "🔗 لینک اختصاصیت:\n<code>{$refLink}</code>";

    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '📤 ارسال برای دوست در تلگرام', 'url' => $shareUrl]],
            [['text' => '📋 کپی لینک (نگه دار و کپی کن)', 'copy_text' => ['text' => $refLink]]],
        ]
    ], JSON_UNESCAPED_UNICODE);

    // copy_text ممکن است در کلاینت‌های قدیمی نباشد — fallback بدون آن
    $kbFallback = json_encode([
        'inline_keyboard' => [
            [['text' => '📤 ارسال برای دوست در تلگرام', 'url' => $shareUrl]],
        ]
    ], JSON_UNESCAPED_UNICODE);

    $sent = sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => $refMsg,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb,
        'disable_web_page_preview' => true,
    ]);
    if (empty($sent['ok'])) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => $refMsg,
            'parse_mode' => 'HTML',
            'reply_markup' => $kbFallback,
            'disable_web_page_preview' => true,
        ]);
    }
    exit();
}

if ((isIdleStep($currentUser) && isMenuKeywordHit($text, 'کیف پول')) || $callback_data === 'my_wallet') {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    $stmt = $db->prepare("SELECT balance FROM users WHERE user_id = ?");
    $stmt->execute([$user_id]);
    $userBalance = number_format((int)$stmt->fetchColumn());
    $refPct = (int)getSetting($db, 'ref_reward_percent', 10);
    $refCap = number_format((int)getSetting($db, 'ref_reward_cap', 50000));

    // چند پرداخت اخیر برای شفافیت
    $payPreview = '';
    try {
        $stPay = $db->prepare("SELECT id, plan_key, price, action_type, status, created_at FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT 5");
        $stPay->execute([$user_id]);
        $pays = $stPay->fetchAll(PDO::FETCH_ASSOC) ?: [];
        if ($pays) {
            $payPreview = "\n\n🧾 <b>آخرین پرداخت‌ها</b>\n";
            foreach ($pays as $pp) {
                $st = (string)($pp['status'] ?? '');
                $stIcon = $st === 'approved' ? '✅' : ($st === 'pending' ? '⏳' : '•');
                $act = (string)($pp['action_type'] ?? 'pay');
                $actFa = $act === 'renew' ? 'تمدید' : ($act === 'deposit' ? 'شارژ کیف' : ($act === 'new' ? 'خرید' : $act));
                $pk = htmlspecialchars((string)($pp['plan_key'] ?? '-'));
                $pr = number_format((int)($pp['price'] ?? 0));
                $payPreview .= "{$stIcon} #{$pp['id']} {$actFa} · {$pk} · {$pr} ت\n";
            }
            $payPreview .= "<i>جزئیات کامل در «تراکنش‌ها»</i>";
        }
    } catch (Throwable $e) {
        $payPreview = '';
    }

    $walletMsg = "💰 <b>کیف پول و تراکنش‌ها</b>\n\n"
               . "👤 شناسه: <code>{$user_id}</code>\n"
               . "💵 موجودی: <b>{$userBalance} تومان</b>\n\n"
               . "با موجودی می‌تونی خرید آنی بزنی. با «دعوت دوست» هم تا {$refPct}٪ خرید دوستت (سقف {$refCap} ت) می‌گیری 🎁"
               . $payPreview;

    $walletKeyboard = json_encode([
        'inline_keyboard' => [
            [['text' => '➕ شارژ و افزایش موجودی 💳', 'callback_data' => 'charge_wallet_menu', 'style' => 'success']],
            [['text' => '📜 تراکنش‌ها (کیف + پرداخت‌ها)', 'callback_data' => 'wallet_history']],
            [['text' => '🔄 انتقال اعتبار به کاربر دیگر 👥', 'callback_data' => 'transfer_balance_start', 'style' => 'primary']],
            [['text' => '🎁 دعوت دوست + هدیه', 'callback_data' => 'referral_menu']]
        ]
    ], JSON_UNESCAPED_UNICODE);

    if ($callback_data) {
        sendTelegram('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $update['callback_query']['message']['message_id'],
            'text' => $walletMsg,
            'parse_mode' => 'HTML',
            'reply_markup' => $walletKeyboard
        ]);
    } else {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => $walletMsg,
            'parse_mode' => 'HTML',
            'reply_markup' => $walletKeyboard
        ]);
    }
    exit();
}

// Phase 2+3: تاریخچه تراکنش‌های کیف پول کاربر (با فیلتر)
if ($callback_data === 'wallet_history' || ($callback_data && strpos($callback_data, 'wallet_history:') === 0)) {
    $filter = 'all';
    if ($callback_data !== 'wallet_history') {
        $filter = str_replace('wallet_history:', '', $callback_data);
        $allowed = ['all', 'credit', 'debit', 'deposit', 'purchase', 'transfer'];
        if (!in_array($filter, $allowed, true)) {
            $filter = 'all';
        }
    }
    $histMsg = formatWalletLedgerMessageFiltered($db, $user_id, $filter, 12);
    // پرداخت‌های سرویس (خرید/تمدید/شارژ) جدا از ledger کیف
    try {
        $stP = $db->prepare("SELECT id, plan_key, price, action_type, status, created_at FROM payments WHERE user_id = ? ORDER BY id DESC LIMIT 10");
        $stP->execute([$user_id]);
        $rowsP = $stP->fetchAll(PDO::FETCH_ASSOC) ?: [];
        if ($rowsP) {
            $histMsg .= "\n\n━━━━━━━━━━━━\n🧾 <b>پرداخت‌های اشتراک</b>\n";
            foreach ($rowsP as $pp) {
                $st = (string)($pp['status'] ?? '');
                $stIcon = $st === 'approved' ? '✅' : ($st === 'pending' ? '⏳' : ($st === 'cancelled' ? '❌' : '•'));
                $act = (string)($pp['action_type'] ?? '');
                $actFa = $act === 'renew' ? 'تمدید' : ($act === 'deposit' ? 'شارژ کیف' : ($act === 'new' ? 'خرید' : $act));
                $pk = htmlspecialchars((string)($pp['plan_key'] ?? '-'));
                $pr = number_format((int)($pp['price'] ?? 0));
                $dt = htmlspecialchars((string)($pp['created_at'] ?? ''));
                $histMsg .= "{$stIcon} #{$pp['id']} {$actFa} · {$pk} · <b>{$pr}</b> ت\n<i>{$dt}</i>\n";
            }
        }
    } catch (Throwable $e) {}
    $kb = json_encode([
        'inline_keyboard' => [
            [
                ['text' => ($filter === 'all' ? '• همه' : 'همه'), 'callback_data' => 'wallet_history:all'],
                ['text' => ($filter === 'credit' ? '• واریز' : 'واریز'), 'callback_data' => 'wallet_history:credit'],
                ['text' => ($filter === 'debit' ? '• برداشت' : 'برداشت'), 'callback_data' => 'wallet_history:debit'],
            ],
            [
                ['text' => ($filter === 'deposit' ? '• شارژ' : 'شارژ'), 'callback_data' => 'wallet_history:deposit'],
                ['text' => ($filter === 'purchase' ? '• خرید' : 'خرید'), 'callback_data' => 'wallet_history:purchase'],
                ['text' => ($filter === 'transfer' ? '• انتقال' : 'انتقال'), 'callback_data' => 'wallet_history:transfer'],
            ],
            [['text' => '🔙 بازگشت به کیف پول', 'callback_data' => 'my_wallet', 'style' => 'danger']]
        ]
    ], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $histMsg,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data === 'transfer_balance_start') {
    if (!isFeatureEnabled($db, 'btn_transfer') && !isBotAdmin($user_id)) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => '⚠️ امکان انتقال اعتبار موقتاً غیرفعال است.', 'show_alert' => true]);
        exit();
    }
    $stmt = $db->prepare("SELECT balance FROM users WHERE user_id = ?");
    $stmt->execute([$user_id]);
    $bal = (int)$stmt->fetchColumn();

    if ($bal < 5000) {
        sendTelegram('answerCallbackQuery', [
            'callback_query_id' => $update['callback_query']['id'],
            'text' => '❌ حداقل موجودی برای انتقال اعتبار ۵,۰۰۰ تومان است.',
            'show_alert' => true
        ]);
        exit();
    }

    $db->prepare("UPDATE users SET step = 'transfer_ask_target' WHERE user_id = ?")->execute([$user_id]);
    $cancelBtn = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'my_wallet', 'style' => 'danger']]]]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🔄 <b>انتقال اعتبار</b>\n\nشناسه عددی (User ID) گیرنده رو بفرست.\n\n💡 طرف مقابل شناسه‌ش رو تو بخش کیف پول می‌بینه.",
        'parse_mode' => 'HTML',
        'reply_markup' => $cancelBtn
    ]);
    exit();
}

if ($text && $currentUser['step'] === 'transfer_ask_target') {
    $targetId = (int)preg_replace('/[^0-9]/', '', $text);

    if ($targetId == $user_id) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "⚠️ شما نمی‌توانید به حساب خودتان وجه انتقال دهید!"]);
        exit();
    }

    $stmt = $db->prepare("SELECT user_id, username FROM users WHERE user_id = ?");
    $stmt->execute([$targetId]);
    $targetUser = $stmt->fetch();

    if (!$targetUser) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ کاربری با این شناسه در ربات یافت نشد! کاربر مقصد باید حداقل یک‌بار دستور /start را در ربات زده باشد."]);
        exit();
    }

    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["transfer_ask_amount:{$targetId}", $user_id]);
    $cancelBtn = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'my_wallet', 'style' => 'danger']]]]);

    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "👤 گیرنده: <b>" . htmlspecialchars($targetUser['username'] ?? 'کاربر') . "</b> (<code>{$targetId}</code>)\n\n💰 مبلغ انتقال به تومان رو بفرست:",
        'parse_mode' => 'HTML',
        'reply_markup' => $cancelBtn
    ]);
    exit();
}

if ($text && strpos($currentUser['step'], 'transfer_ask_amount:') === 0) {
    $targetId = (int)str_replace('transfer_ask_amount:', '', $currentUser['step']);
    $amount = (int)preg_replace('/[^0-9]/', '', $text);

    $stmt = $db->prepare("SELECT balance FROM users WHERE user_id = ?");
    $stmt->execute([$user_id]);
    $currentBal = (int)$stmt->fetchColumn();

    if ($amount < 5000) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "⚠️ حداقل مبلغ انتقال ۵,۰۰۰ تومان است."]);
        exit();
    }

    if ($currentBal < $amount) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ موجودی کیف پول شما برای انتقال این مبلغ کافی نیست!\nموجودی شما: " . number_format($currentBal) . " تومان"]);
        exit();
    }

    $tr = transferWalletBalance($db, $user_id, $targetId, $amount, 'انتقال کیف پول');
    if (empty($tr['ok'])) {
        $err = $tr['error'] ?? 'unknown';
        if ($err === 'insufficient') {
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ موجودی کافی نیست."]);
        } else {
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ انتقال انجام نشد. دوباره تلاش کنید."]);
        }
        exit();
    }
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    $senderMsg = "✅ <b>انتقال انجام شد</b>\n"
               . "──────────────────\n"
               . "👤 گیرنده: <code>{$targetId}</code>\n"
               . "💰 مبلغ: <b>" . number_format($amount) . " تومان</b>\n"
               . "💵 مانده کیف پولت: <b>" . number_format($currentBal - $amount) . " تومان</b>";

    $receiverMsg = "🎁 <b>شارژ کیف پولت رسید!</b>\n"
                 . "──────────────────\n"
                 . "👤 از طرف: <code>{$user_id}</code>\n"
                 . "💰 مبلغ: <b>" . number_format($amount) . " تومان</b>\n"
                 . "به موجودیت اضافه شد — می‌تونی خرید آنی بزنی ⚡️";

    sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => $senderMsg, 'parse_mode' => 'HTML']);
    sendTelegram('sendMessage', ['chat_id' => $targetId, 'text' => $receiverMsg, 'parse_mode' => 'HTML']);
    exit();
}

if ($callback_data === 'charge_wallet_menu') {
    if (!isFeatureEnabled($db, 'btn_wallet') && !isBotAdmin($user_id)) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => '⚠️ امکان شارژ کیف پول موقتاً غیرفعال است.', 'show_alert' => true]);
        exit();
    }
    $keyboard = json_encode([
        'inline_keyboard' => [
            [['text' => '💵 ۵۰,۰۰۰ تومان', 'callback_data' => 'deposit_50000'], ['text' => '💵 ۱۰۰,۰۰۰ تومان', 'callback_data' => 'deposit_100000']],
            [['text' => '💵 ۲۰۰,۰۰۰ تومان', 'callback_data' => 'deposit_200000'], ['text' => '💵 ۵۰۰,۰۰۰ تومان', 'callback_data' => 'deposit_500000']],
            [['text' => '✏️ مبلغ دلخواه', 'callback_data' => 'deposit_custom']],
            [['text' => '🔙 بازگشت به کیف پول', 'callback_data' => 'my_wallet', 'style' => 'danger']]
        ]
    ]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "💳 <b>شارژ کیف پول</b>\n\nیکی از مبالغ زیر رو انتخاب کن، یا <b>مبلغ دلخواه</b> بزن:",
        'parse_mode' => 'HTML',
        'reply_markup' => $keyboard
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'deposit_') === 0 && $callback_data !== 'deposit_custom') {
    $amount = (int)str_replace('deposit_', '', $callback_data);
    issueDepositInvoice($chat_id, $user_id, $amount, $db, $update['callback_query']['message']['message_id']);
    exit();
}

if ($callback_data === 'deposit_custom') {
    $db->prepare("UPDATE users SET step = 'ask_custom_deposit' WHERE user_id = ?")->execute([$user_id]);
    $cancelBtn = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'my_wallet', 'style' => 'danger']]]]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "✏️ <b>مبلغ شارژ</b>\n\nمبلغ مورد نظرت رو به <b>تومان</b> بفرست (حداقل ۲۰٬۰۰۰ تومان):",
        'parse_mode' => 'HTML',
        'reply_markup' => $cancelBtn
    ]);
    exit();
}

if ($text && $currentUser['step'] === 'ask_custom_deposit') {
    $amount = (int)preg_replace('/[^0-9]/', '', $text);
    if ($amount < 20000) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "⚠️ حداقل شارژ ۲۰٬۰۰۰ تومانه. یه مبلغ بالاتر بفرست:"
        ]);
        exit();
    }
    issueDepositInvoice($chat_id, $user_id, $amount, $db);
    exit();
}

if ((isIdleStep($currentUser) && isMenuKeywordHit($text, 'تست رایگان')) || $callback_data === 'get_free_test' || (is_string($callback_data) && strpos($callback_data, 'test_offer:') === 0)) {
    if (!isFeatureEnabled($db, 'btn_test') && !isBotAdmin($user_id)) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "😊 تست رایگان الان موقتاً خاموشه. کمی بعد دوباره امتحان کن یا از خرید اشتراک استفاده کن.", 'reply_markup' => $mainKeyboard]);
        exit();
    }
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    if (!function_exists('testOffersListVisible')) {
        // سازگاری اگر فایل lib نباشد: رفتار قبلی تک‌تست
        if ($currentUser['has_used_test'] == 1) {
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => "😊 تست رایگانت رو قبلاً گرفتی.\n\nبرای ادامه با سرعت بالا، از <b>🛍 خرید اشتراک جدید</b> استفاده کن — پلن‌های به‌صرفه و تحویل آنی 🚀",
                'parse_mode' => 'HTML'
            ]);
            exit();
        }
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "⏳ دارم تست اختصاصیت رو می‌سازم... چند لحظه صبر کن ✨"]);
        $testUsername = 'test_' . $user_id . '_' . rand(10, 99);
        $testPassword = rand(1000, 9999);
        $testPanel = getTestPanel($db);
        $res = createPasargadUser($testUsername, 0.1, 1, $testPanel);
        if ($res && is_array($res) && empty($res['_error']) && isset($res['subscription_url'])) {
            $subUrl = normalizeSubscriptionUrl($res['subscription_url'], $testPanel);
            $db->prepare("UPDATE users SET has_used_test = 1 WHERE user_id = ?")->execute([$user_id]);
            insertBotOrder($db, $user_id, $testUsername, $testPassword, $subUrl, 0.1, 1, (int)($testPanel['id'] ?? 0), 'monthly', 'test_free');
            $qrUrl = getQRCodeUrl($subUrl);
            $dlApp = defined('DIRECT_DOWNLOAD_URL') ? DIRECT_DOWNLOAD_URL : 'https://github.com/majidbusy09-blip/jetconfig-vpn/releases';
            $offerTitle = isset($selectedOffer) ? trim((string)($selectedOffer['title'] ?? '')) : 'تست رایگان';
            $offerCat = isset($selectedOffer) ? trim((string)($selectedOffer['cat_key'] ?? '')) : '';
            $typeLine = $offerTitle !== '' ? ("📦 نوع تست: <b>" . htmlspecialchars($offerTitle) . "</b>" . ($offerCat !== '' ? " <code>(" . htmlspecialchars($offerCat) . ")</code>" : '') . "\n\n") : '';
            $testSuccessMsg = "🎁 <b>تست رایگان آماده است!</b>\n\n"
                        . $typeLine
                        . "👤 نام کاربری: <code>{$testUsername}</code>\n"
                        . "🔑 رمز: <code>{$testPassword}</code>\n\n"
                        . "1️⃣ با اپ اختصاصی <a href=\"{$dlApp}\">JET VPN</a> رو نصب کن (ساده‌ترین راه):\n"
                        . "👉 {$dlApp}\n\n"
                        . "با همین نام کاربری و رمز وارد شو و سرعت رو تست کن.\n\n"
                        . "2️⃣ یا با برنامه‌های دیگه:\n"
                        . (function_exists('appAndroidDownloadHtml') ? appAndroidDownloadHtml() . "\n" : "")
                        . "لینک اشتراک رو کپی کن و داخل برنامه Import کن:\n"
                        . "🔗 لینک اتصال:\n<code>{$subUrl}</code>\n\n"
                        . "اگه سرعت و پایداری خوب بود، از منوی ربات «خرید اشتراک» بزن و بدون قطعی ادامه بده 🚀\n\n"
                        . "سوال داشتی؟ پشتیبانی همین‌جاست.";
            $dl_inline = array_merge(
                serviceInfoChipRow(remainingTimeChipLabel('۲۴ ساعت'), remainingVolumeChipLabel(0.1, 0)),
                [[['text' => '🛍 خرید اشتراک جدید', 'callback_data' => 'main_categories']]]
            );
            sendTelegram('sendPhoto', [
                'chat_id' => $chat_id,
                'photo' => $qrUrl,
                'caption' => $testSuccessMsg,
                'parse_mode' => 'HTML',
                'reply_markup' => json_encode(['inline_keyboard' => $dl_inline])
            ]);
        } else {
            $errDetail = 'نامشخص';
            if (is_array($res)) {
                $errDetail = ($res['_error'] ?? 'error') . ' | ' . ($res['detail'] ?? json_encode($res, JSON_UNESCAPED_UNICODE));
            } elseif ($res === false) {
                $errDetail = 'false (احتمالاً توکن یا اتصال)';
            }
            sendTelegram('sendMessage', [
                'chat_id' => ADMIN_ID,
                'text' => "⚠️ <b>خطا در ساخت تست رایگان</b>\n\nکاربر: <code>{$user_id}</code>\nیوزرنیم تست: <code>{$testUsername}</code>\n\nجزئیات:\n<code>" . htmlspecialchars(substr($errDetail, 0, 500)) . "</code>",
                'parse_mode' => 'HTML'
            ]);
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => "😅 الان نتونستیم تست رو بسازیم.\nیه کم دیگه دوباره امتحان کن؛ اگه باز نشد از <b>پشتیبانی</b> بگو تا کمکت کنیم."
            ]);
        }
        exit();
    }

    // --- مسیر جدید: تست per دسته ---
    $selectedOffer = null;
    if (is_string($callback_data) && strpos($callback_data, 'test_offer:') === 0) {
        $oid = (int)substr($callback_data, strlen('test_offer:'));
        $selectedOffer = $oid > 0 ? testOfferGet($db, $oid) : null;
        if (!$selectedOffer || !(int)($selectedOffer['is_active'] ?? 0)) {
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => "این نوع تست الان فعال نیست. از منوی اصلی دوباره «تست رایگان» را بزن.",
                'reply_markup' => $mainKeyboard
            ]);
            exit();
        }
    }

    $visible = testOffersListVisible($db);
    if (!$selectedOffer) {
        if (count($visible) === 0) {
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => "😊 الان هیچ تست فعالی در دسترس نیست. کمی بعد دوباره سر بزن یا از <b>خرید اشتراک</b> استفاده کن.",
                'parse_mode' => 'HTML',
                'reply_markup' => $mainKeyboard
            ]);
            exit();
        }
        if (count($visible) === 1) {
            $selectedOffer = $visible[0];
        } else {
            $rows = [];
            foreach ($visible as $vo) {
                $used = testOfferUserHasUsed($db, (int)$user_id, (int)$vo['id']);
                $label = testOfferButtonLabel($vo);
                if ($used) {
                    $label = '✅ ' . $label . ' (گرفته‌شده)';
                }
                $rows[] = [[
                    'text' => $label,
                    'callback_data' => 'test_offer:' . (int)$vo['id'],
                    'style' => $used ? 'primary' : 'success',
                ]];
            }
            $rows[] = [['text' => '🔙 انصراف', 'callback_data' => 'cancel_order', 'style' => 'danger']];
            $msg = "🎁 <b>کدام نوع تست را می‌خواهی؟</b>\n\n"
                 . "هر تست مربوط به یک دسته از پلن‌هاست تا کیفیت همان مسیر را ببینی.\n"
                 . "از هر نوع فقط یک‌بار می‌توانی تست بگیری.";
            if ($callback_data) {
                adminSendOrEditText($chat_id, $update, $msg, json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE));
            } else {
                sendTelegram('sendMessage', [
                    'chat_id' => $chat_id,
                    'text' => $msg,
                    'parse_mode' => 'HTML',
                    'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
                ]);
            }
            exit();
        }
    }

    $offerId = (int)($selectedOffer['id'] ?? 0);
    $catKey = (string)($selectedOffer['cat_key'] ?? 'monthly');
    if ($offerId > 0 && testOfferUserHasUsed($db, (int)$user_id, $offerId)) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "😊 تست این دسته را قبلاً گرفتی.\n\nاگر نوع دیگری فعال است از «تست رایگان» دوباره وارد شو، یا از <b>🛍 خرید اشتراک جدید</b> ادامه بده.",
            'parse_mode' => 'HTML'
        ]);
        exit();
    }

    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "⏳ دارم تست اختصاصیت رو می‌سازم... چند لحظه صبر کن ✨"
    ]);

    $vol = (float)($selectedOffer['volume_gb'] ?? 0.1);
    if ($vol <= 0) {
        $vol = 0.1;
    }
    $days = (int)($selectedOffer['days'] ?? 1);
    if ($days < 0) {
        $days = 1;
    }
    $panelId = (int)($selectedOffer['panel_id'] ?? 0);
    $testPanel = $panelId > 0 ? getPanelById($panelId, $db) : getTestPanel($db);
    $testUsername = 'test_' . $user_id . '_' . rand(10, 99);
    $testPassword = rand(1000, 9999);
    $planKey = function_exists('testOfferPlanKey') ? testOfferPlanKey($selectedOffer) : ('test_free_' . $catKey);

    $res = createPasargadUser($testUsername, $vol, $days, $testPanel);

    if ($res && is_array($res) && empty($res['_error']) && isset($res['subscription_url'])) {
        $subUrl = normalizeSubscriptionUrl($res['subscription_url'], $testPanel);
        $oid = insertBotOrder($db, $user_id, $testUsername, $testPassword, $subUrl, $vol, $days, (int)($testPanel['id'] ?? 0), $catKey, $planKey);
        testOfferMarkUsed($db, (int)$user_id, $offerId, $catKey, $oid > 0 ? $oid : null);

        $qrUrl = getQRCodeUrl($subUrl);
        $dlApp = defined('DIRECT_DOWNLOAD_URL') ? DIRECT_DOWNLOAD_URL : 'https://github.com/majidbusy09-blip/jetconfig-vpn/releases';
        $offerTitle = isset($selectedOffer) ? trim((string)($selectedOffer['title'] ?? '')) : 'تست رایگان';
            $offerCat = isset($selectedOffer) ? trim((string)($selectedOffer['cat_key'] ?? '')) : '';
            $typeLine = $offerTitle !== '' ? ("📦 نوع تست: <b>" . htmlspecialchars($offerTitle) . "</b>" . ($offerCat !== '' ? " <code>(" . htmlspecialchars($offerCat) . ")</code>" : '') . "\n\n") : '';
            $testSuccessMsg = "🎁 <b>تست رایگان آماده است!</b>\n\n"
                        . $typeLine
                        . "👤 نام کاربری: <code>{$testUsername}</code>\n"
                        . "🔑 رمز: <code>{$testPassword}</code>\n\n"
                        . "1️⃣ با اپ اختصاصی <a href=\"{$dlApp}\">JET VPN</a> رو نصب کن (ساده‌ترین راه):\n"
                        . "👉 {$dlApp}\n\n"
                        . "با همین نام کاربری و رمز وارد شو و سرعت رو تست کن.\n\n"
                        . "2️⃣ یا با برنامه‌های دیگه:\n"
                        . (function_exists('appAndroidDownloadHtml') ? appAndroidDownloadHtml() . "\n" : "")
                        . "لینک اشتراک رو کپی کن و داخل برنامه Import کن:\n"
                        . "🔗 لینک اتصال:\n<code>{$subUrl}</code>\n\n"
                        . "اگه سرعت و پایداری خوب بود، از منوی ربات «خرید اشتراک» بزن و بدون قطعی ادامه بده 🚀\n\n"
                        . "سوال داشتی؟ پشتیبانی همین‌جاست.";

        $dl_inline = array_merge(
            serviceInfoChipRow(remainingTimeChipLabel($days > 0 ? ($days . ' روز') : '۲۴ ساعت'), remainingVolumeChipLabel($vol, 0)),
            [[['text' => '🛍 خرید اشتراک جدید', 'callback_data' => 'main_categories']]]
        );

        sendTelegram('sendPhoto', [
            'chat_id' => $chat_id,
            'photo' => $qrUrl,
            'caption' => $testSuccessMsg,
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => $dl_inline])
        ]);
    } else {
        $errDetail = 'نامشخص';
        if (is_array($res)) {
            $errDetail = ($res['_error'] ?? 'error') . ' | ' . ($res['detail'] ?? json_encode($res, JSON_UNESCAPED_UNICODE));
        } elseif ($res === false) {
            $errDetail = 'false (احتمالاً توکن یا اتصال)';
        }
        sendTelegram('sendMessage', [
            'chat_id' => ADMIN_ID,
            'text' => "⚠️ <b>خطا در ساخت تست رایگان</b>\n\nکاربر: <code>{$user_id}</code>\nیوزرنیم تست: <code>{$testUsername}</code>\noffer: <code>{$offerId}/{$catKey}</code>\n\nجزئیات:\n<code>" . htmlspecialchars(substr($errDetail, 0, 500)) . "</code>",
            'parse_mode' => 'HTML'
        ]);
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "😅 الان نتونستیم تست رو بسازیم.\nیه کم دیگه دوباره امتحان کن؛ اگه باز نشد از <b>پشتیبانی</b> بگو تا کمکت کنیم."
        ]);
    }
    exit();
}


if ((isIdleStep($currentUser) && isMenuKeywordHit($text, 'خرید اشتراک')) || $callback_data === 'main_categories') {
    if (!isFeatureEnabled($db, 'btn_buy') && !isBotAdmin($user_id)) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "😊 خرید اشتراک الان موقتاً خاموشه. کمی بعد دوباره سر بزن؛ اگه فوریه از پشتیبانی بگو.", 'reply_markup' => $mainKeyboard]);
        exit();
    }
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    // بازگشت از فاکتور / تغییر پلن → پیش‌فاکتور نیمه‌کاره بسته شود
    if (function_exists('cancelAwaitingInvoices')) {
        cancelAwaitingInvoices($db, $user_id);
    }

    $orderedCats = getOrderedVisibleCategories($db, $activePlans);
    $rows = [];
    foreach ($orderedCats as $item) {
        $ck = $item['key'];
        $lb = $item['meta'];
        $btnTitle = ($lb['emoji'] ?? '📦') . ' ' . ($lb['title'] ?? $ck);
        if (!empty($lb['desc'])) {
            $btnTitle .= ' — ' . $lb['desc'];
        }
        if (mb_strlen($btnTitle) > 64) $btnTitle = mb_substr($btnTitle, 0, 61) . '…';
        $rows[] = [['text' => $btnTitle, 'callback_data' => 'cat_' . $ck]]; // رنگ از سیستم highlight/نقش
    }
    $rows[] = [['text' => '❌ انصراف', 'callback_data' => 'cancel_order', 'style' => 'danger']];
    $catKeyboard = json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE);

    $msg = "🛒 <b>نوع اشتراک را انتخاب کن:</b>

"
         . "هر دسته برای نیاز متفاوتی طراحی شده — یکی رو که به کارت می‌خوره بردار 🚀

"
         . "🧪 برای اطمینان از اتصال و سازگاری با شبکه و منطقه‌ات، اول از منوی اصلی <b>دریافت تست رایگان</b> همون نوع پلن رو بگیر و امتحان کن.

"
         . "⭐ پیشنهاد خیلی از کاربرها: بسته <b>۵۰ گیگ یک‌ماهه</b>
"
         . "⚡️ تحویل آنی بعد از تأیید پرداخت
"
         . "🔄 سرورهای پایدار + پشتیبانی در ربات

"
         . "💡 حجم یا مدت خاص می‌خوای؟ به <b>پشتیبانی</b> پیام بده تا برات جور کنیم.";


    // اگر کارت سرویس با عکس/QR باشد editMessageText کار نمی‌کند
    if ($callback_data) {
        adminSendOrEditText($chat_id, $update, $msg, $catKeyboard);
    } else {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => $msg,
            'parse_mode' => 'HTML',
            'reply_markup' => $catKeyboard
        ]);
    }
    exit();
}

// دکمه‌های فقط‌نمایشی وضعیت اشتراک — با زدن هیچ اتفاقی نمی‌افتد
if ($callback_data === 'noop_status') {
    if (!empty($update['callback_query']['id'])) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    }
    exit();
}

if ($callback_data === 'my_services_list' || (isIdleStep($currentUser) && isMenuKeywordHit($text, 'سرویس‌های من'))) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    // فقط سرویس شخصی — سرویس‌های صادرشده نمایندگی در پنل نمایندگی است
    $stmt = $db->prepare("SELECT * FROM orders WHERE user_id = ? AND (reseller_id IS NULL OR reseller_id = 0) ORDER BY id DESC LIMIT 15");
    try {
        $stmt->execute([$user_id]);
        $orders = $stmt->fetchAll();
    } catch (Exception $e) {
        $stmt = $db->prepare("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 15");
        $stmt->execute([$user_id]);
        $orders = $stmt->fetchAll();
    }

    if (empty($orders)) {
        $msg = "📦 هنوز سرویسی نداری 👀\n\nبا <b>🛍 خرید اشتراک جدید</b> شروع کن، یا اگه هنوز تست نگرفتی از منو <b>تست رایگان</b> رو بزن.";
        if ($callback_data) {
            sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $update['callback_query']['message']['message_id'], 'text' => $msg, 'parse_mode' => 'HTML']);
        } else {
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => $msg, 'parse_mode' => 'HTML']);
        }
    } else {
        if ($callback_data) {
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "📋 <b>لیست سرویس‌های شما:</b>", 'parse_mode' => 'HTML']);
        }
        foreach ($orders as $order) {
            $orderPanel = panelFromOrder($order, $db);
            $info = getPasargadUser($order['config_username'], $orderPanel);
            // اکانت روی پنل هست؟ (پاسخ خطا فقط detail دارد)
            $panelAlive = is_array($info)
                && (
                    isset($info['username'])
                    || isset($info['status'])
                    || isset($info['used_traffic'])
                    || array_key_exists('data_limit', $info)
                    || array_key_exists('expire', $info)
                )
                && !(isset($info['detail']) && !isset($info['username']) && !isset($info['status']));

            $used_gb = 0;
            $total_gb = (float)$order['volume_gb'];
            $daysTxt = $order['days'] > 0 ? "{$order['days']} روزه" : "بدون انقضا (VIP)";

            // اولویت با داده زنده پنل (بعد از تمدید انباشتی دقیق‌تر است)
            if ($panelAlive) {
                if (isset($info['used_traffic'])) {
                    $used_gb = round(((float)$info['used_traffic']) / (1024 * 1024 * 1024), 2);
                }
                $panelLimit = (float)($info['data_limit'] ?? 0);
                if ($panelLimit > 0) {
                    $total_gb = round($panelLimit / (1024 * 1024 * 1024), 2);
                    // همگام‌سازی جدول orders با پنل
                    try {
                        $db->prepare("UPDATE orders SET volume_gb = ? WHERE id = ?")->execute([$total_gb, $order['id']]);
                    } catch (Exception $e) {}
                }
                $panelStatus = (string)($info['status'] ?? '');
                $holdDur = (int)($info['on_hold_expire_duration'] ?? 0);
                $expTs = parsePanelExpire($info['expire'] ?? 0);
                if ($panelStatus === 'on_hold') {
                    $holdDays = $holdDur > 0 ? (int)ceil($holdDur / 86400) : (int)($order['days'] ?? 0);
                    $daysTxt = $holdDays > 0
                        ? "از اولین اتصال · {$holdDays} روز"
                        : "از اولین اتصال";
                } elseif ($expTs > 0) {
                    $remainSec = $expTs - time();
                    $expJalali = function_exists('formatJalaliDateTime')
                        ? formatJalaliDateTime(date('Y-m-d H:i:s', $expTs))
                        : date('Y-m-d H:i', $expTs);
                    if ($remainSec <= 0) {
                        $daysTxt = "منقضی شده ({$expJalali})";
                    } else {
                        $remainDays = (int)ceil($remainSec / 86400);
                        $daysTxt = "{$remainDays} روز مانده ({$expJalali})";
                    }
                } elseif ($expTs === 0 && isset($info['expire']) && ($info['expire'] === 0 || $info['expire'] === '0')) {
                    $daysTxt = "بدون انقضا (VIP)";
                }
            }

            $volDisplay = formatVolumeGb($total_gb);

            $orderPass = !empty($order['password']) ? $order['password'] : '1234';
            if (empty($order['password'])) {
                $db->prepare("UPDATE orders SET password = ? WHERE id = ?")->execute([$orderPass, $order['id']]);
            }

            if (!$panelAlive) {
                // حذف‌شده از پنل — فقط سابقه؛ بدون تمدید
                $card = "📋 <b>سرویس قبلی (حذف‌شده)</b>\n\n"
                      . "👤 نام کاربری: <code>{$order['config_username']}</code>\n"
                      . "📊 حجم ثبت‌شده: {$volDisplay}\n"
                      . "⏰ مدت ثبت‌شده: {$daysTxt}\n\n"
                      . "این سرویس دیگه روی سرور نیست و قابل اتصال یا تمدید نیست.\n"
                      . "برای ادامه، یه <b>🛍 اشتراک جدید</b> بگیر 🚀";
                $kb = json_encode([
                    'inline_keyboard' => [
                        [['text' => '🛍 خرید اشتراک جدید', 'callback_data' => 'main_categories', 'style' => 'primary']],
                    ]
                ], JSON_UNESCAPED_UNICODE);
                sendTelegram('sendMessage', [
                    'chat_id' => $chat_id,
                    'text' => $card,
                    'parse_mode' => 'HTML',
                    'reply_markup' => $kb
                ]);
                continue;
            }

            $qrUrl = getQRCodeUrl($order['sub_link']);

            $isTestSvc = isTestServiceOrder($order);

            // باقیمانده واقعی نسبت به سقف فعلی پنل (تمدید انباشتی)
            $lastRenewGb = 0.0;
            try {
                jet_ensure_last_renew_col($db);
                if (isset($order['last_renew_gb']) && (float)$order['last_renew_gb'] > 0) {
                    $lastRenewGb = (float)$order['last_renew_gb'];
                } else {
                    $stLr = $db->prepare('SELECT last_renew_gb FROM orders WHERE id = ? LIMIT 1');
                    $stLr->execute([(int)$order['id']]);
                    $lastRenewGb = (float)($stLr->fetchColumn() ?: 0);
                }
            } catch (Throwable $e) {
                $lastRenewGb = 0.0;
            }
            $remain_gb = max(0.0, round((float)$total_gb - (float)$used_gb, 2));
            if ($panelAlive && isset($info['data_limit'])) {
                $limB = (float)$info['data_limit'];
                $usedB = isset($info['used_traffic']) ? (float)$info['used_traffic'] : 0.0;
                if ($limB > 0) {
                    $remain_gb = max(0.0, round(($limB - $usedB) / (1024 * 1024 * 1024), 2));
                    $total_gb = round($limB / (1024 * 1024 * 1024), 2);
                }
            }
            $volDisplay = formatVolumeGb($total_gb);
            $remainDisplay = formatVolumeGb($remain_gb);

            $card = "📋 <b>مشخصات اشتراک" . ($isTestSvc ? ' (تست رایگان)' : '') . "</b>\n\n"
                  . "👤 نام کاربری: <code>{$order['config_username']}</code>\n"
                  . "🔑 رمز اپ: <code>{$orderPass}</code>\n"
                  . "📊 باقیمانده واقعی: <b>{$remainDisplay}</b> از سقف {$volDisplay}\n"
                  . ($lastRenewGb > 0 ? ("📦 آخرین تمدید: <b>+" . rtrim(rtrim(number_format($lastRenewGb, 2, '.', ''), '0'), '.') . " گیگ</b>\n") : "")
                  . "📈 مصرف کل از ابتدا: {$used_gb} GB\n"
                  . "⏰ مدت: {$daysTxt}\n\n"
                  . "🔗 لینک اتصال:\n<code>{$order['sub_link']}</code>";

            // تمدید فقط وقتی حجم/زمان رو به اتمام است (هم‌راستا با هشدارها)
            // حجم: ≤۲۰٪ مانده یا تمام‌شده | زمان: ≤۳ روز مانده یا منقضی
            $showRenew = false;
            if (!$isTestSvc && $panelAlive) {
                $limitB = 0.0;
                if (isset($info['data_limit'])) {
                    $limitB = (float)$info['data_limit'];
                } elseif ($total_gb > 0) {
                    $limitB = (float)$total_gb * 1024 * 1024 * 1024;
                }
                $usedB = isset($info['used_traffic']) ? (float)$info['used_traffic'] : ((float)$used_gb * 1024 * 1024 * 1024);
                if ($limitB > 0) {
                    $remainB = max(0.0, $limitB - $usedB);
                    $remainGb = $remainB / (1024 * 1024 * 1024);
                    $limitGb = $limitB / (1024 * 1024 * 1024);
                    $remainPct = ($remainB / $limitB) * 100.0;
                    // سقف کوچک: درصد | سقف بزرگ: باقیمانده مطلق (هم‌راستا با کرون)
                    $volLow = ($limitGb <= 15.0)
                        ? ($remainPct <= 20.0 || $usedB >= $limitB)
                        : ($remainGb <= 5.0 || $usedB >= $limitB);
                    if ($volLow) {
                        $showRenew = true;
                    }
                }
                $expTsRenew = parsePanelExpire($info['expire'] ?? 0);
                if ($expTsRenew > 0) {
                    $secLeft = $expTsRenew - time();
                    if ($secLeft <= 3 * 86400) { // ۳ روز یا کمتر / منقضی
                        $showRenew = true;
                    }
                }
            }

            $timeChip = remainingTimeChipLabel($daysTxt);
            $volChip = remainingVolumeChipLabel($total_gb, $used_gb);
            $infoChips = serviceInfoChipRow($timeChip, $volChip);

            if ($isTestSvc) {
                $card .= "\n\nℹ️ تست قابل تمدید نیست — برای ادامه با سرعت کامل، <b>خرید اشتراک</b> بزن 🚀";
                $rowsKb = array_merge($infoChips, [
                    [['text' => '🛍 خرید اشتراک جدید', 'callback_data' => 'main_categories', 'style' => 'primary']],
                    [['text' => '📥 دانلود اپ‌ها', 'url' => DIRECT_DOWNLOAD_URL]],
                ]);
            } else {
                $rowsKb = $infoChips;
                if ($showRenew) {
                    $rowsKb[] = [['text' => "🔄 تمدید اشتراک ({$order['config_username']})", 'callback_data' => "ren_srv:{$order['config_username']}", 'style' => 'success']];
                }
                $rowsKb[] = [['text' => '🛍 خرید اشتراک جدید', 'callback_data' => 'main_categories', 'style' => 'primary']];
                $rowsKb[] = [['text' => '📥 دانلود اپ‌ها', 'url' => DIRECT_DOWNLOAD_URL]];
                if (!$showRenew) {
                    $card .= "\n\n💡 تمدید وقتی حجم یا زمان رو به اتمام باشه اینجا نشون داده می‌شه. برای پلن دیگه از خرید استفاده کن.";
                }
            }
            $renewKeyboard = json_encode(['inline_keyboard' => $rowsKb], JSON_UNESCAPED_UNICODE);

            sendTelegram('sendPhoto', [
                'chat_id' => $chat_id,
                'photo' => $qrUrl,
                'caption' => $card,
                'parse_mode' => 'HTML',
                'reply_markup' => $renewKeyboard
            ]);
        }
    }
    exit();
}

// راهنما در دکمه «اپ و راهنمای اتصال» ادغام شد

elseif ($callback_data && strpos($callback_data, 'cat_') === 0 && $callback_data !== 'cancel_order') {
    $catKey = substr($callback_data, 4);
    if ($catKey === '' || !preg_match('/^[a-z0-9_]+$/i', $catKey)) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'دسته نامعتبر', 'show_alert' => true]);
        exit();
    }
    $labels = getPlanCategoryLabels($db);
    $lb = $labels[$catKey] ?? ['title' => $catKey, 'emoji' => '📦', 'desc' => ''];
    $buttons = [];
    // اگر دسته سراسری خاموش است
    if (!isPlanCategoryActiveForPanel($db, 0, $catKey)) {
        sendTelegram('answerCallbackQuery', [
            'callback_query_id' => $update['callback_query']['id'],
            'text' => 'این دسته فعلاً فعال نیست',
            'show_alert' => true
        ]);
        exit();
    }
    foreach ($activePlans as $k => $p) {
        if (strtolower((string)($p['cat'] ?? '')) !== strtolower($catKey)) continue;
        $pid = (int)($p['panel_id'] ?? 0);
        if (!isPlanCategoryActiveForPanel($db, $pid, $catKey)) continue;
        $priceTxt = number_format((int)$p['price']);
        $titleClean = trim(str_ireplace(['VIP', 'vip'], '', $p['title']));
        $mark = '';
        if ($catKey === 'monthly' && (float)$p['vol'] >= 45 && (float)$p['vol'] <= 55 && (int)$p['days'] === 30) {
            $mark = '⭐ ';
        }
        $btnText = "{$mark}{$titleClean} — {$priceTxt} تومان";
        if (mb_strlen($btnText) > 64) $btnText = mb_substr($btnText, 0, 61) . '…';
        $btn = ['text' => $btnText, 'callback_data' => 'select_' . $k];
        // رنگ از highlight وب‌پنل؛ در صورت نبود، نقش nav اعمال می‌شود
        $buttons[] = [$btn];
    }
    if (empty($buttons)) {
        $buttons[] = [['text' => 'فعلاً بسته‌ای در این دسته نیست', 'callback_data' => 'main_categories']];
    }
    $buttons[] = [['text' => '🔙 بازگشت به دسته‌ها', 'callback_data' => 'main_categories', 'style' => 'danger']];
    $head = ($lb['emoji'] ?? '📦') . ' <b>' . htmlspecialchars($lb['title'] ?? $catKey) . "</b>\n";
    if (!empty($lb['desc'])) $head .= htmlspecialchars($lb['desc']) . "\n";
        $head .= "\n🧪 برای اطمینان از اتصال با شبکه و منطقه‌ات، اول از منوی اصلی «دریافت تست رایگان» همین نوع پلن را بگیر و امتحان کن.\n";
$head .= "\nیکی را انتخاب کن:";
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $head,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $buttons], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

elseif ($callback_data === 'cancel_order') {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if (function_exists('cancelAwaitingInvoices')) {
        cancelAwaitingInvoices($db, $user_id);
    }
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "باشه، لغو شد ✅ فاکتور نیمه‌کاره هم بسته شد. هر وقت خواستی از منو برگرد."
    ]);
    exit();
}

// انتخاب روش پرداخت: صفحه وب
elseif ($callback_data && strpos($callback_data, 'pay_web:') === 0) {
    $paymentId = (int)str_replace('pay_web:', '', $callback_data);
    ensurePaymentPayColumns($db);
    expireStaleInvoices($db);
    $st = $db->prepare('SELECT * FROM payments WHERE id = ? AND user_id = ? LIMIT 1');
    $st->execute([$paymentId, $user_id]);
    $pay = $st->fetch(PDO::FETCH_ASSOC);
    $editId = $update['callback_query']['message']['message_id'] ?? null;
    if (!$pay || ($pay['status'] ?? '') !== 'pending') {
        sendTelegram('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $editId,
            'text' => '❌ این فاکتور معتبر نیست یا قبلاً بسته شده. از منو دوباره شروع کن.',
            'parse_mode' => 'HTML'
        ]);
        exit();
    }
    if (isPaymentExpiredRow($pay)) {
        try {
            $db->prepare("UPDATE payments SET status = 'expired' WHERE id = ?")->execute([$paymentId]);
        } catch (Exception $e) {
        }
        sendTelegram('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $editId,
            'text' => "⏰ <b>مهلت فاکتور تمام شد</b>\n\nدوباره از منو خرید/شارژ را بزن تا فاکتور جدید بگیری.",
            'parse_mode' => 'HTML'
        ]);
        exit();
    }
    $token = (string)($pay['pay_token'] ?? '');
    if ($token === '') {
        $token = generatePayToken();
        try {
            $db->prepare('UPDATE payments SET pay_token = ? WHERE id = ?')->execute([$token, $paymentId]);
        } catch (Exception $e) {
        }
    }
    $link = buildPayPageLink($db, $token);
    $rial = ((int)$pay['price']) * 10;
    $txt = "🌐 <b>صفحه پرداخت امن جت‌کانفیگ</b>\n\n"
         . "💰 مبلغ: <b>" . number_format((int)$pay['price']) . " تومان</b>\n"
         . "🔢 ریال: <code>{$rial}</code>\n\n"
         . "روی دکمه زیر بزن، مبلغ و کارت را کپی کن و واریز کن.\n"
         . "پرداخت هوشمند — معمولاً به‌صورت خودکار تأیید می‌شود ⚡️";
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '🔓 ورود به صفحه پرداخت', 'url' => $link]],
            [['text' => '💬 پرداخت داخل تلگرام', 'callback_data' => 'pay_tg:' . $paymentId, 'style' => 'primary']],
            [['text' => '❌ انصراف', 'callback_data' => 'pay_cancel:' . $paymentId, 'style' => 'danger']],
        ]
    ], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $editId,
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

// برگشت به انتخاب روش پرداخت (بدون ساخت فاکتور جدید)
elseif ($callback_data && strpos($callback_data, 'pay_methods:') === 0) {
    $paymentId = (int)str_replace('pay_methods:', '', $callback_data);
    ensurePaymentPayColumns($db);
    expireStaleInvoices($db);
    $st = $db->prepare('SELECT * FROM payments WHERE id = ? AND user_id = ? LIMIT 1');
    $st->execute([$paymentId, $user_id]);
    $pay = $st->fetch(PDO::FETCH_ASSOC);
    $editId = $update['callback_query']['message']['message_id'] ?? null;
    if (!$pay || ($pay['status'] ?? '') !== 'pending' || isPaymentExpiredRow($pay)) {
        sendTelegram('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $editId,
            'text' => '⏰ این فاکتور دیگر معتبر نیست. از منو دوباره شروع کن.',
            'parse_mode' => 'HTML'
        ]);
        exit();
    }
    $token = (string)($pay['pay_token'] ?? '');
    if ($token === '') {
        $token = generatePayToken();
        try { $db->prepare('UPDATE payments SET pay_token = ? WHERE id = ?')->execute([$token, $paymentId]); } catch (Exception $e) {}
    }
    $payLink = $token !== '' ? buildPayPageLink($db, $token) : '';
    $rial = ((int)$pay['price']) * 10;
    $actionType = (string)$pay['action_type'];
    $ttlMin = 20;
    if (!empty($pay['expires_at'])) {
        $left = max(0, strtotime($pay['expires_at']) - time());
        $ttlMin = max(1, (int)ceil($left / 60));
    }
    $txt = "🧾 <b>فاکتور #{$paymentId}</b>\n\n"
         . "💰 مبلغ: <b>" . number_format((int)$pay['price']) . " تومان</b>\n"
         . "🔢 به ریال: <code>{$rial}</code>\n"
         . "⏱ مهلت باقی‌مانده: حدود <b>{$ttlMin} دقیقه</b>\n\n"
         . "👇 <b>چطور می‌خوای پرداخت کنی؟</b>";
    $rows = [];
    if ($actionType !== 'deposit') {
        $stmt = $db->prepare('SELECT balance FROM users WHERE user_id = ?');
        $stmt->execute([$user_id]);
        $bal = (int)$stmt->fetchColumn();
        if ($bal >= (int)$pay['price']) {
            $pk = (string)$pay['plan_key'];
            $tu = (string)$pay['target_username'];
            $cc = (string)($pay['coupon_code'] ?? '');
            $rows[] = [['text' => '⚡️ پرداخت آنی از کیف پول', 'callback_data' => "pay_wallet:{$actionType}:{$pk}:{$tu}:{$cc}", 'style' => 'success']];
        }
    }
    if ($payLink !== '') {
        $rows[] = [['text' => '🌐 پرداخت در صفحه امن', 'url' => $payLink]];
    }
    $rows[] = [['text' => '💬 پرداخت داخل تلگرام', 'callback_data' => 'pay_tg:' . $paymentId, 'style' => 'primary']];
    $rows[] = [['text' => '❌ انصراف', 'callback_data' => 'pay_cancel:' . $paymentId, 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $editId,
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

// انتخاب روش پرداخت: داخل تلگرام
elseif ($callback_data && strpos($callback_data, 'pay_tg:') === 0) {
    $paymentId = (int)str_replace('pay_tg:', '', $callback_data);
    $editId = $update['callback_query']['message']['message_id'] ?? null;
    showTelegramPaymentDetails($chat_id, $paymentId, $db, $plans, $editId);
    exit();
}

// پرداخت کرده‌ام — بازیابی فاکتور منقضی (تا ۱ روز) بدون تغییر مبلغ
elseif ($callback_data && strpos($callback_data, 'pay_claim:') === 0) {
    $paymentId = (int)str_replace('pay_claim:', '', $callback_data);
    $editId = $update['callback_query']['message']['message_id'] ?? null;
    ensurePaymentPayColumns($db);
    // pending در انتظار فیش + بازیابی منقضی/لغو شده حداکثر ۱ روز
    $st = $db->prepare(
        "SELECT * FROM payments WHERE id = ? AND user_id = ?
         AND (
            (status = 'pending' AND (photo_file_id IS NULL OR photo_file_id IN ('AWAITING_RECEIPT','')))
            OR (status IN ('expired','cancelled','rejected') AND created_at >= (NOW() - INTERVAL 1 DAY))
         )
         LIMIT 1"
    );
    $st->execute([$paymentId, $user_id]);
    $pay = $st->fetch(PDO::FETCH_ASSOC);
    if (!$pay) {
        sendTelegram('answerCallbackQuery', [
            'callback_query_id' => $update['callback_query']['id'],
            'text' => 'این فاکتور قابل ارسال فیش نیست یا منقضی شده. یک فاکتور جدید بساز.',
            'show_alert' => true,
        ]);
        exit();
    }
    // اگر قبلاً سرویس ساخته شده بود، دوباره نساز
    try {
        $chk = $db->prepare("SELECT id FROM orders WHERE user_id = ? AND config_username = ? LIMIT 1");
        $chk->execute([$user_id, (string)$pay['target_username']]);
        if ($chk->fetchColumn() && ($pay['action_type'] ?? '') === 'new') {
            // برای new اگر سفارش موجود است ممکن است قبلاً تایید شده؛ اجازه ارسال فیش برای pending دستی بده
        }
    } catch (Exception $e) {
    }
    $fid = (string)($pay['photo_file_id'] ?? '');
    $keepPhoto = ($fid !== '' && $fid !== 'AWAITING_RECEIPT' && $fid !== 'WALLET_PAY' && $fid !== 'SMS_AUTO');
    $newPhoto = $keepPhoto ? $fid : 'AWAITING_RECEIPT';
    try {
        $db->prepare(
            "UPDATE payments SET status = 'pending', photo_file_id = ?, expires_at = DATE_ADD(NOW(), INTERVAL 1 DAY) WHERE id = ?"
        )->execute([$newPhoto, $paymentId]);
    } catch (Exception $e) {
        $db->prepare("UPDATE payments SET status = 'pending' WHERE id = ?")->execute([$paymentId]);
    }
    $actionType = (string)$pay['action_type'];
    $planKey = (string)$pay['plan_key'];
    $targetUser = (string)$pay['target_username'];
    $couponCode = (string)($pay['coupon_code'] ?? '');
    $finalPrice = (int)$pay['price'];
    // فقط شناسه فاکتور — مبلغ از payments خوانده می‌شود
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")
       ->execute(["payid:{$paymentId}", $user_id]);
    sendTelegram('answerCallbackQuery', [
        'callback_query_id' => $update['callback_query']['id'],
        'text' => 'فاکتور باز شد — عکس فیش را بفرست',
    ]);
    $info = "♻️ <b>فاکتور #{$paymentId} برای ارسال فیش باز شد</b>\n\n"
          . "💰 مبلغ همان فاکتور قبلی: <b>" . number_format($finalPrice) . " تومان</b>\n"
          . "🔢 ریال: <code>" . ($finalPrice * 10) . "</code>\n\n"
          . "📷 الان <b>عکس فیش واریزی</b> را همین‌جا بفرست تا در صف ادمین قرار بگیرد.\n"
          . "سیستم پرداخت هوشمند است و سفارش‌ها معمولاً خودکار ثبت می‌شوند.";
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $editId,
        'text' => $info,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode([
            'inline_keyboard' => [
                [['text' => '💳 جزئیات کارت و مبلغ', 'callback_data' => 'pay_tg:' . $paymentId, 'style' => 'primary']],
                [['text' => '❌ انصراف', 'callback_data' => 'pay_cancel:' . $paymentId, 'style' => 'danger']],
            ]
        ], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}

// انصراف از فاکتور خاص
elseif ($callback_data && strpos($callback_data, 'pay_cancel:') === 0) {
    $paymentId = (int)str_replace('pay_cancel:', '', $callback_data);
    try {
        $db->prepare("UPDATE payments SET status = 'cancelled' WHERE id = ? AND user_id = ? AND status = 'pending'")
           ->execute([$paymentId, $user_id]);
    } catch (Exception $e) {
        try {
            $db->prepare("UPDATE payments SET status = 'rejected' WHERE id = ? AND user_id = ? AND status = 'pending'")
               ->execute([$paymentId, $user_id]);
        } catch (Exception $e2) {
        }
    }
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "باشه، لغو شد ✅ فاکتور بسته شد. هر وقت خواستی از منو برگرد."
    ]);
    exit();
}

elseif ($callback_data && strpos($callback_data, 'select_') === 0) {
    $planKey = str_replace('select_', '', $callback_data);
    if (isset($plans[$planKey])) {
        $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(['ask_user:' . $planKey, $user_id]);

        $keyboard = json_encode([
            'inline_keyboard' => [
                [['text' => '🎲 ساخت خودکار نام کاربری', 'callback_data' => 'auto_user:' . $planKey]],
                [['text' => '🔙 بازگشت به پلن‌ها', 'callback_data' => 'main_categories', 'style' => 'danger']]
            ]
        ]);

        $askMsg = "✏️ <b>انتخاب نام کاربری کانفیگ:</b>\n\n"
                . "نام کاربری دلخواهت رو با <b>حروف انگلیسی</b> بفرست (مثل: <code>ali_vpn</code> یا <code>reza2026</code>)\n\n"
                . "یا برای ساخت سریع، <b>🎲 ساخت خودکار</b> رو بزن:";

        sendTelegram('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $update['callback_query']['message']['message_id'],
            'text' => $askMsg,
            'parse_mode' => 'HTML',
            'reply_markup' => $keyboard
        ]);
    }
    exit();
}

elseif ($callback_data && strpos($callback_data, 'auto_user:') === 0) {
    $planKey = str_replace('auto_user:', '', $callback_data);
    // بازه بزرگ‌تر + چک تکراری در دیتابیس برای کاهش User already exists
    $randomUsername = 'user_' . $user_id . '_' . random_int(1000, 9999);
    try {
        for ($i = 0; $i < 8; $i++) {
            $st = $db->prepare('SELECT id FROM orders WHERE config_username = ? LIMIT 1');
            $st->execute([$randomUsername]);
            if (!$st->fetch()) {
                break;
            }
            $randomUsername = 'user_' . $user_id . '_' . random_int(1000, 9999);
        }
    } catch (Exception $e) {
    }
    issueInvoice($chat_id, $user_id, $planKey, $randomUsername, 'new', $plans, $db, $update['callback_query']['message']['message_id']);
    exit();
}

elseif ($callback_data && strpos($callback_data, 'ren_srv:') === 0) {
    $targetUsername = str_replace('ren_srv:', '', $callback_data);
    // پیام سرویس‌ها با sendPhoto آمده؛ editMessageText روی عکس کار نمی‌کند
    if (!empty($update['callback_query']['id'])) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    }

    // نوع سرویس فعلی: VIP (بدون انقضا) یا ماهانه/مدت‌دار
    $own = $db->prepare("SELECT * FROM orders WHERE user_id = ? AND config_username = ? LIMIT 1");
    $own->execute([$user_id, $targetUsername]);
    $orderRow = $own->fetch(PDO::FETCH_ASSOC);
    if (!$orderRow && !isBotAdmin($user_id)) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => '❌ این سرویس متعلق به شما نیست یا یافت نشد.',
            'parse_mode' => 'HTML'
        ]);
        exit();
    }
    // اکانت تست قابل تمدید نیست
    $isTestRenew = $orderRow ? isTestServiceOrder($orderRow) : isTestServiceOrder($targetUsername);
    if ($isTestRenew) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "ℹ️ تست قابل تمدید نیست\n\n"
                   . "نام: <code>{$targetUsername}</code>\n\n"
                   . "برای ادامه با سرعت کامل، <b>خرید اشتراک جدید</b> بزن 🚀",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '🛍 خرید اشتراک جدید', 'callback_data' => 'main_categories', 'style' => 'primary']],
            ]], JSON_UNESCAPED_UNICODE)
        ]);
        exit();
    }
    // اگر از پنل حذف شده باشد تمدید ممکن نیست — حتماً پنل همان سفارش
    $orderPanel = panelFromOrder($orderRow ?: ['config_username' => $targetUsername], $db);
    $pinfoCheck = getPasargadUser($targetUsername, $orderPanel);
    $panelAlive = is_array($pinfoCheck)
        && (
            isset($pinfoCheck['username'])
            || isset($pinfoCheck['status'])
            || isset($pinfoCheck['used_traffic'])
            || array_key_exists('data_limit', $pinfoCheck)
            || array_key_exists('expire', $pinfoCheck)
        )
        && !(isset($pinfoCheck['detail']) && !isset($pinfoCheck['username']) && !isset($pinfoCheck['status']));
    if (!$panelAlive) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "⚠️ این سرویس دیگه روی سرور نیست\n\n"
                   . "نام: <code>{$targetUsername}</code>\n\n"
                   . "تمدید ممکن نیست — یه <b>🛍 اشتراک جدید</b> بگیر تا دوباره وصل شی 🚀",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '🛍 خرید اشتراک جدید', 'callback_data' => 'main_categories', 'style' => 'primary']],
                [['text' => '🔙 سرویس‌های من', 'callback_data' => 'my_services_list', 'style' => 'danger']],
            ]], JSON_UNESCAPED_UNICODE)
        ]);
        exit();
    }
    // دسته از orders.cat؛ وگرنه از days
    $svcCat = '';
    if ($orderRow) {
        $svcCat = strtolower(trim((string)($orderRow['cat'] ?? '')));
    }
    if ($svcCat === '') {
        if ($orderRow) {
            $svcCat = ((int)($orderRow['days'] ?? 0) === 0) ? 'vip' : 'monthly';
        } else {
            $expTs = parsePanelExpire($pinfoCheck['expire'] ?? 0);
            $svcCat = ($expTs <= 0) ? 'vip' : 'monthly';
        }
    }

    $orderPanelId = (int)($orderRow['panel_id'] ?? 0);
    if ($orderPanelId <= 0 && is_array($orderPanel)) {
        $orderPanelId = (int)($orderPanel['id'] ?? 0);
    }
    $defPanel = getDefaultPanel($db);
    $defPanelId = (int)($defPanel['id'] ?? 0);
    if ($orderPanelId <= 0) {
        $orderPanelId = $defPanelId;
    }
    $labels = function_exists('getPlanCategoryLabels') ? getPlanCategoryLabels($db) : [];

    // فقط پلن فعال + هم‌پنل + هم‌دسته + دسته فعال
    $usePlans = [];
    if (isPlanCategoryActiveForPanel($db, $orderPanelId, $svcCat)) {
        foreach ($activePlans as $k => $p) {
            if (isset($p['is_active']) && (int)$p['is_active'] === 0) {
                continue;
            }
            $planPanelId = (int)($p['panel_id'] ?? 0);
            if ($planPanelId <= 0) {
                $planPanelId = $defPanelId;
            }
            if ($orderPanelId > 0 && $planPanelId !== $orderPanelId) {
                continue;
            }
            $pCat = strtolower(trim((string)($p['cat'] ?? '')));
            if ($pCat === '') {
                $pCat = ((int)($p['days'] ?? 0) === 0) ? 'vip' : 'monthly';
            }
            if ($pCat !== $svcCat) {
                continue;
            }
            if (!isPlanCategoryActiveForPanel($db, $planPanelId, $pCat)) {
                continue;
            }
            $usePlans[$k] = $p;
        }
    }

    $buttons = [];
    $matched = 0;
    foreach ($usePlans as $k => $p) {
        $matched++;
        $pCat = strtolower(trim((string)($p['cat'] ?? '')));
        $catEmoji = '';
        if ($pCat !== '' && isset($labels[$pCat]['emoji'])) {
            $catEmoji = $labels[$pCat]['emoji'] . ' ';
        }
        $buttons[] = [[
            'text' => "🔄 {$catEmoji}{$p['title']} (" . number_format((int)$p['price']) . " ت)",
            'callback_data' => "ren_pln:{$targetUsername}:{$k}",
            'style' => 'success'
        ]];
    }

    $txt = "🔄 <b>تمدید اشتراک</b>
"
         . "سرویس: <code>{$targetUsername}</code>

";
    if ($matched === 0) {
        $txt .= "الان بسته‌ای برای تمدید این سرویس فعال نیست.
"
              . "از <b>خرید اشتراک جدید</b> استفاده کن یا به پشتیبانی پیام بده.";
    } else {
        $txt .= "بسته تمدید را انتخاب کن:";
    }

    $buttons[] = [['text' => '🛍 خرید اشتراک جدید', 'callback_data' => 'main_categories', 'style' => 'primary']];
    $buttons[] = [['text' => '🔙 بازگشت به سرویس‌ها', 'callback_data' => 'my_services_list', 'style' => 'danger']];

    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $buttons], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

elseif ($callback_data && strpos($callback_data, 'ren_pln:') === 0) {
    $parts = explode(':', str_replace('ren_pln:', '', $callback_data));
    $targetUsername = $parts[0] ?? '';
    $planKey = $parts[1] ?? '';
    if ($targetUsername === '' || $planKey === '' || empty($plans[$planKey])) {
        if (!empty($update['callback_query']['id'])) {
            sendTelegram('answerCallbackQuery', [
                'callback_query_id' => $update['callback_query']['id'],
                'text' => 'پلن نامعتبر است',
                'show_alert' => true
            ]);
        }
        exit();
    }

    // فاز B: فقط هم‌پنل + هم‌دسته
    $own = $db->prepare("SELECT days, panel_id, cat FROM orders WHERE user_id = ? AND config_username = ? LIMIT 1");
    $own->execute([$user_id, $targetUsername]);
    $orderMeta = $own->fetch(PDO::FETCH_ASSOC);
    if (!$orderMeta && !isBotAdmin($user_id)) {
        if (!empty($update['callback_query']['id'])) {
            sendTelegram('answerCallbackQuery', [
                'callback_query_id' => $update['callback_query']['id'],
                'text' => 'این سرویس متعلق به شما نیست',
                'show_alert' => true
            ]);
        }
        exit();
    }
    $p = $plans[$planKey];
    if (isset($p['is_active']) && (int)$p['is_active'] === 0) {
        if (!empty($update['callback_query']['id'])) {
            sendTelegram('answerCallbackQuery', [
                'callback_query_id' => $update['callback_query']['id'],
                'text' => 'این بسته دیگر فعال نیست. از خرید اشتراک جدید استفاده کن.',
                'show_alert' => true
            ]);
        }
        exit();
    }
    $orderPanelIdChk = $orderMeta ? (int)($orderMeta['panel_id'] ?? 0) : 0;
    $defIdChk = (int)(getDefaultPanel($db)['id'] ?? 0);
    if ($orderPanelIdChk <= 0) {
        $orderPanelIdChk = $defIdChk;
    }
    $planPanelIdChk = (int)($p['panel_id'] ?? 0);
    if ($planPanelIdChk <= 0) {
        $planPanelIdChk = $defIdChk;
    }
    if ($orderPanelIdChk > 0 && $planPanelIdChk !== $orderPanelIdChk) {
        if (!empty($update['callback_query']['id'])) {
            sendTelegram('answerCallbackQuery', [
                'callback_query_id' => $update['callback_query']['id'],
                'text' => 'این بسته برای تمدید این سرویس مناسب نیست.',
                'show_alert' => true
            ]);
        }
        exit();
    }
    $svcCatChk = $orderMeta ? strtolower(trim((string)($orderMeta['cat'] ?? ''))) : '';
    if ($svcCatChk === '') {
        $svcCatChk = ($orderMeta && (int)($orderMeta['days'] ?? 0) === 0) ? 'vip' : 'monthly';
    }
    $pCatChk = strtolower(trim((string)($p['cat'] ?? '')));
    if ($pCatChk === '') {
        $pCatChk = ((int)($p['days'] ?? 0) === 0) ? 'vip' : 'monthly';
    }
    if ($svcCatChk !== '' && $pCatChk !== $svcCatChk) {
        if (!empty($update['callback_query']['id'])) {
            sendTelegram('answerCallbackQuery', [
                'callback_query_id' => $update['callback_query']['id'],
                'text' => 'این بسته هم‌نوع سرویس شما نیست. از خرید اشتراک جدید استفاده کن.',
                'show_alert' => true
            ]);
        }
        exit();
    }
    if (!isPlanCategoryActiveForPanel($db, $orderPanelIdChk, $svcCatChk)
        || !isPlanCategoryActiveForPanel($db, $planPanelIdChk, $pCatChk)) {
        if (!empty($update['callback_query']['id'])) {
            sendTelegram('answerCallbackQuery', [
                'callback_query_id' => $update['callback_query']['id'],
                'text' => 'این دسته پلن فعلاً فعال نیست. از خرید اشتراک جدید استفاده کن.',
                'show_alert' => true
            ]);
        }
        exit();
    }

    if (!empty($update['callback_query']['id'])) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    }
    // فاکتور را پیام جدید بفرست (نه edit روی عکس)
    issueInvoice($chat_id, $user_id, $planKey, $targetUsername, 'renew', $plans, $db, null);
    exit();
}

if ($callback_data === 'help_payment_guide') {
    $guideText = "📚 <b>پرداخت در ۳ قدم</b>\n\n"
               . "۱️⃣ روی <b>شماره کارت</b> یا <b>مبلغ ریال</b> بزن تا کپی بشه\n"
               . "۲️⃣ تو همراه‌بانک همون مبلغ رو واریز کن (دقیقاً همون عدد)\n"
               . "۳️⃣ اگر خودکار تأیید نشد، عکس فیش رو <b>همین‌جا</b> بفرست ⚡️";

    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => $guideText,
        'parse_mode' => 'HTML'
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'apply_coupon:') === 0) {
    $parts = explode(':', str_replace('apply_coupon:', '', $callback_data));
    $actionType = $parts[0]; $planKey = $parts[1]; $targetUser = $parts[2];

    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["ask_coupon:{$actionType}:{$planKey}:{$targetUser}", $user_id]);
    $cancelBtn = json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به فاکتور', 'callback_data' => "cancel_coupon:{$actionType}:{$planKey}:{$targetUser}", 'style' => 'danger']]]]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🏷 <b>کد تخفیف</b>\n\nکدت رو بفرست تا روی فاکتور اعمال بشه:",
        'parse_mode' => 'HTML',
        'reply_markup' => $cancelBtn
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'cancel_coupon:') === 0) {
    $parts = explode(':', str_replace('cancel_coupon:', '', $callback_data));
    issueInvoice($chat_id, $user_id, $parts[1], $parts[2], $parts[0], $plans, $db, $update['callback_query']['message']['message_id']);
    exit();
}

if ($callback_data && strpos($callback_data, 'pay_wallet:') === 0) {
    $parts = explode(':', str_replace('pay_wallet:', '', $callback_data));
    $actionType = $parts[0]; $planKey = $parts[1]; $targetUser = $parts[2]; $couponCode = $parts[3] ?? null;

    if (isset($plans[$planKey])) {
        $p = $plans[$planKey];
        $finalPrice = $p['price'];

        if ($couponCode) {
            $stmt = $db->prepare("SELECT * FROM coupons WHERE code = ? AND used_count < max_uses");
            $stmt->execute([$couponCode]);
            $cp = $stmt->fetch();
            if ($cp) {
                $expOk = true;
                if (!empty($cp['expires_at'])) {
                    $expTs = strtotime((string)$cp['expires_at']);
                    if ($expTs && $expTs < time()) $expOk = false;
                }
                if ($expOk) {
                    $finalPrice = round($p['price'] * (1 - ($cp['discount_percent'] / 100)));
                    $db->prepare("UPDATE coupons SET used_count = used_count + 1 WHERE id = ?")->execute([$cp['id']]);
                }
            }
        }

        $stmt = $db->prepare("SELECT balance FROM users WHERE user_id = ?");
        $stmt->execute([$user_id]);
        $currentBalance = (int)$stmt->fetchColumn();

        if ($currentBalance < $finalPrice) {
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => "😕 موجودی کیف پولت کافی نیست.\nاول از بخش کیف پول شارژ کن، بعد دوباره پرداخت بزن."
            ]);
            exit();
        }

        $stmt = $db->prepare("INSERT INTO payments (user_id, plan_key, price, photo_file_id, target_username, action_type, coupon_code, status) VALUES (?, ?, ?, 'WALLET_PAY', ?, ?, ?, 'approved')");
        $stmt->execute([$user_id, $planKey, $finalPrice, $targetUser, $actionType, $couponCode]);
        $payId = (int)$db->lastInsertId();

        $adj = adjustWalletBalance($db, $user_id, -$finalPrice, 'pay_wallet', 'payment', (string)$payId, $actionType . ':' . $planKey);
        if (empty($adj['ok'])) {
            // برگرداندن فاکتور اگر کسر موجودی شکست بخورد
            try { $db->prepare("UPDATE payments SET status = 'rejected' WHERE id = ?")->execute([$payId]); } catch (Exception $e) {}
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => "❌ موجودی کیف پول کافی نیست یا خطای ثبت رخ داد. دوباره تلاش کنید."
            ]);
            exit();
        }
        $newBalance = (int)$adj['balance'];
        recordAccountingFromPayment($db, [
            'id' => $payId,
            'user_id' => $user_id,
            'plan_key' => $planKey,
            'price' => $finalPrice,
            'photo_file_id' => 'WALLET_PAY',
            'target_username' => $targetUser,
            'action_type' => $actionType,
            'status' => 'approved',
        ], 'wallet');
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
        // پیش‌فاکتور کارت‌به‌کارت همان خرید دیگر لازم نیست
        if (function_exists('cancelAwaitingInvoices')) {
            cancelAwaitingInvoices($db, $user_id);
        }

        if ($actionType === 'renew') {
            $volRenew = inviteeVolumeWithBonus($db, $user_id, $p['vol']);
            // پنل از سفارش موجود؛ نه لزوماً پلن انتخاب‌شده
            if (!isset($orderPanel) || !is_array($orderPanel)) {
                try {
                    $stOp = $db->prepare('SELECT * FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 1');
                    $stOp->execute([$targetUser]);
                    $ordRow = $stOp->fetch(PDO::FETCH_ASSOC);
                    $orderPanel = panelFromOrder($ordRow ?: [], $db);
                } catch (Exception $e) {
                    $orderPanel = getPanelById(panelIdFromPlan($p));
                }
            }
            $ren = renewPasargadUser($targetUser, $volRenew, $p['days'], $orderPanel);
            $newVol = jet_sync_order_after_renew($db, $targetUser, $ren, (int)$p['days'], (float)$volRenew, (float)$volRenew);

            if ((int)$p['days'] <= 0) {
                $daysLabel = "نامحدود (VIP)";
            } elseif (is_array($ren) && !empty($ren['expire']) && (int)$ren['expire'] > time()) {
                $rd = (int)ceil(((int)$ren['expire'] - time()) / 86400);
                $daysLabel = "{$rd} روز مانده (مانده قبلی + پلن)";
            } else {
                $daysLabel = "{$p['days']} روز";
            }
            $bonusNote = ($volRenew > (float)$p['vol']) ? "\n🎁 حجم هدیه دعوت اعمال شد." : '';
            $msg = "✅ <b>تمدید انجام شد — ادامه بده!</b>\n\n"
                 . "👤 نام کاربری: <code>{$targetUser}</code>\n"
                 . "📊 سقف حجم فعلی: <b>{$newVol}</b> گیگ (باقی‌مانده + پلن جدید)\n"
                 . "⏰ اعتبار جدید: {$daysLabel}{$bonusNote}\n\n"
                 . "💵 کسرشده: " . number_format($finalPrice) . " تومان\n"
                 . "💰 مانده کیف پول: " . number_format($newBalance) . " تومان\n\n"
                 . "📱 تو اپ یک‌بار <b>Update Sub / Refresh</b> بزن تا تغییرات اعمال بشه.";

            sendTelegram('editMessageText', [
                'chat_id' => $chat_id,
                'message_id' => $update['callback_query']['message']['message_id'],
                'text' => $msg,
                'parse_mode' => 'HTML'
            ]);
        } else {
            $volCreate = inviteeVolumeWithBonus($db, $user_id, $p['vol']);
            $panelForCreate = (isset($panel) ? $panel : getPanelById(panelIdFromPlan($p)));
            $res = createPasargadUserUnique($targetUser, $volCreate, $p['days'], $panelForCreate, $user_id, (int)($p['limit_ip'] ?? 0));
            if (!empty($res['_error'])) {
                // برگشت مبلغ به کیف در صورت شکست ساخت
                try {
                    adjustWalletBalance($db, $user_id, $finalPrice, 'refund_create_fail', 'plan', (string)$planKey, 'بازگشت پس از شکست ساخت پنل');
                } catch (Exception $e) {
                }
                sendTelegram('editMessageText', [
                    'chat_id' => $chat_id,
                    'message_id' => $update['callback_query']['message']['message_id'],
                    'text' => "⚠️ پرداخت از کیف انجام شد ولی ساخت سرویس در پنل ناموفق بود.\nمبلغ به کیف برگشت.\nخطا: <code>" . htmlspecialchars((string)($res['detail'] ?? $res['_error'])) . "</code>\nبا پشتیبانی تماس بگیر.",
                    'parse_mode' => 'HTML'
                ]);
                exit();
            }
            $targetUser = (string)($res['_final_username'] ?? $targetUser);
            $subUrl = $res['subscription_url'] ?? '';
            if (strpos($subUrl, 'http') !== 0) {
                $subUrl = normalizeSubscriptionUrl($subUrl, isset($panelForCreate) ? $panelForCreate : (isset($panel) ? $panel : null));
            }

            $orderPassword = rand(1000, 9999);
            $panelRow = isset($panel) ? $panel : getPanelById(panelIdFromPlan($p));
            $pCat = strtolower(trim((string)($p['cat'] ?? '')));
            if ($pCat === '') { $pCat = ((int)($p['days'] ?? 0) === 0) ? 'vip' : 'monthly'; }
            insertBotOrder($db, $user_id, $targetUser, $orderPassword, $subUrl, $volCreate, (int)$p['days'], (int)($panelRow['id'] ?? 0), $pCat, (string)$planKey);

            $qrUrl = getQRCodeUrl($subUrl);
            $daysLabel = $p['days'] > 0 ? "{$p['days']} روز" : "بدون تاریخ انقضا (VIP)";
            $bonusNote = ($volCreate > (float)$p['vol']) ? "\n🎁 <b>هدیه دعوت:</b> +۵٪ حجم اضافه (جمع {$volCreate} گیگ) — جدا از ۱۰٪ تخفیف قیمت" : '';
                        $dlApp = defined('DIRECT_DOWNLOAD_URL') ? DIRECT_DOWNLOAD_URL : 'https://github.com/majidbusy09-blip/jetconfig-vpn/releases';
            $successMsg = "🎉 <b>اشتراکت آماده‌ست!</b>\n\n"
                        . "👤 نام کاربری: <code>{$targetUser}</code>\n"
                        . "🔑 رمز اپ: <code>{$orderPassword}</code>\n"
                        . "📊 حجم: " . formatVolumeGb($volCreate) . "{$bonusNote}\n"
                        . "⏰ اعتبار: {$daysLabel}\n\n"
                        . "💵 مبلغ: " . number_format($finalPrice) . " تومان\n"
                        . "💰 مانده کیف پول: " . number_format($newBalance) . " تومان\n\n"
                        . "📱 با همین اطلاعات وارد اپ <a href=\"{$dlApp}\">JET VPN</a> شو و لذت ببر 🚀\n\n"
                        . "🔗 لینک ساب:\n<code>{$subUrl}</code>\n\n"
                        . "📲 <b>سایر برنامه‌ها</b> — لینک ساب را کپی کن یا QR را اسکن کن:\n"
                        . "• اندروید: <a href=\"https://majid6064.ir/download/\">v2rayNG</a> · <a href=\"https://majid6064.ir/download/\">Happ</a>\n"
                        . "• آیفون: <a href=\"https://apps.apple.com/app/streisand/id6450534064\">Streisand</a> · <a href=\"https://apps.apple.com/app/happ-proxy-utility/id6504287215\">Happ</a>\n"
                        . "• ویندوز: <a href=\"https://github.com/2dust/v2rayN/releases\">v2rayN</a> · <a href=\"https://github.com/Happ-proxy/happ-desktop/releases\">Happ</a>";

            $dl_inline = array_merge(
                serviceInfoChipRow(
                    remainingTimeChipLabel($daysLabel),
                    remainingVolumeChipLabel((float)$volCreate, 0)
                ),
                [[['text' => '📂 سرویس‌های من', 'callback_data' => 'my_services_list']]]
            );

            sendTelegram('sendPhoto', [
                'chat_id' => $chat_id,
                'photo' => $qrUrl,
                'caption' => $successMsg,
                'parse_mode' => 'HTML',
                'reply_markup' => json_encode(['inline_keyboard' => $dl_inline])
            ]);
        }

        checkAndRewardReferral($user_id, $db, $username, (int)$finalPrice);
        sendReferralInviteNudge($db, $user_id);
        postOrderToLogChannel($p['title'], $actionType);

        sendTelegram('sendMessage', [
            'chat_id' => ADMIN_ID,
            'text' => "⚡️ <b>خرید خودکار از کیف پول!</b>\n\n👤 کاربر: @" . htmlspecialchars($username) . " (<code>{$user_id}</code>)\n📦 پلن: {$p['title']}\n💰 مبلغ: " . number_format($finalPrice) . " تومان",
            'parse_mode' => 'HTML'
        ]);
    }
    exit();
}


function getAdminKeyboard() {
    // منوی اصلی خلوت: کارهای روزانه + زیرمنوها (قابلیت‌ها حذف نشده‌اند)
    return json_encode([
        'inline_keyboard' => [
            [['text' => '⏳ فیش‌های در انتظار', 'callback_data' => 'adm_pending_pays', 'style' => 'primary']],
            [
                ['text' => '👥 کاربران', 'callback_data' => 'adm_users_list:0'],
                ['text' => '📦 سرویس‌ها', 'callback_data' => 'adm_services_hub'],
            ],
            [
                ['text' => '📊 مالی و آمار', 'callback_data' => 'adm_fin_menu'],
                ['text' => '📢 پیام همگانی', 'callback_data' => 'adm_broadcast_start'],
            ],
            [
                ['text' => '⚙️ تنظیمات', 'callback_data' => 'adm_settings_menu'],
                ['text' => '🛠 سیستم', 'callback_data' => 'adm_system_menu'],
            ],
            [
                ['text' => '🏪 نمایندگان', 'callback_data' => 'adm_rs_menu', 'style' => 'primary'],
            ],
        ]
    ], JSON_UNESCAPED_UNICODE);
}

function getAdminDashboard($db) {
    try {
        $totalUsers = (int)$db->query("SELECT COUNT(*) FROM users")->fetchColumn();
        // فقط فیش واقعی در صف (نه پیش‌فاکتور)
        $pending = (int)$db->query(
            "SELECT COUNT(*) FROM payments WHERE status = 'pending'
             AND photo_file_id IS NOT NULL
             AND photo_file_id NOT IN ('AWAITING_RECEIPT','WALLET_PAY','SMS_AUTO','ADMIN_CREDIT','ADMIN_DEBIT')"
        )->fetchColumn();
        // درآمد نقدی امروز = کارت‌به‌کارت (خرید مستقیم + شارژ کیف) — بدون خرید از کیف
        $todayIncome = (int)$db->query(
            "SELECT COALESCE(SUM(price),0) FROM payments
             WHERE status = 'approved'
               AND DATE(created_at) = CURDATE()
               AND (photo_file_id IS NULL OR photo_file_id NOT IN ('WALLET_PAY','ADMIN_CREDIT','ADMIN_DEBIT'))"
        )->fetchColumn();
        return "👑 <b>پنل مدیریت JetConfig</b>\n\n"
             . "👥 کاربران: <b>{$totalUsers}</b>\n"
             . "⏳ فیش در انتظار: <b>{$pending}</b>\n"
             . "💰 درآمد نقدی امروز: <b>" . number_format($todayIncome) . " تومان</b>\n\n"
             . "بخش مورد نظر را انتخاب کنید:";
    } catch (Exception $e) {
        return "👑 <b>پنل مدیریت JetConfig</b>\n\nبخش مورد نظر را انتخاب کنید:";
    }
}

// پنل ادمین
if ($text === '/setupmenu' && isBotAdmin($user_id)) {
    setSetting($db, 'bot_menu_cmds_v1', '0');
    setSetting($db, 'bot_menu_cmds_v2', '0');
    $rep = ensureBotMenuCommands($db, true);
    $lines = "✅ تلاش برای تنظیم منو انجام شد.\n\n";
    foreach ($rep as $k => $v) {
        if (is_bool($v)) {
            $lines .= ($v ? '✅' : '❌') . " {$k}\n";
        } elseif (is_scalar($v)) {
            $lines .= "• {$k}: " . mb_substr((string)$v, 0, 120) . "\n";
        }
    }
    $lines .= "\nاز اکانت معمولی /start بزن، چت را ببند و باز کن.";
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => $lines,
        'parse_mode' => 'HTML'
    ]);
    exit();
}

if ($text === '/admin' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => getAdminDashboard($db),
        'parse_mode' => 'HTML',
        'reply_markup' => getAdminKeyboard()
    ]);
    exit();
}

// زیرمنوی سرویس‌ها (لیست همه + مدیریت با نام)
if ($callback_data === 'adm_services_hub' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '📋 لیست همه سرویس‌ها', 'callback_data' => 'adm_services_list:0', 'style' => 'primary']],
            [['text' => '🔍 مدیریت با نام کانفیگ', 'callback_data' => 'adm_manage_service_start']],
            [['text' => '🔙 بازگشت به پنل', 'callback_data' => 'adm_back', 'style' => 'danger']],
        ]
    ], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📦 <b>سرویس‌ها</b>\n\n"
               . "• <b>لیست همه</b>: مرور صفحه‌به‌صفحه\n"
               . "• <b>مدیریت با نام</b>: جستجو و ویرایش یک کانفیگ",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

// زیرمنوی تنظیمات (پلن، کارت، تخفیف، دعوت، تست، دکمه‌ها)
if ($callback_data === 'adm_settings_menu' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '📦 پلن‌ها', 'callback_data' => 'adm_plans_menu'], ['text' => '💳 کارت بانکی', 'callback_data' => 'adm_cards_menu']],
            [['text' => '🏷 کد تخفیف', 'callback_data' => 'adm_coupons'], ['text' => '🎁 پاداش دعوت', 'callback_data' => 'adm_ref_setting']],
            [['text' => '🎁 مدیریت تست', 'callback_data' => 'adm_test_menu'], ['text' => '🎛 وضعیت دکمه‌ها', 'callback_data' => 'adm_features_toggle_menu']],
            [['text' => '🔙 بازگشت به پنل', 'callback_data' => 'adm_back', 'style' => 'danger']],
        ]
    ], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "⚙️ <b>تنظیمات</b>\n\nپلن‌ها، پرداخت، دعوت و نمایش دکمه‌های ربات.",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

// زیرمنوی سیستم (بکاپ + لاگ AI + ادمین‌ها)
if ($callback_data === 'adm_system_menu' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $rows = [
        [['text' => '🖥 مدیریت پنل‌ها', 'callback_data' => 'adm_panels_menu', 'style' => 'primary']],
        [['text' => '💾 بکاپ', 'callback_data' => 'adm_get_backup']],
        [['text' => '🤖 لاگ پشتیبانی AI', 'callback_data' => 'adm_ai_support:0']],
        [['text' => '👨‍💼 لاگ پشتیبانی انسانی', 'callback_data' => 'adm_human_support:0', 'style' => 'primary']],
    ];
    if (isBotOwner($user_id)) {
        $rows[] = [['text' => '👑 مدیریت ادمین‌ها', 'callback_data' => 'adm_admins_menu', 'style' => 'primary']];
    }
    $rows[] = [['text' => '🔙 بازگشت به پنل', 'callback_data' => 'adm_back', 'style' => 'danger']];
    $kb = json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🛠 <b>سیستم</b>\n\nبکاپ دیتابیس، لاگ پشتیبانی و مدیریت ادمین.",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}


// ── مدیریت پنل‌ها (زیرساخت چندپنلی) ──
if ($callback_data === 'adm_panels_menu' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    ensureMultiPanelSchema($db);
    $panels = listBotPanels($db, false);
    $lines = "🖥 <b>مدیریت پنل‌ها</b>\n\n";
    $lines .= "پلن‌های فعلی روی پنل پیش‌فرض می‌مانند.\nبرای سرویس جدید، پنل جدا اضافه کن و موقع ساخت پلن انتخابش کن.\n\n";
    $kbRows = [];
    if (empty($panels)) {
        $lines .= "هنوز پنلی در دیتابیس نیست — از config به‌عنوان پیش‌فرض استفاده می‌شود.\n";
    } else {
        foreach ($panels as $pn) {
            $mark = !empty($pn['is_default']) ? '⭐ ' : '';
            $act = !empty($pn['is_active']) ? '✅' : '⏸';
            $lines .= "{$act} {$mark}<b>" . htmlspecialchars($pn['name']) . "</b>\n";
            $lines .= "   نوع: <code>" . htmlspecialchars($pn['type']) . "</code> | id: <code>{$pn['id']}</code>\n";
            $lines .= "   " . htmlspecialchars(mb_substr((string)$pn['base_url'], 0, 48)) . "\n\n";
            $gShow = getPanelGroupIdsSetting($db, (int)$pn['id']);
            if ($gShow === '' || $gShow === '0') {
                $gShow = '— تنظیم نشده';
            }
            $lines .= "   گروه‌ها: <code>" . htmlspecialchars($gShow) . "</code>

";
            $kbRows[] = [
                ['text' => '🔌 تست ' . $pn['name'], 'callback_data' => 'adm_panel_test:' . $pn['id']],
                ['text' => '⭐ پیش‌فرض', 'callback_data' => 'adm_panel_default:' . $pn['id']],
            ];
            $kbRows[] = [
                ['text' => '📁 گروه‌های ' . $pn['name'], 'callback_data' => 'adm_panel_groups:' . $pn['id'], 'style' => 'primary'],
            ];
        }
    }
    $kbRows[] = [['text' => '➕ افزودن پنل جدید', 'callback_data' => 'adm_panel_add', 'style' => 'success']];
    $kbRows[] = [['text' => '🔙 بازگشت سیستم', 'callback_data' => 'adm_system_menu', 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $lines,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $kbRows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_panel_test:') === 0 && isBotAdmin($user_id)) {
    $pid = (int)str_replace('adm_panel_test:', '', $callback_data);
    $panel = getPanelById($pid);
    $info = getPasargadToken(true, $panel);
    $ok = !empty($info['ok']);
    $msg = ($ok ? "✅ اتصال موفق\n" : "❌ اتصال ناموفق\n")
         . "پنل: <b>" . htmlspecialchars($panel['name'] ?? '-') . "</b>\n"
         . "HTTP: <code>" . (int)($info['http'] ?? 0) . "</code>\n"
         . "URL: <code>" . htmlspecialchars((string)($info['url'] ?? '')) . "</code>\n";
    if (!$ok) {
        $msg .= "جزئیات: <code>" . htmlspecialchars(mb_substr((string)(($info['curl_error'] ?? '') . ' ' . ($info['body_preview'] ?? '')), 0, 200)) . "</code>";
    }
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => $ok ? 'اتصال OK' : 'خطای اتصال', 'show_alert' => true]);
    sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => $msg, 'parse_mode' => 'HTML']);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_panel_default:') === 0 && isBotAdmin($user_id)) {
    $pid = (int)str_replace('adm_panel_default:', '', $callback_data);
    ensureMultiPanelSchema($db);
    $db->exec("UPDATE bot_panels SET is_default = 0");
    $db->prepare("UPDATE bot_panels SET is_default = 1, is_active = 1 WHERE id = ?")->execute([$pid]);
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'پیش‌فرض شد']);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ پنل #{$pid} پیش‌فرض شد.",
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🖥 لیست پنل‌ها', 'callback_data' => 'adm_panels_menu']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}


// ── گروه‌های هر پنل (group_ids اختصاصی) ──
if ($callback_data && strpos($callback_data, 'adm_panel_groups:') === 0 && isBotAdmin($user_id)) {
    $pid = (int)str_replace('adm_panel_groups:', '', $callback_data);
    $pn = getPanelById($pid, $db);
    if (!$pn) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'پنل یافت نشد', 'show_alert' => true]);
        exit();
    }
    $cur = getPanelGroupIdsSetting($db, $pid);
    if ($cur === '' || $cur === '0') {
        $curDisp = '— هنوز تنظیم نشده';
    } else {
        $curDisp = $cur;
    }
    $name = htmlspecialchars((string)$pn['name']);
    $txt = "📁 <b>گروه‌های پنل: {$name}</b>\n"
         . "id پنل: <code>{$pid}</code>\n"
         . "group_ids فعلی: <code>" . htmlspecialchars($curDisp) . "</code>\n\n"
         . "هر پنل گروه خودش را دارد؛ روی ساخت تست/خرید/دستی همان پنل اعمال می‌شود.\n\n"
         . "۱) لیست گروه‌ها از API\n"
         . "۲) خواندن از کانفیگ سالم همین پنل\n"
         . "۳) تنظیم دستی ID";
    $kb = [
        [['text' => '📋 لیست گروه‌ها (API)', 'callback_data' => 'adm_panel_glist:' . $pid]],
        [['text' => '📥 خواندن از نام کاربری', 'callback_data' => 'adm_panel_gfrom:' . $pid]],
        [['text' => '⚙️ تنظیم دستی ID', 'callback_data' => 'adm_panel_gset:' . $pid]],
        [['text' => '🗑 پاک کردن گروه این پنل', 'callback_data' => 'adm_panel_gclear:' . $pid, 'style' => 'danger']],
        [['text' => '🔙 لیست پنل‌ها', 'callback_data' => 'adm_panels_menu', 'style' => 'danger']],
    ];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $kb], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_panel_glist:') === 0 && isBotAdmin($user_id)) {
    $pid = (int)str_replace('adm_panel_glist:', '', $callback_data);
    $pn = getPanelById($pid, $db);
    $kb = json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_panel_groups:' . $pid, 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE);
    if (!$pn) {
        sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $update['callback_query']['message']['message_id'], 'text' => 'پنل یافت نشد', 'reply_markup' => $kb]);
        exit();
    }
    $token = getPasargadToken(false, $pn);
    if (!$token) {
        sendTelegram('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $update['callback_query']['message']['message_id'],
            'text' => "❌ توکن پنل <b>" . htmlspecialchars($pn['name']) . "</b> گرفته نشد.",
            'parse_mode' => 'HTML',
            'reply_markup' => $kb,
        ]);
        exit();
    }
    $url = rtrim(getPanelApiBaseEffective($pn), '/') . '/api/groups';
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Accept: application/json'],
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_TIMEOUT => 20,
    ]);
    $res = curl_exec($ch);
    $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    $data = json_decode((string)$res, true);
    $txt = "📁 <b>گروه‌های " . htmlspecialchars($pn['name']) . "</b>\nHTTP: <code>{$http}</code>\n\n";
    $foundIds = [];
    if (is_array($data) && !empty($data)) {
        $groups = isset($data[0]) ? $data : ($data['groups'] ?? $data);
        if (is_array($groups)) {
            foreach ($groups as $g) {
                if (!is_array($g)) continue;
                $id = $g['id'] ?? '?';
                $name = htmlspecialchars((string)($g['name'] ?? $g['title'] ?? '-'));
                $txt .= "• ID: <code>{$id}</code> — <b>{$name}</b>\n";
                if (is_numeric($id)) $foundIds[] = (int)$id;
            }
        }
        if ($foundIds) {
            $txt .= "\n💡 همه IDها: <code>" . implode(',', $foundIds) . "</code>";
        }
    } else {
        $txt .= "پاسخ خالی:\n<code>" . htmlspecialchars(mb_substr((string)$res, 0, 400)) . "</code>\nاز «خواندن از نام کاربری» استفاده کن.";
    }
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb,
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_panel_gfrom:') === 0 && isBotAdmin($user_id)) {
    $pid = (int)str_replace('adm_panel_gfrom:', '', $callback_data);
    setSetting($db, 'adm_ctx_panel_' . $user_id, (string)$pid);
    $db->prepare("UPDATE users SET step = 'adm_panel_read_groups_user' WHERE user_id = ?")->execute([$user_id]);
    $pn = getPanelById($pid, $db);
    $nm = $pn ? htmlspecialchars($pn['name']) : ('#' . $pid);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📥 <b>خواندن گروه — پنل {$nm}</b>\n\nنام کاربری کانفیگ <b>سالم روی همین پنل</b> را بفرست.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_panel_groups:' . $pid, 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}

if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_panel_read_groups_user' && isBotAdmin($user_id)) {
    $uname = trim($text);
    $pid = (int)getSetting($db, 'adm_ctx_panel_' . $user_id, '0');
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $pn = $pid > 0 ? getPanelById($pid, $db) : null;
    $info = getPasargadUser($uname, $pn ?: null);
    $back = 'adm_panel_groups:' . max(1, $pid);
    if (!$info || !is_array($info)) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ کاربر در این پنل پیدا نشد.",
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => $back, 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE),
        ]);
        exit();
    }
    $gids = $info['group_ids'] ?? $info['groups'] ?? null;
    $ids = [];
    if (is_array($gids)) {
        foreach ($gids as $item) {
            if (is_numeric($item)) $ids[] = (int)$item;
            elseif (is_array($item) && isset($item['id'])) $ids[] = (int)$item['id'];
        }
    }
    $ids = array_values(array_unique(array_filter($ids)));
    if ($ids && $pid > 0) {
        $val = implode(',', $ids);
        setPanelGroupIdsSetting($db, $pid, $val);
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ از <code>{$uname}</code>\nپنل <code>{$pid}</code>\ngroup_ids: <code>{$val}</code>",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 گروه‌های پنل', 'callback_data' => $back]]]], JSON_UNESCAPED_UNICODE),
        ]);
    } else {
        $preview = htmlspecialchars(mb_substr(json_encode($info, JSON_UNESCAPED_UNICODE), 0, 400));
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "⚠️ group_ids واضح نبود.\n<code>{$preview}</code>",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => $back, 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE),
        ]);
    }
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_panel_gset:') === 0 && isBotAdmin($user_id)) {
    $pid = (int)str_replace('adm_panel_gset:', '', $callback_data);
    setSetting($db, 'adm_ctx_panel_' . $user_id, (string)$pid);
    $db->prepare("UPDATE users SET step = 'adm_panel_set_group_ids' WHERE user_id = ?")->execute([$user_id]);
    $cur = getPanelGroupIdsSetting($db, $pid);
    $pn = getPanelById($pid, $db);
    $nm = $pn ? htmlspecialchars($pn['name']) : ('#' . $pid);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "⚙️ <b>تنظیم group_ids — {$nm}</b>\n\nفعلی: <code>" . htmlspecialchars($cur !== '' ? $cur : '—') . "</code>\n\nفقط عدد (مثال <code>1</code> یا <code>2,5</code>)\nخالی: <code>0</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_panel_groups:' . $pid, 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}

if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_panel_set_group_ids' && isBotAdmin($user_id)) {
    $pid = (int)getSetting($db, 'adm_ctx_panel_' . $user_id, '0');
    $val = preg_replace('/[^0-9,]/', '', trim($text));
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if ($pid <= 0) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => 'پنل مشخص نیست.']);
        exit();
    }
    setPanelGroupIdsSetting($db, $pid, ($val === '' || $val === '0') ? '0' : $val);
    $show = ($val === '' || $val === '0') ? 'خالی' : $val;
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ group_ids پنل <code>{$pid}</code> → <code>{$show}</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 گروه‌های پنل', 'callback_data' => 'adm_panel_groups:' . $pid]]]], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_panel_gclear:') === 0 && isBotAdmin($user_id)) {
    $pid = (int)str_replace('adm_panel_gclear:', '', $callback_data);
    setPanelGroupIdsSetting($db, $pid, '0');
    $pn = getPanelById($pid, $db);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "✅ گروه پنل <b>" . htmlspecialchars($pn['name'] ?? (string)$pid) . "</b> پاک شد.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '📁 گروه‌های پنل', 'callback_data' => 'adm_panel_groups:' . $pid]],
            [['text' => '🔙 لیست پنل‌ها', 'callback_data' => 'adm_panels_menu', 'style' => 'danger']],
        ]], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}

if ($callback_data === 'adm_panel_add' && isBotAdmin($user_id)) {
    setSetting($db, 'panel_draft_' . $user_id, json_encode([], JSON_UNESCAPED_UNICODE));
    $db->prepare("UPDATE users SET step = 'adm_panel_wiz_name' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "➕ <b>ویزارد افزودن پنل</b> — مرحله ۱ از ۵\n"
                . "──────────────────\n"
                . "یک نام نمایشی برای این پنل بفرست.\n\n"
                . "📌 <b>راهنما:</b>\n"
                . "• فقط برای خودت در ادمین دیده می‌شود\n"
                . "• کوتاه و واضح باشد\n\n"
                . "✅ مثال‌ها:\n"
                . "• <code>پاسارگاد اصلی</code>\n"
                . "• <code>اینترنت ملی</code>\n"
                . "• <code>نامحدود ویژه</code>\n"
                . "• <code>پنل پشتیبان</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_panel_wiz_cancel', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data === 'adm_panel_wiz_cancel' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    setSetting($db, 'panel_draft_' . $user_id, '');
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'لغو شد']);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => '❌ افزودن پنل لغو شد.',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🖥 مدیریت پنل‌ها', 'callback_data' => 'adm_panels_menu']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text && ($currentUser['step'] ?? '') === 'adm_panel_wiz_name' && isBotAdmin($user_id)) {
    $name = trim($text);
    if (mb_strlen($name) < 2 || mb_strlen($name) > 80) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ نام باید بین ۲ تا ۸۰ حرف باشد. دوباره بفرست.",
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_panel_wiz_cancel', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
        ]);
        exit();
    }
    $draft = ['name' => $name];
    setSetting($db, 'panel_draft_' . $user_id, json_encode($draft, JSON_UNESCAPED_UNICODE));
    $db->prepare("UPDATE users SET step = 'adm_panel_wiz_type' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "➕ <b>ویزارد افزودن پنل</b> — مرحله ۲ از ۵
"
                . "──────────────────
"
                . "نام: <b>" . htmlspecialchars($name) . "</b>

"
                . "نوع <b>اصلی</b> پنل را انتخاب کن.
"
                . "برندهای فرعی (زئوس، نوا، BNB و …) معمولاً از یکی از این‌ها ساخته شده‌اند.

"
                . "📌 فقط گزینه‌های ✅ الان درایور آماده دارند.
⏳ یعنی به‌زودی.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '✅ پاسارگاد (Pasargad)', 'callback_data' => 'adm_panel_wiz_type:pasargad', 'style' => 'success']],
            [['text' => '✅ مرزبان (Marzban)', 'callback_data' => 'adm_panel_wiz_type:marzban', 'style' => 'success']],
            [['text' => '⏳ ثنایی / 3x-UI', 'callback_data' => 'adm_panel_wiz_type:sanaei']],
            [['text' => '⏳ هیدیفای (Hiddify)', 'callback_data' => 'adm_panel_wiz_type:hiddify']],
            [['text' => '⏳ مرزنشین (Marzneshin)', 'callback_data' => 'adm_panel_wiz_type:marzneshin']],
            [['text' => '❌ انصراف', 'callback_data' => 'adm_panel_wiz_cancel', 'style' => 'danger']],
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_panel_wiz_type:') === 0 && isBotAdmin($user_id)) {
    $type = str_replace('adm_panel_wiz_type:', '', $callback_data);
    // درایورهای آماده (marzban ≈ همان API خانواده پاسارگاد)
    $ready = ['pasargad' => 'پاسارگاد', 'marzban' => 'مرزبان'];
    $soon = ['sanaei' => 'ثنایی/3x-UI', 'hiddify' => 'هیدیفای', 'marzneshin' => 'مرزنشین'];
    if (isset($soon[$type])) {
        sendTelegram('answerCallbackQuery', [
            'callback_query_id' => $update['callback_query']['id'],
            'text' => 'درایور «' . $soon[$type] . '» هنوز آماده نیست. فعلاً پاسارگاد یا مرزبان را انتخاب کن.',
            'show_alert' => true
        ]);
        exit();
    }
    if (!isset($ready[$type])) {
        sendTelegram('answerCallbackQuery', [
            'callback_query_id' => $update['callback_query']['id'],
            'text' => 'نوع نامعتبر',
            'show_alert' => true
        ]);
        exit();
    }
    $draft = json_decode((string)getSetting($db, 'panel_draft_' . $user_id, '{}'), true);
    if (!is_array($draft)) $draft = [];
    // ذخیره نوع انتخابی؛ اجرای API فعلاً با موتور پاسارگاد (خانواده مرزبان)
    $draft['type'] = $type;
    $draft['driver'] = 'pasargad';
    setSetting($db, 'panel_draft_' . $user_id, json_encode($draft, JSON_UNESCAPED_UNICODE));
    $db->prepare("UPDATE users SET step = 'adm_panel_wiz_url' WHERE user_id = ?")->execute([$user_id]);
    $typeLabel = $ready[$type];
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'نوع: ' . $typeLabel]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "➕ <b>ویزارد افزودن پنل</b> — مرحله ۳ از ۵
"
                . "──────────────────
"
                . "نوع: <b>" . htmlspecialchars($typeLabel) . "</b> ✅ درایور فعال

"
                . "آدرس پایه (Base URL) پنل را بفرست.

"
                . "📌 <b>راهنما:</b>
"
                . "• با <code>https://</code> شروع شود
"
                . "• بدون اسلش پایانی
"
                . "• آدرس ورود پنل ادمین (نه لینک ساب)

"
                . "✅ مثال: <code>https://panel.example.com</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_panel_wiz_cancel', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}


if ($text && ($currentUser['step'] ?? '') === 'adm_panel_wiz_url' && isBotAdmin($user_id)) {
    $url = trim($text);
    $url = rtrim($url, '/');
    if (!preg_match('#^https?://#i', $url)) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ آدرس باید با http:// یا https:// شروع شود.\nمثال: <code>https://panel.example.com</code>",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_panel_wiz_cancel', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
        ]);
        exit();
    }
    $draft = json_decode((string)getSetting($db, 'panel_draft_' . $user_id, '{}'), true);
    if (!is_array($draft)) $draft = [];
    $draft['base_url'] = $url;
    $draft['public_url'] = $url;
    setSetting($db, 'panel_draft_' . $user_id, json_encode($draft, JSON_UNESCAPED_UNICODE));
    $db->prepare("UPDATE users SET step = 'adm_panel_wiz_user' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "➕ <b>ویزارد افزودن پنل</b> — مرحله ۴ از ۵\n"
                . "──────────────────\n"
                . "آدرس: <code>" . htmlspecialchars($url) . "</code>\n\n"
                . "نام کاربری <b>ادمین پنل</b> را بفرست.\n\n"
                . "📌 <b>راهنما:</b>\n"
                . "• همان یوزری که با آن وارد پنل وب می‌شوی\n"
                . "• نه نام کاربری مشتری / کانفیگ\n"
                . "• معمولاً چیزی شبیه <code>admin</code> یا ایمیل ادمین",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_panel_wiz_cancel', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text && ($currentUser['step'] ?? '') === 'adm_panel_wiz_user' && isBotAdmin($user_id)) {
    $uname = trim($text);
    if ($uname === '' || mb_strlen($uname) > 120) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ نام کاربری نامعتبر است. دوباره بفرست.']);
        exit();
    }
    $draft = json_decode((string)getSetting($db, 'panel_draft_' . $user_id, '{}'), true);
    if (!is_array($draft)) $draft = [];
    $draft['username'] = $uname;
    setSetting($db, 'panel_draft_' . $user_id, json_encode($draft, JSON_UNESCAPED_UNICODE));
    $db->prepare("UPDATE users SET step = 'adm_panel_wiz_pass' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "➕ <b>ویزارد افزودن پنل</b> — مرحله ۵ از ۵\n"
                . "──────────────────\n"
                . "یوزر: <code>" . htmlspecialchars($uname) . "</code>\n\n"
                . "رمز عبور <b>ادمین پنل</b> را بفرست.\n\n"
                . "📌 <b>راهنما:</b>\n"
                . "• همان رمز ورود به پنل وب\n"
                . "• در محیط امن بفرست\n"
                . "• فقط ادمین‌های ربات به این بخش دسترسی دارند",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_panel_wiz_cancel', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text && ($currentUser['step'] ?? '') === 'adm_panel_wiz_pass' && isBotAdmin($user_id)) {
    $pass = trim($text);
    if ($pass === '') {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ رمز خالی است. دوباره بفرست.']);
        exit();
    }
    $draft = json_decode((string)getSetting($db, 'panel_draft_' . $user_id, '{}'), true);
    if (!is_array($draft) || empty($draft['name']) || empty($draft['base_url']) || empty($draft['username'])) {
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ پیش‌نویس ناقص است. از اول ویزارد را شروع کن.']);
        exit();
    }
    $draft['password'] = $pass;
    $draft['type'] = $draft['type'] ?? 'pasargad';
    setSetting($db, 'panel_draft_' . $user_id, json_encode($draft, JSON_UNESCAPED_UNICODE));
    $db->prepare("UPDATE users SET step = 'adm_panel_wiz_confirm' WHERE user_id = ?")->execute([$user_id]);
    $passMask = str_repeat('*', min(8, max(4, mb_strlen($pass))));
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "📋 <b>تأیید نهایی پنل</b>\n"
                . "──────────────────\n"
                . "🏷 نام: <b>" . htmlspecialchars($draft['name']) . "</b>\n"
                . "🧩 نوع: <code>" . htmlspecialchars($draft['type']) . "</code>\n"
                . "🔗 آدرس: <code>" . htmlspecialchars($draft['base_url']) . "</code>\n"
                . "👤 یوزر: <code>" . htmlspecialchars($draft['username']) . "</code>\n"
                . "🔑 رمز: <code>{$passMask}</code>\n\n"
                . "اگر درست است «ثبت و تست اتصال» را بزن.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '✅ ثبت و تست اتصال', 'callback_data' => 'adm_panel_wiz_save', 'style' => 'success']],
            [['text' => '❌ انصراف', 'callback_data' => 'adm_panel_wiz_cancel', 'style' => 'danger']],
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data === 'adm_panel_wiz_save' && isBotAdmin($user_id)) {
    $draft = json_decode((string)getSetting($db, 'panel_draft_' . $user_id, '{}'), true);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if (!is_array($draft) || empty($draft['name']) || empty($draft['base_url']) || empty($draft['username']) || empty($draft['password'])) {
        setSetting($db, 'panel_draft_' . $user_id, '');
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'پیش‌نویس ناقص', 'show_alert' => true]);
        exit();
    }
    ensureMultiPanelSchema($db);
    $st = $db->prepare("INSERT INTO bot_panels (name, type, base_url, public_url, username, password, use_worker, is_default, is_active) VALUES (?, ?, ?, ?, ?, ?, 0, 0, 1)");
    $st->execute([
        $draft['name'],
        $draft['type'] ?? 'pasargad',
        rtrim($draft['base_url'], '/'),
        rtrim($draft['public_url'] ?? $draft['base_url'], '/'),
        $draft['username'],
        $draft['password'],
    ]);
    $newId = (int)$db->lastInsertId();
    setSetting($db, 'panel_draft_' . $user_id, '');
    $test = getPasargadToken(true, getPanelById($newId));
    $ok = !empty($test['ok']);
    $testLine = $ok
        ? "✅ تست اتصال موفق بود — پنل آماده استفاده است.\nحالا می‌توانی هنگام ساخت پلن جدید این پنل را انتخاب کنی."
        : "⚠️ پنل ذخیره شد ولی تست اتصال ناموفق بود.\nHTTP: <code>" . (int)($test['http'] ?? 0) . "</code>\n"
          . "جزئیات: <code>" . htmlspecialchars(mb_substr((string)(($test['curl_error'] ?? '') . ' ' . ($test['body_preview'] ?? '')), 0, 180)) . "</code>\n"
          . "آدرس/یوزر/رمز را از لیست پنل‌ها دوباره بررسی کن.";
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => $ok ? 'ثبت شد' : 'ذخیره شد — تست ناموفق']);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ پنل <b>" . htmlspecialchars($draft['name']) . "</b> ثبت شد (id: <code>{$newId}</code>).\n\n{$testLine}",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '🖥 لیست پنل‌ها', 'callback_data' => 'adm_panels_menu']],
            [['text' => '📦 مدیریت پلن‌ها', 'callback_data' => 'adm_plans_menu']],
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

// ── مدیریت ادمین‌ها (فقط مالک اصلی) ──
if ($callback_data === 'adm_admins_menu' && isBotOwner($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    ensureBotAdminsTable($db);
    $extra = getExtraAdmins($db);
    $lines = "👑 <b>مدیریت ادمین‌ها</b>\n\n";
    $lines .= "⭐ مالک اصلی: <code>" . (int)ADMIN_ID . "</code> (غیرقابل حذف)\n\n";
    if (empty($extra)) {
        $lines .= "هنوز ادمین اضافه‌ای ثبت نشده.\n";
    } else {
        $lines .= "ادمین‌های اضافه:\n";
        foreach ($extra as $i => $row) {
            $aid = (int)$row['user_id'];
            $uname = '';
            try {
                $st = $db->prepare("SELECT username FROM users WHERE user_id = ? LIMIT 1");
                $st->execute([$aid]);
                $u = $st->fetchColumn();
                if ($u) {
                    $uname = ' @' . ltrim((string)$u, '@');
                }
            } catch (Exception $e) {}
            $lines .= ($i + 1) . ") <code>{$aid}</code>{$uname}\n";
        }
    }
    $lines .= "\nفقط مالک اصلی می‌تواند ادمین اضافه یا حذف کند.";
    $kbRows = [[['text' => '➕ افزودن ادمین', 'callback_data' => 'adm_admin_add', 'style' => 'success']]];
    foreach ($extra as $row) {
        $aid = (int)$row['user_id'];
        $kbRows[] = [['text' => "🗑 حذف {$aid}", 'callback_data' => "adm_admin_del:{$aid}", 'style' => 'danger']];
    }
    $kbRows[] = [['text' => '🔙 بازگشت سیستم', 'callback_data' => 'adm_system_menu', 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $lines,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $kbRows], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}

if ($callback_data === 'adm_admin_add' && isBotOwner($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_add_admin_id' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "➕ <b>افزودن ادمین</b>\n\n"
               . "شناسه عددی تلگرام (User ID) نفر را بفرست.\n"
               . "طرف بهتر است یک‌بار ربات را /start کرده باشد.\n\n"
               . "مثال: <code>123456789</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 انصراف', 'callback_data' => 'adm_admins_menu', 'style' => 'danger']]]]),
    ]);
    exit();
}

if ($text && ($currentUser['step'] ?? '') === 'adm_add_admin_id' && isBotOwner($user_id)) {
    $newId = (int)preg_replace('/\D+/', '', trim($text));
    if ($newId <= 0) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ آیدی نامعتبر است. فقط عدد بفرست.",
        ]);
        exit();
    }
    if (isBotOwner($newId)) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "ℹ️ این آیدی همان مالک اصلی است؛ نیازی به افزودن نیست.",
        ]);
        exit();
    }
    ensureBotAdminsTable($db);
    try {
        $db->prepare("INSERT INTO bot_admins (user_id, added_by) VALUES (?, ?) ON DUPLICATE KEY UPDATE added_by = VALUES(added_by)")
           ->execute([$newId, $user_id]);
    } catch (Exception $e) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ خطا در ذخیره."]);
        exit();
    }
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    try {
        sendTelegram('setMyCommands', [
            'commands' => json_encode([
                ['command' => 'start', 'description' => 'شروع و منوی اصلی'],
                ['command' => 'admin', 'description' => 'پنل مدیریت'],
            ], JSON_UNESCAPED_UNICODE),
            'scope' => json_encode(['type' => 'chat', 'chat_id' => $newId]),
        ]);
    } catch (Exception $e) {}
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ کاربر <code>{$newId}</code> به لیست ادمین اضافه شد.\nاز /admin می‌تواند پنل را باز کند.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '👑 لیست ادمین‌ها', 'callback_data' => 'adm_admins_menu']]]]),
    ]);
    sendTelegram('sendMessage', [
        'chat_id' => $newId,
        'text' => "👑 دسترسی <b>ادمین ربات JetConfig</b> برای شما فعال شد.\nدستور /admin را بزن.",
        'parse_mode' => 'HTML',
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_admin_del:') === 0 && isBotOwner($user_id)) {
    $delId = (int)substr($callback_data, strlen('adm_admin_del:'));
    if ($delId > 0 && !isBotOwner($delId)) {
        ensureBotAdminsTable($db);
        $db->prepare("DELETE FROM bot_admins WHERE user_id = ?")->execute([$delId]);
        try {
            sendTelegram('setMyCommands', [
                'commands' => json_encode([
                    ['command' => 'start', 'description' => 'شروع و منوی اصلی'],
                ], JSON_UNESCAPED_UNICODE),
                'scope' => json_encode(['type' => 'chat', 'chat_id' => $delId]),
            ]);
        } catch (Exception $e) {}
        sendTelegram('sendMessage', [
            'chat_id' => $delId,
            'text' => "ℹ️ دسترسی ادمین ربات برای شما برداشته شد.",
        ]);
    }
    // بازسازی منوی لیست
    ensureBotAdminsTable($db);
    $extra = getExtraAdmins($db);
    $lines = "👑 <b>مدیریت ادمین‌ها</b>\n\n";
    $lines .= "⭐ مالک اصلی: <code>" . (int)ADMIN_ID . "</code> (غیرقابل حذف)\n\n";
    if (empty($extra)) {
        $lines .= "لیست ادمین اضافه خالی است.\n";
    } else {
        $lines .= "ادمین‌های اضافه:\n";
        foreach ($extra as $i => $row) {
            $aid = (int)$row['user_id'];
            $lines .= ($i + 1) . ") <code>{$aid}</code>\n";
        }
    }
    $kbRows = [[['text' => '➕ افزودن ادمین', 'callback_data' => 'adm_admin_add', 'style' => 'success']]];
    foreach ($extra as $row) {
        $aid = (int)$row['user_id'];
        $kbRows[] = [['text' => "🗑 حذف {$aid}", 'callback_data' => "adm_admin_del:{$aid}", 'style' => 'danger']];
    }
    $kbRows[] = [['text' => '🔙 بازگشت سیستم', 'callback_data' => 'adm_system_menu', 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $lines,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $kbRows], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}

// واگذاری کانفیگ دستی: ساخت خودکار در پنل + ربات
if ($callback_data === 'adm_manual_config_start' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_mc_uid' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "➕ <b>ساخت و واگذاری سرویس</b>\n\n"
               . "ربات خودش در <b>پنل</b> و <b>دیتابیس</b> اکانت می‌سازد.\n\n"
               . "مرحله ۱ از ۳\n"
               . "شناسه عددی کاربر (User ID) را بفرستید:",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به پنل', 'callback_data' => 'adm_back', 'style' => 'danger']]]])
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_mc_for:') === 0 && isBotAdmin($user_id)) {
    $targetUid = (int)str_replace('adm_mc_for:', '', $callback_data);
    $st = $db->prepare("SELECT user_id, username FROM users WHERE user_id = ?");
    $st->execute([$targetUid]);
    $tu = $st->fetch();
    if (!$tu) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'کاربر یافت نشد', 'show_alert' => true]);
        exit();
    }
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["adm_mc_vol|{$targetUid}", $user_id]);
    $uname = $tu['username'] ?? '-';
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "➕ <b>ساخت سرویس برای کاربر</b>\n"
               . "<code>{$targetUid}</code> (@{$uname})\n\n"
               . "مرحله ۲ از ۳\n"
               . "حجم را به <b>گیگابایت</b> بفرستید:\n"
               . "(مثال: <code>50</code> یا <code>0.1</code>)",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_user_view:' . $targetUid]]]])
    ]);
    exit();
}

if ($text && ($currentUser['step'] ?? '') === 'adm_mc_uid' && isBotAdmin($user_id)) {
    $targetUid = (int)preg_replace('/\D/', '', $text);
    if ($targetUid <= 0) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ شناسه نامعتبر. دوباره بفرستید:']);
        exit();
    }
    $st = $db->prepare("SELECT user_id, username FROM users WHERE user_id = ?");
    $st->execute([$targetUid]);
    $tu = $st->fetch();
    if (!$tu) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ کاربر <code>{$targetUid}</code> در ربات نیست.",
            'parse_mode' => 'HTML'
        ]);
        exit();
    }
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["adm_mc_vol|{$targetUid}", $user_id]);
    $uname = $tu['username'] ?? '-';
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ کاربر: <code>{$targetUid}</code> (@{$uname})\n\n"
               . "مرحله ۲ از ۳\n"
               . "حجم را به <b>گیگابایت</b> بفرستید:\n"
               . "(مثال: <code>50</code> یا <code>0.1</code>)",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_back', 'style' => 'danger']]]])
    ]);
    exit();
}

if ($text !== null && $text !== '' && strpos(($currentUser['step'] ?? ''), 'adm_mc_vol|') === 0 && isBotAdmin($user_id)) {
    $targetUid = (int)str_replace('adm_mc_vol|', '', $currentUser['step']);
    $rawVol = trim($text);
    $rawVol = str_replace(['۰','۱','۲','۳','۴','۵','۶','۷','۸','۹', ',', ' '], ['0','1','2','3','4','5','6','7','8','9', '.', ''], $rawVol);
    if (in_array(mb_strtolower($rawVol), ['نامحدود', 'unlimited', 'inf'], true)) {
        $volGb = 0.0;
    } elseif ($rawVol === '' || !is_numeric($rawVol) || (float)$rawVol < 0) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ حجم نامعتبر. عدد ≥ ۰ بفرستید (۰ = نامحدود):']);
        exit();
    } else {
        $volGb = (float)$rawVol;
    }
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["adm_mc_days|{$targetUid}|{$volGb}", $user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ حجم: <b>" . formatVolumeGb($volGb) . "</b>\n\n"
               . "مرحله ۳ از ۳\n"
               . "مدت اعتبار (روز) را بفرستید:\n"
               . "• ماهانه: مثلاً <code>30</code>\n"
               . "• VIP بدون انقضا: <code>0</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_back', 'style' => 'danger']]]])
    ]);
    exit();
}


if ($text !== null && $text !== '' && strpos(($currentUser['step'] ?? ''), 'adm_mc_days|') === 0 && isBotAdmin($user_id)) {
    $rest = str_replace('adm_mc_days|', '', $currentUser['step']);
    $parts = explode('|', $rest);
    if (count($parts) < 2) {
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ خطا. از اول شروع کنید.', 'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 پنل', 'callback_data' => 'adm_back', 'style' => 'danger']]]])]);
        exit();
    }
    $targetUid = (int)$parts[0];
    $volGb = (float)$parts[1];
    if (!preg_match('/^\d+$/', trim($text))) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ فقط عدد روز (مثل 30 یا 0):']);
        exit();
    }
    $days = (int)trim($text);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    $panels = listActivePanels($db);
    if (!$panels) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ هیچ پنل فعالی تعریف نشده.']);
        exit();
    }
    $rows = [];
    foreach ($panels as $pn) {
        $lab = ($pn['name'] ?? ('#' . $pn['id']));
        if (!empty($pn['is_default'])) $lab .= ' ⭐';
        $rows[] = [['text' => '🖥 ' . $lab, 'callback_data' => 'adm_mc_do:' . $targetUid . '|' . $volGb . '|' . $days . '|' . (int)$pn['id']]];
    }
    $rows[] = [['text' => '❌ انصراف', 'callback_data' => 'adm_user_view:' . $targetUid, 'style' => 'danger']];
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ حجم: <b>" . formatVolumeGb($volGb) . "</b> | مدت: <b>" . ($days > 0 ? "{$days} روز" : "بدون انقضا") . "</b>\n\n"
               . "مرحله ۴ — <b>پنل ساخت</b> را انتخاب کن:",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_mc_do:') === 0 && isBotAdmin($user_id)) {
    $raw = substr($callback_data, strlen('adm_mc_do:'));
    $parts = explode('|', $raw);
    if (count($parts) < 4) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'داده ناقص', 'show_alert' => true]);
        exit();
    }
    $targetUid = (int)$parts[0];
    $volGb = (float)$parts[1];
    $days = (int)$parts[2];
    $panelId = (int)$parts[3];
    $panel = getPanelById($panelId, $db);
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'در حال ساخت...']);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "⏳ ساخت روی پنل <b>" . htmlspecialchars((string)($panel['name'] ?? $panelId)) . "</b> ...",
        'parse_mode' => 'HTML',
    ]);

    $cfgUsername = 'man_' . $targetUid . '_' . rand(10, 99);
    for ($i = 0; $i < 5; $i++) {
        $chk = getPasargadUser($cfgUsername, $panel);
        if (!$chk || (is_array($chk) && empty($chk['username']))) break;
        $cfgUsername = 'man_' . $targetUid . '_' . rand(100, 999);
    }
    $cfgPassword = rand(1000, 9999);
    $res = createPasargadUser($cfgUsername, $volGb, $days, $panel);

    if (!$res || !is_array($res) || !empty($res['_error']) || empty($res['subscription_url'])) {
        $err = is_array($res) ? ($res['detail'] ?? $res['_error'] ?? json_encode($res, JSON_UNESCAPED_UNICODE)) : 'پاسخ نامعتبر از پنل';
        if (is_array($err)) $err = json_encode($err, JSON_UNESCAPED_UNICODE);
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ <b>ساخت در پنل ناموفق بود</b>\n\n"
                   . "پنل: <code>" . htmlspecialchars((string)($panel['name'] ?? '')) . "</code>\n"
                   . "نام: <code>{$cfgUsername}</code>\n"
                   . "خطا: <code>" . htmlspecialchars(mb_substr((string)$err, 0, 400)) . "</code>",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '🔄 تلاش دوباره', 'callback_data' => 'adm_mc_for:' . $targetUid]],
                [['text' => '👑 پنل', 'callback_data' => 'adm_back']]
            ]])
        ]);
        exit();
    }

    $subUrl = normalizeSubscriptionUrl($res['subscription_url'] ?? '', $panel);

    if ($days > 0) {
        $wantedExpire = time() + ($days * 86400);
        $panelExpire = parsePanelExpire($res['expire'] ?? 0);
        if ($panelExpire <= time() + 3600) {
            modifyPasargadUserDirect($cfgUsername, null, $days, 'active', $panel);
            $tokenFix = getPasargadToken(false, $panel);
            if ($tokenFix) {
                $editUrl = getPanelApiBaseEffective($panel) . '/api/user/' . rawurlencode($cfgUsername);
                $payloadFix = json_encode(['expire' => $wantedExpire, 'status' => 'active']);
                $chFix = curl_init($editUrl);
                $optsFix = panelCurlBaseOpts(12);
                $optsFix[CURLOPT_CUSTOMREQUEST] = 'PUT';
                $optsFix[CURLOPT_POSTFIELDS] = $payloadFix;
                $optsFix[CURLOPT_HTTPHEADER] = ['Authorization: Bearer ' . $tokenFix, 'Content-Type: application/json'];
                curl_setopt_array($chFix, $optsFix);
                curl_exec($chFix);
                curl_close($chFix);
            }
        }
    }

    $mcCat = ((int)$days === 0) ? 'vip' : 'monthly';
    insertBotOrder($db, $targetUid, $cfgUsername, $cfgPassword, $subUrl, $volGb, $days, (int)($panel['id'] ?? $panelId), $mcCat, null);

    $daysLabel = $days > 0 ? "{$days} روز" : "بدون انقضا (VIP)";
    $userMsg = "🎁 <b>یک سرویس اختصاصی برات ساخته شد!</b>\n\n"
             . "👤 نام کاربری: <code>{$cfgUsername}</code>\n"
             . "🔑 رمز اپ: <code>{$cfgPassword}</code>\n"
             . "📊 حجم: " . formatVolumeGb($volGb) . "\n"
             . "⏰ مدت: {$daysLabel}\n\n"
             . "🔗 لینک ساب:\n<code>{$subUrl}</code>\n\n"
             . "تو اپ یک‌بار Refresh بزن 🚀";
    $kbManualUser = serviceInfoChipRow(
        remainingTimeChipLabel($daysLabel),
        remainingVolumeChipLabel((float)$volGb, 0)
    );
    sendTelegram('sendMessage', [
        'chat_id' => $targetUid,
        'text' => $userMsg,
        'parse_mode' => 'HTML',
        'disable_web_page_preview' => true,
        'reply_markup' => json_encode(['inline_keyboard' => $kbManualUser], JSON_UNESCAPED_UNICODE),
    ]);

    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ <b>سرویس دستی آماده شد</b>\n\n"
               . "کاربر: <code>{$targetUid}</code>\n"
               . "نام کاربری: <code>{$cfgUsername}</code>\n"
               . "رمز اپ: <code>{$cfgPassword}</code>\n"
               . "حجم: {$volGb}GB | مدت: {$daysLabel}\n"
               . "پنل: <b>" . htmlspecialchars((string)($panel['name'] ?? '')) . "</b>\n"
               . "لینک:\n<code>{$subUrl}</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '👤 مشاهده کاربر', 'callback_data' => 'adm_user_view:' . $targetUid]],
            [['text' => '⚙️ مدیریت سرویس', 'callback_data' => 'adm_svc_open:' . $cfgUsername]],
            [['text' => '➕ سرویس دیگر', 'callback_data' => 'adm_manual_config_start']],
            [['text' => '👑 پنل', 'callback_data' => 'adm_back']]
        ]])
    ]);
    exit();
}


// منوی مدیریت وضعیت دکمه‌ها و بخش‌های ربات
if ($callback_data === 'adm_features_toggle_menu' && isBotAdmin($user_id)) {
    $fBuy = isFeatureEnabled($db, 'btn_buy') ? 'روشن 🟢' : 'خاموش 🔴';
    $fTest = isFeatureEnabled($db, 'btn_test') ? 'روشن 🟢' : 'خاموش 🔴';
    $fWallet = isFeatureEnabled($db, 'btn_wallet') ? 'روشن 🟢' : 'خاموش 🔴';
    $fTransfer = isFeatureEnabled($db, 'btn_transfer') ? 'روشن 🟢' : 'خاموش 🔴';
    $fRef = isFeatureEnabled($db, 'btn_ref') ? 'روشن 🟢' : 'خاموش 🔴';
    $fSupport = isFeatureEnabled($db, 'btn_support') ? 'روشن 🟢' : 'خاموش 🔴';

    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => "🛍 خرید اشتراک: {$fBuy}", 'callback_data' => 'adm_toggle_feat:btn_buy']],
            [['text' => "🎁 تست رایگان: {$fTest}", 'callback_data' => 'adm_toggle_feat:btn_test']],
            [['text' => "💳 شارژ کیف پول: {$fWallet}", 'callback_data' => 'adm_toggle_feat:btn_wallet']],
            [['text' => "🔄 انتقال اعتبار: {$fTransfer}", 'callback_data' => 'adm_toggle_feat:btn_transfer']],
            [['text' => "👥 زیرمجموعه‌گیری: {$fRef}", 'callback_data' => 'adm_toggle_feat:btn_ref']],
            [['text' => "☎️ پشتیبانی: {$fSupport}", 'callback_data' => 'adm_toggle_feat:btn_support']],
            [['text' => '🔙 تنظیمات', 'callback_data' => 'adm_settings_menu', 'style' => 'danger'], ['text' => '👑 پنل', 'callback_data' => 'adm_back']]
        ]
    ]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🎛 <b>کنترل و خاموش/روشن کردن بخش‌های ربات:</b>\n\nبرای تغییر وضعیت هر بخش، روی دکمه مربوط به آن بزنید:",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_toggle_feat:') === 0 && isBotAdmin($user_id)) {
    $featKey = str_replace('adm_toggle_feat:', '', $callback_data);
    $currentVal = getSetting($db, $featKey, '1');
    $newVal = ($currentVal === '1') ? '0' : '1';
    setSetting($db, $featKey, $newVal);

    sendTelegram('answerCallbackQuery', [
        'callback_query_id' => $update['callback_query']['id'],
        'text' => '✅ وضعیت تغییر کرد.'
    ]);

    $fBuy = isFeatureEnabled($db, 'btn_buy') ? 'روشن 🟢' : 'خاموش 🔴';
    $fTest = isFeatureEnabled($db, 'btn_test') ? 'روشن 🟢' : 'خاموش 🔴';
    $fWallet = isFeatureEnabled($db, 'btn_wallet') ? 'روشن 🟢' : 'خاموش 🔴';
    $fTransfer = isFeatureEnabled($db, 'btn_transfer') ? 'روشن 🟢' : 'خاموش 🔴';
    $fRef = isFeatureEnabled($db, 'btn_ref') ? 'روشن 🟢' : 'خاموش 🔴';
    $fSupport = isFeatureEnabled($db, 'btn_support') ? 'روشن 🟢' : 'خاموش 🔴';

    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => "🛍 خرید اشتراک: {$fBuy}", 'callback_data' => 'adm_toggle_feat:btn_buy']],
            [['text' => "🎁 تست رایگان: {$fTest}", 'callback_data' => 'adm_toggle_feat:btn_test']],
            [['text' => "💳 شارژ کیف پول: {$fWallet}", 'callback_data' => 'adm_toggle_feat:btn_wallet']],
            [['text' => "🔄 انتقال اعتبار: {$fTransfer}", 'callback_data' => 'adm_toggle_feat:btn_transfer']],
            [['text' => "👥 زیرمجموعه‌گیری: {$fRef}", 'callback_data' => 'adm_toggle_feat:btn_ref']],
            [['text' => "☎️ پشتیبانی: {$fSupport}", 'callback_data' => 'adm_toggle_feat:btn_support']],
            [['text' => '🔙 تنظیمات', 'callback_data' => 'adm_settings_menu', 'style' => 'danger'], ['text' => '👑 پنل', 'callback_data' => 'adm_back']]
        ]
    ]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🎛 <b>کنترل و خاموش/روشن کردن بخش‌های ربات:</b>\n\nبرای تغییر وضعیت هر بخش، روی دکمه مربوط به آن بزنید:",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

// جستجو و مدیریت دستی سرویس توسط ادمین
if ($callback_data === 'adm_manage_service_start' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_input_search_srv' WHERE user_id = ?")->execute([$user_id]);
    $cancelBtn = json_encode(['inline_keyboard' => [
        [['text' => '🔙 سرویس‌ها', 'callback_data' => 'adm_services_hub', 'style' => 'danger'], ['text' => '👑 پنل', 'callback_data' => 'adm_back']]
    ]], JSON_UNESCAPED_UNICODE);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🔍 <b>جستجوی سرویس و کانفیگ:</b>\n\nلطفاً <b>نام کاربری کانفیگ</b> مورد نظر را ارسال فرمایید (مثال: <code>M01</code> یا <code>ali_vpn</code>):",
        'parse_mode' => 'HTML',
        'reply_markup' => $cancelBtn
    ]);
    exit();
}

/** user_id مالک یک کانفیگ از جدول orders */
function getOrderOwnerUid($db, $configUsername) {
    try {
        $st = $db->prepare("SELECT user_id FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 1");
        $st->execute([$configUsername]);
        $uid = (int)($st->fetchColumn() ?: 0);
        return $uid > 0 ? $uid : 0;
    } catch (Exception $e) {
        return 0;
    }
}

/** پیام اطلاع‌رسانی به کاربر (خطا را نادیده می‌گیرد) */
function notifyUserFromBot($uid, $text, $replyMarkup = null) {
    if ($uid <= 0 || $text === '') {
        return false;
    }
    $payload = [
        'chat_id' => $uid,
        'text' => $text,
        'parse_mode' => 'HTML',
        'disable_web_page_preview' => true,
    ];
    if ($replyMarkup) {
        $payload['reply_markup'] = is_string($replyMarkup) ? $replyMarkup : json_encode($replyMarkup, JSON_UNESCAPED_UNICODE);
    }
    $r = sendTelegram('sendMessage', $payload);
    return !empty($r['ok']);
}

function showAdminServiceCard($chat_id, $targetUsername, $db, $editMsgId = null) {
    // صاحب سرویس در ربات (از جدول orders + users)
    $ownerUid = 0;
    $ownerUname = '';
    try {
        $st = $db->prepare(
            "SELECT o.user_id, u.username
             FROM orders o
             LEFT JOIN users u ON u.user_id = o.user_id
             WHERE o.config_username = ?
             ORDER BY o.id DESC LIMIT 1"
        );
        $st->execute([$targetUsername]);
        $own = $st->fetch(PDO::FETCH_ASSOC);
        if ($own) {
            $ownerUid = (int)($own['user_id'] ?? 0);
            $ownerUname = trim((string)($own['username'] ?? ''));
        }
    } catch (Exception $e) { /* ignore */ }

    $ownerLine = '👤 مالک ربات: <b>—</b>';
    if ($ownerUid > 0) {
        $tg = $ownerUname !== '' ? '@' . htmlspecialchars($ownerUname) : 'بدون یوزرنیم';
        $ownerLine = "👤 مالک ربات: <b>{$tg}</b>\n🆔 ID: <code>{$ownerUid}</code>";
    }

    $info = getPasargadUser($targetUsername, panelFromUsername($targetUsername, $db));
    if (!$info || (is_array($info) && isset($info['detail']) && !isset($info['username']) && !isset($info['status']))) {
        $msg = "❌ کانفیگ با نام <code>{$targetUsername}</code> در سرور پنل مربوطه یافت نشد!\n\n"
             . $ownerLine;
        $kbRows = [];
        if ($ownerUid > 0) {
            $kbRows[] = [['text' => '👤 مشاهده کاربر', 'callback_data' => 'adm_user_view:' . $ownerUid, 'style' => 'primary']];
        }
        $kbRows[] = [['text' => '🔙 بازگشت', 'callback_data' => 'adm_manage_service_start', 'style' => 'danger']];
        $kb = json_encode(['inline_keyboard' => $kbRows], JSON_UNESCAPED_UNICODE);
        if ($editMsgId) sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $editMsgId, 'text' => $msg, 'parse_mode' => 'HTML', 'reply_markup' => $kb]);
        else sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => $msg, 'parse_mode' => 'HTML', 'reply_markup' => $kb]);
        return;
    }

    $usedGb = round(($info['used_traffic'] ?? 0) / (1024*1024*1024), 2);
    $totalGb = ($info['data_limit'] > 0) ? round($info['data_limit'] / (1024*1024*1024), 1) . ' GB' : 'نامحدود';
    $status = $info['status'] ?? 'نامشخص';
    $statusLabel = ($status === 'active') ? 'فعال 🟢' : 'غیرفعال / مسدود 🔴';

    $expireTimestamp = parsePanelExpire($info['expire'] ?? 0);
    // بعضی پنل‌ها expire را در فیلدهای دیگر هم می‌گذارند
    if ($expireTimestamp <= 0 && !empty($info['expire_date'])) {
        $expireTimestamp = parsePanelExpire($info['expire_date']);
    }

    $expireTxt = 'نامحدود / بدون انقضا ♾';
    if ($expireTimestamp > 0) {
        $diff = (int)ceil(($expireTimestamp - time()) / 86400);
        $expJalali = function_exists('formatJalaliDateTime')
            ? formatJalaliDateTime(date('Y-m-d H:i:s', $expireTimestamp))
            : date('Y-m-d H:i', $expireTimestamp);
        if ($diff > 0) {
            $expireTxt = "{$diff} روز مانده ({$expJalali})";
        } else {
            $expireTxt = "منقضی شده ({$expJalali})";
        }
    }

    $cardText = "⚙️ <b>مدیریت دستی سرویس:</b> <code>{$targetUsername}</code>\n"
              . $ownerLine . "\n"
              . "──────────────────\n"
              . "▫️ وضعیت: <b>{$statusLabel}</b>\n"
              . "📊 مصرف: <b>{$usedGb} GB از {$totalGb}</b>\n"
              . "⏰ مهلت اعتبار: <b>{$expireTxt}</b>\n"
              . "──────────────────\n"
              . "عملیات مورد نظر را انتخاب فرمایید:";

    $toggleStatusData = ($status === 'active') ? "adm_srv_status:{$targetUsername}:disabled" : "adm_srv_status:{$targetUsername}:active";
    $toggleStatusText = ($status === 'active') ? "🔴 غیرفعال / مسدود کردن" : "🟢 فعال‌سازی مجدد";

    $kbRows = [
        [['text' => '➕ افزودن ۱۰ گیگ', 'callback_data' => "adm_srv_addvol:{$targetUsername}:10"], ['text' => '➕ افزودن ۳۰ گیگ', 'callback_data' => "adm_srv_addvol:{$targetUsername}:30"]],
        [['text' => '⏳ تمدید ۳۰ روزه', 'callback_data' => "adm_srv_addday:{$targetUsername}:30"], ['text' => '⏳ تمدید ۶۰ روزه', 'callback_data' => "adm_srv_addday:{$targetUsername}:60"]],
        [['text' => '✏️ ➕ حجم دلخواه', 'callback_data' => "adm_srv_customvol:{$targetUsername}"], ['text' => '✏️ ⏳ تمدید دلخواه (روز)', 'callback_data' => "adm_srv_customday:{$targetUsername}"]],
        [['text' => $toggleStatusText, 'callback_data' => $toggleStatusData]],
        [['text' => '🗑 حذف سرویس…', 'callback_data' => "adm_svc_del_ask:{$targetUsername}", 'style' => 'danger']],
    ];
    if ($ownerUid > 0) {
        $kbRows[] = [
            ['text' => '👤 مشاهده کاربر مالک', 'callback_data' => 'adm_user_view:' . $ownerUid, 'style' => 'primary'],
            ['text' => '✉️ پیام به کاربر', 'callback_data' => 'adm_msg_user:' . $ownerUid],
        ];
    }
    $kbRows[] = [['text' => '🔙 جستجوی دیگر', 'callback_data' => 'adm_manage_service_start', 'style' => 'danger'], ['text' => '👑 پنل اصلی', 'callback_data' => 'adm_back']];
    $kb = json_encode(['inline_keyboard' => $kbRows], JSON_UNESCAPED_UNICODE);

    if ($editMsgId) sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $editMsgId, 'text' => $cardText, 'parse_mode' => 'HTML', 'reply_markup' => $kb]);
    else sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => $cardText, 'parse_mode' => 'HTML', 'reply_markup' => $kb]);
}

if ($text && $currentUser['step'] === 'adm_input_search_srv' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    showAdminServiceCard($chat_id, trim($text), $db);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_srv_addvol:') === 0 && isBotAdmin($user_id)) {
    $parts = explode(':', str_replace('adm_srv_addvol:', '', $callback_data));
    $targetUsername = $parts[0];
    $addGb = (float)$parts[1];

    $u = getPasargadUser($targetUsername, panelFromUsername($targetUsername, $db));
    if ($u) {
        $currentLimitGb = round(($u['data_limit'] ?? 0) / (1024*1024*1024), 2);
        $newLimitGb = $currentLimitGb + $addGb;
        modifyPasargadUserDirect($targetUsername, $newLimitGb, null, null, panelFromUsername($targetUsername, $db));
        $db->prepare("UPDATE orders SET volume_gb = volume_gb + ?, warned_volume = 0 WHERE config_username = ?")->execute([$addGb, $targetUsername]);
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => "✅ مقدار {$addGb} گیگ به سرویس افزوده شد."]);
        $ownerUid = getOrderOwnerUid($db, $targetUsername);
        $addGbLabel = rtrim(rtrim(number_format($addGb, 2, '.', ''), '0'), '.');
        notifyUserFromBot($ownerUid,
            "🎁 <b>کاربر گرامی، {$addGbLabel} گیگابایت حجم هدیه به سرویس شما اضافه شد!</b> ⚡️\n\n"
            . "👤 سرویس: <code>{$targetUsername}</code>\n\n"
            . "برای اعمال حجم جدید در اپلیکیشن، یک‌بار گزینه <b>Update Sub / Refresh</b> را بزنید.\n\n"
            . "همراه شما هستیم — با قدرت ادامه بده 🚀"
        );
        showAdminServiceCard($chat_id, $targetUsername, $db, $update['callback_query']['message']['message_id']);
    }
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_srv_customvol:') === 0 && isBotAdmin($user_id)) {
    $targetUsername = str_replace('adm_srv_customvol:', '', $callback_data);
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["adm_set_custom_vol:{$targetUsername}", $user_id]);
    $cancelBtn = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_manage_service_start', 'style' => 'danger']]]]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "✏️ <b>افزودن حجم دلخواه به:</b> <code>{$targetUsername}</code>\n\nلطفاً مقدار حجم را به **گیگابایت (GB)** ارسال فرمایید (مثال: <code>25</code> یا <code>50.5</code>):",
        'parse_mode' => 'HTML',
        'reply_markup' => $cancelBtn
    ]);
    exit();
}

if ($text && strpos($currentUser['step'], 'adm_set_custom_vol:') === 0 && isBotAdmin($user_id)) {
    $targetUsername = str_replace('adm_set_custom_vol:', '', $currentUser['step']);
    $addGb = (float)preg_replace('/[^0-9.]/', '', $text);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    if ($addGb > 0) {
        $u = getPasargadUser($targetUsername, panelFromUsername($targetUsername, $db));
        if ($u) {
            $currentLimitGb = round(($u['data_limit'] ?? 0) / (1024*1024*1024), 2);
            $newLimitGb = $currentLimitGb + $addGb;
            modifyPasargadUserDirect($targetUsername, $newLimitGb, null, null, panelFromUsername($targetUsername, $db));
            $db->prepare("UPDATE orders SET volume_gb = volume_gb + ?, warned_volume = 0 WHERE config_username = ?")->execute([$addGb, $targetUsername]);
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ مقدار {$addGb} گیگابایت با موفقیت اضافه شد."]);
            $ownerUid = getOrderOwnerUid($db, $targetUsername);
            $addGbLabel = rtrim(rtrim(number_format($addGb, 2, '.', ''), '0'), '.');
            notifyUserFromBot($ownerUid,
                "🎁 <b>کاربر گرامی، {$addGbLabel} گیگابایت حجم هدیه به سرویس شما اضافه شد!</b> ⚡️\n\n"
                . "👤 سرویس: <code>{$targetUsername}</code>\n\n"
                . "برای اعمال حجم جدید در اپلیکیشن، یک‌بار گزینه <b>Update Sub / Refresh</b> را بزنید.\n\n"
                . "همراه شما هستیم — با قدرت ادامه بده 🚀"
            );
        }
    }
    showAdminServiceCard($chat_id, $targetUsername, $db);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_srv_addday:') === 0 && isBotAdmin($user_id)) {
    $parts = explode(':', str_replace('adm_srv_addday:', '', $callback_data));
    $targetUsername = $parts[0];
    $addDays = (int)$parts[1];

    modifyPasargadUserDirect($targetUsername, null, $addDays, 'active', panelFromUsername($targetUsername, $db));
    $db->prepare("UPDATE orders SET days = days + ?, warned_expire = 0 WHERE config_username = ?")->execute([$addDays, $targetUsername]);
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => "✅ سرویس {$addDays} روز تمدید شد."]);
    $ownerUid = getOrderOwnerUid($db, $targetUsername);
    notifyUserFromBot($ownerUid,
        "🎁 <b>کاربر گرامی، {$addDays} روز اعتبار هدیه به سرویس شما اضافه شد!</b> ⚡️\n\n"
        . "👤 سرویس: <code>{$targetUsername}</code>\n\n"
        . "برای اعمال تغییرات در اپلیکیشن، یک‌بار گزینه <b>Update Sub / Refresh</b> را بزنید.\n\n"
        . "از اعتماد شما سپاسگزاریم — همیشه آنلاین بمون 🌐"
    );
    showAdminServiceCard($chat_id, $targetUsername, $db, $update['callback_query']['message']['message_id']);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_srv_customday:') === 0 && isBotAdmin($user_id)) {
    $targetUsername = str_replace('adm_srv_customday:', '', $callback_data);
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["adm_set_custom_day:{$targetUsername}", $user_id]);
    $cancelBtn = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_manage_service_start', 'style' => 'danger']]]]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "✏️ <b>تمدید مهلت زمانی دلخواه برای:</b> <code>{$targetUsername}</code>\n\nلطفاً تعداد **روزهای تمدید** را ارسال فرمایید (مثال: <code>45</code> یا <code>90</code>):",
        'parse_mode' => 'HTML',
        'reply_markup' => $cancelBtn
    ]);
    exit();
}

if ($text && strpos($currentUser['step'], 'adm_set_custom_day:') === 0 && isBotAdmin($user_id)) {
    $targetUsername = str_replace('adm_set_custom_day:', '', $currentUser['step']);
    $addDays = (int)preg_replace('/[^0-9]/', '', $text);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    if ($addDays > 0) {
        modifyPasargadUserDirect($targetUsername, null, $addDays, 'active', panelFromUsername($targetUsername, $db));
        $db->prepare("UPDATE orders SET days = days + ?, warned_expire = 0 WHERE config_username = ?")->execute([$addDays, $targetUsername]);
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ سرویس به مدت {$addDays} روز با موفقیت تمدید شد."]);
        $ownerUid = getOrderOwnerUid($db, $targetUsername);
        notifyUserFromBot($ownerUid,
            "🎁 <b>کاربر گرامی، {$addDays} روز اعتبار هدیه به سرویس شما اضافه شد!</b> ⚡️\n\n"
            . "👤 سرویس: <code>{$targetUsername}</code>\n\n"
            . "برای اعمال تغییرات در اپلیکیشن، یک‌بار گزینه <b>Update Sub / Refresh</b> را بزنید.\n\n"
            . "از اعتماد شما سپاسگزاریم — همیشه آنلاین بمون 🌐"
        );
    }
    showAdminServiceCard($chat_id, $targetUsername, $db);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_srv_status:') === 0 && isBotAdmin($user_id)) {
    $parts = explode(':', str_replace('adm_srv_status:', '', $callback_data));
    $targetUsername = $parts[0];
    $newStatus = $parts[1];

    modifyPasargadUserDirect($targetUsername, null, null, $newStatus, panelFromUsername($targetUsername, $db));
    $statusTxt = ($newStatus === 'active') ? 'فعال شد' : 'مسدود شد';
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => "✅ وضعیت سرویس: {$statusTxt}"]);
    $ownerUid = getOrderOwnerUid($db, $targetUsername);
    if ($newStatus === 'active') {
        notifyUserFromBot($ownerUid,
            "🟢 <b>سرویس شما فعال شد</b>\n"
            . "──────────────────\n"
            . "👤 سرویس: <code>{$targetUsername}</code>\n\n"
            . "اکنون می‌توانید متصل شوید."
        );
    } else {
        notifyUserFromBot($ownerUid,
            "🔴 <b>سرویس شما موقتاً غیرفعال شد</b>\n"
            . "──────────────────\n"
            . "👤 سرویس: <code>{$targetUsername}</code>\n\n"
            . "در صورت نیاز با پشتیبانی در ارتباط باشید."
        );
    }
    showAdminServiceCard($chat_id, $targetUsername, $db, $update['callback_query']['message']['message_id']);
    exit();
}

if ($callback_data === 'adm_get_backup' && isBotAdmin($user_id)) {
    sendTelegram('answerCallbackQuery', [
        'callback_query_id' => $update['callback_query']['id'],
        'text' => '⏳ در حال ایجاد فایل بکاپ دیتابیس...'
    ]);

    $sqlContent = exportDatabaseSql($db);
    $backupFileName = 'backup_jetconfig_' . date('Y_m_d_H_i') . '.sql';
    $tempFilePath = sys_get_temp_dir() . '/' . $backupFileName;
    file_put_contents($tempFilePath, $sqlContent);

    if (file_exists($tempFilePath)) {
        $cfile = new CURLFile($tempFilePath, 'application/sql', $backupFileName);
        sendTelegram('sendDocument', [
            'chat_id' => ADMIN_ID,
            'document' => $cfile,
            'caption' => "💾 <b>نسخه پشتیبان کامل پایگاه داده JetConfig</b>\n\n📅 تاریخ: <code>" . (function_exists('formatJalaliDateTime') ? formatJalaliDateTime(date('Y-m-d H:i:s')) : date('Y-m-d H:i:s')) . "</code>\n📊 حجم فایل: <b>" . round(filesize($tempFilePath) / 1024, 2) . " KB</b>",
            'parse_mode' => 'HTML'
        ]);
        @unlink($tempFilePath);
    } else {
        sendTelegram('sendMessage', [
            'chat_id' => ADMIN_ID,
            'text' => "❌ خطا در ساخت فایل بکاپ."
        ]);
    }
    exit();
}

if ($callback_data === 'adm_fin_menu' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $resetAt = getSetting($db, 'financial_reset_at', '2020-01-01 00:00:00');
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '📊 حسابداری امروز', 'callback_data' => 'adm_acc_sum:today'], ['text' => '📊 حسابداری ۷ روز', 'callback_data' => 'adm_acc_sum:7days']],
            [['text' => '📊 حسابداری ۳۰ روز', 'callback_data' => 'adm_acc_sum:30days'], ['text' => '📊 حسابداری از مبدأ', 'callback_data' => 'adm_acc_sum:all']],
            [['text' => '📦 فروش بر اساس پلن (۳۰روز)', 'callback_data' => 'adm_acc_plans:30days']],
            [['text' => '💳 آخرین پرداخت‌ها', 'callback_data' => 'adm_acc_recent_pays'], ['text' => '📦 آخرین سرویس‌ها', 'callback_data' => 'adm_acc_recent_svc']],
            [['text' => '📥 CSV حسابداری ۳۰روز', 'callback_data' => 'adm_acc_csv:30days'], ['text' => '📥 CSV از مبدأ', 'callback_data' => 'adm_acc_csv:all']],
            [['text' => '📅 گزارش قدیمی امروز', 'callback_data' => 'adm_fin_rep:today'], ['text' => '📅 گزارش قدیمی ۳۰روز', 'callback_data' => 'adm_fin_rep:30days']],
            [['text' => '📒 دفتر کل کیف‌پول', 'callback_data' => 'adm_ledger_rep:30days'], ['text' => '🔎 مغایرت کیف‌پول', 'callback_data' => 'adm_ledger_reconcile']],
            [['text' => '📋 آخرین سفارش‌ها', 'callback_data' => 'adm_recent_orders']],
            [['text' => '🌐 وضعیت سرور', 'callback_data' => 'adm_fin_server']],
            [['text' => '📅 ریست از تاریخ دلخواه', 'callback_data' => 'adm_fin_reset_date_start']],
            [['text' => '🔄 ریست آمار از همین لحظه', 'callback_data' => 'adm_fin_reset_confirm']],
            [['text' => '🔙 بازگشت به پنل', 'callback_data' => 'adm_back', 'style' => 'danger']]
        ]
    ]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📊 <b>مدیریت مالی و آمار</b>\n\n"
            . "مبدأ فعلی آمار: <code>" . formatJalaliDateTime($resetAt) . "</code>\n\n"
            . "• <b>حسابداری</b>: ورود نقدی، فروش، شارژ کیف\n"
            . "• <b>دفتر کل</b>: حرکت موجودی کیف‌پول\n"
            . "• ریست فقط مبدأ گزارش را عوض می‌کند؛ داده پاک نمی‌شود.",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

// فاز ۴-B: خلاصه حسابداری
if ($callback_data && strpos($callback_data, 'adm_acc_sum:') === 0 && isBotAdmin($user_id)) {
    $period = str_replace('adm_acc_sum:', '', $callback_data);
    if (!in_array($period, ['today', 'yesterday', '7days', '30days', 'all'], true)) {
        $period = 'today';
    }
    $resetAt = getSetting($db, 'financial_reset_at', '2020-01-01 00:00:00');
    $msg = getAccountingSummaryReport($db, $period, $resetAt);
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '🔄 بروزرسانی', 'callback_data' => 'adm_acc_sum:' . $period]],
            [['text' => '🔙 منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]
        ]
    ]);
    adminSendOrEditText($chat_id, $update, $msg, $kb);
    exit();
}

// فاز ۴-B: فروش بر اساس پلن
if ($callback_data && strpos($callback_data, 'adm_acc_plans:') === 0 && isBotAdmin($user_id)) {
    $period = str_replace('adm_acc_plans:', '', $callback_data);
    if (!in_array($period, ['today', '7days', '30days', 'all'], true)) {
        $period = '30days';
    }
    $resetAt = getSetting($db, 'financial_reset_at', '2020-01-01 00:00:00');
    $msg = getAccountingByPlanReport($db, $period, $resetAt);
    $kb = json_encode([
        'inline_keyboard' => [
            [
                ['text' => '۷روز', 'callback_data' => 'adm_acc_plans:7days'],
                ['text' => '۳۰روز', 'callback_data' => 'adm_acc_plans:30days'],
                ['text' => 'از مبدأ', 'callback_data' => 'adm_acc_plans:all'],
            ],
            [['text' => '🔙 منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]
        ]
    ]);
    adminSendOrEditText($chat_id, $update, $msg, $kb);
    exit();
}

// فاز ۴-B: آخرین پرداخت‌ها
if ($callback_data === 'adm_acc_recent_pays' && isBotAdmin($user_id)) {
    $msg = getAccountingRecentPaymentsReport($db, 15);
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '🔄 بروزرسانی', 'callback_data' => 'adm_acc_recent_pays']],
            [['text' => '🔙 منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]
        ]
    ]);
    adminSendOrEditText($chat_id, $update, $msg, $kb);
    exit();
}

// فاز ۴-B: آخرین سرویس‌ها
if ($callback_data === 'adm_acc_recent_svc' && isBotAdmin($user_id)) {
    $msg = getAccountingRecentServicesReport($db, 15);
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '🔄 بروزرسانی', 'callback_data' => 'adm_acc_recent_svc']],
            [['text' => '🔙 منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]
        ]
    ]);
    adminSendOrEditText($chat_id, $update, $msg, $kb);
    exit();
}

// فاز ۴-B: CSV حسابداری (payments)
if ($callback_data && strpos($callback_data, 'adm_acc_csv:') === 0 && isBotAdmin($user_id)) {
    $period = str_replace('adm_acc_csv:', '', $callback_data);
    if (!in_array($period, ['7days', '30days', 'all'], true)) {
        $period = '30days';
    }
    $resetAt = getSetting($db, 'financial_reset_at', '2020-01-01 00:00:00');
    sendTelegram('answerCallbackQuery', [
        'callback_query_id' => $update['callback_query']['id'],
        'text' => 'در حال ساخت CSV حسابداری…'
    ]);
    $exp = exportAccountingPaymentsCsv($db, $period, $resetAt);
    if (empty($exp['ok']) || empty($exp['path']) || !is_file($exp['path'])) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => '❌ ساخت CSV ناموفق: ' . htmlspecialchars($exp['error'] ?? 'unknown'),
            'parse_mode' => 'HTML'
        ]);
        exit();
    }
    $cfile = new CURLFile($exp['path'], 'text/csv', 'accounting_' . ($exp['tag'] ?? $period) . '.csv');
    sendTelegram('sendDocument', [
        'chat_id' => $chat_id,
        'document' => $cfile,
        'caption' => "📥 <b>CSV حسابداری</b>\nبازه: <code>{$period}</code>\nردیف: <b>" . (int)$exp['rows'] . "</b>\nمبدأ: <code>" . formatJalaliDateTime($resetAt) . "</code>",
        'parse_mode' => 'HTML'
    ]);
    @unlink($exp['path']);
    exit();
}

// فاز ۴-B/C: ریست مبدأ آمار از تاریخ دلخواه
if ($callback_data === 'adm_fin_reset_date_start' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_fin_reset_date' WHERE user_id = ?")->execute([$user_id]);
    $kb = json_encode([
        'inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]]
    ]);
    adminSendOrEditText(
        $chat_id,
        $update,
        "📅 <b>ریست مبدأ آمار از تاریخ دلخواه</b>\n\n"
        . "تاریخ را <b>شمسی</b> بفرست:\n"
        . "• <code>1405/06/24</code>\n"
        . "• <code>1405/06/24 14:30</code>\n\n"
        . "<i>میلادی هم قبول است (مثلاً 2026-09-15) ولی در دیتابیس همیشه میلادی ذخیره می‌شود.</i>\n"
        . "داده پاک نمی‌شود؛ فقط گزارش‌ها از آن لحظه به بعد شمرده می‌شوند.",
        $kb
    );
    exit();
}

if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_fin_reset_date' && isBotAdmin($user_id)) {
    $parsed = parseAccountingResetDate($text);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if (!$parsed) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ فرمت تاریخ نامعتبر است.\nمثال شمسی: <code>1405/06/24</code> یا <code>1405/06/24 14:30</code>",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]]])
        ]);
        exit();
    }
    setSetting($db, 'financial_reset_at', $parsed);
    $jalaliShow = formatJalaliDateTime($parsed);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ مبدأ آمار مالی روی <code>{$jalaliShow}</code> تنظیم شد.\nگزارش «از مبدأ» فقط بعد از این تاریخ را می‌شمارد.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '📊 حسابداری از مبدأ', 'callback_data' => 'adm_acc_sum:all'], ['text' => '🔙 منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]]])
    ]);
    exit();
}

// Phase 2: خلاصه دفتر کل کیف پول
if ($callback_data && strpos($callback_data, 'adm_ledger_rep:') === 0 && isBotAdmin($user_id)) {
    $period = str_replace('adm_ledger_rep:', '', $callback_data);
    $msg = getWalletLedgerAdminSummary($db, $period);
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '🔄 بروزرسانی', 'callback_data' => 'adm_ledger_rep:' . $period]],
            [['text' => '🔙 منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]
        ]
    ]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $msg,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

// Phase 3: مغایرت‌گیری موجودی users با جمع ledger
if ($callback_data === 'adm_ledger_reconcile' && isBotAdmin($user_id)) {
    $msg = reconcileWalletBalances($db, 25);
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '🔄 اجرای دوباره', 'callback_data' => 'adm_ledger_reconcile']],
            [['text' => '🔙 منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]
        ]
    ]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $msg,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

// Phase 3: خروجی CSV دفتر کل
if ($callback_data && strpos($callback_data, 'adm_ledger_csv:') === 0 && isBotAdmin($user_id)) {
    $period = str_replace('adm_ledger_csv:', '', $callback_data);
    if (!in_array($period, ['today', '7days', '30days', 'all'], true)) {
        $period = '30days';
    }
    sendTelegram('answerCallbackQuery', [
        'callback_query_id' => $update['callback_query']['id'],
        'text' => 'در حال ساخت فایل CSV…'
    ]);
    $exp = exportWalletLedgerCsv($db, $period);
    if (empty($exp['ok']) || empty($exp['path']) || !is_file($exp['path'])) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => '❌ ساخت CSV ناموفق بود: ' . htmlspecialchars($exp['error'] ?? 'unknown'),
            'parse_mode' => 'HTML'
        ]);
        exit();
    }
    $cfile = new CURLFile($exp['path'], 'text/csv', 'wallet_ledger_' . ($exp['tag'] ?? $period) . '.csv');
    sendTelegram('sendDocument', [
        'chat_id' => $chat_id,
        'document' => $cfile,
        'caption' => "📥 <b>خروجی دفتر کل</b>\nبازه: <code>{$period}</code>\nتعداد ردیف: <b>" . (int)$exp['rows'] . "</b>",
        'parse_mode' => 'HTML'
    ]);
    @unlink($exp['path']);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_fin_rep:') === 0 && isBotAdmin($user_id)) {
    $period = str_replace('adm_fin_rep:', '', $callback_data);
    $reportMsg = getFinancialReport($db, $period);

    $kb = json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]]]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $reportMsg,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data === 'adm_fin_server' && isBotAdmin($user_id)) {
    $totalConfigs = $db->query("SELECT COUNT(*) FROM orders")->fetchColumn() ?: 0;
    $totalVols = $db->query("SELECT SUM(volume_gb) FROM orders")->fetchColumn() ?: 0;
    $totalRefRewards = $db->query("SELECT SUM(total_ref_earned) FROM users")->fetchColumn() ?: 0;
    $totalWallets = $db->query("SELECT SUM(balance) FROM users")->fetchColumn() ?: 0;

    $msg = "🌐 <b>وضعیت سرور، کانفیگ‌ها و دارایی‌ها:</b>\n"
         . "──────────────────\n"
         . "📦 کل کانفیگ‌های صادرشده: <b>{$totalConfigs} عدد</b>\n"
         . "📊 کل حجم ترافیک واگذارشده: <b>" . number_format($totalVols, 1) . " GB</b>\n"
         . "💵 مجموع موجودی در کیف پول کاربران: <b>" . number_format($totalWallets) . " تومان</b>\n"
         . "🎁 کل پورسانت‌های واریزی به معرف‌ها: <b>" . number_format($totalRefRewards) . " تومان</b>\n"
         . "──────────────────";

    $kb = json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]]]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $msg,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data === 'adm_fin_reset_confirm' && isBotAdmin($user_id)) {
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '⚠️ بله، آمار مالی از هم‌اکنون صفر شود', 'callback_data' => 'adm_fin_reset_do']],
            [['text' => '❌ انصراف', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]
        ]
    ]);

    $warnMsg = "⚠️ <b>آیا از ریست و صفر کردن آمار مالی اطمینان دارید؟</b>\n\n"
             . "🔹 مبدا محاسبات درآمدی روی <b>همین لحظه</b> تنظیم می‌شود و آمار از صفر شمرده خواهد شد.\n\n"
             . "💡 <i>سرویس‌ها، کیف پول و اکانت کاربران بدون تغییر باقی می‌مانند.</i>";

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $warnMsg,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data === 'adm_fin_reset_do' && isBotAdmin($user_id)) {
    $now = date('Y-m-d H:i:s');
    setSetting($db, 'financial_reset_at', $now);

    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'آمار مالی صفر شد.']);

    $kb = json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به منوی مالی', 'callback_data' => 'adm_fin_menu', 'style' => 'danger']]]]);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "✅ <b>آمار مالی با موفقیت ریست شد!</b>\n\nمبدا روی تاریخ <code>" . (function_exists('formatJalaliDateTime') ? formatJalaliDateTime($now) : $now) . "</code> تنظیم گردید.",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data === 'adm_cards_menu' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $mode = getSetting($db, 'card_mode', 'random');
    $modeTitles = ['random' => '🔀 رندوم', 'sequential' => '🔁 ترتیبی', 'fixed' => '🎯 کارت خاص'];
    $currentModeTitle = $modeTitles[$mode] ?? 'رندوم';

    $cards = $db->query("SELECT * FROM bank_cards ORDER BY id ASC")->fetchAll();
    $buttons = [];
    $buttons[] = [['text' => '➕ افزودن کارت بانکی جدید 💳', 'callback_data' => 'adm_add_card']];
    $buttons[] = [['text' => "⚙️ تغییر حالت نمایش (فعلی: {$mode})", 'callback_data' => 'adm_card_mode_menu']];

    foreach ($cards as $c) {
        $statusIcon = ($c['is_active'] == 1) ? '🟢' : '🔴';
        $buttons[] = [['text' => "{$statusIcon} {$c['bank_name']} ◂ {$c['card_holder']}", 'callback_data' => "adm_view_card:{$c['id']}"]];
    }
    $buttons[] = [['text' => '🔙 تنظیمات', 'callback_data' => 'adm_settings_menu', 'style' => 'danger'], ['text' => '👑 پنل', 'callback_data' => 'adm_back']];

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "💳 <b>مدیریت کارت‌های بانکی:</b>\nحالت فعلی: <b>{$currentModeTitle}</b>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $buttons], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data === 'adm_card_mode_menu' && isBotAdmin($user_id)) {
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '🔀 حالت رندوم (تصادفی)', 'callback_data' => 'adm_set_cmode:random']],
            [['text' => '🔁 حالت ترتیبی (چرخشی)', 'callback_data' => 'adm_set_cmode:sequential']],
            [['text' => '🎯 حالت کارت خاص (ثابت)', 'callback_data' => 'adm_set_cmode:fixed']],
            [['text' => '🔙 بازگشت', 'callback_data' => 'adm_cards_menu', 'style' => 'danger']]
        ]
    ]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "⚙️ انتخاب نحوه توزیع کارت‌ها:",
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_set_cmode:') === 0 && isBotAdmin($user_id)) {
    setSetting($db, 'card_mode', str_replace('adm_set_cmode:', '', $callback_data));
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'ذخیره شد.']);
    exit();
}

if ($callback_data === 'adm_add_card' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_input_new_card' WHERE user_id = ?")->execute([$user_id]);
    $kb = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_cards_menu', 'style' => 'danger']]]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "➕ <b>افزودن کارت بانکی</b>\n\nبا جداکننده <code>|</code> بفرست:\n<code>6037... | نام صاحب حساب | بانک ملی</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($text && $currentUser['step'] === 'adm_input_new_card' && isBotAdmin($user_id)) {
    $parts = array_map('trim', explode('|', $text));
    if (count($parts) >= 3) {
        $db->prepare("INSERT INTO bank_cards (card_number, card_holder, bank_name, is_active) VALUES (?, ?, ?, 1)")
           ->execute([preg_replace('/[^0-9]/', '', $parts[0]), $parts[1], $parts[2]]);
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ کارت اضافه شد."]);
    }
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_view_card:') === 0 && isBotAdmin($user_id)) {
    $cardId = (int)str_replace('adm_view_card:', '', $callback_data);
    $stmt = $db->prepare("SELECT * FROM bank_cards WHERE id = ?");
    $stmt->execute([$cardId]);
    $c = $stmt->fetch();
    if ($c) {
        $statusTxt = ($c['is_active'] == 1) ? 'فعال 🟢' : 'غیرفعال 🔴';
        $kb = json_encode(['inline_keyboard' => [
            [['text' => '🎯 انتخاب به عنوان کارت ثابت', 'callback_data' => "adm_set_fixed_card:{$c['id']}"]],
            [['text' => '🗑', 'callback_data' => "adm_del_card:{$c['id']}", 'style' => 'danger']],
            [['text' => '🔙 بازگشت', 'callback_data' => 'adm_cards_menu', 'style' => 'danger']]
        ]]);
        sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $update['callback_query']['message']['message_id'], 'text' => "💳 کارت: <code>{$c['card_number']}</code>\nدارنده: {$c['card_holder']}\nوضعیت: {$statusTxt}", 'parse_mode' => 'HTML', 'reply_markup' => $kb]);
    }
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_set_fixed_card:') === 0 && isBotAdmin($user_id)) {
    $cardId = (int)str_replace('adm_set_fixed_card:', '', $callback_data);
    setSetting($db, 'card_mode', 'fixed');
    setSetting($db, 'fixed_card_id', $cardId);
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'تنظیم شد.']);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_del_card:') === 0 && isBotAdmin($user_id)) {
    $db->prepare("DELETE FROM bank_cards WHERE id = ?")->execute([(int)str_replace('adm_del_card:', '', $callback_data)]);
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'حذف شد.']);
    exit();
}

if ($callback_data === 'adm_plans_menu' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    clearPlanDraft($db, $user_id);
    $buttons = [];
    $buttons[] = [['text' => '➕ افزودن پلن جدید 🚀', 'callback_data' => 'adm_add_plan', 'style' => 'success']];
    $buttons[] = [['text' => '📂 مدیریت دسته‌ها (نام/ترتیب/فعال)', 'callback_data' => 'adm_cats_menu']];
    foreach ($plans as $k => $p) {
        $statusIcon = ($p['is_active'] == 1) ? '🟢' : '🔴';
        $buttons[] = [['text' => "{$statusIcon} {$p['title']} ◂ " . number_format($p['price']) . " ت", 'callback_data' => "adm_view_pln:{$k}"]];
    }
    $buttons[] = [['text' => '🔙 تنظیمات', 'callback_data' => 'adm_settings_menu', 'style' => 'danger'], ['text' => '👑 پنل', 'callback_data' => 'adm_back']];
    sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $update['callback_query']['message']['message_id'], 'text' => "📦 مدیریت پلن‌ها:", 'reply_markup' => json_encode(['inline_keyboard' => $buttons], JSON_UNESCAPED_UNICODE)]);
    exit();
}

if ($callback_data === 'adm_cats_menu' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $meta = getPlanCategoryMeta($db);
    $keys = listPlanCategoriesInUse($db, false);
    // همه کلیدهای متا + در حال استفاده
    foreach (array_keys($meta) as $mk) {
        if (!in_array($mk, $keys, true)) $keys[] = $mk;
    }
    $items = [];
    foreach ($keys as $ck) {
        $m = $meta[$ck] ?? ['title' => $ck, 'emoji' => '📦', 'sort' => 999, 'enabled' => 1];
        $items[] = ['key' => $ck, 'm' => $m, 'sort' => (int)($m['sort'] ?? 999)];
    }
    usort($items, function ($a, $b) {
        if ($a['sort'] === $b['sort']) return strcmp($a['key'], $b['key']);
        return $a['sort'] <=> $b['sort'];
    });
    $lines = "📂 <b>مدیریت دسته‌های پلن</b>
"
           . "ترتیب = عدد کوچکتر بالاتر در منوی خرید مشتری
"
           . "غیرفعال = به مشتری نشان داده نمی‌شود (پلن‌ها حذف نمی‌شوند)

";
    $rows = [];
    foreach ($items as $it) {
        $ck = $it['key'];
        $m = $it['m'];
        $en = ((int)($m['enabled'] ?? 1) === 1) ? '🟢' : '🔴';
        $lines .= "{$en} <b>" . htmlspecialchars($m['title'] ?? $ck) . "</b> (<code>{$ck}</code>) · ترتیب " . (int)($m['sort'] ?? 0) . "
";
        $rows[] = [['text' => $en . ' ' . ($m['title'] ?? $ck), 'callback_data' => 'adm_cat_view:' . $ck]];
    }
    $rows[] = [['text' => '🔙 پلن‌ها', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $lines,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_cat_view:') === 0 && isBotAdmin($user_id)) {
    $ck = str_replace('adm_cat_view:', '', $callback_data);
    $meta = getPlanCategoryMeta($db);
    $m = $meta[$ck] ?? ['title' => $ck, 'emoji' => '📦', 'desc' => '', 'sort' => 100, 'enabled' => 1];
    $en = ((int)($m['enabled'] ?? 1) === 1);
    $txt = "📂 <b>دسته:</b> " . htmlspecialchars($m['title'] ?? $ck) . "
"
         . "کلید: <code>{$ck}</code>
"
         . "ایموجی: " . ($m['emoji'] ?? '📦') . "
"
         . "توضیح: " . htmlspecialchars($m['desc'] ?? '-') . "
"
         . "ترتیب: <code>" . (int)($m['sort'] ?? 0) . "</code>
"
         . "وضعیت مشتری: " . ($en ? '🟢 فعال' : '🔴 غیرفعال') . "
";
    $rows = [
        [['text' => '✏️ تغییر نام', 'callback_data' => 'adm_cat_edit_title:' . $ck]],
        [['text' => '🔢 تغییر ترتیب', 'callback_data' => 'adm_cat_edit_sort:' . $ck]],
        [['text' => $en ? '🔴 غیرفعال برای مشتری' : '🟢 فعال برای مشتری', 'callback_data' => 'adm_cat_toggle:' . $ck, 'style' => $en ? 'danger' : 'success']],
        [['text' => '🔙 دسته‌ها', 'callback_data' => 'adm_cats_menu', 'style' => 'danger']],
    ];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_cat_toggle:') === 0 && isBotAdmin($user_id)) {
    $ck = str_replace('adm_cat_toggle:', '', $callback_data);
    $meta = getPlanCategoryMeta($db);
    $m = $meta[$ck] ?? ['title' => $ck, 'emoji' => '📦', 'desc' => '', 'sort' => 100, 'enabled' => 1];
    $newEn = ((int)($m['enabled'] ?? 1) === 1) ? 0 : 1;
    savePlanCategoryMeta($db, $ck, [
        'title' => $m['title'] ?? $ck,
        'emoji' => $m['emoji'] ?? '📦',
        'desc' => $m['desc'] ?? '',
        'sort' => (int)($m['sort'] ?? 100),
        'enabled' => $newEn,
    ]);
    // همگام با جدول per-panel تا تمدید/خرید هر دو قطع شوند
    try {
        $db->prepare('UPDATE bot_plan_categories SET is_active = ? WHERE cat_key = ?')->execute([$newEn, $ck]);
        if (function_exists('testOffersSyncFromCategories')) { testOffersSyncFromCategories($db); }
    } catch (Exception $e) {}

    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => $newEn ? 'فعال شد' : 'غیرفعال شد']);
    // نمایش مجدد
    $callback_data = 'adm_cat_view:' . $ck;
    $meta = getPlanCategoryMeta($db);
    $m = $meta[$ck];
    $en = ((int)($m['enabled'] ?? 1) === 1);
    $txt = "📂 <b>دسته:</b> " . htmlspecialchars($m['title'] ?? $ck) . "
"
         . "کلید: <code>{$ck}</code>
"
         . "ایموجی: " . ($m['emoji'] ?? '📦') . "
"
         . "توضیح: " . htmlspecialchars($m['desc'] ?? '-') . "
"
         . "ترتیب: <code>" . (int)($m['sort'] ?? 0) . "</code>
"
         . "وضعیت مشتری: " . ($en ? '🟢 فعال' : '🔴 غیرفعال') . "
";
    $rows = [
        [['text' => '✏️ تغییر نام', 'callback_data' => 'adm_cat_edit_title:' . $ck]],
        [['text' => '🔢 تغییر ترتیب', 'callback_data' => 'adm_cat_edit_sort:' . $ck]],
        [['text' => $en ? '🔴 غیرفعال برای مشتری' : '🟢 فعال برای مشتری', 'callback_data' => 'adm_cat_toggle:' . $ck, 'style' => $en ? 'danger' : 'success']],
        [['text' => '🔙 دسته‌ها', 'callback_data' => 'adm_cats_menu', 'style' => 'danger']],
    ];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_cat_edit_title:') === 0 && isBotAdmin($user_id)) {
    $ck = str_replace('adm_cat_edit_title:', '', $callback_data);
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(['adm_cat_set_title:' . $ck, $user_id]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "نام جدید دسته <code>{$ck}</code> را بفرست:",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_cat_view:' . $ck]]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text && strpos(($currentUser['step'] ?? ''), 'adm_cat_set_title:') === 0 && isBotAdmin($user_id)) {
    $ck = str_replace('adm_cat_set_title:', '', $currentUser['step']);
    $title = trim($text);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if (mb_strlen($title) < 2 || mb_strlen($title) > 40) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ نام بین ۲ تا ۴۰ حرف باشد.']);
        exit();
    }
    $meta = getPlanCategoryMeta($db);
    $m = $meta[$ck] ?? [];
    savePlanCategoryMeta($db, $ck, [
        'title' => $title,
        'emoji' => $m['emoji'] ?? '📦',
        'desc' => $m['desc'] ?? '',
        'sort' => (int)($m['sort'] ?? 100),
        'enabled' => (int)($m['enabled'] ?? 1),
    ]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => '✅ نام دسته به‌روز شد: ' . htmlspecialchars($title),
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '📂 دسته', 'callback_data' => 'adm_cat_view:' . $ck]]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_cat_edit_sort:') === 0 && isBotAdmin($user_id)) {
    $ck = str_replace('adm_cat_edit_sort:', '', $callback_data);
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(['adm_cat_set_sort:' . $ck, $user_id]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "عدد ترتیب دسته <code>{$ck}</code> را بفرست.
عدد <b>کوچکتر</b> = بالاتر در منوی خرید.
مثال: ماهانه ۱۰ · VIP ۲۰ · ملی ۳۰",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_cat_view:' . $ck]]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text && strpos(($currentUser['step'] ?? ''), 'adm_cat_set_sort:') === 0 && isBotAdmin($user_id)) {
    $ck = str_replace('adm_cat_set_sort:', '', $currentUser['step']);
    $sort = (int)preg_replace('/[^0-9]/', '', $text);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $meta = getPlanCategoryMeta($db);
    $m = $meta[$ck] ?? [];
    savePlanCategoryMeta($db, $ck, [
        'title' => $m['title'] ?? $ck,
        'emoji' => $m['emoji'] ?? '📦',
        'desc' => $m['desc'] ?? '',
        'sort' => $sort,
        'enabled' => (int)($m['enabled'] ?? 1),
    ]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ ترتیب <code>{$ck}</code> = <b>{$sort}</b>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '📂 دسته', 'callback_data' => 'adm_cat_view:' . $ck]],
            [['text' => '📋 همه دسته‌ها', 'callback_data' => 'adm_cats_menu']],
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}


if ($callback_data === 'adm_add_plan' && isBotAdmin($user_id)) {
    clearPlanDraft($db, $user_id);
    ensureMultiPanelSchema($db);
    if (function_exists('plans_ensure_schema')) {
        plans_ensure_schema($db);
    }
    $panels = listBotPanels($db, true);
    if (!$panels) {
        sendTelegram('answerCallbackQuery', [
            'callback_query_id' => $update['callback_query']['id'],
            'text' => 'اول یک پنل فعال تعریف کن',
            'show_alert' => true
        ]);
        exit();
    }
    $rows = [];
    foreach ($panels as $pn) {
        $mark = !empty($pn['is_default']) ? '⭐ ' : '';
        $rows[] = [['text' => $mark . ($pn['name'] ?? ('#' . $pn['id'])), 'callback_data' => 'adm_plan_wiz_panel:' . (int)$pn['id'], 'style' => 'primary']];
    }
    $rows[] = [['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📦 <b>ویزارد پلن جدید</b> — مرحله ۱ از ۳
"
                . "──────────────────
"
                . "اول <b>پنل</b> را انتخاب کن.
"
                . "بعد دستهٔ همان پنل، سپس مشخصات پلن.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data === 'adm_plan_wiz_cat_new' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_newcat_key' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📦 <b>دسته جدید</b>\n\n"
                . "یک <b>کلید انگلیسی</b> کوتاه بفرست (فقط حروف و عدد و _).\n\n"
                . "✅ مثال: <code>national</code> · <code>unlimited</code> · <code>game</code>\n"
                . "❌ فارسی یا فاصله نزن.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text && ($currentUser['step'] ?? '') === 'adm_plan_wiz_newcat_key' && isBotAdmin($user_id)) {
    $key = strtolower(trim($text));
    if (!preg_match('/^[a-z][a-z0-9_]{1,30}$/', $key)) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ کلید نامعتبر. فقط انگلیسی کوچک، عدد و _ (شروع با حرف).']);
        exit();
    }
    if (in_array($key, ['monthly', 'vip'], true)) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ این کلید رزرو شده است.']);
        exit();
    }
    $draft = getPlanDraft($db, $user_id);
    $draft['cat'] = $key;
    $draft['new_cat'] = true;
    setPlanDraft($db, $user_id, $draft);
    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_newcat_title' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "نام نمایشی این دسته را به فارسی بفرست.\nمثال: <code>اینترنت ملی</code> یا <code>گیمینگ</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text && ($currentUser['step'] ?? '') === 'adm_plan_wiz_newcat_title' && isBotAdmin($user_id)) {
    $title = trim($text);
    if (mb_strlen($title) < 2 || mb_strlen($title) > 40) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ نام بین ۲ تا ۴۰ حرف باشد.']);
        exit();
    }
    $draft = getPlanDraft($db, $user_id);
    $cat = $draft['cat'] ?? '';
    if ($cat === '') {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ پیش‌نویس ناقص. از اول شروع کن.']);
        exit();
    }
    savePlanCategoryLabel($db, $cat, $title, '📦', '');
    $pid = (int)($draft['panel_id'] ?? 0);
    if ($pid <= 0) {
        $pid = (int)(getDefaultPanel($db)['id'] ?? 0);
        $draft['panel_id'] = $pid;
    }
    if ($pid > 0 && function_exists('cats_ensure')) {
        cats_ensure($db, $pid, $cat, ['title' => $title, 'emoji' => '📦', 'description' => '']);
    }
    $draft['new_cat'] = false;
    setPlanDraft($db, $user_id, $draft);
    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_title' WHERE user_id = ?")->execute([$user_id]);
    $pn = getPanelById($pid);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ دسته <b>" . htmlspecialchars($title) . "</b> روی پنل ثبت شد.

"
                . "📦 عنوان نمایشی <b>پلن</b> را بفرست.
مثال: <code>۵۰ گیگ یک‌ماهه</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}


if ($callback_data && strpos($callback_data, 'adm_plan_wiz_cat:') === 0 && isBotAdmin($user_id)) {
    $cat = str_replace('adm_plan_wiz_cat:', '', $callback_data);
    $draft = getPlanDraft($db, $user_id);
    $draft['cat'] = $cat;
    $pid = (int)($draft['panel_id'] ?? 0);
    if ($pid <= 0) {
        $pid = (int)(getDefaultPanel($db)['id'] ?? 0);
        $draft['panel_id'] = $pid;
    }
    setPlanDraft($db, $user_id, $draft);
    if ($pid > 0 && function_exists('cats_ensure')) {
        $lb = getPlanCategoryLabels($db);
        cats_ensure($db, $pid, $cat, [
            'title' => $lb[$cat]['title'] ?? $cat,
            'emoji' => $lb[$cat]['emoji'] ?? '📦',
            'description' => $lb[$cat]['desc'] ?? '',
        ]);
    }
    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_title' WHERE user_id = ?")->execute([$user_id]);
    $pn = getPanelById($pid);
    $catTitle = getPlanCategoryLabels($db)[$cat]['title'] ?? $cat;
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📦 <b>ویزارد پلن</b> — مرحله ۳
"
                . "پنل: <b>" . htmlspecialchars($pn['name'] ?? ('#' . $pid)) . "</b> · دسته: <b>" . htmlspecialchars($catTitle) . "</b>

"
                . "عنوان نمایشی پلن را بفرست.
مثال: <code>۵۰ گیگ یک‌ماهه</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}


if ($callback_data && strpos($callback_data, 'adm_plan_wiz_panel:') === 0 && isBotAdmin($user_id)) {
    $pid = (int)str_replace('adm_plan_wiz_panel:', '', $callback_data);
    $draft = getPlanDraft($db, $user_id);
    $draft['panel_id'] = $pid;
    setPlanDraft($db, $user_id, $draft);
    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_cat' WHERE user_id = ?")->execute([$user_id]);
    $pn = getPanelById($pid);
    $rows = [];
    $seen = [];
    if (function_exists('cats_list_for_panel')) {
        foreach (cats_list_for_panel($db, $pid, false) as $c) {
            $ck = (string)($c['cat_key'] ?? '');
            if ($ck === '') continue;
            $seen[$ck] = true;
            $en = ((int)($c['is_active'] ?? 1) === 1) ? '' : '⏸ ';
            $rows[] = [['text' => $en . ($c['emoji'] ?? '📦') . ' ' . ($c['title'] ?? $ck), 'callback_data' => 'adm_plan_wiz_cat:' . $ck]];
        }
    }
    $labels = getPlanCategoryLabels($db);
    foreach (['monthly', 'vip'] as $ck) {
        if (isset($seen[$ck])) continue;
        $lb = $labels[$ck] ?? ['title' => $ck, 'emoji' => '📦'];
        $rows[] = [['text' => ($lb['emoji'] ?? '📦') . ' ' . ($lb['title'] ?? $ck), 'callback_data' => 'adm_plan_wiz_cat:' . $ck, 'style' => 'primary']];
    }
    $rows[] = [['text' => '➕ دسته جدید روی این پنل', 'callback_data' => 'adm_plan_wiz_cat_new', 'style' => 'success']];
    $rows[] = [['text' => '🔙 انتخاب پنل', 'callback_data' => 'adm_add_plan', 'style' => 'danger']];
    $rows[] = [['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📦 <b>ویزارد پلن</b> — مرحله ۲ از ۳
"
                . "پنل: <b>" . htmlspecialchars($pn['name'] ?? ('#' . $pid)) . "</b>

"
                . "دسته را انتخاب کن:",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_plan_wiz_title' && isBotAdmin($user_id)) {
    $title = trim($text);
    if (mb_strlen($title) < 2 || mb_strlen($title) > 80) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ عنوان بین ۲ تا ۸۰ حرف باشد.']);
        exit();
    }
    $draft = getPlanDraft($db, $user_id);
    $draft['title'] = $title;
    setPlanDraft($db, $user_id, $draft);
    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_vol' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "حجم را به <b>گیگابایت</b> بفرست.\nمثال: <code>50</code> یا <code>100</code>\nبرای <b>نامحدود</b> عدد <code>0</code> بفرست.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_plan_wiz_vol' && isBotAdmin($user_id)) {
    $rawVol = trim($text);
    $rawVol = str_replace(['۰','۱','۲','۳','۴','۵','۶','۷','۸','۹', ',', ' '], ['0','1','2','3','4','5','6','7','8','9', '.', ''], $rawVol);
    if (in_array(mb_strtolower($rawVol), ['نامحدود', 'unlimited', 'inf'], true)) {
        $vol = 0.0;
    } elseif ($rawVol === '' || !is_numeric($rawVol)) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ حجم نامعتبر. عدد بفرست؛ نامحدود = <code>0</code>', 'parse_mode' => 'HTML']);
        exit();
    } else {
        $vol = (float)$rawVol;
    }
    if ($vol < 0 || $vol > 100000) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ حجم نامعتبر است.']);
        exit();
    }
    $draft = getPlanDraft($db, $user_id);

    $draft['vol'] = $vol;
    setPlanDraft($db, $user_id, $draft);
    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_days' WHERE user_id = ?")->execute([$user_id]);
    $hint = (( $draft['cat'] ?? '') === 'vip')
        ? "برای VIP معمولاً <code>0</code> بفرست (بدون انقضا)."
        : "مثال: <code>30</code> برای یک ماه. برای بدون انقضا <code>0</code>.";
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "تعداد <b>روز اعتبار</b> را بفرست.\n{$hint}",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_plan_wiz_days' && isBotAdmin($user_id)) {
    $days = (int)preg_replace('/[^0-9]/', '', $text);
    if ($days < 0 || $days > 3650) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ روز نامعتبر است.']);
        exit();
    }
    $draft = getPlanDraft($db, $user_id);
    $draft['days'] = $days;
    setPlanDraft($db, $user_id, $draft);
    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_price' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "قیمت را به <b>تومان</b> بفرست (فقط عدد).\nمثال: <code>199000</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_plan_wiz_price' && isBotAdmin($user_id)) {
    $price = (int)preg_replace('/[^0-9]/', '', $text);
    if ($price < 0) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ قیمت نامعتبر.']);
        exit();
    }
    $draft = getPlanDraft($db, $user_id);
    $draft['price'] = $price;
    // کلید یکتا
    $cat = preg_replace('/[^a-z0-9_]/', '', strtolower($draft['cat'] ?? 'p'));
    $baseKey = $cat . '_' . (int)$draft['vol'] . 'g_' . (int)$draft['days'] . 'd';
    $planKey = $baseKey;
    $n = 2;
    while (isset($plans[$planKey])) {
        $planKey = $baseKey . '_' . $n;
        $n++;
        if ($n > 50) { $planKey = $baseKey . '_' . time(); break; }
    }
    $draft['plan_key'] = $planKey;
    $draft['limit_ip'] = (int)($draft['limit_ip'] ?? 0);
    setPlanDraft($db, $user_id, $draft);

    $pnCheck = getPanelById((int)($draft['panel_id'] ?? 0));
    if (function_exists('planIsFardadUnlimited') && planIsFardadUnlimited($draft, $pnCheck)) {
        $db->prepare("UPDATE users SET step = 'adm_plan_wiz_limit_ip' WHERE user_id = ?")->execute([$user_id]);
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "👥 <b>تعداد کاربر هم‌زمان</b> (پلن نامحدود فرداد)

"
                    . "چند IP هم‌زمان به این اشتراک وصل شوند؟
"
                    . "• <b>۱</b> = تک‌کاربره
"
                    . "• <b>۲</b> = گوشی + لپ‌تاپ (پیشنهادی)
"
                    . "• بدون محدودیت توصیه نمی‌شود",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [
                [
                    ['text' => '۱ کاربر', 'callback_data' => 'adm_plan_wiz_lip:1', 'style' => 'primary'],
                    ['text' => '۲ کاربر ⭐', 'callback_data' => 'adm_plan_wiz_lip:2', 'style' => 'success']
                ],
                [['text' => 'بدون محدودیت IP', 'callback_data' => 'adm_plan_wiz_lip:0']],
                [['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']],
            ]], JSON_UNESCAPED_UNICODE)
        ]);
        exit();
    }

    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_confirm' WHERE user_id = ?")->execute([$user_id]);
    $labels = getPlanCategoryLabels($db);
    $catTitle = $labels[$draft['cat']]['title'] ?? $draft['cat'];
    $pn = getPanelById((int)($draft['panel_id'] ?? 0));
    $daysTxt = ((int)$draft['days'] === 0) ? 'بدون انقضا' : ((int)$draft['days'] . ' روز');
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "📋 <b>تأیید پلن جدید</b>\n"
                . "──────────────────\n"
                . "🔑 کلید: <code>{$planKey}</code>\n"
                . "🏷 عنوان: <b>" . htmlspecialchars($draft['title']) . "</b>\n"
                . "📂 دسته: <b>" . htmlspecialchars($catTitle) . "</b>\n"
                . "📦 حجم: <b>" . (((float)$draft['vol'] <= 0) ? "نامحدود" : ($draft['vol'] . " GB")) . "</b>\n"
                . "⏱ اعتبار: <b>{$daysTxt}</b>\n"
                . "💰 قیمت: <b>" . number_format($price) . "</b> تومان\n"
                . "🖥 پنل: <b>" . htmlspecialchars($pn['name'] ?? 'پیش‌فرض') . "</b>\n\n"
                . "اگر درست است ثبت کن.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '✅ ثبت پلن', 'callback_data' => 'adm_plan_wiz_save', 'style' => 'success']],
            [['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']],
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}


if ($callback_data && strpos($callback_data, 'adm_plan_wiz_next:') === 0 && isBotAdmin($user_id)) {
    $rest = str_replace('adm_plan_wiz_next:', '', $callback_data);
    $parts = explode(':', $rest, 2);
    $pid = (int)($parts[0] ?? 0);
    $cat = $parts[1] ?? '';
    clearPlanDraft($db, $user_id);
    $draft = ['panel_id' => $pid, 'cat' => $cat];
    setPlanDraft($db, $user_id, $draft);
    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_title' WHERE user_id = ?")->execute([$user_id]);
    $pn = getPanelById($pid);
    $catTitle = getPlanCategoryLabels($db)[$cat]['title'] ?? $cat;
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "📦 پلن بعدی
پنل: <b>" . htmlspecialchars($pn['name'] ?? ('#'.$pid)) . "</b> · دسته: <b>" . htmlspecialchars($catTitle) . "</b>

عنوان پلن را بفرست:",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}


if ($callback_data && strpos($callback_data, 'adm_plan_wiz_lip:') === 0 && isBotAdmin($user_id)) {
    $lip = (int)str_replace('adm_plan_wiz_lip:', '', $callback_data);
    if ($lip < 0) { $lip = 0; }
    if ($lip > 10) { $lip = 10; }
    $draft = getPlanDraft($db, $user_id);
    $draft['limit_ip'] = $lip;
    setPlanDraft($db, $user_id, $draft);
    $db->prepare("UPDATE users SET step = 'adm_plan_wiz_confirm' WHERE user_id = ?")->execute([$user_id]);
    $planKey = (string)($draft['plan_key'] ?? '');
    $labels = getPlanCategoryLabels($db);
    $catTitle = $labels[$draft['cat'] ?? '']['title'] ?? ($draft['cat'] ?? '');
    $pn = getPanelById((int)($draft['panel_id'] ?? 0));
    $daysTxt = ((int)($draft['days'] ?? 0) === 0) ? 'بدون انقضا' : ((int)$draft['days'] . ' روز');
    $lipTxt = formatLimitIpLabel($lip);
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "📋 <b>تأیید پلن جدید</b>\n"
                . "──────────────────\n"
                . "🔑 کلید: <code>" . htmlspecialchars($planKey) . "</code>\n"
                . "🏷 عنوان: <b>" . htmlspecialchars((string)($draft['title'] ?? '')) . "</b>\n"
                . "📂 دسته: <b>" . htmlspecialchars((string)$catTitle) . "</b>\n"
                . "📦 حجم: <b>" . (((float)($draft['vol'] ?? 0) <= 0) ? "نامحدود" : ($draft['vol'] . " GB")) . "</b>\n"
                . "⏱ اعتبار: <b>{$daysTxt}</b>\n"
                . "💰 قیمت: <b>" . number_format((int)($draft['price'] ?? 0)) . "</b> تومان\n"
                . "👥 کاربر: <b>" . htmlspecialchars($lipTxt) . "</b>\n"
                . "🖥 پنل: <b>" . htmlspecialchars($pn['name'] ?? 'پیش‌فرض') . "</b>\n\n"
                . "اگر درست است ثبت کن.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '✅ ثبت پلن', 'callback_data' => 'adm_plan_wiz_save', 'style' => 'success']],
            [['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']],
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data === 'adm_plan_wiz_save' && isBotAdmin($user_id)) {
    $draft = getPlanDraft($db, $user_id);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if (empty($draft['plan_key']) || empty($draft['title']) || empty($draft['cat'])) {
        clearPlanDraft($db, $user_id);
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'پیش‌نویس ناقص', 'show_alert' => true]);
        exit();
    }
    ensureMultiPanelSchema($db);
    if (function_exists('plans_ensure_schema')) {
        plans_ensure_schema($db);
    }
    $pid = (int)($draft['panel_id'] ?? 0);
    if ($pid <= 0) $pid = (int)(getDefaultPanel($db)['id'] ?? 0);
    if (function_exists('plans_save')) {
        $resSave = plans_save($db, [
            'plan_key' => $draft['plan_key'],
            'title' => $draft['title'],
            'cat' => $draft['cat'],
            'vol' => (float)$draft['vol'],
            'days' => (int)$draft['days'],
            'price' => (int)$draft['price'],
            'description' => '',
            'is_active' => 1,
            'panel_id' => $pid,
            'limit_ip' => (int)($draft['limit_ip'] ?? 0),
        ]);
        if (empty($resSave['ok'])) {
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ خطا در ذخیره: ' . ($resSave['error'] ?? '')]);
            exit();
        }
        if ($pid > 0 && function_exists('cats_ensure')) {
            $lb = getPlanCategoryLabels($db);
            $ck = $draft['cat'];
            cats_ensure($db, $pid, $ck, [
                'title' => $lb[$ck]['title'] ?? $ck,
                'emoji' => $lb[$ck]['emoji'] ?? '📦',
                'description' => $lb[$ck]['desc'] ?? '',
            ]);
        }
    } else {
        try {
            $db->prepare("INSERT INTO bot_plans (plan_key, title, cat, vol, days, price, description, is_active, panel_id) VALUES (?, ?, ?, ?, ?, ?, '', 1, ?)")
               ->execute([
                   $draft['plan_key'], $draft['title'], $draft['cat'],
                   (float)$draft['vol'], (int)$draft['days'], (int)$draft['price'], $pid
               ]);
        } catch (Exception $e) {
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ خطا در ذخیره: ' . $e->getMessage()]);
            exit();
        }
    }
    clearPlanDraft($db, $user_id);
    // پاک کردن کش پلن‌ها در همین درخواست ممکن نیست؛ ریکوئست بعدی تازه می‌شود
    $pn = getPanelById($pid);
    $labels = getPlanCategoryLabels($db);
    $catTitle = $labels[$draft['cat']]['title'] ?? $draft['cat'];
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'ثبت شد']);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ پلن <b>" . htmlspecialchars($draft['title']) . "</b> ذخیره شد.\n"
                . "📂 دسته: " . htmlspecialchars($catTitle) . "\n"
                . "🖥 پنل: " . htmlspecialchars($pn['name'] ?? ('#' . $pid)),
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '➕ پلن بعدی همین دسته', 'callback_data' => 'adm_plan_wiz_next:' . $pid . ':' . $draft['cat'], 'style' => 'success']],
            [['text' => '📦 لیست پلن‌ها', 'callback_data' => 'adm_plans_menu']],
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_view_pln:') === 0 && isBotAdmin($user_id)) {
    $planKey = str_replace('adm_view_pln:', '', $callback_data);
    $p = $plans[$planKey] ?? null;
    if ($p) {
        $kb = json_encode(['inline_keyboard' => [
            [['text' => '✏️ ویرایش قیمت', 'callback_data' => "adm_chg_price:{$planKey}"], ['text' => '🗑', 'callback_data' => "adm_del_pln:{$planKey}", 'style' => 'danger']],
            [['text' => '🔙 بازگشت', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']]
        ]]);
        sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $update['callback_query']['message']['message_id'], 'text' => "📦 پلن: {$p['title']}\nقیمت: " . number_format($p['price']), 'reply_markup' => $kb]);
    }
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_del_pln:') === 0 && isBotAdmin($user_id)) {
    // مرحله ۱: غیرفعال
    $pk = str_replace('adm_del_pln:', '', $callback_data);
    if (function_exists('plans_soft_delete')) {
        plans_soft_delete($db, $pk);
    } else {
        try {
            $db->prepare("UPDATE bot_plans SET is_active = 0 WHERE plan_key = ?")->execute([$pk]);
        } catch (Exception $e) {}
    }
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'غیرفعال شد']);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "⏸ پلن <code>" . htmlspecialchars($pk) . "</code> غیرفعال شد.
"
                . "از خرید مشتری حذف می‌شود؛ سفارش‌های قبلی دست نمی‌خورند.

"
                . "اگر تستی/اضافه است و می‌خواهی از لیست هم پاک شود:",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '🗑 حذف کامل از دیتابیس', 'callback_data' => 'adm_hard_del_pln:' . $pk, 'style' => 'danger']],
            [['text' => '📦 لیست پلن‌ها', 'callback_data' => 'adm_plans_menu']],
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_hard_del_pln:') === 0 && isBotAdmin($user_id)) {
    $pk = str_replace('adm_hard_del_pln:', '', $callback_data);
    if (function_exists('plans_hard_delete')) {
        $hr = plans_hard_delete($db, $pk);
        $msg = !empty($hr['ok'])
            ? ("✅ پلن <code>" . htmlspecialchars($pk) . "</code> کامل حذف شد.")
            : ("❌ حذف نشد: " . ($hr['error'] ?? ''));
    } else {
        try {
            $db->prepare("DELETE FROM bot_plans WHERE plan_key = ?")->execute([$pk]);
            $msg = "✅ پلن <code>" . htmlspecialchars($pk) . "</code> کامل حذف شد.";
        } catch (Exception $e) {
            $msg = "❌ حذف نشد: " . $e->getMessage();
        }
    }
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'حذف شد']);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => $msg,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '📦 لیست پلن‌ها', 'callback_data' => 'adm_plans_menu']],
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_chg_price:') === 0 && isBotAdmin($user_id)) {
    $planKey = str_replace('adm_chg_price:', '', $callback_data);
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(['adm_set_price:' . $planKey, $user_id]);
    $kb = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_plans_menu', 'style' => 'danger']]]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "💰 قیمت جدید پلن <code>{$planKey}</code> را به تومان بفرست:",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($text && strpos($currentUser['step'], 'adm_set_price:') === 0 && isBotAdmin($user_id)) {
    $planKey = str_replace('adm_set_price:', '', $currentUser['step']);
    $db->prepare("UPDATE bot_plans SET price = ? WHERE plan_key = ?")->execute([(int)preg_replace('/[^0-9]/', '', $text), $planKey]);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ قیمت به‌روز شد."]);
    exit();
}

if ($callback_data === 'adm_ref_setting' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $refPct = (int)getSetting($db, 'ref_reward_percent', 10);
    $refCap = (int)getSetting($db, 'ref_reward_cap', 50000);
    $refVol = (int)getSetting($db, 'ref_invitee_vol_percent', 5);
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => "٪ پاداش معرف ({$refPct}٪)", 'callback_data' => 'adm_ref_edit:percent']],
            [['text' => 'سقف پاداش (' . number_format($refCap) . ' ت)', 'callback_data' => 'adm_ref_edit:cap']],
            [['text' => "٪ حجم هدیه دعوت‌شده ({$refVol}٪)", 'callback_data' => 'adm_ref_edit:vol']],
            [['text' => '🔙 بازگشت', 'callback_data' => 'adm_settings_menu', 'style' => 'danger']],
        ]
    ], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🎁 <b>تنظیمات دعوت دوست</b>\n\n"
            . "• پاداش معرف: <b>{$refPct}٪</b> از مبلغ اولین خرید\n"
            . "• سقف پاداش: <b>" . number_format($refCap) . " تومان</b>\n"
            . "• حجم هدیه دعوت‌شده: <b>{$refVol}٪</b> (جدا از ۱۰٪ تخفیف اولین خرید همگانی)\n\n"
            . "کدام مورد را تغییر می‌دهی؟",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_ref_edit:') === 0 && isBotAdmin($user_id)) {
    $which = str_replace('adm_ref_edit:', '', $callback_data);
    $map = [
        'percent' => ['step' => 'adm_input_ref_percent', 'title' => 'درصد پاداش معرف', 'hint' => 'عدد ۱ تا ۵۰ (مثلاً ۱۰)', 'cur' => (int)getSetting($db, 'ref_reward_percent', 10) . '٪'],
        'cap' => ['step' => 'adm_input_ref_cap', 'title' => 'سقف پاداش معرف', 'hint' => 'مبلغ به تومان (مثلاً ۵۰۰۰۰)', 'cur' => number_format((int)getSetting($db, 'ref_reward_cap', 50000)) . ' تومان'],
        'vol' => ['step' => 'adm_input_ref_vol', 'title' => 'درصد حجم هدیه دعوت‌شده', 'hint' => 'عدد ۰ تا ۳۰ (مثلاً ۵)', 'cur' => (int)getSetting($db, 'ref_invitee_vol_percent', 5) . '٪'],
    ];
    if (!isset($map[$which])) {
        exit();
    }
    $m = $map[$which];
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute([$m['step'], $user_id]);
    $kb = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_ref_setting', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🎁 <b>{$m['title']}</b>\n\nمقدار فعلی: <b>{$m['cur']}</b>\n\n{$m['hint']}\nعدد جدید را بفرست:",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($text && $currentUser['step'] === 'adm_input_ref_percent' && isBotAdmin($user_id)) {
    $v = (int)preg_replace('/[^0-9]/', '', $text);
    if ($v < 1) {
        $v = 1;
    }
    if ($v > 50) {
        $v = 50;
    }
    setSetting($db, 'ref_reward_percent', $v);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ درصد پاداش معرف: <b>{$v}٪</b>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🎁 بازگشت به تنظیمات دعوت', 'callback_data' => 'adm_ref_setting']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text && $currentUser['step'] === 'adm_input_ref_cap' && isBotAdmin($user_id)) {
    $v = (int)preg_replace('/[^0-9]/', '', $text);
    if ($v < 1000) {
        $v = 1000;
    }
    setSetting($db, 'ref_reward_cap', $v);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ سقف پاداش معرف: <b>" . number_format($v) . " تومان</b>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🎁 بازگشت به تنظیمات دعوت', 'callback_data' => 'adm_ref_setting']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text && $currentUser['step'] === 'adm_input_ref_vol' && isBotAdmin($user_id)) {
    $v = (int)preg_replace('/[^0-9]/', '', $text);
    if ($v < 0) {
        $v = 0;
    }
    if ($v > 30) {
        $v = 30;
    }
    setSetting($db, 'ref_invitee_vol_percent', $v);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ حجم هدیه دعوت‌شده: <b>{$v}٪</b>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🎁 بازگشت به تنظیمات دعوت', 'callback_data' => 'adm_ref_setting']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

// سازگاری با استپ قدیمی (اگر هنوز در session باشد)
if ($text && $currentUser['step'] === 'adm_input_ref_reward' && isBotAdmin($user_id)) {
    $v = (int)preg_replace('/[^0-9]/', '', $text);
    if ($v < 1000) {
        $v = 1000;
    }
    setSetting($db, 'ref_reward_cap', $v);
    setSetting($db, 'ref_reward', $v);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ سقف پاداش روی <b>" . number_format($v) . " تومان</b> تنظیم شد.\n(مدل جدید: درصد + سقف — از منوی پاداش دعوت می‌تونی درصد را هم عوض کنی)",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🎁 تنظیمات دعوت', 'callback_data' => 'adm_ref_setting']]]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_rep:') === 0 && isBotAdmin($user_id)) {
    $targetUid = (int)str_replace('adm_rep:', '', $callback_data);
    if (function_exists('openSupportTicket')) {
        openSupportTicket($db, $targetUid);
        if (function_exists('assignSupportTicket')) {
            assignSupportTicket($db, $targetUid, $user_id);
        }
    }
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(['admin_reply:' . $targetUid, $user_id]);
    if (!empty($update['callback_query']['id'])) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    }
    if (function_exists('clearAdminBroadcastMessages')) {
        clearAdminBroadcastMessages(
            $db,
            'support',
            $targetUid,
            $user_id,
            "🎫 تیکت <code>{$targetUid}</code>\n\n⏳ در حال پاسخ توسط ادمین <code>{$user_id}</code>"
        );
    }
    $kb = function_exists('supportAdminReplyModeKeyboard')
        ? supportAdminReplyModeKeyboard($targetUid)
        : json_encode(['inline_keyboard' => [[['text' => '⏸ ترک پاسخ (تیکت باز بماند)', 'callback_data' => 'adm_sup_leave_reply']]]]);
    $card = function_exists('buildSupportTicketCard') ? buildSupportTicketCard($db, $targetUid) : '';
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => $card . "\n✍️ <b>حالت پاسخ فعال</b>\nمتن را بفرست (چند پیام پشت‌سرهم اوکی است).\nیا از پاسخ‌های آماده استفاده کن:",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb,
    ]);
    exit();
}

if ($callback_data === 'adm_sup_leave_reply' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if (!empty($update['callback_query']['id'])) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'حالت پاسخ بسته شد']);
    }
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ حالت پاسخ بسته شد.\nتیکت کاربر هنوز باز است — هر وقت خواستی دوباره «پاسخ» بزن.",
        'reply_markup' => getAdminKeyboard(),
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_sup_close:') === 0 && isBotAdmin($user_id)) {
    $targetUid = (int)str_replace('adm_sup_close:', '', $callback_data);
    if (function_exists('closeSupportTicket')) {
        closeSupportTicket($db, $targetUid, 'admin', $user_id);
    }
    if (strpos((string)($currentUser['step'] ?? ''), 'admin_reply:' . $targetUid) === 0) {
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    }
    try {
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ? AND step = 'support_human_wait'")->execute([$targetUid]);
    } catch (Exception $e) {}
    if (function_exists('clearAdminBroadcastMessages')) {
        clearAdminBroadcastMessages($db, 'support', $targetUid, $user_id, "🎫 تیکت <code>{$targetUid}</code> بسته شد.");
    }
    if (!empty($update['callback_query']['id'])) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'تیکت بسته شد']);
    }
    sendTelegram('sendMessage', [
        'chat_id' => $targetUid,
        'text' => "✅ گفتگوی پشتیبانی توسط تیم بسته شد.\nاگر باز سوالی داشتی از منو «پشتیبانی» رو بزن 💬",
        'reply_markup' => $mainKeyboard,
    ]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ تیکت کاربر <code>{$targetUid}</code> بسته شد.",
        'parse_mode' => 'HTML',
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_sup_canned_menu:') === 0 && isBotAdmin($user_id)) {
    $targetUid = (int)str_replace('adm_sup_canned_menu:', '', $callback_data);
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(['admin_reply:' . $targetUid, $user_id]);
    if (!empty($update['callback_query']['id'])) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    }
    $kb = function_exists('supportAdminReplyModeKeyboard') ? supportAdminReplyModeKeyboard($targetUid) : null;
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "⚡️ یک پاسخ آماده انتخاب کن (برای کاربر <code>{$targetUid}</code>):",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb,
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_sup_send_canned:') === 0 && isBotAdmin($user_id)) {
    $rest = str_replace('adm_sup_send_canned:', '', $callback_data);
    $parts = explode(':', $rest, 2);
    $targetUid = (int)($parts[0] ?? 0);
    $cKey = (string)($parts[1] ?? '');
    $cText = function_exists('getSupportCannedText') ? getSupportCannedText($cKey) : null;
    if (!$targetUid || !$cText) {
        if (!empty($update['callback_query']['id'])) {
            sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'نامعتبر', 'show_alert' => true]);
        }
        exit();
    }
    if (function_exists('openSupportTicket')) {
        openSupportTicket($db, $targetUid);
        if (function_exists('assignSupportTicket')) {
            assignSupportTicket($db, $targetUid, $user_id);
        }
    }
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(['admin_reply:' . $targetUid, $user_id]);
    if (function_exists('logSupportHumanMessage')) {
        logSupportHumanMessage($db, $targetUid, 'admin', $cText, $user_id, null);
    }
    if (function_exists('touchSupportTicket')) {
        touchSupportTicket($db, $targetUid);
    }
    $replyHtml = "👨‍💼 <b>پشتیبانی JET VPN</b>\n\n" . htmlspecialchars($cText, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
    $ukb = function_exists('supportUserOpenKeyboard') ? supportUserOpenKeyboard() : null;
    $sendRes = sendTelegram('sendMessage', array_filter([
        'chat_id' => $targetUid,
        'text' => $replyHtml,
        'parse_mode' => 'HTML',
        'reply_markup' => $ukb,
    ]));
    if (!empty($update['callback_query']['id'])) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => !empty($sendRes['ok']) ? 'ارسال شد' : 'خطا']);
    }
    $adminKb = function_exists('supportAdminReplyModeKeyboard') ? supportAdminReplyModeKeyboard($targetUid) : null;
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => !empty($sendRes['ok'])
            ? "✅ پاسخ آماده ارسال شد. می‌تونی ادامه بدی یا تیکت را ببندی."
            : "⚠️ ارسال ناموفق بود.",
        'reply_markup' => $adminKb,
    ]);
    exit();
}


if ($callback_data === 'adm_coupons' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $rows = $db->query("SELECT * FROM coupons ORDER BY id DESC LIMIT 20")->fetchAll();
    $txt = "🏷 <b>کدهای تخفیف</b>\n\n";
    $buttons = [[['text' => '➕ ساخت کد جدید', 'callback_data' => 'adm_add_coupon']]];
    if (empty($rows)) {
        $txt .= "هنوز کدی ثبت نشده.";
    } else {
        foreach ($rows as $c) {
            $txt .= "• <code>{$c['code']}</code> — {$c['discount_percent']}% | استفاده: {$c['used_count']}/{$c['max_uses']}\n";
            $buttons[] = [
                ['text' => (string)$c['code'], 'callback_data' => 'adm_del_coupon:' . $c['id']],
                ['text' => '🗑', 'callback_data' => 'adm_del_coupon:' . $c['id'], 'style' => 'danger']
            ];
        }
    }
    $buttons[] = [['text' => '🔙 تنظیمات', 'callback_data' => 'adm_settings_menu', 'style' => 'danger'], ['text' => '👑 پنل', 'callback_data' => 'adm_back']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $buttons], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_del_coupon:') === 0 && isBotAdmin($user_id)) {
    $cid = (int)str_replace('adm_del_coupon:', '', $callback_data);
    $db->prepare("DELETE FROM coupons WHERE id = ?")->execute([$cid]);
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'حذف شد', 'show_alert' => false]);
    // رفرش لیست
    $callback_data = 'adm_coupons';
    // fall through by re-triggering is hard; send simple confirm
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ کد تخفیف حذف شد.",
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🏷 بازگشت به تخفیف‌ها', 'callback_data' => 'adm_coupons', 'style' => 'danger']]]])
    ]);
    exit();
}

// ===== ویزارد ساخت کد تخفیف =====
if ($callback_data === 'adm_add_coupon' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'admin_coupon_wiz_code' WHERE user_id = ?")->execute([$user_id]);
    $rand = strtoupper(substr(bin2hex(random_bytes(3)), 0, 6));
    $kb = json_encode(['inline_keyboard' => [
        [['text' => "🎲 کد تصادفی: {$rand}", 'callback_data' => "adm_cp_code:{$rand}"]],
        [['text' => '❌ انصراف', 'callback_data' => 'adm_coupons', 'style' => 'danger']]
    ]], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🏷 <b>ویزارد کد تخفیف — مرحله ۱/۳</b>\n\n"
            . "نام کد را بفرست (فقط حروف و عدد انگلیسی)\n"
            . "یا از دکمه کد تصادفی استفاده کن.\n\n"
            . "مثال: <code>OFF30</code> یا <code>JET20</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_cp_code:') === 0 && isBotAdmin($user_id)) {
    $code = strtoupper(preg_replace('/[^A-Z0-9]/i', '', str_replace('adm_cp_code:', '', $callback_data)));
    if (strlen($code) < 3 || strlen($code) > 20) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'کد نامعتبر', 'show_alert' => true]);
        exit();
    }
    $stmt = $db->prepare("SELECT id FROM coupons WHERE code = ?");
    $stmt->execute([$code]);
    if ($stmt->fetch()) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'این کد از قبل هست', 'show_alert' => true]);
        exit();
    }
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["admin_coupon_wiz_pct:{$code}", $user_id]);
    $pctBtns = [];
    foreach ([10, 15, 20, 25, 30, 40, 50] as $p) {
        $pctBtns[] = ['text' => "{$p}٪", 'callback_data' => "adm_cp_pct:{$code}:{$p}"];
    }
    $rows = array_chunk($pctBtns, 4);
    $rows[] = [['text' => '❌ انصراف', 'callback_data' => 'adm_coupons', 'style' => 'danger']];
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🏷 <b>ویزارد کد تخفیف — مرحله ۲/۳</b>\n\nکد: <code>{$code}</code>\n\nدرصد تخفیف را انتخاب کن:",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text && ($currentUser['step'] ?? '') === 'admin_coupon_wiz_code' && isBotAdmin($user_id)) {
    $code = strtoupper(preg_replace('/[^A-Z0-9]/i', '', trim($text)));
    if (strlen($code) < 3 || strlen($code) > 20) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "⚠️ کد باید ۳ تا ۲۰ کاراکتر انگلیسی/عدد باشد."]);
        exit();
    }
    $stmt = $db->prepare("SELECT id FROM coupons WHERE code = ?");
    $stmt->execute([$code]);
    if ($stmt->fetch()) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ این کد از قبل وجود دارد. کد دیگری بفرست."]);
        exit();
    }
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["admin_coupon_wiz_pct:{$code}", $user_id]);
    $pctBtns = [];
    foreach ([10, 15, 20, 25, 30, 40, 50] as $p) {
        $pctBtns[] = ['text' => "{$p}٪", 'callback_data' => "adm_cp_pct:{$code}:{$p}"];
    }
    $rows = array_chunk($pctBtns, 4);
    $rows[] = [['text' => '❌ انصراف', 'callback_data' => 'adm_coupons', 'style' => 'danger']];
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "🏷 <b>ویزارد کد تخفیف — مرحله ۲/۳</b>\n\nکد: <code>{$code}</code>\n\nدرصد تخفیف را انتخاب کن:",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_cp_pct:') === 0 && isBotAdmin($user_id)) {
    $parts = explode(':', str_replace('adm_cp_pct:', '', $callback_data));
    $code = strtoupper($parts[0] ?? '');
    $pct = (int)($parts[1] ?? 0);
    if ($code === '' || $pct < 1 || $pct > 90) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'نامعتبر', 'show_alert' => true]);
        exit();
    }
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["admin_coupon_wiz_uses:{$code}:{$pct}", $user_id]);
    $useBtns = [];
    foreach ([1, 5, 10, 20, 50, 100, 500] as $u) {
        $useBtns[] = ['text' => (string)$u, 'callback_data' => "adm_cp_uses:{$code}:{$pct}:{$u}"];
    }
    $rows = array_chunk($useBtns, 4);
    $rows[] = [['text' => '❌ انصراف', 'callback_data' => 'adm_coupons', 'style' => 'danger']];
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "🏷 <b>ویزارد کد تخفیف — مرحله ۳/۳</b>\n\nکد: <code>{$code}</code>\nتخفیف: <b>{$pct}٪</b>\n\nحداکثر تعداد استفاده را انتخاب کن:",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_cp_uses:') === 0 && isBotAdmin($user_id)) {
    $parts = explode(':', str_replace('adm_cp_uses:', '', $callback_data));
    $code = strtoupper($parts[0] ?? '');
    $pct = (int)($parts[1] ?? 0);
    $uses = (int)($parts[2] ?? 0);
    if ($code === '' || $pct < 1 || $pct > 90 || $uses < 1) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'نامعتبر', 'show_alert' => true]);
        exit();
    }
    try {
        $stmt = $db->prepare("SELECT id FROM coupons WHERE code = ?");
        $stmt->execute([$code]);
        if ($stmt->fetch()) {
            sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'کد تکراری است', 'show_alert' => true]);
            exit();
        }
        $db->prepare("INSERT INTO coupons (code, discount_percent, max_uses, used_count) VALUES (?, ?, ?, 0)")
            ->execute([$code, $pct, $uses]);
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'ساخته شد']);
        sendTelegram('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $update['callback_query']['message']['message_id'],
            'text' => "✅ <b>کد تخفیف ساخته شد</b>\n\n"
                . "🏷 کد: <code>{$code}</code>\n"
                . "💯 تخفیف: {$pct}٪\n"
                . "🔢 سقف استفاده: {$uses}\n\n"
                . "مشتری موقع فاکتور می‌تواند این کد را وارد کند.",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '➕ ساخت کد دیگر', 'callback_data' => 'adm_add_coupon']],
                [['text' => '🏷 لیست کدها', 'callback_data' => 'adm_coupons']],
                [['text' => '🔙 پنل', 'callback_data' => 'adm_back', 'style' => 'danger']]
            ]], JSON_UNESCAPED_UNICODE)
        ]);
    } catch (Throwable $e) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'خطا در ذخیره', 'show_alert' => true]);
        @file_put_contents(__DIR__ . '/bot_error.log', date('c') . ' coupon_wiz ' . $e->getMessage() . "\n", FILE_APPEND);
    }
    exit();
}

// سازگاری با فرمت قدیمی: CODE PERCENT USES در یک پیام
if ($text && ($currentUser['step'] ?? '') === 'admin_add_coupon' && isBotAdmin($user_id)) {
    $parts = preg_split('/\s+/', trim($text));
    if (count($parts) >= 3) {
        $db->prepare("INSERT INTO coupons (code, discount_percent, max_uses, used_count) VALUES (?, ?, ?, 0)")->execute([strtoupper($parts[0]), (int)$parts[1], (int)$parts[2]]);
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ کد ساخته شد."]);
    }
    exit();
}


if ($callback_data === 'adm_broadcast_start' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'admin_broadcast' WHERE user_id = ?")->execute([$user_id]);
    $kb = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_back', 'style' => 'danger']]]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📢 <b>ارسال پیام همگانی</b>\n\nمتن پیام را ارسال کنید:\n(برای همه کاربران ربات فرستاده می‌شود)",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data === 'adm_recent_orders' && isBotAdmin($user_id)) {
    $list = $db->query("SELECT o.*, u.username as tg_user FROM orders o LEFT JOIN users u ON o.user_id = u.user_id ORDER BY o.id DESC LIMIT 8")->fetchAll();
    $txt = "📋 <b>آخرین سفارش‌ها</b>\n\n";
    if (empty($list)) {
        $txt .= "هنوز سفارشی ثبت نشده.";
    } else {
        foreach ($list as $l) {
            $date = function_exists('formatJalaliDateTime')
                ? formatJalaliDateTime($l['created_at'] ?? '')
                : substr($l['created_at'] ?? '', 0, 16);
            $vol = $l['volume_gb'] < 1 ? ($l['volume_gb'] * 1000) . "MB" : $l['volume_gb'] . "GB";
            $txt .= "• <code>{$l['config_username']}</code> | {$vol}\n  کاربر: <code>{$l['user_id']}</code> | {$date}\n\n";
        }
    }
    $kb = json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت به پنل', 'callback_data' => 'adm_back', 'style' => 'danger']]]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}


// ===== مدیریت تست رایگان =====
if ($callback_data === 'adm_test_menu' && isBotAdmin($user_id)) {
    $testEnabled = isFeatureEnabled($db, 'btn_test') ? '🟢 روشن' : '🔴 خاموش';
    $defP = null; try { foreach (listBotPanels($db, true) as $_p) { if (!empty($_p['is_default'])) { $defP = $_p; break; } } } catch (Exception $e) {}
    $groupIds = getPanelGroupIdsSetting($db, (int)($defP['id'] ?? 0));
    if ($groupIds === '' || $groupIds === '0') { $groupIds = '—'; }
    $usedTests = (int)$db->query("SELECT COUNT(*) FROM users WHERE has_used_test = 1")->fetchColumn();
    $testOrders = (int)$db->query("SELECT COUNT(*) FROM orders WHERE volume_gb <= 0.15 OR config_username LIKE 'test_%'")->fetchColumn();

    $txt = "🎁 <b>مدیریت تست رایگان</b>\n\n"
         . "وضعیت دکمه تست: <b>{$testEnabled}</b>\n"
         . "کاربران استفاده‌کرده: <b>{$usedTests}</b>\n"
         . "اکانت‌های تست در دیتابیس: <b>{$testOrders}</b>\n"
         . "گروه پنل پیش‌فرض: <code>{$groupIds}</code> (هر پنل جدا — از مدیریت پنل‌ها)\n\n"
         . "یکی از گزینه‌ها را انتخاب کنید:";

    $kb = json_encode(['inline_keyboard' => [
        [['text' => '🔌 تست اتصال پنل پاسارگاد', 'callback_data' => 'adm_test_panel']],
        [['text' => '📁 لیست گروه‌های پنل (ID واقعی)', 'callback_data' => 'adm_test_list_groups']],
        [['text' => '📥 خواندن گروه از نام کاربری', 'callback_data' => 'adm_test_groups_from_user']],
        [['text' => '📋 آخرین اکانت‌های تست', 'callback_data' => 'adm_test_list']],
        [['text' => '♻️ ریست تست یک کاربر', 'callback_data' => 'adm_test_reset_start']],
        [['text' => '⚙️ تغییر group_ids', 'callback_data' => 'adm_test_set_groups']],
        [['text' => ($testEnabled === '🟢 روشن' ? '🔴 خاموش کردن تست' : '🟢 روشن کردن تست'), 'callback_data' => 'adm_toggle_feat:btn_test']],
        [['text' => '🔙 تنظیمات', 'callback_data' => 'adm_settings_menu', 'style' => 'danger'], ['text' => '👑 پنل', 'callback_data' => 'adm_back']]
    ]], JSON_UNESCAPED_UNICODE);

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data === 'adm_test_panel' && isBotAdmin($user_id)) {
    $info = getPasargadToken(true);
    if (!empty($info['ok'])) {
        $msg = "✅ <b>اتصال به پنل برقرار است</b>\n\n"
             . "توکن با موفقیت دریافت شد.\n"
             . "HTTP: <code>{$info['http']}</code>\n\n"
             . "اگر ساخت تست هنوز خطا می‌دهد، <code>group_ids</code> را از منوی تست تنظیم کن.";
    } else {
        $preview = htmlspecialchars($info['body_preview'] ?? '');
        $curlErr = htmlspecialchars($info['curl_error'] ?? '');
        $urlShow = htmlspecialchars($info['url'] ?? '');
        $msg = "❌ <b>اتصال به پنل ناموفق</b>\n\n"
             . "آدرس درخواست:\n<code>{$urlShow}</code>\n"
             . "HTTP: <code>{$info['http']}</code>\n"
             . ($curlErr ? "خطای cURL: <code>{$curlErr}</code>\n" : "")
             . "\nپاسخ خام پنل:\n<code>{$preview}</code>\n\n"
             . "📌 موارد رایج:\n"
             . "• PANEL_URL اشتباه یا بدون https\n"
             . "• یوزر/پسورد ادمین پنل اشتباه\n"
             . "• فایروال پنل دسترسی هاست را بسته\n"
             . "• پنل خاموش یا دامنه منقضی";
    }
    $kb = json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_test_menu', 'style' => 'danger']]]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $msg,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}



if ($callback_data === 'adm_test_groups_from_user' && isBotAdmin($user_id)) {
    $panels = listBotPanels($db, true);
    $rows = [];
    foreach ($panels as $pn) {
        $rows[] = [['text' => '📥 ' . $pn['name'], 'callback_data' => 'adm_panel_gfrom:' . $pn['id']]];
    }
    $rows[] = [['text' => '🔙 بازگشت', 'callback_data' => 'adm_test_menu', 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📥 خواندن گروه — اول پنل را انتخاب کن:",
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}
if (false && $callback_data === 'adm_test_groups_from_user_old' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_read_groups_user' WHERE user_id = ?")->execute([$user_id]);
    $kb = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_test_menu', 'style' => 'danger']]]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📥 <b>خواندن group_ids از کاربر پنل</b>\n\nنام کاربری یک کانفیگ <b>سالم</b> را بفرست (مثال: <code>M01</code>)\nتا گروه همان کاربر برای ساخت‌های بعدی ذخیره شود.",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_read_groups_user' && isBotAdmin($user_id)) {
    $uname = trim($text);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $info = getPasargadUser($uname, panelFromUsername($uname, $db));
    if (!$info || !is_array($info)) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ کاربر در پنل پیدا نشد یا اتصال برقرار نشد.",
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_test_menu', 'style' => 'danger']]]])
        ]);
        exit();
    }
    $gids = $info['group_ids'] ?? $info['groups'] ?? null;
    $raw = json_encode($info, JSON_UNESCAPED_UNICODE);
    $preview = mb_substr($raw, 0, 500);

    if (is_array($gids) && !empty($gids)) {
        // ممکن است آرایه عدد یا آرایه آبجکت باشد
        $ids = [];
        foreach ($gids as $item) {
            if (is_numeric($item)) $ids[] = (int)$item;
            elseif (is_array($item) && isset($item['id'])) $ids[] = (int)$item['id'];
        }
        $ids = array_values(array_unique(array_filter($ids)));
        if (!empty($ids)) {
            $val = implode(',', $ids);
            setSetting($db, 'pasargad_group_ids', $val);
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => "✅ از کاربر <code>{$uname}</code> خوانده شد.\n\ngroup_ids ذخیره شد: <code>{$val}</code>\n\nاز این به بعد تست و خرید با همین گروه ساخته می‌شوند.",
                'parse_mode' => 'HTML',
                'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_test_menu', 'style' => 'danger']]]])
            ]);
            exit();
        }
    }

    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "⚠️ فیلد group_ids واضح نبود.\n\nبخشی از پاسخ پنل:\n<code>" . htmlspecialchars($preview) . "</code>\n\nاگر داخلش id گروه دیدی، دستی در «تغییر group_ids» همان عدد را بفرست.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_test_menu', 'style' => 'danger']]]])
    ]);
    exit();
}

if ($callback_data === 'adm_test_list_groups' && isBotAdmin($user_id)) {
    $panels = listBotPanels($db, true);
    $rows = [];
    foreach ($panels as $pn) {
        $rows[] = [['text' => '📁 ' . $pn['name'], 'callback_data' => 'adm_panel_glist:' . $pn['id']]];
    }
    $rows[] = [['text' => '🔙 بازگشت', 'callback_data' => 'adm_test_menu', 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📁 <b>لیست گروه‌ها</b>

کدام پنل؟",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}
if (false && $callback_data === 'adm_test_list_groups_old' && isBotAdmin($user_id)) {
    $token = getPasargadToken();
    $kb = json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_test_menu', 'style' => 'danger']]]]);
    if (!$token) {
        sendTelegram('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $update['callback_query']['message']['message_id'],
            'text' => "❌ توکن پنل گرفته نشد.",
            'reply_markup' => $kb
        ]);
        exit();
    }
    $url = getPanelApiBase() . '/api/groups';
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Accept: application/json'],
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_TIMEOUT => 20
    ]);
    $res = curl_exec($ch);
    $http = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    $data = json_decode($res, true);

    $txt = "📁 <b>گروه‌های پنل</b>\nHTTP: <code>{$http}</code>\n\n";
    if (is_array($data) && !empty($data)) {
        // ممکن است آرایه مستقیم یا داخل key باشد
        $groups = isset($data[0]) ? $data : ($data['groups'] ?? $data);
        if (is_array($groups)) {
            foreach ($groups as $g) {
                if (!is_array($g)) continue;
                $id = $g['id'] ?? '?';
                $name = htmlspecialchars($g['name'] ?? $g['title'] ?? '-');
                $txt .= "• ID: <code>{$id}</code> — نام: <b>{$name}</b>\n";
            }
        } else {
            $txt .= "<code>" . htmlspecialchars(mb_substr($res, 0, 400)) . "</code>";
        }
        $txt .= "\n\nهمین <code>ID</code> را در تنظیم group_ids بفرست.";
    } else {
        $txt .= "پاسخ خالی یا نامعتبر:\n<code>" . htmlspecialchars(mb_substr((string)$res, 0, 400)) . "</code>\n\nاگر API گروه‌ها در این پنل نباشد، group_ids را خالی بگذار (عدد 0 بفرست).";
    }
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data === 'adm_test_list' && isBotAdmin($user_id)) {
    $list = $db->query("SELECT * FROM orders WHERE volume_gb <= 0.15 OR config_username LIKE 'test_%' ORDER BY id DESC LIMIT 10")->fetchAll();
    $txt = "📋 <b>آخرین اکانت‌های تست</b>\n\n";
    if (empty($list)) {
        $txt .= "موردی یافت نشد.";
    } else {
        foreach ($list as $l) {
            $date = function_exists('formatJalaliDateTime')
                ? formatJalaliDateTime($l['created_at'] ?? '')
                : substr($l['created_at'] ?? '', 0, 16);
            $txt .= "• <code>{$l['config_username']}</code>\n  کاربر: <code>{$l['user_id']}</code> | {$date}\n\n";
        }
    }
    $kb = json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_test_menu', 'style' => 'danger']]]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data === 'adm_test_reset_start' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_test_reset_uid' WHERE user_id = ?")->execute([$user_id]);
    $kb = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_test_menu', 'style' => 'danger']]]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "♻️ <b>ریست تست رایگان</b>\n\nشناسه عددی (User ID) کاربر را بفرست تا بتواند دوباره تست بگیرد:",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($text && ($currentUser['step'] ?? '') === 'adm_test_reset_uid' && isBotAdmin($user_id)) {
    $targetUid = (int)preg_replace('/[^0-9]/', '', $text);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if ($targetUid > 0) {
        if (function_exists('jetResetUserTests')) {
            jetResetUserTests($db, $targetUid);
        } else {
            $db->prepare("UPDATE users SET has_used_test = 0 WHERE user_id = ?")->execute([$targetUid]);
        }
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ تست‌های کاربر <code>{$targetUid}</code> ریست شد. الان می‌تواند دوباره از هر دسته تست بگیرد.",
            'parse_mode' => 'HTML'
        ]);
        sendTelegram('sendMessage', [
            'chat_id' => $targetUid,
            'text' => "🎁 امکان دریافت تست رایگان دوباره برای شما فعال شد.
از منوی اصلی گزینه تست را بزنید."
        ]);

    } else {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "شناسه نامعتبر است."]);
    }
    exit();
}

if ($callback_data === 'adm_test_set_groups' && isBotAdmin($user_id)) {
    $panels = listBotPanels($db, true);
    $rows = [];
    foreach ($panels as $pn) {
        $g = getPanelGroupIdsSetting($db, (int)$pn['id']);
        $g = ($g === '' || $g === '0') ? '—' : $g;
        $rows[] = [['text' => '⚙️ ' . $pn['name'] . ' (' . $g . ')', 'callback_data' => 'adm_panel_gset:' . $pn['id']]];
    }
    $rows[] = [['text' => '🔙 بازگشت', 'callback_data' => 'adm_test_menu', 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "⚙️ group_ids — هر پنل جدا. یکی را انتخاب کن:",
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE),
    ]);
    exit();
}
if (false && $callback_data === 'adm_test_set_groups_old' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_set_group_ids' WHERE user_id = ?")->execute([$user_id]);
    $current = getSetting($db, 'pasargad_group_ids', '25,24');
    $kb = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_test_menu', 'style' => 'danger']]]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "⚙️ <b>تنظیم group_ids پنل</b>\n\nمقدار فعلی: <code>{$current}</code>\n\nفقط <b>ID عددی</b> را بفرست (نه نام گروه).\nمثال: <code>1</code> یا <code>2,3</code>\nبرای بدون گروه عدد <code>0</code> را بفرست.\n\nاز دکمه «لیست گروه‌های پنل» می‌توانی ID واقعی را ببینی.",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

// توجه: در PHP رشته "0" در شرط if ($text) برابر false است
if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_set_group_ids' && isBotAdmin($user_id)) {
    $val = preg_replace('/[^0-9,]/', '', trim($text));
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if ($val === '' || $val === '0') {
        setSetting($db, 'pasargad_group_ids', '0');
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ group_ids خالی شد (بدون گروه).\nحالا دوباره تست رایگان را امتحان کن.",
            'parse_mode' => 'HTML'
        ]);
    } else {
        setSetting($db, 'pasargad_group_ids', $val);
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ group_ids روی <code>{$val}</code> تنظیم شد.\nحالا دوباره تست رایگان را امتحان کن.",
            'parse_mode' => 'HTML'
        ]);
    }
    exit();
}


// ===== فیش‌های در انتظار =====
if ($callback_data === 'adm_pending_pays' && isBotAdmin($user_id)) {
    // فقط فیش واقعی در صف — نه پیش‌فاکتور AWAITING_RECEIPT
    $list = $db->query("SELECT * FROM payments WHERE status = 'pending' AND photo_file_id IS NOT NULL AND photo_file_id NOT IN ('AWAITING_RECEIPT','WALLET_PAY','SMS_AUTO','ADMIN_CREDIT','ADMIN_DEBIT') ORDER BY id DESC LIMIT 15")->fetchAll();
    if (empty($list)) {
        $kb = json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_back', 'style' => 'danger']]]]);
        sendTelegram('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $update['callback_query']['message']['message_id'],
            'text' => "✅ هیچ فیش در انتظاری وجود ندارد.",
            'reply_markup' => $kb
        ]);
        exit();
    }
    $txt = "⏳ <b>فیش‌های در انتظار</b> (" . count($list) . ")\n\nیکی را برای جزئیات انتخاب کن:";
    $buttons = [];
    foreach ($list as $p) {
        $label = "#{$p['id']} | " . number_format((int)$p['price']) . "ت | " . ($p['action_type'] ?: 'buy');
        $buttons[] = [['text' => $label, 'callback_data' => 'adm_pend_view:' . $p['id']]];
    }
    $buttons[] = [['text' => '🔙 بازگشت', 'callback_data' => 'adm_back', 'style' => 'danger']];
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $buttons])
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_pend_view:') === 0 && isBotAdmin($user_id)) {
    $pid = (int)str_replace('adm_pend_view:', '', $callback_data);
    if (!empty($update['callback_query']['id'])) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    }
    $stmt = $db->prepare("SELECT * FROM payments WHERE id = ?");
    $stmt->execute([$pid]);
    $p = $stmt->fetch();
    if (!$p) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ فیش یافت نشد یا حذف شده.']);
        exit();
    }
    $review = buildPaymentReviewInfo($db, $p);
    $txt = $review['html'];
    $kb = json_encode(['inline_keyboard' => [
        [['text' => '✅ تأیید', 'callback_data' => "adm_app_{$pid}"], ['text' => '❌ رد', 'callback_data' => "adm_rej_{$pid}", 'style' => 'danger']],
        [['text' => '🔙 لیست فیش‌ها', 'callback_data' => 'adm_pending_pays', 'style' => 'danger']]
    ]]);

    // فقط file_id واقعی تلگرام (نه AWAITING_RECEIPT / WALLET_PAY)
    $fid = (string)($p['photo_file_id'] ?? '');
    $isRealPhoto = ($fid !== '' && $fid !== 'WALLET_PAY' && $fid !== 'AWAITING_RECEIPT' && strlen($fid) > 20);

    if ($isRealPhoto) {
        $res = sendTelegram('sendPhoto', [
            'chat_id' => $chat_id,
            'photo' => $fid,
            'caption' => $txt,
            'parse_mode' => 'HTML',
            'reply_markup' => $kb
        ]);
        if (empty($res['ok'])) {
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => $txt . "\n\n⚠️ عکس فیش قابل نمایش نیست.",
                'parse_mode' => 'HTML',
                'reply_markup' => $kb
            ]);
        }
    } else {
        $note = ($fid === 'AWAITING_RECEIPT') ? "\n\n⏳ هنوز عکس فیش ارسال نشده (فقط پیش‌فاکتور)." : '';
        $hasPhotoMsg = !empty($update['callback_query']['message']['photo']);
        if (!$hasPhotoMsg && !empty($update['callback_query']['message']['message_id'])) {
            sendTelegram('editMessageText', [
                'chat_id' => $chat_id,
                'message_id' => $update['callback_query']['message']['message_id'],
                'text' => $txt . $note,
                'parse_mode' => 'HTML',
                'reply_markup' => $kb
            ]);
        } else {
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => $txt . $note,
                'parse_mode' => 'HTML',
                'reply_markup' => $kb
            ]);
        }
    }
    exit();
}

// ===== جستجوی کاربر (جزئی + چند نتیجه) =====
if ($callback_data === 'adm_user_search_start' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_user_search' WHERE user_id = ?")->execute([$user_id]);
    $kb = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_back', 'style' => 'danger']]]], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "👤 <b>جستجوی کاربر</b>\n\n"
               . "می‌توانی بخشی از این‌ها را بفرستی:\n"
               . "• شناسه عددی تلگرام\n"
               . "• یوزرنیم تلگرام (با یا بدون @)\n"
               . "• نام کانفیگ / سرویس\n\n"
               . "نتایج نزدیک به‌صورت لیست انتخابی نمایش داده می‌شود.",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_user_search' && isBotAdmin($user_id)) {
    $q = trim($text);
    $q = ltrim($q, '@');
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    if (mb_strlen($q) < 2 && !preg_match('/^\d+$/', $q)) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "⚠️ حداقل ۲ کاراکتر وارد کن (یا یک شناسه عددی کامل).",
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '🔍 جستجوی دوباره', 'callback_data' => 'adm_user_search_start']],
                [['text' => '🔙 پنل', 'callback_data' => 'adm_back', 'style' => 'danger']]
            ]], JSON_UNESCAPED_UNICODE)
        ]);
        exit();
    }

    $esc = str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], $q);
    $like = '%' . $esc . '%';
    $byId = [];

    // تطبیق دقیق ID
    if (preg_match('/^\d+$/', $q)) {
        $stmt = $db->prepare("SELECT * FROM users WHERE user_id = ? LIMIT 1");
        $stmt->execute([(int)$q]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        if ($row) {
            $byId[(int)$row['user_id']] = $row;
        }
        // بخشی از شناسه
        $stmt = $db->prepare("SELECT * FROM users WHERE CAST(user_id AS CHAR) LIKE ? ORDER BY user_id DESC LIMIT 20");
        $stmt->execute([$like]);
        foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
            $byId[(int)$row['user_id']] = $row;
        }
    }

    // یوزرنیم تلگرام (جزئی، بدون حساسیت به حروف در collation معمول)
    $stmt = $db->prepare("SELECT * FROM users WHERE username IS NOT NULL AND username != '' AND username LIKE ? ORDER BY user_id DESC LIMIT 20");
    $stmt->execute([$like]);
    foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
        $byId[(int)$row['user_id']] = $row;
    }

    // نام کانفیگ / سرویس (جزئی)
    $stmt = $db->prepare(
        "SELECT u.* FROM users u
         WHERE u.user_id IN (
             SELECT DISTINCT o.user_id FROM orders o WHERE o.config_username LIKE ?
         )
         ORDER BY u.user_id DESC
         LIMIT 20"
    );
    $stmt->execute([$like]);
    foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
        $byId[(int)$row['user_id']] = $row;
    }

    // کانفیگ‌های منطبق برای نمایش کنار دکمه
    $cfgByUser = [];
    $stmt = $db->prepare(
        "SELECT user_id, config_username FROM orders WHERE config_username LIKE ? ORDER BY id DESC LIMIT 40"
    );
    $stmt->execute([$like]);
    foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $o) {
        $uidk = (int)$o['user_id'];
        if (!isset($cfgByUser[$uidk])) {
            $cfgByUser[$uidk] = $o['config_username'];
        }
    }

    if (empty($byId)) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ نتیجه‌ای برای «" . htmlspecialchars($q) . "» پیدا نشد.",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '🔍 جستجوی دوباره', 'callback_data' => 'adm_user_search_start']],
                [['text' => '🔙 پنل', 'callback_data' => 'adm_back', 'style' => 'danger']]
            ]], JSON_UNESCAPED_UNICODE)
        ]);
        exit();
    }

    // یک نتیجه → مستقیم جزئیات (از طریق view)
    if (count($byId) === 1) {
        $only = reset($byId);
        // شبیه‌سازی adm_user_view با ارسال پیام جزئیات
        $callback_data = 'adm_user_view:' . (int)$only['user_id'];
        // ادامه در همان handler بعدی سخت است؛ خودمان جزئیات را می‌سازیم مثل قبل با ریدایرکت ساده
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ یک نتیجه پیدا شد — در حال باز کردن کاربر…",
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '👤 باز کردن کاربر', 'callback_data' => 'adm_user_view:' . (int)$only['user_id'], 'style' => 'primary']],
                [['text' => '🔍 جستجوی دوباره', 'callback_data' => 'adm_user_search_start']],
            ]], JSON_UNESCAPED_UNICODE)
        ]);
        exit();
    }

    // چند نتیجه → لیست انتخابی
    $list = array_values($byId);
    usort($list, function ($a, $b) {
        return (int)$b['user_id'] - (int)$a['user_id'];
    });
    $list = array_slice($list, 0, 15);
    $txt = "🔍 <b>نتایج جستجو</b> برای «" . htmlspecialchars($q) . "»\n"
         . "تعداد: <b>" . count($byId) . "</b>" . (count($byId) > 15 ? ' (نمایش ۱۵ مورد اول)' : '') . "\n\n"
         . "یکی را انتخاب کن:";
    $buttons = [];
    foreach ($list as $r) {
        $uname = !empty($r['username']) ? '@' . $r['username'] : '—';
        $cfgHint = '';
        $uidk = (int)$r['user_id'];
        if (!empty($cfgByUser[$uidk])) {
            $cfgHint = ' | ' . $cfgByUser[$uidk];
        }
        $label = "{$r['user_id']} | {$uname}{$cfgHint}";
        if (mb_strlen($label) > 64) {
            $label = mb_substr($label, 0, 61) . '…';
        }
        $buttons[] = [['text' => $label, 'callback_data' => 'adm_user_view:' . $r['user_id']]];
    }
    $buttons[] = [['text' => '🔍 جستجوی دوباره', 'callback_data' => 'adm_user_search_start']];
    $buttons[] = [['text' => '🔙 پنل', 'callback_data' => 'adm_back', 'style' => 'danger']];

    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $buttons], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_usr_reset_test:') === 0 && isBotAdmin($user_id)) {
    $tid = (int)str_replace('adm_usr_reset_test:', '', $callback_data);
    jetResetUserTests($db, (int)$tid);
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'تست ریست شد', 'show_alert' => true]);
    sendTelegram('sendMessage', ['chat_id' => $tid, 'text' => "🎁 امکان تست رایگان دوباره برای شما فعال شد."]);
    exit();
}


// ===== لیست کاربران / سرویس‌ها + حذف از پنل =====
// callback: adm_users_list:{filter}:{sort}:{page}
// سازگار با قدیمی: adm_users_list:{page} و adm_users_list:{filter}:{page}
if ($callback_data && strpos($callback_data, 'adm_users_list:') === 0 && isBotAdmin($user_id)) {
    if (getSetting($db, 'users_created_at_col_v1', '') !== '1') {
        try {
            $db->exec("ALTER TABLE users ADD COLUMN created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP");
        } catch (Exception $e) { /* already exists */ }
        try { setSetting($db, 'users_created_at_col_v1', '1'); } catch (Exception $e) {}
    }

    $rest = str_replace('adm_users_list:', '', $callback_data);
    $filter = 'all';
    $sort = 'new';
    $page = 0;
    if (preg_match('/^(all|bought|test|svc|bal):(new|sbal|ssvc):(\d+)$/', $rest, $m)) {
        $filter = $m[1];
        $sort = $m[2];
        $page = max(0, (int)$m[3]);
    } elseif (preg_match('/^(all|bought|test|svc|bal):(\d+)$/', $rest, $m)) {
        $filter = $m[1];
        $sort = 'new';
        $page = max(0, (int)$m[2]);
    } elseif (ctype_digit($rest)) {
        $page = max(0, (int)$rest);
        $filter = 'all';
        $sort = 'new';
    }
    if (!in_array($sort, ['new', 'sbal', 'ssvc'], true)) {
        $sort = 'new';
    }

    $perPage = 8;
    $offset = $page * $perPage;

    $filterTitles = [
        'all' => 'همه',
        'bought' => 'پرداختی (حداقل یک خرید)',
        'test' => 'استفاده‌کننده تست',
        'svc' => 'دارای سرویس (حتی تست)',
        'bal' => 'موجودی کیف > ۰',
    ];
    $sortTitles = [
        'new' => 'جدیدترین عضویت',
        'sbal' => 'بیشترین موجودی',
        'ssvc' => 'بیشترین سرویس',
    ];
    switch ($filter) {
        case 'bought':
            $where = 'u.has_bought = 1';
            break;
        case 'test':
            $where = 'u.has_used_test = 1';
            break;
        case 'svc':
            $where = 'EXISTS (SELECT 1 FROM orders o2 WHERE o2.user_id = u.user_id)';
            break;
        case 'bal':
            $where = 'u.balance > 0';
            break;
        default:
            $filter = 'all';
            $where = '1=1';
            break;
    }

    switch ($sort) {
        case 'sbal':
            $orderBy = 'u.balance DESC, u.user_id DESC';
            break;
        case 'ssvc':
            $orderBy = 'svc_count DESC, u.user_id DESC';
            break;
        default:
            $sort = 'new';
            // جدیدترین = زمان عضویت در ربات (نه آخرین خرید)
            $orderBy = 'COALESCE(u.created_at, FROM_UNIXTIME(0)) DESC, u.user_id DESC';
            break;
    }

    $baseCb = function ($f, $s, $p) {
        return 'adm_users_list:' . $f . ':' . $s . ':' . $p;
    };

    try {
        $db->exec("ALTER TABLE users ADD COLUMN admin_note VARCHAR(255) NULL DEFAULT NULL");
    } catch (Exception $e) { /* exists */ }
    $total = 0;
    $rows = [];
    try {
        $total = (int)$db->query("SELECT COUNT(*) FROM users u WHERE {$where}")->fetchColumn();
        $stmt = $db->prepare(
            "SELECT u.user_id, u.username, u.balance, u.has_bought, u.has_used_test, u.created_at, u.admin_note,
                    (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.user_id) AS svc_count,
                    (SELECT COALESCE(MAX(o.id), 0) FROM orders o WHERE o.user_id = u.user_id) AS last_order_id
             FROM users u
             WHERE {$where}
             ORDER BY {$orderBy}
             LIMIT {$perPage} OFFSET {$offset}"
        );
        $stmt->execute();
        $rows = $stmt->fetchAll();
    } catch (Exception $e) {
        // fallback بدون created_at / last_order
        try {
            $total = (int)$db->query("SELECT COUNT(*) FROM users u WHERE {$where}")->fetchColumn();
            $stmt = $db->prepare(
                "SELECT u.user_id, u.username, u.balance, u.has_bought, u.has_used_test, u.admin_note,
                        (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.user_id) AS svc_count,
                        0 AS last_order_id
                 FROM users u
                 WHERE {$where}
                 ORDER BY u.user_id DESC
                 LIMIT {$perPage} OFFSET {$offset}"
            );
            $stmt->execute();
            $rows = $stmt->fetchAll();
        } catch (Exception $e2) {
            sendTelegram('answerCallbackQuery', [
                'callback_query_id' => $update['callback_query']['id'],
                'text' => 'خطا در لیست کاربران',
                'show_alert' => true
            ]);
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => '❌ خطا در بارگذاری کاربران: ' . htmlspecialchars(mb_substr($e2->getMessage(), 0, 200)),
                'parse_mode' => 'HTML'
            ]);
            exit();
        }
    }

    $fTitle = $filterTitles[$filter] ?? 'همه';
    $sTitle = $sortTitles[$sort] ?? 'جدیدترین عضویت در ربات';
    $txt = "👥 <b>لیست کاربران</b>\n"
         . "فیلتر: <b>{$fTitle}</b> | مرتب‌سازی: <b>{$sTitle}</b>\n"
         . "صفحه " . ($page + 1) . " | تعداد: <b>{$total}</b>\n\n"
         . "🔵 فیلتر · 🟢 مرتب‌سازی · 🔴 پاک‌کردن\n"
         . "برای یک نفر مشخص از <b>جستجو</b> استفاده کن.";

    $markF = function ($key, $label) use ($filter) {
        return ($filter === $key ? '• ' : '') . $label;
    };
    $markS = function ($key, $label) use ($sort) {
        return ($sort === $key ? '• ' : '') . $label;
    };

    $buttons = [
        [
            ['text' => $markF('all', 'همه'), 'callback_data' => $baseCb('all', $sort, 0), 'style' => 'primary'],
            ['text' => $markF('bought', 'پرداختی'), 'callback_data' => $baseCb('bought', $sort, 0), 'style' => 'primary'],
            ['text' => $markF('test', 'تست'), 'callback_data' => $baseCb('test', $sort, 0), 'style' => 'primary'],
        ],
        [
            ['text' => $markF('svc', 'دارای سرویس'), 'callback_data' => $baseCb('svc', $sort, 0), 'style' => 'primary'],
            ['text' => $markF('bal', 'با موجودی'), 'callback_data' => $baseCb('bal', $sort, 0), 'style' => 'primary'],
        ],
        [
            ['text' => $markS('new', 'جدیدترین'), 'callback_data' => $baseCb($filter, 'new', 0), 'style' => 'success'],
            ['text' => $markS('sbal', '💰 موجودی'), 'callback_data' => $baseCb($filter, 'sbal', 0), 'style' => 'success'],
            ['text' => $markS('ssvc', '📦 سرویس'), 'callback_data' => $baseCb($filter, 'ssvc', 0), 'style' => 'success'],
        ],
        [
            ['text' => '🔄 حذف فیلتر و مرتب‌سازی', 'callback_data' => $baseCb('all', 'new', 0), 'style' => 'danger'],
            ['text' => '🔍 جستجو', 'callback_data' => 'adm_user_search_start'],
        ],
    ];

    foreach ($rows as $r) {
        $uname = $r['username'] ? '@' . $r['username'] : '—';
        $note = trim((string)($r['admin_note'] ?? ''));
        $notePart = $note !== '' ? (' | 📝' . $note) : '';
        $bal = (int)$r['balance'];
        $balTxt = $bal >= 1000 ? (number_format((int)round($bal / 1000)) . 'k') : (string)$bal;
        $flags = [];
        if ((int)$r['has_bought']) {
            $flags[] = '✅';
        }
        if ((int)$r['has_used_test']) {
            $flags[] = '🎁';
        }
        $flagStr = $flags ? (' ' . implode('', $flags)) : '';
        // هم یوزرنیم هم توضیح؛ محدودیت ۶۴ کاراکتر تلگرام
        $label = "{$r['user_id']} | {$uname}{$notePart} | 💰{$balTxt} | 📦{$r['svc_count']}{$flagStr}";
        if (mb_strlen($label) > 64) {
            $label = mb_substr($label, 0, 61) . '...';
        }
        $buttons[] = [['text' => $label, 'callback_data' => 'adm_user_view:' . $r['user_id']]];
    }

    $nav = [];
    if ($page > 0) {
        $nav[] = ['text' => '◀️ قبلی', 'callback_data' => $baseCb($filter, $sort, $page - 1)];
    }
    if (($offset + $perPage) < $total) {
        $nav[] = ['text' => 'بعدی ▶️', 'callback_data' => $baseCb($filter, $sort, $page + 1)];
    }
    if (!empty($nav)) {
        $buttons[] = $nav;
    }
    $buttons[] = [['text' => '🔙 بازگشت به پنل', 'callback_data' => 'adm_back', 'style' => 'danger']];

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $buttons], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_user_view:') === 0 && isBotAdmin($user_id)) {
    $uid = (int)str_replace('adm_user_view:', '', $callback_data);
    try {
        $db->exec("ALTER TABLE users ADD COLUMN admin_note VARCHAR(255) NULL DEFAULT NULL");
    } catch (Exception $e) { /* exists */ }
    $stmt = $db->prepare("SELECT * FROM users WHERE user_id = ?");
    $stmt->execute([$uid]);
    $u = $stmt->fetch();
    if (!$u) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'کاربر یافت نشد', 'show_alert' => true]);
        exit();
    }
    $orders = $db->prepare("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 20");
    $orders->execute([$uid]);
    $orderRows = $orders->fetchAll();

    $joinTxt = '—';
    if (!empty($u['created_at']) && function_exists('formatJalaliDateTime')) {
        $joinTxt = formatJalaliDateTime($u['created_at'], true);
    } elseif (!empty($u['created_at'])) {
        $joinTxt = htmlspecialchars(substr((string)$u['created_at'], 0, 16));
    }
    $noteRaw = trim((string)($u['admin_note'] ?? ''));
    $noteLine = $noteRaw !== ''
        ? "📝 توضیح ادمین: <b>" . htmlspecialchars($noteRaw) . "</b>
"
        : "📝 توضیح ادمین: <i>ثبت نشده</i>
";
    $isAppUser = ($uid >= 700000000000);
    if (!$isAppUser) {
        try {
            $unChk = ltrim((string)($u['username'] ?? ''), '@');
            if ($unChk !== '') {
                $stA = $db->prepare('SELECT id FROM app_accounts WHERE LOWER(config_username) = LOWER(?) LIMIT 1');
                $stA->execute([$unChk]);
                if ($stA->fetch()) { $isAppUser = true; }
            }
        } catch (Exception $e) {}
    }
    $channelLine = $isAppUser ? "📡 کانال: <b>📱 اپ اختصاصی</b>
" : "📡 کانال: <b>✈️ تلگرام</b>
";
    $unDisp = htmlspecialchars(ltrim((string)($u['username'] ?? '-'), '@'));
    $txt = "👤 <b>کاربر</b> <code>{$uid}</code>
"
         . $channelLine
         . ($isAppUser ? "نام کاربری اپ: <code>{$unDisp}</code>
" : "یوزرنیم: @{$unDisp}
")
         . $noteLine
         . "📅 عضویت: <b>{$joinTxt}</b>
"
         . "💰 موجودی: <b>" . number_format((int)$u['balance']) . " ت</b>
"
         . "🛒 خرید: " . ((int)$u['has_bought'] ? 'بله' : 'خیر') . " | 🎁 تست: " . ((int)$u['has_used_test'] ? 'بله' : 'خیر') . "

"
         . "📦 <b>سرویس‌ها (" . count($orderRows) . "):</b>
";
    if (empty($orderRows)) {
        $txt .= "— سفارشی ثبت نشده\n";
    } else {
        foreach ($orderRows as $o) {
            $vol = ((float)$o['volume_gb'] < 1) ? round($o['volume_gb'] * 1000) . "MB" : $o['volume_gb'] . "GB";
            $txt .= "• <code>{$o['config_username']}</code> | {$vol} | {$o['days']}روز\n";
        }
    }

    $buttons = [];
    if (!empty($isAppUser)) {
        $buttons[] = [
            ['text' => '📝 ثبت / ویرایش توضیح', 'callback_data' => 'adm_user_note:' . $uid, 'style' => 'primary'],
        ];
    } else {
        $buttons[] = [
            ['text' => '📝 ثبت / ویرایش توضیح', 'callback_data' => 'adm_user_note:' . $uid, 'style' => 'primary'],
            ['text' => '✉️ پیام به کاربر', 'callback_data' => 'adm_msg_user:' . $uid],
        ];
    }
    foreach ($orderRows as $o) {
        $uname = $o['config_username'];
        $buttons[] = [
            ['text' => '⚙️ ' . mb_substr($uname, 0, 40), 'callback_data' => 'adm_svc_open:' . $uname],
            ['text' => '🗑', 'callback_data' => 'adm_svc_del_ask:' . $uname, 'style' => 'danger']
        ];
    }
    if (!empty($orderRows)) {
        $buttons[] = [['text' => '🗑 حذف همه سرویس‌های این کاربر', 'callback_data' => 'adm_user_del_ask:' . $uid, 'style' => 'danger']];
    }
    $buttons[] = [['text' => '💰 شارژ کیف پول', 'callback_data' => 'adm_wallet_charge:' . $uid], ['text' => '♻️ ریست تست', 'callback_data' => 'adm_usr_reset_test:' . $uid]];
    $buttons[] = [['text' => '📋 سوابق واریز و خرید', 'callback_data' => 'adm_user_activity:' . $uid]];
    $buttons[] = [['text' => '📜 تاریخچه کیف پول', 'callback_data' => 'adm_user_ledger:' . $uid]];
    $buttons[] = [['text' => '➕ افزودن کانفیگ دستی', 'callback_data' => 'adm_mc_for:' . $uid]];
    if (function_exists('getOpenSupportTicket') && getOpenSupportTicket($db, $uid)) {
        $buttons[] = [['text' => '✍️ بازگشت به پاسخ تیکت', 'callback_data' => 'adm_rep:' . $uid, 'style' => 'primary']];
    }
    $buttons[] = [['text' => '👥 لیست کاربران', 'callback_data' => 'adm_users_list:0'], ['text' => '👑 پنل', 'callback_data' => 'adm_back']];

    adminSendOrEditText($chat_id, $update, $txt, json_encode(['inline_keyboard' => $buttons], JSON_UNESCAPED_UNICODE));
    exit();
}

// پیام مستقیم ادمین به کاربر از طرف ربات
if ($callback_data && strpos($callback_data, 'adm_msg_user:') === 0 && isBotAdmin($user_id)) {
    $targetUid = (int)str_replace('adm_msg_user:', '', $callback_data);
    if ($targetUid <= 0) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'کاربر نامعتبر', 'show_alert' => true]);
        exit();
    }
    if ($targetUid >= 700000000000) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'این کاربر از اپ است و پیام تلگرام ندارد', 'show_alert' => true]);
        exit();
    }
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["adm_msg_user|{$targetUid}", $user_id]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "✉️ <b>پیام به کاربر</b> <code>{$targetUid}</code>\n\n"
               . "متن پیام را بنویس و ارسال کن.\n"
               . "پیام از طرف ربات برای کاربر می‌رود.",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '❌ انصراف', 'callback_data' => 'adm_user_view:' . $targetUid]]
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text !== null && $text !== '' && strpos(($currentUser['step'] ?? ''), 'adm_msg_user|') === 0 && isBotAdmin($user_id)) {
    $targetUid = (int)str_replace('adm_msg_user|', '', $currentUser['step']);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $body = trim($text);
    if ($targetUid <= 0 || $body === '') {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ پیام خالی یا کاربر نامعتبر.']);
        exit();
    }
    $msg = "📨 <b>پیام پشتیبانی</b>\n"
         . "──────────────────\n"
         . htmlspecialchars($body);
    $ok = notifyUserFromBot($targetUid, $msg, [
        'inline_keyboard' => [
            [['text' => '💬 پشتیبانی', 'callback_data' => 'start_support']],
        ]
    ]);
    if (!$ok) {
        $ok = notifyUserFromBot($targetUid, $msg);
    }
    if ($ok) {
        if (function_exists('logSupportHumanMessage')) {
            logSupportHumanMessage($db, $targetUid, 'admin', $body, $user_id, null);
        }
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ پیام برای کاربر <code>{$targetUid}</code> ارسال شد.",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '👤 بازگشت به کاربر', 'callback_data' => 'adm_user_view:' . $targetUid, 'style' => 'primary']],
                [['text' => '✉️ پیام دیگر', 'callback_data' => 'adm_msg_user:' . $targetUid]],
            ]], JSON_UNESCAPED_UNICODE)
        ]);
    } else {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "⚠️ ارسال ناموفق بود (کاربر ممکن است ربات را بلاک کرده باشد).",
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '👤 بازگشت به کاربر', 'callback_data' => 'adm_user_view:' . $targetUid]],
            ]], JSON_UNESCAPED_UNICODE)
        ]);
    }
    exit();
}

// یادداشت ادمین روی کاربر (فقط برای ادمین؛ در صفحه کاربر نمایش داده می‌شود)
if ($callback_data && strpos($callback_data, 'adm_user_note:') === 0 && isBotAdmin($user_id)) {
    $uid = (int)str_replace('adm_user_note:', '', $callback_data);
    try {
        $db->exec("ALTER TABLE users ADD COLUMN admin_note VARCHAR(255) NULL DEFAULT NULL");
    } catch (Exception $e) { /* exists */ }
    $st = $db->prepare("SELECT admin_note FROM users WHERE user_id = ?");
    $st->execute([$uid]);
    $cur = trim((string)($st->fetchColumn() ?: ''));
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["adm_user_note|{$uid}", $user_id]);
    $hint = $cur !== '' ? ("\n\nتوضیح فعلی:\n<code>" . htmlspecialchars($cur) . "</code>") : '';
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "📝 <b>توضیح ادمین برای کاربر</b> <code>{$uid}</code>\n\n"
               . "یک متن کوتاه بفرست (مثلاً اسم واقعی یا یادداشت).\n"
               . "برای پاک کردن توضیح بنویس: <code>-</code>"
               . $hint,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '❌ انصراف', 'callback_data' => 'adm_user_view:' . $uid]]
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($text !== null && $text !== '' && strpos(($currentUser['step'] ?? ''), 'adm_user_note|') === 0 && isBotAdmin($user_id)) {
    $uid = (int)str_replace('adm_user_note|', '', $currentUser['step']);
    $note = trim($text);
    if ($note === '-' || $note === '—' || mb_strtolower($note) === 'clear') {
        $note = null;
    } else {
        $note = mb_substr($note, 0, 200);
    }
    try {
        $db->exec("ALTER TABLE users ADD COLUMN admin_note VARCHAR(255) NULL DEFAULT NULL");
    } catch (Exception $e) { /* exists */ }
    $db->prepare("UPDATE users SET admin_note = ? WHERE user_id = ?")->execute([$note, $uid]);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $shown = $note !== null ? htmlspecialchars($note) : '— (پاک شد)';
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ توضیح ذخیره شد:\n<b>{$shown}</b>",
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => [
            [['text' => '👤 بازگشت به کاربر', 'callback_data' => 'adm_user_view:' . $uid, 'style' => 'primary']]
        ]], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

// فاز ۴-A: سوابق واریز و خرید سرویس کاربر (از جدول payments — عکس فقط file_id تلگرام)
if ($callback_data && strpos($callback_data, 'adm_user_activity:') === 0 && isBotAdmin($user_id)) {
    $uid = (int)str_replace('adm_user_activity:', '', $callback_data);
    $rows = getUserActivityTimeline($db, $uid, 20);
    $histMsg = formatUserActivityMessage($db, $uid, 20);
    $kb = json_encode(buildUserActivityKeyboard($uid, $rows), JSON_UNESCAPED_UNICODE);
    adminSendOrEditText($chat_id, $update, $histMsg, $kb);
    exit();
}

// فاز ۴-A: نمایش مجدد عکس فیش ذخیره‌شده در تلگرام
if ($callback_data && strpos($callback_data, 'adm_show_receipt:') === 0 && isBotAdmin($user_id)) {
    $pid = (int)str_replace('adm_show_receipt:', '', $callback_data);
    $st = $db->prepare('SELECT * FROM payments WHERE id = ?');
    $st->execute([$pid]);
    $pay = $st->fetch(PDO::FETCH_ASSOC);
    if (!$pay || !isRealReceiptFileId($pay['photo_file_id'] ?? '')) {
        sendTelegram('answerCallbackQuery', [
            'callback_query_id' => $update['callback_query']['id'],
            'text' => 'فیش تصویری برای این پرداخت نیست.',
            'show_alert' => true
        ]);
        exit();
    }
    $caption = "🖼 <b>فیش پرداخت #{$pid}</b>\n"
        . "کاربر: <code>{$pay['user_id']}</code>\n"
        . "نوع: " . accountingActionLabel($pay['action_type'], $pay['status']) . "\n"
        . "مبلغ: <b>" . number_format((int)$pay['price']) . " تومان</b>\n"
        . "وضعیت: <code>{$pay['status']}</code>\n"
        . "زمان: <code>" . formatJalaliDateTime($pay['created_at']) . "</code>";
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    sendTelegram('sendPhoto', [
        'chat_id' => $chat_id,
        'photo' => $pay['photo_file_id'],
        'caption' => $caption,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode([
            'inline_keyboard' => [[
                ['text' => '📋 سوابق کاربر', 'callback_data' => 'adm_user_activity:' . (int)$pay['user_id']],
                ['text' => '👤 کاربر', 'callback_data' => 'adm_user_view:' . (int)$pay['user_id']],
            ]]
        ], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

// Phase 2: تاریخچه کیف پول یک کاربر برای ادمین
if ($callback_data && strpos($callback_data, 'adm_user_ledger:') === 0 && isBotAdmin($user_id)) {
    $uid = (int)str_replace('adm_user_ledger:', '', $callback_data);
    $histMsg = "👤 کاربر <code>{$uid}</code>\n\n" . formatWalletLedgerMessage($db, $uid, 15);
    $kb = json_encode([
        'inline_keyboard' => [
            [['text' => '🔄 بروزرسانی', 'callback_data' => 'adm_user_ledger:' . $uid]],
            [['text' => '👤 بازگشت به کاربر', 'callback_data' => 'adm_user_view:' . $uid]]
        ]
    ]);
    adminSendOrEditText($chat_id, $update, $histMsg, $kb);
    exit();
}

// callback: adm_services_list:{filter}:{sort}:{page}  | قدیمی: adm_services_list:{page}
if ($callback_data && strpos($callback_data, 'adm_services_list:') === 0 && isBotAdmin($user_id)) {
    $rest = str_replace('adm_services_list:', '', $callback_data);
    $filter = 'all';
    $sort = 'new';
    $page = 0;
    if (preg_match('/^(all|test|monthly|vip):(new|old|svol):(\d+)$/', $rest, $m)) {
        $filter = $m[1];
        $sort = $m[2];
        $page = max(0, (int)$m[3]);
    } elseif (preg_match('/^(all|test|monthly|vip):(\d+)$/', $rest, $m)) {
        $filter = $m[1];
        $sort = 'new';
        $page = max(0, (int)$m[2]);
    } elseif (ctype_digit($rest)) {
        $page = max(0, (int)$rest);
        $filter = 'all';
        $sort = 'new';
    }
    if (!in_array($sort, ['new', 'old', 'svol'], true)) {
        $sort = 'new';
    }

    $perPage = 8;
    $offset = $page * $perPage;

    $filterTitles = [
        'all' => 'همه',
        'test' => 'تست',
        'monthly' => 'ماهانه / مدت‌دار',
        'vip' => 'VIP بدون انقضا',
    ];
    $sortTitles = [
        'new' => 'جدیدترین',
        'old' => 'قدیمی‌ترین',
        'svol' => 'بیشترین حجم',
    ];

    $isTestSql = "(o.config_username LIKE 'test\\_%' OR o.volume_gb <= 0.15)";
    switch ($filter) {
        case 'test':
            $where = $isTestSql;
            break;
        case 'monthly':
            $where = "o.days > 0 AND NOT {$isTestSql}";
            break;
        case 'vip':
            $where = "o.days = 0 AND NOT {$isTestSql}";
            break;
        default:
            $filter = 'all';
            $where = '1=1';
            break;
    }

    switch ($sort) {
        case 'old':
            $orderBy = 'o.id ASC';
            break;
        case 'svol':
            $orderBy = 'o.volume_gb DESC, o.id DESC';
            break;
        default:
            $sort = 'new';
            $orderBy = 'o.id DESC';
            break;
    }

    $baseCb = function ($f, $s, $p) {
        return 'adm_services_list:' . $f . ':' . $s . ':' . $p;
    };

    $total = (int)$db->query("SELECT COUNT(*) FROM orders o WHERE {$where}")->fetchColumn();
    $stmt = $db->prepare(
        "SELECT o.id, o.user_id, o.config_username, o.volume_gb, o.days
         FROM orders o
         WHERE {$where}
         ORDER BY {$orderBy}
         LIMIT {$perPage} OFFSET {$offset}"
    );
    $stmt->execute();
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);

    $fTitle = $filterTitles[$filter] ?? 'همه';
    $sTitle = $sortTitles[$sort] ?? 'جدیدترین';
    $txt = "📦 <b>همه سرویس‌ها</b>\n"
         . "فیلتر: <b>{$fTitle}</b> | مرتب‌سازی: <b>{$sTitle}</b>\n"
         . "صفحه " . ($page + 1) . " | تعداد: <b>{$total}</b>\n\n"
         . "🔵 فیلتر · 🟢 مرتب‌سازی\n"
         . "روی نام بزن تا جزئیات باز شود.";

    $markF = function ($key, $label) use ($filter) {
        return ($filter === $key ? '• ' : '') . $label;
    };
    $markS = function ($key, $label) use ($sort) {
        return ($sort === $key ? '• ' : '') . $label;
    };

    $buttons = [
        [
            ['text' => $markF('all', 'همه'), 'callback_data' => $baseCb('all', $sort, 0), 'style' => 'primary'],
            ['text' => $markF('test', 'تست'), 'callback_data' => $baseCb('test', $sort, 0), 'style' => 'primary'],
            ['text' => $markF('monthly', 'ماهانه'), 'callback_data' => $baseCb('monthly', $sort, 0), 'style' => 'primary'],
            ['text' => $markF('vip', 'VIP'), 'callback_data' => $baseCb('vip', $sort, 0), 'style' => 'primary'],
        ],
        [
            ['text' => $markS('new', 'جدیدترین'), 'callback_data' => $baseCb($filter, 'new', 0), 'style' => 'success'],
            ['text' => $markS('old', 'قدیمی‌ترین'), 'callback_data' => $baseCb($filter, 'old', 0), 'style' => 'success'],
            ['text' => $markS('svol', '📦 حجم'), 'callback_data' => $baseCb($filter, 'svol', 0), 'style' => 'success'],
        ],
        [
            ['text' => '🔄 حذف فیلتر و مرتب‌سازی', 'callback_data' => $baseCb('all', 'new', 0), 'style' => 'danger'],
            ['text' => '🔍 جستجو با نام', 'callback_data' => 'adm_manage_service_start'],
        ],
    ];

    foreach ($rows as $r) {
        $volF = (float)$r['volume_gb'];
        $vol = ($volF < 1) ? (round($volF * 1000) . 'MB') : ($volF . 'GB');
        $isTest = (stripos((string)$r['config_username'], 'test_') === 0) || ($volF <= 0.15);
        if ($isTest) {
            $typeTag = '🎁';
        } elseif ((int)$r['days'] === 0) {
            $typeTag = '💎';
        } else {
            $typeTag = '📅';
        }
        $label = "{$typeTag} {$r['config_username']} | {$vol}";
        if (mb_strlen($label) > 64) {
            $label = mb_substr($label, 0, 61) . '…';
        }
        // حذف فقط داخل کارت سرویس (تلگرام عرض دکمه را کنترل نمی‌کند؛ ردیف دوتایی حذف را بزرگ نشان می‌دهد)
        $buttons[] = [
            ['text' => $label, 'callback_data' => 'adm_svc_open:' . $r['config_username']],
        ];
    }

    $nav = [];
    if ($page > 0) {
        $nav[] = ['text' => '◀️ قبلی', 'callback_data' => $baseCb($filter, $sort, $page - 1)];
    }
    if (($offset + $perPage) < $total) {
        $nav[] = ['text' => 'بعدی ▶️', 'callback_data' => $baseCb($filter, $sort, $page + 1)];
    }
    if (!empty($nav)) {
        $buttons[] = $nav;
    }
    $buttons[] = [
        ['text' => '🔙 سرویس‌ها', 'callback_data' => 'adm_services_hub', 'style' => 'danger'],
        ['text' => '👑 پنل', 'callback_data' => 'adm_back'],
    ];

    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $buttons], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_svc_open:') === 0 && isBotAdmin($user_id)) {
    $targetUsername = str_replace('adm_svc_open:', '', $callback_data);
    showAdminServiceCard($chat_id, $targetUsername, $db, $update['callback_query']['message']['message_id']);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_svc_del_ask:') === 0 && isBotAdmin($user_id)) {
    $targetUsername = str_replace('adm_svc_del_ask:', '', $callback_data);
    $txt = "⚠️ <b>حذف سرویس</b>\n\n"
         . "سرویس: <code>{$targetUsername}</code>\n\n"
         . "نوع حذف را انتخاب کن:\n\n"
         . "🔹 <b>فقط پنل</b> (پیشنهادی)\n"
         . "از پاسارگاد حذف می‌شود؛ ردیف در دیتابیس می‌ماند تا سابقه خرید/کاربر حفظ شود.\n\n"
         . "🔸 <b>پنل + دیتابیس</b>\n"
         . "کامل پاک می‌شود (قابل بازگشت نیست).";
    $kb = json_encode(['inline_keyboard' => [
        [['text' => '🔹 فقط از پنل (حفظ سابقه)', 'callback_data' => 'adm_svc_del_do:panel:' . $targetUsername, 'style' => 'primary']],
        [['text' => '🔸 پنل + دیتابیس (کامل)', 'callback_data' => 'adm_svc_del_do:full:' . $targetUsername, 'style' => 'danger']],
        [['text' => '❌ انصراف', 'callback_data' => 'adm_svc_open:' . $targetUsername]]
    ]], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

// adm_svc_del_do:panel:username  یا  adm_svc_del_do:full:username  (قدیمی: adm_svc_del_do:username = full)
if ($callback_data && strpos($callback_data, 'adm_svc_del_do:') === 0 && isBotAdmin($user_id)) {
    $rest = str_replace('adm_svc_del_do:', '', $callback_data);
    $mode = 'full';
    $targetUsername = $rest;
    if (preg_match('/^(panel|full):(.+)$/', $rest, $m)) {
        $mode = $m[1];
        $targetUsername = $m[2];
    }
    $panelRes = deletePasargadUser($targetUsername, panelFromUsername($targetUsername, $db));
    $dbDeleted = 0;
    $dbNote = 'حفظ شد (سابقه)';
    if ($mode === 'full') {
        try {
            $stmt = $db->prepare("DELETE FROM orders WHERE config_username = ?");
            $stmt->execute([$targetUsername]);
            $dbDeleted = $stmt->rowCount();
            $dbNote = ($dbDeleted >= 0 ? "{$dbDeleted} ردیف حذف شد" : 'خطا');
        } catch (Exception $e) {
            $dbDeleted = -1;
            $dbNote = 'خطا';
        }
    }

    $modeLabel = ($mode === 'panel') ? 'فقط پنل' : 'پنل + دیتابیس';
    if ($panelRes['ok']) {
        $msg = "✅ <b>حذف انجام شد</b> ({$modeLabel})\n\n"
             . "سرویس: <code>{$targetUsername}</code>\n"
             . "• پنل: {$panelRes['detail']} (HTTP {$panelRes['http']})\n"
             . "• دیتابیس orders: {$dbNote}";
        if ($mode === 'panel') {
            $msg .= "\n\nسابقه در ربات باقی است؛ از صفحه کاربر / سوابق قابل مشاهده است.";
        }
    } else {
        $msg = "⚠️ <b>حذف ناقص</b> ({$modeLabel})\n\n"
             . "• پنل: خطا — HTTP {$panelRes['http']}\n<code>" . htmlspecialchars($panelRes['detail']) . "</code>\n"
             . "• دیتابیس: {$dbNote}\n\n"
             . "اگر پنل در دسترس نبود، سرویس ممکن است هنوز روی سرور باشد.";
    }
    $kb = json_encode(['inline_keyboard' => [
        [['text' => '📦 لیست سرویس‌ها', 'callback_data' => 'adm_services_list:0']],
        [['text' => '👥 کاربران', 'callback_data' => 'adm_users_list:0']],
        [['text' => '👑 پنل اصلی', 'callback_data' => 'adm_back']]
    ]], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $msg,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_user_del_ask:') === 0 && isBotAdmin($user_id)) {
    $uid = (int)str_replace('adm_user_del_ask:', '', $callback_data);
    $st = $db->prepare("SELECT COUNT(*) FROM orders WHERE user_id = ?");
    $st->execute([$uid]);
    $cnt = (int)$st->fetchColumn();
    $txt = "⚠️ <b>حذف همه سرویس‌های کاربر</b>\n\n"
         . "User ID: <code>{$uid}</code>\n"
         . "تعداد سرویس: <b>{$cnt}</b>\n\n"
         . "نوع حذف را انتخاب کن:\n\n"
         . "🔹 <b>فقط پنل</b> — سابقه سفارش در ربات می‌ماند\n"
         . "🔸 <b>پنل + دیتابیس</b> — سفارش‌ها هم پاک می‌شوند\n\n"
         . "خود کاربر تلگرام در جدول users باقی می‌ماند.";
    $kb = json_encode(['inline_keyboard' => [
        [['text' => '🔹 فقط از پنل (حفظ سابقه)', 'callback_data' => 'adm_user_del_do:panel:' . $uid, 'style' => 'primary']],
        [['text' => '🔸 پنل + دیتابیس (کامل)', 'callback_data' => 'adm_user_del_do:full:' . $uid, 'style' => 'danger']],
        [['text' => '❌ انصراف', 'callback_data' => 'adm_user_view:' . $uid]]
    ]], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $txt,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_user_del_do:') === 0 && isBotAdmin($user_id)) {
    $rest = str_replace('adm_user_del_do:', '', $callback_data);
    $mode = 'full';
    $uid = 0;
    if (preg_match('/^(panel|full):(\d+)$/', $rest, $m)) {
        $mode = $m[1];
        $uid = (int)$m[2];
    } else {
        $uid = (int)$rest;
    }
    $st = $db->prepare("SELECT config_username, panel_id FROM orders WHERE user_id = ?");
    $st->execute([$uid]);
    $rowsDel = $st->fetchAll(PDO::FETCH_ASSOC);
    $ok = 0; $fail = 0; $details = [];
    foreach ($rowsDel as $rowDel) {
        $uname = (string)($rowDel['config_username'] ?? '');
        if ($uname === '') continue;
        $r = deletePasargadUser($uname, panelFromOrder($rowDel, $db));
        if ($r['ok']) $ok++; else { $fail++; $details[] = "{$uname}: {$r['detail']}"; }
    }
    $dbNote = 'سفارش‌ها حفظ شدند (سابقه)';
    if ($mode === 'full') {
        $db->prepare("DELETE FROM orders WHERE user_id = ?")->execute([$uid]);
        $dbNote = 'سفارش‌های دیتابیس پاک شدند';
    }
    $modeLabel = ($mode === 'panel') ? 'فقط پنل' : 'پنل + دیتابیس';
    $msg = "🗑 <b>نتیجه حذف</b> ({$modeLabel})\nکاربر: <code>{$uid}</code>\n\n"
         . "✅ حذف از پنل: {$ok}\n"
         . "❌ خطا در پنل: {$fail}\n"
         . "📦 {$dbNote}\n";
    if (!empty($details)) {
        $msg .= "\nجزئیات خطا:\n<code>" . htmlspecialchars(implode("\n", array_slice($details, 0, 5))) . "</code>";
    }
    $kb = json_encode(['inline_keyboard' => [
        [['text' => '👤 بازگشت به کاربر', 'callback_data' => 'adm_user_view:' . $uid]],
        [['text' => '👥 کاربران', 'callback_data' => 'adm_users_list:0']],
        [['text' => '👑 پنل اصلی', 'callback_data' => 'adm_back']]
    ]], JSON_UNESCAPED_UNICODE);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => $msg,
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}


// ===== شارژ دستی کیف پول توسط ادمین =====
if ($callback_data === 'adm_wallet_charge_start' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'adm_wallet_charge_uid' WHERE user_id = ?")->execute([$user_id]);
    $kb = json_encode(['inline_keyboard' => [[['text' => '❌ انصراف', 'callback_data' => 'adm_back', 'style' => 'danger']]]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "💰 <b>شارژ دستی کیف پول</b>\n\nشناسه عددی کاربر (User ID) را ارسال کنید:",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($callback_data && strpos($callback_data, 'adm_wallet_charge:') === 0 && isBotAdmin($user_id)) {
    $targetUid = (int)str_replace('adm_wallet_charge:', '', $callback_data);
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["adm_wallet_charge_amt:{$targetUid}", $user_id]);
    $st = $db->prepare("SELECT balance, username FROM users WHERE user_id = ?");
    $st->execute([$targetUid]);
    $tu = $st->fetch();
    $bal = $tu ? (int)$tu['balance'] : 0;
    $uname = $tu['username'] ?? '-';
    $kb = json_encode(['inline_keyboard' => [
        [['text' => '۵۰,۰۰۰', 'callback_data' => "adm_wallet_do:{$targetUid}:50000"], ['text' => '۱۰۰,۰۰۰', 'callback_data' => "adm_wallet_do:{$targetUid}:100000"]],
        [['text' => '۲۰۰,۰۰۰', 'callback_data' => "adm_wallet_do:{$targetUid}:200000"], ['text' => '۵۰۰,۰۰۰', 'callback_data' => "adm_wallet_do:{$targetUid}:500000"]],
        [['text' => '❌ انصراف', 'callback_data' => 'adm_user_view:' . $targetUid]]
    ]]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => "💰 <b>شارژ کیف پول</b>\n\n"
               . "کاربر: <code>{$targetUid}</code> (@{$uname})\n"
               . "موجودی فعلی: <b>" . number_format($bal) . " تومان</b>\n\n"
               . "مبلغ را از دکمه‌ها انتخاب کنید یا <b>مبلغ دلخواه به تومان</b> را تایپ کنید.\n"
               . "برای کاهش موجودی، مبلغ منفی بفرستید (مثال: <code>-50000</code>).",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($text !== null && $text !== '' && ($currentUser['step'] ?? '') === 'adm_wallet_charge_uid' && isBotAdmin($user_id)) {
    $targetUid = (int)preg_replace('/\D/', '', $text);
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if ($targetUid <= 0) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => '❌ شناسه نامعتبر است.',
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_back', 'style' => 'danger']]]])
        ]);
        exit();
    }
    $st = $db->prepare("SELECT user_id FROM users WHERE user_id = ?");
    $st->execute([$targetUid]);
    if (!$st->fetch()) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "❌ کاربری با شناسه <code>{$targetUid}</code> در ربات یافت نشد.",
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_back', 'style' => 'danger']]]])
        ]);
        exit();
    }
    $db->prepare("UPDATE users SET step = ? WHERE user_id = ?")->execute(["adm_wallet_charge_amt:{$targetUid}", $user_id]);
    $st = $db->prepare("SELECT balance, username FROM users WHERE user_id = ?");
    $st->execute([$targetUid]);
    $tu = $st->fetch();
    $bal = (int)$tu['balance'];
    $uname = $tu['username'] ?? '-';
    $kb = json_encode(['inline_keyboard' => [
        [['text' => '۵۰,۰۰۰', 'callback_data' => "adm_wallet_do:{$targetUid}:50000"], ['text' => '۱۰۰,۰۰۰', 'callback_data' => "adm_wallet_do:{$targetUid}:100000"]],
        [['text' => '۲۰۰,۰۰۰', 'callback_data' => "adm_wallet_do:{$targetUid}:200000"], ['text' => '۵۰۰,۰۰۰', 'callback_data' => "adm_wallet_do:{$targetUid}:500000"]],
        [['text' => '❌ انصراف', 'callback_data' => 'adm_back', 'style' => 'danger']]
    ]]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "💰 <b>شارژ کیف پول</b>\n\n"
               . "کاربر: <code>{$targetUid}</code> (@{$uname})\n"
               . "موجودی فعلی: <b>" . number_format($bal) . " تومان</b>\n\n"
               . "مبلغ را انتخاب کنید یا مبلغ دلخواه (تومان) را تایپ کنید.\n"
               . "برای کاهش: <code>-50000</code>",
        'parse_mode' => 'HTML',
        'reply_markup' => $kb
    ]);
    exit();
}

if ($text !== null && $text !== '' && strpos(($currentUser['step'] ?? ''), 'adm_wallet_charge_amt:') === 0 && isBotAdmin($user_id)) {
    $targetUid = (int)str_replace('adm_wallet_charge_amt:', '', $currentUser['step']);
    $rawAmt = str_replace([',', ' ', 'تومان', 'ت'], '', trim($text));
    if (!preg_match('/^-?\d+$/', $rawAmt)) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => '❌ فقط عدد وارد کنید (مثال: 100000 یا -50000).',
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_back', 'style' => 'danger']]]])
        ]);
        exit();
    }
    $amount = (int)$rawAmt;
    if ($amount == 0) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => '❌ مبلغ نمی‌تواند صفر باشد.',
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 بازگشت', 'callback_data' => 'adm_back', 'style' => 'danger']]]])
        ]);
        exit();
    }
    $callback_data = "adm_wallet_do:{$targetUid}:{$amount}";
    $update['callback_query']['message']['message_id'] = null;
}

if ($callback_data && strpos($callback_data, 'adm_wallet_do:') === 0 && isBotAdmin($user_id)) {
    $parts = explode(':', $callback_data);
    $targetUid = isset($parts[1]) ? (int)$parts[1] : 0;
    $amount = isset($parts[2]) ? (int)$parts[2] : 0;
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);

    if ($targetUid <= 0 || $amount == 0) {
        if (!empty($update['callback_query']['id'])) {
            sendTelegram('answerCallbackQuery', [
                'callback_query_id' => $update['callback_query']['id'],
                'text' => 'مقادیر نامعتبر',
                'show_alert' => true
            ]);
        }
        exit();
    }

    $st = $db->prepare("SELECT balance, username FROM users WHERE user_id = ?");
    $st->execute([$targetUid]);
    $tu = $st->fetch();
    if (!$tu) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ کاربر یافت نشد.']);
        exit();
    }

    $oldBal = (int)$tu['balance'];
    $delta = (int)$amount;
    if ($delta < 0 && ($oldBal + $delta) < 0) {
        $delta = -$oldBal; // حداکثر تا صفر
    }
    $type = $delta >= 0 ? 'admin_deposit' : 'admin_deduct';
    $adj = adjustWalletBalance($db, $targetUid, $delta, $type, 'admin', (string)$user_id, 'شارژ/کسر دستی ادمین');
    if (empty($adj['ok'])) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => '❌ به‌روزرسانی موجودی ناموفق بود.']);
        exit();
    }
    $newBal = (int)$adj['balance'];

    try {
        $db->prepare("INSERT INTO payments (user_id, plan_key, price, photo_file_id, target_username, action_type, coupon_code, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'approved')")
           ->execute([$targetUid, 'admin_credit', abs($delta), 'ADMIN_CREDIT', null, $type, null]);
    } catch (Exception $e) {}

    $signTxt = $amount >= 0 ? ('+' . number_format($amount)) : number_format($amount);
    $adminMsg = "✅ <b>موجودی به‌روز شد</b>\n\n"
              . "کاربر: <code>{$targetUid}</code>\n"
              . "تغییر: <b>{$signTxt} تومان</b>\n"
              . "قبل: " . number_format($oldBal) . " ← بعد: <b>" . number_format($newBal) . " تومان</b>";

    $userMsg = $amount >= 0
        ? ("💰 <b>کیف پول شما توسط مدیریت شارژ شد</b>\n\n"
           . "مبلغ: <b>" . number_format($amount) . " تومان</b>\n"
           . "موجودی جدید: <b>" . number_format($newBal) . " تومان</b>")
        : ("📉 <b>تعدیل موجودی کیف پول</b>\n\n"
           . "مبلغ کسر شده: <b>" . number_format(abs($amount)) . " تومان</b>\n"
           . "موجودی جدید: <b>" . number_format($newBal) . " تومان</b>");

    $kbDone = json_encode(['inline_keyboard' => [
        [['text' => '👤 مشاهده کاربر', 'callback_data' => 'adm_user_view:' . $targetUid]],
        [['text' => '💰 شارژ مجدد', 'callback_data' => 'adm_wallet_charge:' . $targetUid]],
        [['text' => '👑 پنل', 'callback_data' => 'adm_back']]
    ]]);

    if (!empty($update['callback_query']['message']['message_id'])) {
        sendTelegram('editMessageText', [
            'chat_id' => $chat_id,
            'message_id' => $update['callback_query']['message']['message_id'],
            'text' => $adminMsg,
            'parse_mode' => 'HTML',
            'reply_markup' => $kbDone
        ]);
    } else {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => $adminMsg,
            'parse_mode' => 'HTML',
            'reply_markup' => $kbDone
        ]);
    }

    try {
        sendTelegram('sendMessage', [
            'chat_id' => $targetUid,
            'text' => $userMsg,
            'parse_mode' => 'HTML'
        ]);
    } catch (Exception $e) {}

    exit();
}

if ($callback_data === 'adm_back' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('editMessageText', [
        'chat_id' => $chat_id,
        'message_id' => $update['callback_query']['message']['message_id'],
        'text' => getAdminDashboard($db),
        'parse_mode' => 'HTML',
        'reply_markup' => getAdminKeyboard()
    ]);
    exit();
}

if ($callback_data && (strpos($callback_data, 'adm_app_') === 0 || strpos($callback_data, 'adm_rej_') === 0)) {
    if (isBotAdmin($user_id)) {
        $isApprove = strpos($callback_data, 'adm_app_') === 0;
        $paymentId = (int)str_replace(['adm_app_', 'adm_rej_'], '', $callback_data);
        $stmt = $db->prepare("SELECT * FROM payments WHERE id = ?");
        $stmt->execute([$paymentId]);
        $pay = $stmt->fetch();

        // فیش بازیابی‌شده / عکس روی فاکتور منقضی: اگر عکس واقعی دارد، برای تأیید دستی pending کن
        if ($pay && in_array((string)$pay['status'], ['expired', 'cancelled', 'rejected'], true)) {
            $fid0 = (string)($pay['photo_file_id'] ?? '');
            $hasReal = ($fid0 !== '' && !in_array($fid0, ['AWAITING_RECEIPT', 'WALLET_PAY', 'SMS_AUTO', 'ADMIN_CREDIT', 'ADMIN_DEBIT'], true));
            $recent = false;
            try {
                $recent = strtotime((string)($pay['created_at'] ?? '')) >= (time() - 86400);
            } catch (Exception $e) {
                $recent = true;
            }
            if ($hasReal && $recent) {
                try {
                    $db->prepare("UPDATE payments SET status = 'pending', expires_at = DATE_ADD(NOW(), INTERVAL 1 DAY) WHERE id = ?")
                       ->execute([$paymentId]);
                    $pay['status'] = 'pending';
                } catch (Exception $e) {
                    try {
                        $db->prepare("UPDATE payments SET status = 'pending' WHERE id = ?")->execute([$paymentId]);
                        $pay['status'] = 'pending';
                    } catch (Exception $e2) {
                    }
                }
            }
        }

        if ($pay && $pay['status'] === 'pending') {
            if ($isApprove) {
                if ($pay['action_type'] === 'reseller_deposit' || strtolower((string)($pay['target_username'] ?? '')) === 'reseller_wallet') {
                    $creditAmount = (is_numeric($pay['plan_key']) && (int)$pay['plan_key'] > 0)
                        ? (int)$pay['plan_key']
                        : (int)$pay['price'];
                    if (!function_exists('reseller_credit_from_payment')) {
                        sendTelegram('sendMessage', [
                            'chat_id' => $pay['user_id'],
                            'text' => 'موتور شارژ نمایندگی در دسترس نیست. با پشتیبانی تماس بگیرید.',
                        ]);
                    } else {
                        $rc = reseller_credit_from_payment($db, $pay);
                        if (empty($rc['ok'])) {
                            sendTelegram('sendMessage', [
                                'chat_id' => $pay['user_id'],
                                'text' => '⚠️ پرداخت هنوز نهایی نشد. شارژ اعتبار نمایندگی ناموفق بود؛ دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.',
                            ]);
                            postOrderToLogChannel("خطای شارژ اعتبار نمایندگی", "reseller_deposit_fail");
                        } else {
                            $db->prepare("UPDATE payments SET status = 'approved' WHERE id = ? AND status = 'pending'")->execute([$paymentId]);
                            $pay['status'] = 'approved';
                            sendTelegram('sendMessage', [
                                'chat_id' => $pay['user_id'],
                                'text' => "✅ اعتبار نمایندگی شارژ شد 💰

مبلغ: <b>" . number_format($creditAmount) . " تومان</b>
موجودی اعتبار: <b>" . number_format((int)($rc['balance'] ?? 0)) . " تومان</b>",
                                'parse_mode' => 'HTML',
                                'reply_markup' => json_encode(['inline_keyboard' => [
                                    [['text' => '🛒 ادامه فروش اشتراک', 'callback_data' => 'rs_sell_start', 'style' => 'success']],
                                    [['text' => '📋 گردش اعتبار', 'callback_data' => 'rs_ledger']],
                                    [['text' => '🔙 پنل نمایندگی', 'callback_data' => 'rs_panel']],
                                ]], JSON_UNESCAPED_UNICODE),
                            ]);
                            postOrderToLogChannel("شارژ اعتبار نمایندگی", "reseller_deposit");
                        }
                    }
                } elseif ($pay['action_type'] === 'deposit') {
                    // plan_key = مبلغ درخواستی اصلی، price = مبلغ یکتا برای تطبیق SMS
                    $creditAmount = (is_numeric($pay['plan_key']) && (int)$pay['plan_key'] > 0)
                        ? (int)$pay['plan_key']
                        : (int)$pay['price'];
                    $db->prepare("UPDATE payments SET status = 'approved' WHERE id = ?")->execute([$paymentId]);
                    adjustWalletBalance($db, $pay['user_id'], $creditAmount, 'deposit_card', 'payment', (string)$paymentId, 'شارژ با تایید ادمین');
                    $pay['status'] = 'approved';
                    recordAccountingFromPayment($db, $pay, 'admin');
                    sendTelegram('sendMessage', [
                        'chat_id' => $pay['user_id'],
                        'text' => "✅ کیف پولت شارژ شد 💰\n\nمبلغ: <b>" . number_format($creditAmount) . " تومان</b>\nحالا می‌تونی خرید آنی بزنی ⚡️",
                        'parse_mode' => 'HTML'
                    ]);
                    postOrderToLogChannel("شارژ کیف پول", "deposit");
                } else {
                    $p = $plans[$pay['plan_key']];
                    $targetUser = $pay['target_username'];
                    if (!empty($pay['coupon_code'])) $db->prepare("UPDATE coupons SET used_count = used_count + 1 WHERE code = ?")->execute([$pay['coupon_code']]);

                    if ($pay['action_type'] === 'renew') {
                        $volRenew = inviteeVolumeWithBonus($db, (int)$pay['user_id'], $p['vol']);
                        if (!isset($orderPanel) || !is_array($orderPanel)) {
                            try {
                                $stOp = $db->prepare('SELECT * FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 1');
                                $stOp->execute([$targetUser]);
                                $ordRow = $stOp->fetch(PDO::FETCH_ASSOC);
                                $orderPanel = panelFromOrder($ordRow ?: [], $db);
                            } catch (Exception $e) {
                                $orderPanel = isset($panel) ? $panel : getPanelById(panelIdFromPlan($p));
                            }
                        }
                        $ren = renewPasargadUser($targetUser, $volRenew, $p['days'], $orderPanel);
                        $newVol = jet_sync_order_after_renew($db, $targetUser, $ren, (int)$p['days'], (float)$volRenew, (float)$volRenew);
                        sendTelegram('sendMessage', [
                            'chat_id' => $pay['user_id'],
                            'text' => "✅ <b>تمدید انجام شد!</b>\n\n"
                                   . "سرویس: <code>{$targetUser}</code>\n"
                                   . "حجم کل: {$newVol} گیگ\n\n"
                                   . "تو اپ یک‌بار <b>Update Sub / Refresh</b> بزن تا تغییرات اعمال بشه 🚀",
                            'parse_mode' => 'HTML'
                        ]);
                    } else {
                        $existOrd = $db->prepare("SELECT * FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 1");
                        $existOrd->execute([$targetUser]);
                        $existRow = $existOrd->fetch(PDO::FETCH_ASSOC);

                        $isTestOrd = false;
                        if ($existRow) {
                            $exPk = strtolower(trim((string)($existRow['plan_key'] ?? '')));
                            $exCn = strtolower(trim((string)($existRow['config_username'] ?? '')));
                            $isTestOrd = ($exPk === 'test_free' || strpos($exPk, 'test') !== false || strpos($exCn, 'test_') === 0
                                || ((float)($existRow['volume_gb'] ?? 0) > 0 && (float)($existRow['volume_gb'] ?? 0) <= 0.2 && (int)($existRow['days'] ?? 0) <= 3));
                        }

                        if ($existRow && !$isTestOrd) {
                            $subUrl = (string)($existRow['sub_link'] ?? '');
                            $orderPassword = (string)($existRow['password'] ?? '');
                            $dupMsg = "✅ این سرویس از قبل فعاله؛ فیش تکراری بسته شد.\n\n"
                                    . "👤 نام کاربری: <code>{$targetUser}</code>\n";
                            if ($orderPassword !== '') {
                                $dupMsg .= "🔑 رمز اپ: <code>{$orderPassword}</code>\n";
                            }
                            if ($subUrl !== '') {
                                $dupMsg .= "🔗 لینک:\n<code>{$subUrl}</code>";
                            }
                            sendTelegram('sendMessage', [
                                'chat_id' => $pay['user_id'],
                                'text' => $dupMsg,
                                'parse_mode' => 'HTML'
                            ]);
                        } elseif ($existRow && $isTestOrd) {
                            // ارتقای تست رایگان به پلن خریداری‌شده
                            $volCreate = inviteeVolumeWithBonus($db, (int)$pay['user_id'], $p['vol']);
                            $panelForCreate = (isset($panel) ? $panel : getPanelById(panelIdFromPlan($p)));
                            try {
                                if (function_exists('deletePasargadUser')) {
                                    deletePasargadUser($targetUser, $panelForCreate);
                                }
                            } catch (Exception $e) {}
                            $res = createPasargadUserUnique($targetUser, $volCreate, $p['days'], $panelForCreate, (int)$pay['user_id']);
                            if (!empty($res['_error'])) {
                                sendTelegram('sendMessage', [
                                    'chat_id' => $chat_id,
                                    'text' => "⚠️ فیش تأیید شد ولی ارتقای تست به پلن واقعی ناموفق بود.\nکاربر: <code>{$targetUser}</code>\nخطا: <code>" . htmlspecialchars((string)($res['detail'] ?? $res['_error'])) . "</code>",
                                    'parse_mode' => 'HTML'
                                ]);
                                exit();
                            }
                            $targetUser = (string)($res['_final_username'] ?? $targetUser);
                            try { $db->prepare('UPDATE payments SET target_username = ? WHERE id = ?')->execute([$targetUser, $paymentId]); } catch (Exception $e) {}
                            $subUrl = $res['subscription_url'] ?? '';
                            if (strpos($subUrl, 'http') !== 0) {
                                $subUrl = normalizeSubscriptionUrl($subUrl, isset($panelForCreate) ? $panelForCreate : (isset($panel) ? $panel : null));
                            }
                            $orderPassword = (string)($existRow['password'] ?? '');
                            if ($orderPassword === '') { $orderPassword = (string)rand(1000, 9999); }
                            $panelRow = isset($panel) ? $panel : getPanelById(panelIdFromPlan($p));
                            $pCat = strtolower(trim((string)($p['cat'] ?? '')));
                            if ($pCat === '') { $pCat = ((int)($p['days'] ?? 0) === 0) ? 'vip' : 'monthly'; }
                            try {
                                $db->prepare('UPDATE orders SET volume_gb = ?, days = ?, sub_link = ?, panel_id = ?, plan_key = ?, cat = ?, warned_volume = 0, warned_expire = 0 WHERE id = ?')
                                   ->execute([$volCreate, (int)$p['days'], $subUrl, (int)($panelRow['id'] ?? 0), (string)($pay['plan_key'] ?? ''), $pCat, (int)$existRow['id']]);
                            } catch (Exception $e) {
                                try {
                                    $db->prepare('UPDATE orders SET volume_gb = ?, days = ?, sub_link = ? WHERE id = ?')
                                       ->execute([$volCreate, (int)$p['days'], $subUrl, (int)$existRow['id']]);
                                } catch (Exception $e2) {}
                            }
                            try { $db->prepare('UPDATE users SET has_bought = 1 WHERE user_id = ?')->execute([(int)$pay['user_id']]); } catch (Exception $e) {}
                            $planTitleAp = trim((string)($p['title'] ?? $pay['plan_key'] ?? 'اشتراک'));
                            $volShowAp = ((float)$volCreate > 0)
                                ? (rtrim(rtrim(number_format((float)$volCreate, 2, '.', ''), '0'), '.') . ' گیگ')
                                : 'نامحدود';
                            $daysShowAp = ((int)($p['days'] ?? 0) > 0) ? ((int)$p['days'] . ' روز') : 'بدون انقضا';
                            $approveMsg = "✅ <b>پرداختت تایید شد و اشتراکت فعال شد</b>\n\n"
                                        . "📋 پلن: <b>{$planTitleAp}</b>\n"
                                        . "👤 نام کاربری: <code>{$targetUser}</code>\n"
                                        . "🔑 رمز اپ: <code>{$orderPassword}</code>\n"
                                        . "📦 حجم: <b>{$volShowAp}</b>\n"
                                        . "⏰ مدت: <b>{$daysShowAp}</b>\n\n"
                                        . "تو اپ یک‌بار بروزرسانی سابسکریپشن بزن 🚀";
                            sendTelegram('sendMessage', [
                                'chat_id' => $pay['user_id'],
                                'text' => $approveMsg,
                                'parse_mode' => 'HTML'
                            ]);
                        } else {
                            $volCreate = inviteeVolumeWithBonus($db, (int)$pay['user_id'], $p['vol']);
                            $panelForCreate = (isset($panel) ? $panel : getPanelById(panelIdFromPlan($p)));
                            $res = createPasargadUserUnique($targetUser, $volCreate, $p['days'], $panelForCreate, (int)$pay['user_id']);
                            if (!empty($res['_error'])) {
                                sendTelegram('sendMessage', [
                                    'chat_id' => $chat_id,
                                    'text' => "⚠️ فیش تأیید شد ولی ساخت پنل ناموفق بود.\nکاربر: <code>{$targetUser}</code>\nخطا: <code>" . htmlspecialchars((string)($res['detail'] ?? $res['_error'])) . "</code>\nفیش pending ماند؛ بعد از رفع مشکل دوباره تأیید کن یا دستی بساز.",
                                    'parse_mode' => 'HTML'
                                ]);
                                exit();
                            }
                            $targetUser = (string)($res['_final_username'] ?? $targetUser);
                            try {
                                $db->prepare('UPDATE payments SET target_username = ? WHERE id = ?')->execute([$targetUser, $paymentId]);
                            } catch (Exception $e) {
                            }
                            $subUrl = $res['subscription_url'] ?? '';
                            if (strpos($subUrl, 'http') !== 0) {
                                $subUrl = normalizeSubscriptionUrl($subUrl, isset($panelForCreate) ? $panelForCreate : (isset($panel) ? $panel : null));
                            }

                                                        $orderPassword = (string)rand(1000, 9999);
                            try {
                                if ((int)$pay['user_id'] >= 700000000000) {
                                    $rowsA = $db->query('SELECT config_username, password FROM app_accounts')->fetchAll(PDO::FETCH_ASSOC) ?: [];
                                    foreach ($rowsA as $ar) {
                                        $su = 700000000000 + (abs(crc32(strtolower((string)$ar['config_username']))) % 999999999);
                                        if ($su === (int)$pay['user_id'] && !empty($ar['password'])) {
                                            $orderPassword = (string)$ar['password'];
                                            break;
                                        }
                                    }
                                }
                            } catch (Exception $e) {}
                            $panelRow = isset($panel) ? $panel : getPanelById(panelIdFromPlan($p));
                            $pCat = strtolower(trim((string)($p['cat'] ?? '')));
                            if ($pCat === '') { $pCat = ((int)($p['days'] ?? 0) === 0) ? 'vip' : 'monthly'; }
                            insertBotOrder($db, (int)$pay['user_id'], $targetUser, $orderPassword, $subUrl, $volCreate, (int)$p['days'], (int)($panelRow['id'] ?? 0), $pCat, (string)($pay['plan_key'] ?? $planKey ?? ''));


                            $qrUrl = getQRCodeUrl($subUrl);

                            $dlApp = defined('DIRECT_DOWNLOAD_URL') ? DIRECT_DOWNLOAD_URL : 'https://github.com/majidbusy09-blip/jetconfig-vpn/releases';
                            $bonusLine = ($volCreate > (float)$p['vol']) ? "\n🎁 هدیه دعوت: حجم {$volCreate} گیگ (+۵٪)\n" : "\n";
                            $planTitleAp = trim((string)($p['title'] ?? $planKey ?? 'اشتراک'));
                            $volShowAp = ((float)$volCreate > 0)
                                ? (rtrim(rtrim(number_format((float)$volCreate, 2, '.', ''), '0'), '.') . ' گیگ')
                                : 'نامحدود';
                            $daysShowAp = ((int)($p['days'] ?? 0) > 0) ? ((int)$p['days'] . ' روز') : 'بدون انقضا';
                            $holdAp = ((int)($p['days'] ?? 0) > 0) ? "⏱ شروع اعتبار: از <b>اولین اتصال</b>\n" : '';
                            $approveMsg = "✅ <b>پرداختت به صورت خودکار تایید شد و اشتراکت فعال شد</b>\n\n"
                                        . "📋 پلن: <b>{$planTitleAp}</b>\n"
                                        . "👤 نام کاربری: <code>{$targetUser}</code>\n"
                                        . "🔑 رمز اپ: <code>{$orderPassword}</code>{$bonusLine}"
                                        . "📦 حجم: <b>{$volShowAp}</b>\n"
                                        . "⏰ مدت: <b>{$daysShowAp}</b>\n"
                                        . $holdAp
                                        . "\n━━━━━━━━━━━━━━\n"
                                        . "📱 اپ <a href=\"{$dlApp}\">JET VPN</a>\n"
                                        . "۱) دانلود کن  ۲) با یوزر و رمز وارد شو  ۳) وصل شو\n\n"
                                        . "🔗 <b>لینک ساب</b>\n"
                                        . "<code>{$subUrl}</code>\n\n"
                                        . "📲 <b>سایر برنامه‌ها</b> — لینک ساب را کپی کن یا QR را اسکن کن:\n"
                                        . "• اندروید: <a href=\"https://majid6064.ir/download/\">v2rayNG</a> · <a href=\"https://majid6064.ir/download/\">Happ</a>\n"
                                        . "• آیفون: <a href=\"https://apps.apple.com/app/streisand/id6450534064\">Streisand</a> · <a href=\"https://apps.apple.com/app/happ-proxy-utility/id6504287215\">Happ</a>\n"
                                        . "• ویندوز: <a href=\"https://github.com/2dust/v2rayN/releases\">v2rayN</a> · <a href=\"https://github.com/Happ-proxy/happ-desktop/releases\">Happ</a>\n\n"
                                        . "💬 پشتیبانی ربات همیشه در دسترسه.";

                            $daysLabelAp = ((int)($p['days'] ?? 0) > 0)
                                ? (((int)$p['days']) . ' روز')
                                : 'بدون انقضا';
                            $kbAp = array_merge(
                                serviceInfoChipRow(
                                    remainingTimeChipLabel($daysLabelAp),
                                    remainingVolumeChipLabel((float)$volCreate, 0)
                                ),
                                [[['text' => '📂 سرویس‌های من', 'callback_data' => 'my_services_list']]]
                            );
                            sendTelegram('sendPhoto', [
                                'chat_id' => $pay['user_id'],
                                'photo' => $qrUrl,
                                'caption' => $approveMsg,
                                'parse_mode' => 'HTML',
                                'reply_markup' => json_encode(['inline_keyboard' => $kbAp], JSON_UNESCAPED_UNICODE),
                            ]);
                        }
                    }
                    $buyerName = '';
                    try {
                        $stn = $db->prepare('SELECT username FROM users WHERE user_id = ? LIMIT 1');
                        $stn->execute([(int)$pay['user_id']]);
                        $buyerName = (string)($stn->fetchColumn() ?: '');
                    } catch (Exception $e) {}
                    checkAndRewardReferral((int)$pay['user_id'], $db, $buyerName !== '' ? $buyerName : (string)$username, (int)$pay['price']);
                    sendReferralInviteNudge($db, (int)$pay['user_id']);
                    postOrderToLogChannel($p['title'], $pay['action_type']);
                }
                $db->prepare("UPDATE payments SET status = 'approved' WHERE id = ?")->execute([$paymentId]);
                $pay['status'] = 'approved';
                if ($pay['action_type'] !== 'deposit') {
                    recordAccountingFromPayment($db, $pay, 'admin');
                }
                $__mid = $update['callback_query']['message']['message_id'] ?? null;
                if (!empty($update['callback_query']['message']['photo'])) {
                    sendTelegram('editMessageCaption', ['chat_id' => $chat_id, 'message_id' => $__mid, 'caption' => ($update['callback_query']['message']['caption'] ?? '') . "\n\n✅ تایید شد.", 'parse_mode' => 'HTML']);
                } elseif ($__mid) {
                    sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $__mid, 'text' => ($update['callback_query']['message']['text'] ?? 'فیش') . "\n\n✅ تایید شد.", 'parse_mode' => 'HTML']);
                }
                if (function_exists('clearAdminBroadcastMessages')) {
                    clearAdminBroadcastMessages($db, 'payment', $paymentId, $user_id, "🔔 فیش #{$paymentId}\n\n✅ توسط ادمین <code>{$user_id}</code> تایید شد.");
                }
            } else {
                $db->prepare("UPDATE payments SET status = 'rejected' WHERE id = ?")->execute([$paymentId]);
                sendTelegram('sendMessage', [
                    'chat_id' => $pay['user_id'],
                    'text' => "❌ فیش تایید نشد.\n\n"
                           . "مبلغ رو دوباره با همون عدد فاکتور چک کن و فیش جدید بفرست، یا از <b>پشتیبانی</b> بپرس 💬",
                    'parse_mode' => 'HTML'
                ]);
                $__mid = $update['callback_query']['message']['message_id'] ?? null;
                if (!empty($update['callback_query']['message']['photo'])) {
                    sendTelegram('editMessageCaption', ['chat_id' => $chat_id, 'message_id' => $__mid, 'caption' => ($update['callback_query']['message']['caption'] ?? '') . "\n\n❌ رد شد.", 'parse_mode' => 'HTML']);
                } elseif ($__mid) {
                    sendTelegram('editMessageText', ['chat_id' => $chat_id, 'message_id' => $__mid, 'text' => ($update['callback_query']['message']['text'] ?? 'فیش') . "\n\n❌ رد شد.", 'parse_mode' => 'HTML']);
                }
                if (function_exists('clearAdminBroadcastMessages')) {
                    clearAdminBroadcastMessages($db, 'payment', $paymentId, $user_id, "🔔 فیش #{$paymentId}\n\n❌ توسط ادمین <code>{$user_id}</code> رد شد.");
                }
            }
        } else {
            $stLabel = $pay ? (string)$pay['status'] : 'not_found';
            if ($pay && function_exists('clearAdminBroadcastMessages')) {
                clearAdminBroadcastMessages($db, 'payment', $paymentId, $user_id, "🔔 فیش #{$paymentId}\n\n⚠️ قابل تأیید نبود (وضعیت: {$stLabel}).");
            }
            if (!empty($update['callback_query']['id'])) {
                $hint = 'این فیش قابل تأیید نیست';
                if ($stLabel === 'approved') {
                    $hint = 'این فیش قبلاً تأیید شده';
                } elseif ($stLabel === 'rejected' || $stLabel === 'cancelled') {
                    $hint = 'این فیش رد/لغو شده — از مشتری فیش جدید بخواه';
                } elseif ($stLabel === 'expired') {
                    $hint = 'فاکتور منقضی است — مشتری «پرداخت کرده‌ام» بزند یا فیش را دوباره بفرستد';
                } elseif ($stLabel === 'not_found') {
                    $hint = 'فیش در دیتابیس پیدا نشد';
                }
                sendTelegram('answerCallbackQuery', [
                    'callback_query_id' => $update['callback_query']['id'],
                    'text' => $hint . " (#{$paymentId})",
                    'show_alert' => true,
                ]);
            }
        }
    }
    exit();
}

if ($text && strpos($currentUser['step'], 'ask_coupon:') === 0) {
    $parts = explode(':', str_replace('ask_coupon:', '', $currentUser['step']));
    $cp = strtoupper(trim($text));
    $stmt = $db->prepare("SELECT * FROM coupons WHERE code = ?");
    $stmt->execute([$cp]);
    $cData = $stmt->fetch();
    $okCoupon = false;
    if ($cData && (int)$cData['used_count'] < (int)$cData['max_uses']) {
        $okCoupon = true;
        // انقضای اختیاری (ستون expires_at)
        if (!empty($cData['expires_at'])) {
            $expTs = strtotime((string)$cData['expires_at']);
            if ($expTs && $expTs < time()) {
                $okCoupon = false;
            }
        }
    }
    if ($okCoupon) {
        issueInvoice($chat_id, $user_id, $parts[1], $parts[2], $parts[0], $plans, $db, null, $cData);
    } else {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "❌ کد تخفیف نامعتبر یا منقضی است."]);
    }
    exit();
}

// پایان گفتگو با دستیار

// ===== لاگ پشتیبانی AI برای ادمین =====
if ($callback_data !== null && strpos($callback_data, 'adm_ai_support:') === 0 && isBotAdmin($user_id)) {
    $offset = (int)str_replace('adm_ai_support:', '', $callback_data);
    if (function_exists('ensureSupportAiTable')) ensureSupportAiTable($db);
    $sessions = function_exists('listSupportAiSessions') ? listSupportAiSessions($db, $offset, 8) : [];
    if (!$sessions) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "🤖 هنوز گفتگویی در لاگ پشتیبانی AI نیست.",
            'reply_markup' => getAdminKeyboard()
        ]);
        exit();
    }
    $lines = ["🤖 <b>آخرین گفتگوهای پشتیبانی AI</b>\n"];
    $rows = [];
    foreach ($sessions as $s) {
        $uid = (int)$s['user_id'];
        $lines[] = "👤 <code>{$uid}</code> | پیام‌ها: {$s['msg_count']} | {$s['last_at']}";
        $rows[] = [['text' => "💬 کاربر {$uid}", 'callback_data' => "adm_ai_thread:{$uid}"]];
    }
    $nav = [];
    if ($offset > 0) $nav[] = ['text' => '◀️ قبلی', 'callback_data' => 'adm_ai_support:' . max(0, $offset - 8)];
    $nav[] = ['text' => '▶️ بعدی', 'callback_data' => 'adm_ai_support:' . ($offset + 8)];
    $rows[] = $nav;
    $rows[] = [['text' => '🔙 پنل ادمین', 'callback_data' => 'adm_back', 'style' => 'danger']];
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => implode("\n", $lines),
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data !== null && strpos($callback_data, 'adm_ai_thread:') === 0 && isBotAdmin($user_id)) {
    $uid = (int)str_replace('adm_ai_thread:', '', $callback_data);
    $thread = function_exists('getSupportAiThread') ? getSupportAiThread($db, $uid, 24) : [];
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    if (!$thread) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "گفتگویی برای این کاربر نیست."]);
        exit();
    }
    $chunks = [];
    $buf = "🤖 گفتگوی AI با کاربر <code>{$uid}</code>\n\n";
    foreach ($thread as $m) {
        $who = $m['role'] === 'user' ? '👤 کاربر' : ($m['role'] === 'ai' ? '🤖 AI' : $m['role']);
        $line = "<b>{$who}</b> <i>{$m['created_at']}</i>\n" . htmlspecialchars(mb_substr($m['message'], 0, 800)) . "\n\n";
        if (mb_strlen($buf . $line) > 3500) {
            $chunks[] = $buf;
            $buf = $line;
        } else {
            $buf .= $line;
        }
    }
    $chunks[] = $buf;
    $kb = json_encode(['inline_keyboard' => [
        [['text' => '✍️ پاسخ انسانی', 'callback_data' => "adm_rep:{$uid}"]],
        [['text' => '🔙 لیست AI', 'callback_data' => 'adm_ai_support:0', 'style' => 'danger']]
    ]], JSON_UNESCAPED_UNICODE);
    foreach ($chunks as $i => $c) {
        $payload = ['chat_id' => $chat_id, 'text' => $c, 'parse_mode' => 'HTML'];
        if ($i === count($chunks) - 1) $payload['reply_markup'] = $kb;
        sendTelegram('sendMessage', $payload);
    }
    exit();
}

// ===== لاگ پشتیبانی انسانی برای ادمین =====
if ($callback_data !== null && strpos($callback_data, 'adm_human_support:') === 0 && isBotAdmin($user_id)) {
    $offset = (int)str_replace('adm_human_support:', '', $callback_data);
    if (function_exists('ensureSupportHumanTable')) ensureSupportHumanTable($db);
    $sessions = function_exists('listSupportHumanSessions') ? listSupportHumanSessions($db, $offset, 8) : [];
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    if (!$sessions) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "👨‍💼 هنوز گفتگوی پشتیبانی انسانی ثبت نشده.\nوقتی کاربر از «پشتیبانی انسانی» پیام بفرستد یا شما پاسخ دهید، اینجا می‌آید.",
            'reply_markup' => json_encode(['inline_keyboard' => [
                [['text' => '🔙 سیستم', 'callback_data' => 'adm_system_menu', 'style' => 'danger']],
                [['text' => '👑 پنل', 'callback_data' => 'adm_back']],
            ]], JSON_UNESCAPED_UNICODE)
        ]);
        exit();
    }
    $lines = ["👨‍💼 <b>لاگ پشتیبانی انسانی</b>\nکاربر را انتخاب کنید:\n"];
    $rows = [];
    foreach ($sessions as $s) {
        $uid = (int)$s['user_id'];
        $un = !empty($s['username']) ? ('@' . ltrim($s['username'], '@')) : '—';
        $last = $s['last_at'] ?? '';
        if ($last && function_exists('formatJalaliDateTime')) {
            $last = formatJalaliDateTime($last);
        }
        $lines[] = "👤 <code>{$uid}</code> {$un}\n   💬 {$s['msg_count']} پیام | {$last}";
        $rows[] = [['text' => "💬 {$uid} {$un}", 'callback_data' => "adm_human_thread:{$uid}"]];
    }
    $nav = [];
    if ($offset > 0) $nav[] = ['text' => '◀️ قبلی', 'callback_data' => 'adm_human_support:' . max(0, $offset - 8)];
    $nav[] = ['text' => '▶️ بعدی', 'callback_data' => 'adm_human_support:' . ($offset + 8)];
    $rows[] = $nav;
    $rows[] = [['text' => '🔙 سیستم', 'callback_data' => 'adm_system_menu', 'style' => 'danger'], ['text' => '👑 پنل', 'callback_data' => 'adm_back']];
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => implode("\n", $lines),
        'parse_mode' => 'HTML',
        'reply_markup' => json_encode(['inline_keyboard' => $rows], JSON_UNESCAPED_UNICODE)
    ]);
    exit();
}

if ($callback_data !== null && strpos($callback_data, 'adm_human_thread:') === 0 && isBotAdmin($user_id)) {
    $uid = (int)str_replace('adm_human_thread:', '', $callback_data);
    $thread = function_exists('getSupportHumanThread') ? getSupportHumanThread($db, $uid, 40) : [];
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    $uname = '';
    try {
        $st = $db->prepare("SELECT username FROM users WHERE user_id = ? LIMIT 1");
        $st->execute([$uid]);
        $u = $st->fetchColumn();
        if ($u) $uname = ' @' . ltrim((string)$u, '@');
    } catch (Exception $e) {}
    if (!$thread) {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "گفتگویی برای این کاربر نیست.",
            'reply_markup' => json_encode(['inline_keyboard' => [[['text' => '🔙 لیست', 'callback_data' => 'adm_human_support:0', 'style' => 'danger']]]])
        ]);
        exit();
    }
    $chunks = [];
    $buf = "👨‍💼 گفتگوی انسانی با <code>{$uid}</code>{$uname}\n\n";
    $photos = [];
    $photoIdx = 0;
    foreach ($thread as $m) {
        $role = $m['role'] ?? '';
        if ($role === 'user') {
            $who = '👤 کاربر';
        } elseif ($role === 'admin') {
            $aid = (int)($m['admin_id'] ?? 0);
            $who = $aid ? "🧑‍💼 ادمین <code>{$aid}</code>" : '🧑‍💼 ادمین';
        } else {
            $who = $role;
        }
        $ts = $m['created_at'] ?? '';
        if ($ts && function_exists('formatJalaliDateTime')) {
            $ts = formatJalaliDateTime($ts);
        }
        $body = htmlspecialchars(mb_substr((string)($m['message'] ?? ''), 0, 900));
        $fid = trim((string)($m['media_file_id'] ?? ''));
        if ($fid !== '' && strlen($fid) >= 10) {
            $photoIdx++;
            $body .= "\n🖼 تصویر #{$photoIdx} ↓";
            $cap = strip_tags($who) . ' | ' . $ts;
            $msgTxt = trim((string)($m['message'] ?? ''));
            if ($msgTxt !== '' && mb_strpos($msgTxt, '[تصویر') === false) {
                $cap .= "\n" . mb_substr($msgTxt, 0, 150);
            }
            $photos[] = ['file_id' => $fid, 'caption' => $cap];
        }
        $line = "<b>{$who}</b> <i>{$ts}</i>\n{$body}\n\n";
        if (mb_strlen($buf . $line) > 3500) {
            $chunks[] = $buf;
            $buf = $line;
        } else {
            $buf .= $line;
        }
    }
    $chunks[] = $buf;
    $kb = json_encode(['inline_keyboard' => [
        [['text' => '✍️ پاسخ', 'callback_data' => "adm_rep:{$uid}", 'style' => 'primary']],
        [['text' => '👤 صفحه کاربر', 'callback_data' => "adm_user_view:{$uid}"]],
        [['text' => '🔙 لیست انسانی', 'callback_data' => 'adm_human_support:0', 'style' => 'danger']],
    ]], JSON_UNESCAPED_UNICODE);
    foreach ($chunks as $i => $c) {
        $payload = ['chat_id' => $chat_id, 'text' => $c, 'parse_mode' => 'HTML'];
        if ($i === count($chunks) - 1 && empty($photos)) {
            $payload['reply_markup'] = $kb;
        }
        sendTelegram('sendMessage', $payload);
    }
    // نمایش عکس‌ها با file_id ذخیره‌شده در دیتابیس (بدون فایل روی سرور)
    foreach ($photos as $pi => $ph) {
        $payload = [
            'chat_id' => $chat_id,
            'photo' => $ph['file_id'],
            'caption' => mb_substr($ph['caption'], 0, 900),
        ];
        if ($pi === count($photos) - 1) {
            $payload['reply_markup'] = $kb;
        }
        $res = sendTelegram('sendPhoto', $payload);
        if (empty($res['ok'])) {
            sendTelegram('sendMessage', [
                'chat_id' => $chat_id,
                'text' => "⚠️ تصویر #" . ($pi + 1) . " قابل نمایش نیست (شناسه فایل منقضی یا نامعتبر).",
            ]);
        }
    }
    exit();
}




// درخواست مستقیم پشتیبانی انسانی — باز کردن تیکت
// درخواست مستقیم پشتیبانی انسانی — باز کردن تیکت
if ($callback_data === 'support_human') {
    if (!isFeatureEnabled($db, 'btn_support') && !isBotAdmin($user_id)) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'پشتیبانی غیرفعال است', 'show_alert' => true]);
        exit();
    }
    if (function_exists('openSupportTicket')) {
        openSupportTicket($db, $user_id);
    }
    $db->prepare("UPDATE users SET step = 'support_human_wait' WHERE user_id = ?")->execute([$user_id]);
    sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id']]);
    $ukb = function_exists('supportUserOpenKeyboard') ? supportUserOpenKeyboard() : json_encode(['inline_keyboard' => [[['text' => '🔚 پایان گفتگو', 'callback_data' => 'support_ticket_close_user', 'style' => 'danger']]]]);
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "👨‍💼 <b>گفتگوی پشتیبانی انسانی</b>\n\n"
               . "پیام یا عکست رو بفرست — مستقیم به تیم پشتیبانی می‌رسه.\n"
               . "می‌تونی چند پیام پشت‌سرهم بفرستی تا موضوع حل بشه.\n\n"
               . "هر وقت تمام شد، «پایان گفتگو» رو بزن ✅",
        'parse_mode' => 'HTML',
        'reply_markup' => $ukb,
    ]);
    exit();
}

// کاربر تیکت را می‌بندد
if ($callback_data === 'support_ticket_close_user' || $callback_data === 'support_done') {
    if (function_exists('closeSupportTicket')) {
        closeSupportTicket($db, $user_id, 'user', null);
    }
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    if (!empty($update['callback_query']['id'])) {
        sendTelegram('answerCallbackQuery', ['callback_query_id' => $update['callback_query']['id'], 'text' => 'گفتگو بسته شد']);
    }
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ گفتگوی پشتیبانی بسته شد.\nهر وقت لازم شد دوباره از منو «پشتیبانی» رو بزن 💬",
        'reply_markup' => $mainKeyboard,
    ]);
    if (function_exists('notifyAdmins')) {
        notifyAdmins("🔚 کاربر <code>{$user_id}</code> گفتگوی پشتیبانی را بست.", null, null, 'support', $user_id);
    }
    exit();
}

// پیام برای پشتیبانی انسانی (گفتگوی باز — step پاک نمی‌شود)
if (($text || $photo) && ($currentUser['step'] ?? '') === 'support_human_wait') {
    if ($text) {
        $menuHints = ['خرید اشتراک', 'سرویس‌های من', 'کیف پول', 'دعوت دوست', 'زیرمجموعه', 'دانلود اپ', 'اپ و راهنما', 'کانال', 'راهنمای اتصال', 'دریافت تست'];
        foreach ($menuHints as $mw) {
            if (mb_strpos($text, $mw) !== false && mb_strlen($text) < 50) {
                if (function_exists('closeSupportTicket')) {
                    closeSupportTicket($db, $user_id, 'user_menu', null);
                }
                $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
                sendTelegram('sendMessage', [
                    'chat_id' => $chat_id,
                    'text' => "✅ از پشتیبانی خارج شدی.\nبرای ادامه، همان گزینه منو را دوباره لمس کن.",
                    'reply_markup' => $mainKeyboard,
                ]);
                exit();
            }
        }
    }

    if (function_exists('openSupportTicket')) {
        openSupportTicket($db, $user_id);
    }

    $ukb = function_exists('supportUserOpenKeyboard') ? supportUserOpenKeyboard() : null;
    sendTelegram('sendMessage', [
        'chat_id' => $chat_id,
        'text' => "✅ رسید — تیم پشتیبانی می‌بینه و همین‌جا جواب می‌ده.\nاگر نکته‌ای موند بفرست؛ وگرنه «پایان گفتگو» رو بزن.",
        'reply_markup' => $ukb,
    ]);

    $uname = '';
    try {
        $st = $db->prepare("SELECT username FROM users WHERE user_id = ? LIMIT 1");
        $st->execute([$user_id]);
        $u = $st->fetchColumn();
        if ($u) $uname = ' @' . ltrim((string)$u, '@');
    } catch (Exception $e) {}

    $card = function_exists('buildSupportTicketCard') ? buildSupportTicketCard($db, $user_id) : ("🎫 پشتیبانی\n👤 <code>{$user_id}</code>{$uname}\n");
    $admKb = function_exists('supportAdminTicketKeyboard') ? supportAdminTicketKeyboard($user_id) : json_encode(['inline_keyboard' => [[['text' => '✍️ پاسخ', 'callback_data' => "adm_rep:{$user_id}"]]]]);

    if ($photo) {
        $fid = end($photo)['file_id'];
        $logTxt = $text !== '' ? $text : '[تصویر]';
        if (function_exists('logSupportHumanMessage')) {
            logSupportHumanMessage($db, $user_id, 'user', $logTxt, null, $fid);
        }
        $cap = $card . "\n🖼 <b>تصویر از کاربر</b>";
        if ($text !== '') {
            $cap .= "\n💬 " . htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
        }
        // کپشن تلگرام حداکثر ۱۰۲۴ کاراکتر
        if (mb_strlen($cap) > 1000) {
            $cap = mb_substr($cap, 0, 1000) . "\n…";
        }
        if (function_exists('notifyAdmins')) {
            notifyAdmins($cap, $admKb, $fid, 'support', $user_id);
        } else {
            sendTelegram('sendPhoto', [
                'chat_id' => ADMIN_ID,
                'photo' => $fid,
                'caption' => $cap,
                'parse_mode' => 'HTML',
                'reply_markup' => $admKb,
            ]);
        }
    } elseif ($text !== '') {
        if (function_exists('logSupportHumanMessage')) {
            logSupportHumanMessage($db, $user_id, 'user', $text, null, null);
        }
        $body = $card . "\n💬 <b>پیام کاربر:</b>\n" . htmlspecialchars($text, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
        if (mb_strlen($body) > 4000) {
            $body = mb_substr($body, 0, 4000) . "\n…";
        }
        if (function_exists('notifyAdmins')) {
            notifyAdmins($body, $admKb, null, 'support', $user_id);
        } else {
            sendTelegram('sendMessage', [
                'chat_id' => ADMIN_ID,
                'text' => $body,
                'parse_mode' => 'HTML',
                'reply_markup' => $admKb,
            ]);
        }
    }
    if (function_exists('touchSupportTicket')) {
        touchSupportTicket($db, $user_id);
    }
    exit();
}

// دستیار هوشمند پشتیبانی
if (($text || $photo) && ($currentUser['step'] ?? '') === 'support_message') {
    $aiKb = json_encode(['inline_keyboard' => [
        [['text' => '👨‍💼 پشتیبانی انسانی', 'callback_data' => 'support_human', 'style' => 'primary']],
        [['text' => '✅ تمام شد', 'callback_data' => 'support_done', 'style' => 'success']]
    ]], JSON_UNESCAPED_UNICODE);

    // عکس: به ادمین فوروارد + پیام راهنما (AI تصویر را نمی‌بیند)
    if ($photo) {
        $replyBtn = json_encode(['inline_keyboard' => [[['text' => '✍️ پاسخ', 'callback_data' => "adm_rep:{$user_id}"]]]]);
        $fid = end($photo)['file_id'];
        if (function_exists('logSupportHumanMessage')) {
            logSupportHumanMessage($db, $user_id, 'user', $text ?: '[تصویر پشتیبانی]', null, $fid);
        }
        sendTelegram('sendPhoto', [
            'chat_id' => ADMIN_ID,
            'photo' => $fid,
            'caption' => "📩 تصویر پشتیبانی از کاربر {$user_id}" . ($text ? ("\n" . $text) : ''),
            'reply_markup' => $replyBtn
        ]);
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "✅ تصویر برای مدیریت ارسال شد.\nاگر سوال متنی داری همین‌جا بپرس؛ در غیر این صورت منتظر پاسخ انسانی بمان.",
            'reply_markup' => $aiKb
        ]);
        // step را support_message نگه می‌داریم تا سوال بعدی ممکن باشد
        exit();
    }

    if ($text) {
        // اگر دکمه منوی اصلی زده شد، از حالت پشتیبانی خارج شو
        $menuHints = ['خرید اشتراک', 'سرویس‌های من', 'کیف پول', 'دعوت دوست', 'زیرمجموعه', 'دانلود اپ', 'اپ و راهنما', 'کانال', 'راهنمای اتصال', 'دریافت تست'];
        foreach ($menuHints as $mw) {
            if ($text !== '' && mb_strpos($text, $mw) !== false && mb_strlen($text) < 50) {
                $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
                sendTelegram('sendMessage', [
                    'chat_id' => $chat_id,
                    'text' => "✅ از پشتیبانی خارج شدی.\nبرای ادامه، همان گزینه منو را دوباره لمس کن.",
                    'reply_markup' => $mainKeyboard
                ]);
                exit();
            }
        }
        if ($text === '/start') {
            $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
            // ادامه به هندلرهای start در صورت وجود بالاتر ممکن نیست؛ منو را نشان بده
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => 'منوی اصلی:', 'reply_markup' => $mainKeyboard]);
            exit();
        }

        sendTelegram('sendChatAction', ['chat_id' => $chat_id, 'action' => 'typing']);
        $aiAnswer = '';
        try {
            // برای support_ai.php: دسترسی به db و user_id
            $GLOBALS['db'] = $db;
            $GLOBALS['user_id'] = $user_id;
            if (function_exists('ensureSupportAiTable')) ensureSupportAiTable($db);
            if (function_exists('logSupportAiMessage')) logSupportAiMessage($db, $user_id, 'user', $text);
            $userCtx = function_exists('buildSupportUserContext') ? buildSupportUserContext($db, $user_id) : '';
            $hist = function_exists('getSupportAiHistory') ? getSupportAiHistory($db, $user_id, 4) : '';
            $aiAnswer = function_exists('callSupportAI') ? (string)callSupportAI($text, $userCtx, $hist) : '';
        } catch (Throwable $e) {
            @file_put_contents(__DIR__ . '/support_ai.log', date('c') . ' bot_catch ' . $e->getMessage() . "\n", FILE_APPEND);
            $aiAnswer = function_exists('getSupportFaqFallback') ? getSupportFaqFallback($text) : 'لطفاً دوباره تلاش کنید یا پشتیبانی انسانی را بزنید.';
        }
        if ($aiAnswer === '') {
            $aiAnswer = function_exists('getSupportFaqFallback') ? getSupportFaqFallback($text) : 'لطفاً پشتیبانی انسانی را بزنید.';
        }
        if (function_exists('logSupportAiMessage')) logSupportAiMessage($db, $user_id, 'ai', $aiAnswer);
        $out = "🤖 دستیار پشتیبانی:\n\n" . $aiAnswer;
        if (mb_strlen($out) > 4000) $out = mb_substr($out, 0, 4000) . "\n…";
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => $out,
            'reply_markup' => $aiKb
        ]);
        exit();
    }
    exit();
}

if ($text && strpos($currentUser['step'], 'ask_user:') === 0) {
    $planKey = str_replace('ask_user:', '', $currentUser['step']);
    $desiredUsername = strtolower($text);
    if (!preg_match('/^[a-z0-9_]{3,18}$/', $desiredUsername)) {
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "⚠️ فقط حروف انگلیسی و عدد (۳ تا ۱۸ کاراکتر):"]);
        exit();
    }
    issueInvoice($chat_id, $user_id, $planKey, $desiredUsername, 'new', $plans, $db);
    exit();
}

if ($text && $currentUser['step'] === 'admin_broadcast' && isBotAdmin($user_id)) {
    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
    $all = $db->query("SELECT user_id FROM users")->fetchAll(PDO::FETCH_COLUMN);
    foreach($all as $u) {
        sendTelegram('sendMessage', ['chat_id' => $u, 'text' => "🔔 <b>اطلاعیه:</b>\n\n" . htmlspecialchars($text), 'parse_mode' => 'HTML']);
        usleep(35000);
    }
    sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ همگانی ارسال شد."]);
    exit();
}

if ($photo && (strpos($currentUser['step'], 'pay:') === 0 || strpos($currentUser['step'], 'payid:') === 0)) {
    // مبلغ و پلن فقط از جدول payments — نه از step طولانی (قبلاً VARCHAR کوتاه مبلغ را قطع می‌کرد: 249871 → 2498)
    $fileId = end($photo)['file_id'];
    $paymentId = 0;
    $price = 0;
    $actionType = 'new';
    $planOrAmount = '';
    $targetUser = '';
    $couponCode = null;
    $exist = null;

    $stepRaw = (string)$currentUser['step'];
    if (strpos($stepRaw, 'payid:') === 0) {
        $paymentId = (int)substr($stepRaw, 6);
        if ($paymentId > 0) {
            $st = $db->prepare(
                "SELECT * FROM payments WHERE id = ? AND user_id = ?
                   AND (
                     status IN ('pending','approved')
                     OR (status IN ('expired','cancelled','rejected') AND created_at >= (NOW() - INTERVAL 1 DAY))
                   )
                 LIMIT 1"
            );
            $st->execute([$paymentId, $user_id]);
            $exist = $st->fetch(PDO::FETCH_ASSOC);
        }
    }

    // سازگاری با step قدیمی pay:action:plan:user:coupon:price
    if (!$exist && strpos($stepRaw, 'pay:') === 0) {
        $parts = explode(':', $stepRaw);
        $actionType = $parts[1] ?? 'new';
        $planOrAmount = $parts[2] ?? '';
        $targetUser = $parts[3] ?? '';
        $couponCode = $parts[4] ?? null;
        $exactPayablePrice = isset($parts[5]) ? (int)$parts[5] : 0;
        // اگر مبلغ مشکوک کوتاه بود (قطع‌شدگی)، آخرین فاکتور pending کاربر را بگیر
        $st = $db->prepare(
            "SELECT * FROM payments
             WHERE user_id = ? AND status IN ('pending','expired','cancelled','rejected')
               AND (photo_file_id = 'AWAITING_RECEIPT' OR photo_file_id IS NULL OR photo_file_id = ''
                    OR (status IN ('expired','cancelled','rejected') AND created_at >= (NOW() - INTERVAL 1 DAY)))
             ORDER BY id DESC LIMIT 1"
        );
        $st->execute([$user_id]);
        $latest = $st->fetch(PDO::FETCH_ASSOC);
        if ($latest) {
            $planPrice = 0;
            try {
                if (!empty($latest['plan_key']) && $latest['action_type'] !== 'deposit') {
                    $pq = $db->prepare("SELECT price FROM bot_plans WHERE plan_key = ? LIMIT 1");
                    $pq->execute([(string)$latest['plan_key']]);
                    $planPrice = (int)$pq->fetchColumn();
                }
            } catch (Exception $e) {}
            $lp = (int)$latest['price'];
            // اگر مبلغ step با فاکتور DB نخواند یا خیلی کوچکتر از قیمت پلن بود → DB معتبر است
            if ($exactPayablePrice <= 0 || ($planPrice > 0 && $exactPayablePrice < (int)($planPrice * 0.4)) || ($lp > 0 && $exactPayablePrice < (int)($lp * 0.5) && $lp >= 10000)) {
                $exist = $latest;
            } else {
                $st2 = $db->prepare(
                    "SELECT * FROM payments
                     WHERE user_id = ? AND price = ? AND action_type = ?
                       AND (
                         status IN ('pending','approved')
                         OR (status IN ('expired','cancelled','rejected') AND created_at >= (NOW() - INTERVAL 1 DAY))
                       )
                     ORDER BY id DESC LIMIT 1"
                );
                $st2->execute([$user_id, $exactPayablePrice, $actionType]);
                $exist = $st2->fetch(PDO::FETCH_ASSOC);
                if (!$exist) {
                    $exist = $latest;
                }
            }
        }
    }

    if ($exist) {
        $paymentId = (int)$exist['id'];
        $price = (int)$exist['price'];
        $actionType = (string)($exist['action_type'] ?? 'new');
        $planOrAmount = (string)($exist['plan_key'] ?? '');
        $targetUser = (string)($exist['target_username'] ?? '');
        $couponCode = $exist['coupon_code'] ?? null;
        if (($exist['status'] ?? '') === 'approved') {
            $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
            sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ این پرداخت قبلاً به‌صورت خودکار تأیید شده است.", 'parse_mode' => 'HTML']);
            exit();
        }
        try {
            $db->prepare(
                "UPDATE payments SET photo_file_id = ?, status = 'pending', expires_at = DATE_ADD(NOW(), INTERVAL 1 DAY) WHERE id = ?"
            )->execute([$fileId, $paymentId]);
        } catch (Exception $e) {
            $db->prepare("UPDATE payments SET photo_file_id = ?, status = 'pending' WHERE id = ?")
               ->execute([$fileId, $paymentId]);
        }
    }

    if ($paymentId > 0 && $price > 0) {
        $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ?")->execute([$user_id]);
        sendTelegram('sendMessage', ['chat_id' => $chat_id, 'text' => "✅ <b>فیش ثبت شد و در صف بررسی قرار گرفت.</b>", 'parse_mode' => 'HTML']);
        $admKb = json_encode(['inline_keyboard' => [[['text' => '✅ تایید', 'callback_data' => "adm_app_{$paymentId}"], ['text' => '❌ رد', 'callback_data' => "adm_rej_{$paymentId}", 'style' => 'danger']]]]);
        $payRow = null;
        try {
            $stPay = $db->prepare('SELECT * FROM payments WHERE id = ? LIMIT 1');
            $stPay->execute([$paymentId]);
            $payRow = $stPay->fetch(PDO::FETCH_ASSOC) ?: null;
        } catch (Exception $e) {}
        if (!$payRow) {
            $payRow = [
                'id' => $paymentId,
                'user_id' => $user_id,
                'price' => $price,
                'action_type' => $actionType ?? 'new',
                'plan_key' => $planOrAmount ?? '',
                'coupon_code' => $couponCode ?? null,
                'target_username' => $targetUser ?? '',
                'photo_file_id' => $fileId,
                'created_at' => date('Y-m-d H:i:s'),
            ];
        }
        $review = buildPaymentReviewInfo($db, $payRow);
        notifyAdmins(
            $review['html'],
            $admKb,
            $fileId,
            'payment',
            $paymentId
        );
    } else {
        sendTelegram('sendMessage', [
            'chat_id' => $chat_id,
            'text' => "⚠️ فاکتور فعالی پیدا نشد. لطفاً دوباره از منوی خرید فاکتور بسازید.",
            'parse_mode' => 'HTML',
        ]);
    }
    exit();
}
?>
