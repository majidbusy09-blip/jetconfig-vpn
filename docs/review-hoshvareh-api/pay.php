<?php
/**
 * JetConfig — صفحه پرداخت امن کارت‌به‌کارت
 * URL: pay.php?t=TOKEN
 * AJAX: pay.php?t=TOKEN&ajax=1
 */
declare(strict_types=1);

header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');

require_once __DIR__ . '/config.php';

const PAY_TTL_FALLBACK = 1200;

function pay_db(): PDO
{
    static $db = null;
    if ($db instanceof PDO) {
        return $db;
    }
    $db = new PDO(
        'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
        DB_USER,
        DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]
    );
    return $db;
}

function pay_ensure_cols(PDO $db): void
{
    static $done = false;
    if ($done) {
        return;
    }
    $done = true;
    try {
        $cols = $db->query('SHOW COLUMNS FROM payments')->fetchAll(PDO::FETCH_COLUMN);
        $cols = array_map('strtolower', $cols ?: []);
        if (!in_array('pay_token', $cols, true)) {
            $db->exec("ALTER TABLE payments ADD COLUMN pay_token VARCHAR(64) NULL DEFAULT NULL");
        }
        if (!in_array('expires_at', $cols, true)) {
            $db->exec("ALTER TABLE payments ADD COLUMN expires_at DATETIME NULL DEFAULT NULL");
        }
    } catch (Throwable $e) {
    }
}

function pay_active_card(PDO $db): array
{
    try {
        $row = $db->query("SELECT * FROM bank_cards WHERE is_active = 1 ORDER BY RAND() LIMIT 1")->fetch();
        if ($row) {
            return $row;
        }
    } catch (Throwable $e) {
    }
    return [
        'card_number' => '',
        'card_holder' => 'جت‌کانفیگ',
        'bank_name' => '',
    ];
}

function pay_format_card(string $num): string
{
    $d = preg_replace('/\D/', '', $num);
    return trim(chunk_split($d, 4, ' '));
}


/** خرید از اپ: target در app_accounts یا user_id مصنوعی 700… */
function pay_is_app_purchase(PDO $db, array $pay): bool
{
    $uid = (int)($pay['user_id'] ?? 0);
    if ($uid >= 700000000000) {
        return true;
    }
    // منبع اپ / صفحه وب پرداخت اپ
    $photo = (string)($pay['photo_file_id'] ?? '');
    if (stripos($photo, 'APP') !== false || stripos($photo, 'AWAITING') !== false) {
        // alone not enough for telegram web pay which also uses AWAITING_RECEIPT
    }
    $target = trim((string)($pay['target_username'] ?? ''));
    if ($target === '' || $target === 'wallet') {
        return false;
    }
    try {
        $st = $db->prepare('SELECT id FROM app_accounts WHERE LOWER(config_username) = LOWER(?) LIMIT 1');
        $st->execute([$target]);
        if ($st->fetch()) {
            return true;
        }
    } catch (Throwable $e) {
    }
    // نام کانفیگ ربات نیست و user_id مصنوعی در پرداخت‌های مرتبط
    if ($uid > 0 && $uid < 700000000000) {
        return false;
    }
    return false;
}

function pay_bot_username(): string
{
    if (defined('BOT_USERNAME') && BOT_USERNAME) {
        return ltrim((string)BOT_USERNAME, '@');
    }
    static $cached = null;
    if ($cached !== null) {
        return $cached;
    }
    $cached = 'JetConfig1bot';
    if (defined('BOT_TOKEN') && BOT_TOKEN) {
        $ch = curl_init('https://api.telegram.org/bot' . BOT_TOKEN . '/getMe');
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 8,
            CURLOPT_SSL_VERIFYPEER => false,
        ]);
        $res = curl_exec($ch);
        curl_close($ch);
        $j = json_decode((string)$res, true);
        if (!empty($j['ok']) && !empty($j['result']['username'])) {
            $cached = (string)$j['result']['username'];
        }
    }
    return $cached;
}

function pay_bot_link(): string
{
    return 'https://t.me/' . pay_bot_username();
}

function pay_tg_api(string $method, array $fields)
{
    if (!defined('BOT_TOKEN') || !BOT_TOKEN) {
        return null;
    }
    $ch = curl_init('https://api.telegram.org/bot' . BOT_TOKEN . '/' . $method);
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => $fields,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 25,
        CURLOPT_SSL_VERIFYPEER => false,
    ]);
    $res = curl_exec($ch);
    curl_close($ch);
    $j = json_decode((string)$res, true);
    return is_array($j) ? $j : null;
}

function pay_admin_ids(PDO $db): array
{
    $ids = [];
    if (defined('ADMIN_ID') && ADMIN_ID) {
        $ids[] = (int)ADMIN_ID;
    }
    try {
        $rows = $db->query('SELECT user_id FROM bot_admins')->fetchAll(PDO::FETCH_COLUMN);
        foreach ($rows as $id) {
            $ids[] = (int)$id;
        }
    } catch (Throwable $e) {
    }
    return array_values(array_unique(array_filter($ids)));
}

function pay_handle_receipt_upload(PDO $db, array $pay): array
{
    if (empty($_FILES['receipt']['tmp_name']) || !is_uploaded_file($_FILES['receipt']['tmp_name'])) {
        return ['ok' => false, 'error' => 'فایلی انتخاب نشده'];
    }
    $err = (int)($_FILES['receipt']['error'] ?? 0);
    if ($err !== UPLOAD_ERR_OK) {
        return ['ok' => false, 'error' => 'آپلود ناموفق'];
    }
    $size = (int)($_FILES['receipt']['size'] ?? 0);
    if ($size <= 0 || $size > 8 * 1024 * 1024) {
        return ['ok' => false, 'error' => 'حجم فایل باید کمتر از ۸ مگابایت باشد'];
    }
    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    $mime = $finfo ? (string)finfo_file($finfo, $_FILES['receipt']['tmp_name']) : '';
    if ($finfo) {
        finfo_close($finfo);
    }
    $okMime = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp'];
    if (!isset($okMime[$mime])) {
        return ['ok' => false, 'error' => 'فقط عکس JPG / PNG / WEBP'];
    }
    $dir = __DIR__ . '/receipts';
    if (!is_dir($dir)) {
        @mkdir($dir, 0755, true);
    }
    $name = 'p' . (int)$pay['id'] . '_' . time() . '.' . $okMime[$mime];
    $dest = $dir . '/' . $name;
    if (!move_uploaded_file($_FILES['receipt']['tmp_name'], $dest)) {
        return ['ok' => false, 'error' => 'ذخیره فایل ناموفق'];
    }

    $pid = (int)$pay['id'];
    $price = (int)$pay['price'];

    // کارت کامل مثل تأیید پیامکی / ربات
    $caption = '';
    $approveLib = __DIR__ . '/approve_lib.php';
    if (is_readable($approveLib)) {
        require_once $approveLib;
    }
    if (function_exists('buildPaymentReviewInfo')) {
        try {
            $review = buildPaymentReviewInfo($db, $pay);
            $caption = (string)($review['html'] ?? '');
            if ($caption !== '') {
                $caption .= "\n\n📥 منبع: <b>صفحه پرداخت وب / عکس فیش</b>";
                $caption .= "\nاز دکمه‌های زیر می‌تونی تأیید یا رد کنی.";
            }
        } catch (Throwable $e) {
            $caption = '';
        }
    }
    if ($caption === '') {
        // fallback غنی بدون وابستگی
        $uid = (int)($pay['user_id'] ?? 0);
        $act = strtolower(trim((string)($pay['action_type'] ?? 'new')));
        $planKey = trim((string)($pay['plan_key'] ?? ''));
        $coupon = trim((string)($pay['coupon_code'] ?? ''));
        $target = trim((string)($pay['target_username'] ?? ''));
        $actMap = ['new' => 'خرید جدید', 'renew' => 'تمدید', 'deposit' => 'شارژ کیف پول'];
        $actLabel = $actMap[$act] ?? $act;
        $tgUser = '';
        $balance = 0;
        $orderCount = 0;
        $hasBought = 0;
        try {
            $st = $db->prepare('SELECT username, balance, has_bought FROM users WHERE user_id = ? LIMIT 1');
            $st->execute([$uid]);
            $u = $st->fetch(PDO::FETCH_ASSOC);
            if ($u) {
                $tgUser = ltrim((string)($u['username'] ?? ''), '@');
                $balance = (int)($u['balance'] ?? 0);
                $hasBought = (int)($u['has_bought'] ?? 0);
            }
        } catch (Throwable $e) {}
        try {
            // فقط سرویس‌های غیرتست = خرید واقعی (تست رایگان مشتری قبلی حساب نشود)
            $st = $db->prepare(
                "SELECT COUNT(*) FROM orders WHERE user_id = ?
                 AND COALESCE(plan_key,'') NOT LIKE '%test%'
                 AND COALESCE(plan_key,'') <> 'test_free'
                 AND COALESCE(config_username,'') NOT LIKE 'test_%'
                 AND NOT (
                   COALESCE(volume_gb, 0) > 0 AND COALESCE(volume_gb, 0) <= 0.2
                   AND COALESCE(days, 0) >= 0 AND COALESCE(days, 0) <= 1
                   AND (COALESCE(plan_key,'') = '' OR COALESCE(plan_key,'') LIKE '%test%')
                 )"
            );
            $st->execute([$uid]);
            $orderCount = (int)$st->fetchColumn();
        } catch (Throwable $e) {
            try {
                $st = $db->prepare(
                    "SELECT COUNT(*) FROM orders WHERE user_id = ?
                     AND COALESCE(plan_key,'') NOT LIKE '%test%'
                     AND COALESCE(plan_key,'') <> 'test_free'"
                );
                $st->execute([$uid]);
                $orderCount = (int)$st->fetchColumn();
            } catch (Throwable $e2) {
                $orderCount = 0;
            }
        }
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
            } catch (Throwable $e) {}
        }
        $discountPct = 0;
        if (strtoupper($coupon) === 'FIRST10') {
            $discountPct = 10;
        } elseif ($coupon !== '') {
            try {
                $st = $db->prepare('SELECT discount_percent FROM coupons WHERE code = ? LIMIT 1');
                $st->execute([$coupon]);
                $discountPct = (int)$st->fetchColumn();
            } catch (Throwable $e) {}
        }
        $channel = ($uid >= 700000000000) ? '📱 اپ اختصاصی' : '🤖 ربات تلگرام';
        $cust = ($hasBought > 0 || $orderCount > 0) ? 'مشتری قبلی (خرید غیرتست)' : 'خرید اول / کاربر جدید';
        $tgLine = $tgUser !== '' ? '@' . htmlspecialchars($tgUser) : '—';
        $lines = [];
        $lines[] = "🔔 <b>فیش وب برای بررسی</b>";
        $lines[] = "";
        $lines[] = "#️⃣ فاکتور: <code>#{$pid}</code>";
        $lines[] = "👤 کاربر: {$tgLine} (<code>{$uid}</code>)";
        $lines[] = "📡 کانال: <b>{$channel}</b>";
        $lines[] = "🏷 وضعیت: {$cust} | 💼 کیف: <b>" . number_format($balance) . "</b> ت";
        if ($orderCount > 0) {
            $lines[] = "📊 سرویس ثبت‌شده: <b>{$orderCount}</b>";
        }
        $lines[] = "";
        $lines[] = "📦 نوع: <b>{$actLabel}</b>";
        if ($act === 'deposit') {
            $reqAmt = is_numeric($planKey) ? (int)$planKey : 0;
            if ($reqAmt > 0) {
                $lines[] = "💳 مبلغ درخواست شارژ: <b>" . number_format($reqAmt) . "</b> ت";
            }
        } else {
            if ($planTitle !== '') {
                $lines[] = "🏷 پلن: <b>" . htmlspecialchars($planTitle) . "</b>";
            }
            if ($planKey !== '') {
                $lines[] = "🔑 کد پلن: <code>" . htmlspecialchars($planKey) . "</code>";
            }
            if ($planPrice > 0) {
                $lines[] = "💰 قیمت پلن: <b>" . number_format($planPrice) . "</b> ت";
            }
            if ($planVol !== null || $planDays !== null) {
                $volTxt = ((float)$planVol <= 0) ? 'نامحدود' : (rtrim(rtrim(number_format((float)$planVol, 2, '.', ''), '0'), '.') . ' گیگ');
                $dayTxt = ((int)$planDays <= 0) ? 'بدون انقضا' : ((int)$planDays . ' روز');
                $lines[] = "📐 حجم/مدت: {$volTxt} / {$dayTxt}";
            }
        }
        if ($coupon !== '') {
            $cLine = "🎟 تخفیف: <code>" . htmlspecialchars($coupon) . "</code>";
            if ($discountPct > 0) {
                $cLine .= " ({$discountPct}٪)";
            }
            $lines[] = $cLine;
        } else {
            $lines[] = "🎟 تخفیف: —";
        }
        $lines[] = "🔢 مبلغ قابل پرداخت: <b>" . number_format($price) . "</b> ت";
        $lines[] = "💵 ریال: <code>" . number_format($price * 10) . "</code>";
        if ($target !== '' && $target !== 'wallet') {
            $lines[] = "👤 کانفیگ: <code>" . htmlspecialchars($target) . "</code>";
        }
        $lines[] = "📥 منبع: صفحه پرداخت وب / عکس فیش";
        $lines[] = "";
        $lines[] = "از دکمه‌های زیر می‌تونی تأیید یا رد کنی.";
        $caption = implode("\n", $lines);
    }
    $kb = json_encode([
        'inline_keyboard' => [[
            ['text' => '✅ تایید', 'callback_data' => "adm_app_{$pid}"],
            ['text' => '❌ رد', 'callback_data' => "adm_rej_{$pid}"],
        ]]
    ], JSON_UNESCAPED_UNICODE);

    $fileId = '';
    $admins = pay_admin_ids($db);
    $first = true;
    foreach ($admins as $aid) {
        if ($first) {
            $tg = pay_tg_api('sendPhoto', [
                'chat_id' => $aid,
                'caption' => $caption,
                'parse_mode' => 'HTML',
                'reply_markup' => $kb,
                'photo' => new CURLFile($dest, $mime, $name),
            ]);
            $first = false;
        } else {
            $tg = pay_tg_api('sendPhoto', [
                'chat_id' => $aid,
                'photo' => $fileId !== '' ? $fileId : new CURLFile($dest, $mime, $name),
                'caption' => $caption,
                'parse_mode' => 'HTML',
                'reply_markup' => $kb,
            ]);
        }
        if (!empty($tg['ok']) && !empty($tg['result']['photo']) && $fileId === '') {
            $ph = $tg['result']['photo'];
            $fileId = (string)end($ph)['file_id'];
        }
        $mid = (int)($tg['result']['message_id'] ?? 0);
        if ($mid > 0) {
            try {
                $db->prepare('DELETE FROM admin_broadcast_msgs WHERE kind = ? AND ref_id = ? AND admin_id = ?')
                    ->execute(['payment', (string)$pid, $aid]);
                $db->prepare('INSERT INTO admin_broadcast_msgs (kind, ref_id, admin_id, message_id) VALUES (?, ?, ?, ?)')
                    ->execute(['payment', (string)$pid, $aid, $mid]);
            } catch (Throwable $e) {
            }
        }
    }
    if ($fileId === '') {
        $fileId = 'WEB_' . $name;
    }
    try {
        $db->prepare('UPDATE payments SET photo_file_id = ? WHERE id = ? AND status = ?')
            ->execute([$fileId, (int)$pay['id'], 'pending']);
    } catch (Throwable $e) {
    }
    return ['ok' => true, 'file_id' => $fileId];
}

$token = preg_replace('/[^a-zA-Z0-9]/', '', (string)($_GET['t'] ?? $_POST['t'] ?? ''));
$ajax = isset($_GET['ajax']) || (isset($_POST['ajax']) && $_POST['ajax']);
$action = (string)($_POST['action'] ?? '');

$state = [
    'ok' => false,
    'status' => 'invalid',
    'message' => 'لینک نامعتبر است',
];

$db = null;
$pay = null;
$card = null;
$remainSec = 0;

try {
    $db = pay_db();
    pay_ensure_cols($db);
    if ($token !== '') {
        $st = $db->prepare('SELECT * FROM payments WHERE pay_token = ? LIMIT 1');
        $st->execute([$token]);
        $pay = $st->fetch(PDO::FETCH_ASSOC) ?: null;
    }

    if ($pay) {
        $status = (string)$pay['status'];
        $expTs = !empty($pay['expires_at']) ? strtotime((string)$pay['expires_at']) : 0;
        if (!$expTs && !empty($pay['created_at'])) {
            $expTs = strtotime((string)$pay['created_at']) + PAY_TTL_FALLBACK;
        }
        $remainSec = max(0, $expTs - time());

        if ($status === 'pending' && $remainSec <= 0) {
            $didExpire = false;
            try {
                $up = $db->prepare("UPDATE payments SET status = 'expired' WHERE id = ? AND status = 'pending'");
                $up->execute([(int)$pay['id']]);
                $didExpire = $up->rowCount() > 0;
            } catch (Throwable $e) {
            }
            $status = 'expired';
            $pay['status'] = 'expired';
            if ($didExpire && ($pay['photo_file_id'] ?? '') === 'AWAITING_RECEIPT') {
                $uid = (int)$pay['user_id'];
                $pid = (int)$pay['id'];
                $mid = (int)($pay['invoice_msg_id'] ?? 0);
                $txt = "⏰ مهلت فاکتور #{$pid} تمام شد.\n\nاگر هنوز پرداخت نکردی، از منو فاکتور جدید بساز.\n\nاگر پرداخت کردی ولی هنوز خودکار تأیید نشد، روی «پرداخت کرده‌ام» بزن و عکس فیش را بفرست.";
                if ($uid > 0 && $mid > 0) {
                    pay_tg_api('deleteMessage', ['chat_id' => $uid, 'message_id' => $mid]);
                }
                if ($uid > 0) {
                    pay_tg_api('sendMessage', [
                        'chat_id' => $uid,
                        'text' => $txt,
                        'reply_markup' => json_encode([
                            'inline_keyboard' => [
                                [['text' => '✅ پرداخت کرده‌ام — ارسال فیش', 'callback_data' => 'pay_claim:' . $pid]],
                                [['text' => '🛍 خرید اشتراک جدید', 'callback_data' => 'main_categories']],
                            ]
                        ], JSON_UNESCAPED_UNICODE),
                    ]);
                }
                try {
                    $db->prepare("UPDATE users SET step = 'none' WHERE user_id = ? AND step LIKE 'pay:%'")->execute([$uid]);
                } catch (Throwable $e) {
                }
            }
        }

        if ($action === 'cancel' && $status === 'pending') {
            try {
                $db->prepare("UPDATE payments SET status = 'cancelled' WHERE id = ? AND status = 'pending'")
                    ->execute([(int)$pay['id']]);
                $status = 'cancelled';
                $pay['status'] = 'cancelled';
            } catch (Throwable $e) {
            }
        }

        $receiptNote = '';
        if ($action === 'upload' && $status === 'pending') {
            $up = pay_handle_receipt_upload($db, $pay);
            if (!empty($up['ok'])) {
                $receiptNote = 'uploaded';
                $pay['photo_file_id'] = $up['file_id'] ?? $pay['photo_file_id'];
            } else {
                $receiptNote = 'error:' . ($up['error'] ?? 'آپلود ناموفق');
            }
        }
        $hasReceipt = !empty($pay['photo_file_id'])
            && !in_array($pay['photo_file_id'], ['AWAITING_RECEIPT', 'WALLET_PAY', 'SMS_AUTO', 'ADMIN_CREDIT', 'ADMIN_DEBIT'], true);

        $card = pay_active_card($db);
        $price = (int)$pay['price'];
        $rial = $price * 10;
        $discountNote = '';
        $cc = strtoupper(trim((string)($pay['coupon_code'] ?? '')));
        if ($cc === 'FIRST10') {
            $discountNote = 'مبلغ پس از ۱۰٪ تخفیف اولین خرید + کسر جزئی یکتا برای تأیید خودکار';
        } elseif ($cc !== '') {
            $discountNote = 'مبلغ پس از اعمال کد تخفیف ' . $cc . ' + کسر جزئی یکتا برای تأیید خودکار';
        } else {
            $discountNote = 'کسر جزئی تصادفی روی مبلغ برای تطبیق خودکار واریز';
        }
        $planKey = (string)$pay['plan_key'];
        $actionType = (string)$pay['action_type'];
        $title = $actionType === 'deposit' ? 'شارژ کیف پول' : ($actionType === 'renew' ? 'تمدید اشتراک' : 'خرید اشتراک');
        if ($actionType !== 'deposit') {
            try {
                $pl = $db->prepare('SELECT title FROM bot_plans WHERE plan_key = ? LIMIT 1');
                $pl->execute([$planKey]);
                $t = $pl->fetchColumn();
                if ($t) {
                    $title = (string)$t;
                }
            } catch (Throwable $e) {
            }
        }

        $state = [
            'ok' => true,
            'status' => $status,
            'payment_id' => (int)$pay['id'],
            'price' => $price,
            'price_fmt' => number_format($price),
            'discount_note' => $discountNote,
            'rial' => $rial,
            'rial_fmt' => number_format($rial),
            'card' => preg_replace('/\D/', '', (string)($card['card_number'] ?? '')),
            'card_fmt' => pay_format_card((string)($card['card_number'] ?? '')),
            'holder' => (string)($card['card_holder'] ?? ''),
            'bank' => (string)($card['bank_name'] ?? ''),
            'title' => $title,
            'username' => (string)($pay['target_username'] ?? ''),
            'remain' => $remainSec,
            'expires_at' => $expTs ? date('c', $expTs) : null,
            'bot' => pay_bot_link(),
            'message' => '',
            'has_receipt' => !empty($hasReceipt),
            'is_app' => pay_is_app_purchase($db, $pay),
            'receipt_note' => $receiptNote ?? '',
        ];
        $isAppPay = pay_is_app_purchase($db, $pay);
        $state['is_app'] = $isAppPay;
        if ($status === 'approved') {
            $state['message'] = $isAppPay
                ? 'پرداخت تأیید شد. به اپ JET VPN برگردید و یک‌بار بروزرسانی بزنید.'
                : 'پرداخت تأیید شد. به ربات برگردید؛ سرویس در «سرویس‌های من» است.';
            $state['message_detail'] = $isAppPay
                ? 'همان نام کاربری و رمزی که در اپ ساخته‌اید را وارد کنید.'
                : 'اگر پیام ربات را ندیدید، از منوی ربات «سرویس‌های من» را باز کنید.';
        } elseif ($status === 'expired' || $status === 'cancelled' || $status === 'rejected') {
            $state['message'] = 'این فاکتور دیگر معتبر نیست';
            $state['message_detail'] = $isAppPay
                ? 'از داخل اپ دوباره خرید را شروع کنید.'
                : 'از داخل ربات دوباره فاکتور بسازید.';
        }
    }
} catch (Throwable $e) {
    $state = ['ok' => false, 'status' => 'error', 'message' => 'خطای سرور'];
}

if ($ajax) {
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($state, JSON_UNESCAPED_UNICODE);
    exit;
}

$s = $state;
$isPending = ($s['ok'] ?? false) && ($s['status'] ?? '') === 'pending';
$isApproved = ($s['status'] ?? '') === 'approved';
$isDead = in_array($s['status'] ?? '', ['expired', 'cancelled', 'rejected', 'invalid', 'error'], true);
?>
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0b1220">
<title>پرداخت امن | جت‌کانفیگ</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg0: #070b14;
  --bg1: #0d1526;
  --card: rgba(18, 28, 48, 0.72);
  --stroke: rgba(120, 160, 255, 0.18);
  --text: #e8eefc;
  --muted: #8b9bb8;
  --accent: #3b82f6;
  --accent2: #22d3ee;
  --green: #22c55e;
  --red: #f43f5e;
  --warn: #f59e0b;
  --glow: 0 0 40px rgba(59, 130, 246, 0.25);
  --radius: 20px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Vazirmatn', system-ui, sans-serif;
  min-height: 100dvh;
  color: var(--text);
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(59,130,246,.22), transparent 55%),
    radial-gradient(900px 500px at 100% 0%, rgba(34,211,238,.12), transparent 50%),
    radial-gradient(800px 400px at 50% 100%, rgba(99,102,241,.1), transparent 45%),
    linear-gradient(165deg, var(--bg0), var(--bg1));
  padding: 20px 16px 40px;
  overflow-x: hidden;
}
.wrap { max-width: 440px; margin: 0 auto; position: relative; z-index: 1; }

/* floating orbs */
.orb {
  position: fixed; border-radius: 50%; filter: blur(60px); opacity: .35; pointer-events: none; z-index: 0;
  animation: drift 14s ease-in-out infinite alternate;
}
.orb.a { width: 220px; height: 220px; background: #3b82f6; top: -40px; right: -40px; }
.orb.b { width: 180px; height: 180px; background: #22d3ee; bottom: 10%; left: -50px; animation-delay: -4s; }
@keyframes drift {
  from { transform: translate(0,0) scale(1); }
  to { transform: translate(20px, 30px) scale(1.08); }
}

.brand {
  display: flex; align-items: center; gap: 12px; margin-bottom: 22px;
  animation: fadeUp .6s ease both;
}
.brand-logo {
  width: 48px; height: 48px; border-radius: 14px;
  background: linear-gradient(135deg, #1e3a8a, #0ea5e9);
  display: grid; place-items: center;
  box-shadow: var(--glow);
  overflow: hidden;
}
.brand-logo img { width: 100%; height: 100%; object-fit: cover; }
.brand-logo span { font-size: 22px; }
.brand h1 { font-size: 1.15rem; font-weight: 800; letter-spacing: -.02em; }
.brand p { font-size: .78rem; color: var(--muted); }

.steps {
  display: flex; gap: 6px; margin-bottom: 18px;
  animation: fadeUp .6s .05s ease both;
}
.step {
  flex: 1; text-align: center; font-size: .68rem; color: var(--muted);
  padding: 8px 4px; border-radius: 12px; background: rgba(255,255,255,.03);
  border: 1px solid transparent; position: relative;
}
.step.on {
  color: var(--text); border-color: var(--stroke);
  background: linear-gradient(180deg, rgba(59,130,246,.15), rgba(255,255,255,.03));
}
.step.done { color: var(--green); }
.step .n {
  display: inline-grid; place-items: center; width: 20px; height: 20px; border-radius: 50%;
  font-size: .65rem; font-weight: 700; margin-bottom: 4px;
  background: rgba(255,255,255,.08);
}
.step.on .n { background: var(--accent); color: #fff; }
.step.done .n { background: rgba(34,197,94,.25); color: var(--green); }

.card {
  background: var(--card);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 14px;
  box-shadow: 0 20px 50px rgba(0,0,0,.35);
  animation: fadeUp .55s ease both;
}
.card.delay1 { animation-delay: .08s; }
.card.delay2 { animation-delay: .14s; }
.card.delay3 { animation-delay: .2s; }

.amount-label { font-size: .8rem; color: var(--muted); margin-bottom: 6px; }
.amount-big {
  font-size: 2.1rem; font-weight: 800; line-height: 1.15;
  background: linear-gradient(90deg, #fff, #93c5fd);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.amount-rial { font-size: .95rem; color: var(--accent2); margin-top: 6px; font-weight: 600; }
.hint-warn {
  margin-top: 12px; padding: 10px 12px; border-radius: 12px;
  background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.25);
  color: #fcd34d; font-size: .8rem;
}

.meta { font-size: .82rem; color: var(--muted); margin-bottom: 12px; }
.meta strong { color: var(--text); }

.field-label { font-size: .75rem; color: var(--muted); margin-bottom: 6px; }
.field-value {
  font-size: 1.25rem; font-weight: 700; letter-spacing: .06em;
  font-variant-numeric: tabular-nums; direction: ltr; text-align: left;
  padding: 12px 14px; border-radius: 14px;
  background: rgba(0,0,0,.25); border: 1px solid rgba(255,255,255,.06);
  margin-bottom: 10px;
}

.btn {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  width: 100%; border: none; border-radius: 14px; padding: 14px 16px;
  font-family: inherit; font-size: .95rem; font-weight: 700; cursor: pointer;
  transition: transform .15s ease, box-shadow .2s ease, opacity .2s;
}
.btn:active { transform: scale(.98); }
.btn-primary {
  background: linear-gradient(135deg, #2563eb, #0ea5e9);
  color: #fff; box-shadow: 0 10px 30px rgba(37,99,235,.35);
  margin-bottom: 10px;
}
.btn-primary:hover { box-shadow: 0 12px 36px rgba(37,99,235,.45); }
.btn-green {
  background: linear-gradient(135deg, #16a34a, #22c55e);
  color: #fff; box-shadow: 0 10px 28px rgba(34,197,94,.3);
  margin-top: 8px;
}
.btn-ghost {
  background: transparent; color: var(--muted);
  border: 1px solid rgba(255,255,255,.08); margin-top: 10px;
}
.btn-ghost:hover { color: var(--text); border-color: rgba(255,255,255,.18); }
.btn-bot {
  font-size: 1.08rem;
  padding: 16px 18px;
  margin-top: 18px;
  text-decoration: none;
}

.timer {
  display: flex; align-items: center; justify-content: space-between;
  gap: 10px; font-size: .85rem;
}
.timer-bar {
  flex: 1; height: 6px; border-radius: 99px; background: rgba(255,255,255,.08); overflow: hidden;
}
.timer-bar > i {
  display: block; height: 100%; width: 100%; transform-origin: right center;
  background: linear-gradient(90deg, var(--accent2), var(--accent));
  border-radius: 99px; transition: transform 1s linear;
}
.timer-val { font-weight: 700; font-variant-numeric: tabular-nums; min-width: 52px; text-align: left; direction: ltr; }

.toast {
  position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%) translateY(20px);
  background: rgba(15,23,42,.95); color: #fff; padding: 12px 20px; border-radius: 99px;
  font-size: .85rem; font-weight: 600; opacity: 0; pointer-events: none;
  border: 1px solid rgba(255,255,255,.1); transition: .3s ease; z-index: 50;
  box-shadow: 0 10px 40px rgba(0,0,0,.4);
}
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

.status-box { text-align: center; padding: 28px 12px; }
.status-box .icon { font-size: 3rem; margin-bottom: 12px; animation: pop .5s ease; }
.status-box h2 { font-size: 1.2rem; margin-bottom: 8px; }
.status-box p { color: var(--muted); font-size: .9rem; line-height: 1.6; }

.waiting {
  display: none; text-align: center; padding: 16px 8px 4px;
}
.waiting.on { display: block; animation: fadeUp .4s ease; }
.spinner {
  width: 36px; height: 36px; margin: 0 auto 12px;
  border: 3px solid rgba(59,130,246,.2); border-top-color: var(--accent);
  border-radius: 50%; animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes pop {
  from { transform: scale(.6); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.footer {
  text-align: center; margin-top: 20px; font-size: .72rem; color: var(--muted);
  line-height: 1.7; animation: fadeUp .6s .25s ease both;
}
.footer a { color: var(--accent2); text-decoration: none; }

.pulse-dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  background: var(--green); margin-left: 6px;
  box-shadow: 0 0 0 0 rgba(34,197,94,.5);
  animation: pulse 1.6s infinite;
}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(34,197,94,.45); }
  70% { box-shadow: 0 0 0 10px rgba(34,197,94,0); }
  100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
}
</style>
</head>
<body>
<div class="orb a"></div>
<div class="orb b"></div>
<div class="wrap">

  <div class="brand">
    <div class="brand-logo">
      <?php if (is_file(__DIR__ . '/logo.png')): ?>
        <img src="logo.png" alt="JetConfig">
      <?php else: ?>
        <span>🚀</span>
      <?php endif; ?>
    </div>
    <div>
      <h1>جت‌کانفیگ</h1>
      <p>پرداخت امن کارت‌به‌کارت</p>
    </div>
  </div>

<?php if ($isApproved): ?>
  <div class="card">
    <div class="status-box">
      <div class="icon">✅</div>
      <h2>پرداخت تأیید شد ✅</h2>
      <?php if (!empty($s['is_app'])): ?>
        <p>اشتراک شما فعال شد.<br>
        به <b>اپ JET VPN</b> برگردید و یک‌بار <b>بروزرسانی</b> بزنید.<br>
        <span style="color:var(--muted);font-size:.9em">همان نام کاربری و رمز ورود اپ را استفاده کنید.</span></p>
      <?php else: ?>
        <p>اشتراک / شارژ شما فعال شد.<br>
        به <b>ربات تلگرام</b> برگردید و از «سرویس‌های من» جزئیات را ببینید.</p>
        <a class="btn btn-primary btn-bot" href="<?= htmlspecialchars($s['bot'] ?? '#') ?>">بازگشت به ربات تلگرام</a>
      <?php endif; ?>
    </div>
  </div>

<?php elseif ($isDead): ?>
  <div class="card">
    <div class="status-box">
      <div class="icon">⏰</div>
      <h2><?= ($s['status'] ?? '') === 'cancelled' ? 'فاکتور لغو شد' : 'مهلت تمام شد' ?></h2>
      <p><?= htmlspecialchars($s['message'] ?: 'این لینک دیگر معتبر نیست.') ?><br>از داخل ربات دوباره خرید یا شارژ را شروع کن.</p>
      <a class="btn btn-primary btn-bot" href="<?= htmlspecialchars($s['bot'] ?? '#') ?>">بازگشت به ربات تلگرام</a>
    </div>
  </div>

<?php elseif ($isPending): ?>
  <div class="steps" id="steps">
    <div class="step done"><div class="n">✓</div>مبلغ</div>
    <div class="step on" id="st-pay"><div class="n">2</div>واریز</div>
    <div class="step" id="st-match"><div class="n">3</div>تطبیق</div>
    <div class="step" id="st-done"><div class="n">4</div>تحویل</div>
  </div>

  <div class="card delay1">
    <div class="meta">#️⃣ فاکتور <strong>#<?= (int)($s['payment_id'] ?? 0) ?></strong>
      · 📦 <?= htmlspecialchars($s['title'] ?? '') ?>
      <?php if (!empty($s['username']) && $s['username'] !== 'wallet'): ?>
        · 👤 <strong dir="ltr"><?= htmlspecialchars($s['username']) ?></strong>
      <?php endif; ?>
    </div>
    <div class="amount-label">مبلغ دقیق واریز</div>
    <div class="amount-big"><?= htmlspecialchars($s['price_fmt']) ?> <small style="font-size:.55em">تومان</small></div>
    <div class="amount-rial" dir="ltr"><?= htmlspecialchars($s['rial_fmt']) ?> ریال</div>
    <?php if (!empty($s['discount_note'])): ?>
      <div class="meta" style="margin-top:10px;color:var(--accent2);font-size:.82rem;line-height:1.5">🏷 <?= htmlspecialchars($s['discount_note']) ?></div>
    <?php endif; ?>
    <div class="hint-warn">⚠️ دقیقاً همین مبلغ را واریز کن تا سیستم هوشمند خودکار تأیید کند</div>
    <button type="button" class="btn btn-primary" style="margin-top:14px" onclick="copyText('<?= htmlspecialchars((string)$s['rial'], ENT_QUOTES) ?>','مبلغ ریال کپی شد')">
      📋 کپی مبلغ به ریال
    </button>
  </div>

  <div class="card delay2">
    <div class="field-label">شماره کارت مقصد</div>
    <div class="field-value" dir="ltr"><?= htmlspecialchars($s['card_fmt']) ?></div>
    <?php if (!empty($s['holder'])): ?>
      <div class="meta" style="margin-bottom:10px">👤 <?= htmlspecialchars($s['holder']) ?><?= $s['bank'] ? ' · ' . htmlspecialchars($s['bank']) : '' ?></div>
    <?php endif; ?>
    <button type="button" class="btn btn-primary" onclick="copyText('<?= htmlspecialchars($s['card'], ENT_QUOTES) ?>','شماره کارت کپی شد')">
      📋 کپی شماره کارت
    </button>
  </div>

  <div class="card delay3">
    <div class="timer">
      <span>⏱ مهلت واریز</span>
      <span class="timer-val" id="timerVal">--:--</span>
    </div>
    <div class="timer-bar" style="margin-top:10px"><i id="timerBar"></i></div>

    <div class="waiting" id="waiting">
      <div class="spinner"></div>
      <div style="font-weight:700;margin-bottom:4px">در حال تأیید خودکار پرداخت…</div>
      <p style="color:var(--muted);font-size:.82rem">چند ثانیه تا یک دقیقه طول می‌کشد</p>
    </div>

    <form id="receiptForm" style="margin-top:14px" enctype="multipart/form-data" method="post">
      <input type="hidden" name="t" value="<?= htmlspecialchars($token) ?>">
      <input type="hidden" name="action" value="upload">
      <input type="file" id="receiptInput" name="receipt" accept="image/*" style="display:none" onchange="this.form.submit()">
      <button type="button" class="btn btn-primary" onclick="document.getElementById('receiptInput').click()">
        📷 ارسال عکس فیش
      </button>
      <p style="margin-top:8px;font-size:.78rem;color:var(--muted);line-height:1.6">
        پرداخت خودکار تأیید می‌شود؛ اگر طول کشید، عکس فیش را بفرست.
      </p>
    </form>
    <?php if (!empty($s['has_receipt'])): ?>
      <p style="margin-top:8px;color:var(--green);font-size:.85rem;font-weight:700">✅ عکس فیش دریافت شد</p>
    <?php elseif (!empty($s['receipt_note']) && strpos((string)$s['receipt_note'], 'error:') === 0): ?>
      <p style="margin-top:8px;color:var(--red);font-size:.85rem"><?= htmlspecialchars(substr((string)$s['receipt_note'], 6)) ?></p>
    <?php endif; ?>

    <button type="button" class="btn btn-green" id="btnPaid" onclick="markPaid()">
      ✅ پرداخت کردم
    </button>
    <button type="button" class="btn btn-ghost" onclick="cancelPay()">انصراف از پرداخت</button>
  </div>

  <div class="footer">
    <span class="pulse-dot"></span> پرداخت هوشمند — تأیید خودکار پس از واریز<br>
    پرداخت مستقیم به حساب جت‌کانفیگ<br>
    <a class="btn btn-primary btn-bot" href="<?= htmlspecialchars($s['bot']) ?>">بازگشت به ربات تلگرام</a>
  </div>

<?php else: ?>
  <div class="card">
    <div class="status-box">
      <div class="icon">🔗</div>
      <h2>لینک نامعتبر</h2>
      <p>این صفحه فقط با لینک معتبر از داخل ربات باز می‌شود.</p>
    </div>
  </div>
<?php endif; ?>

</div>
<div class="toast" id="toast"></div>

<?php if ($isPending): ?>
<script>
const TOTAL = <?= (int)$s['remain'] ?>;
const START = Date.now();
const TOKEN = <?= json_encode($token) ?>;
let polling = false;

function pad(n){ return String(n).padStart(2,'0'); }
function tick(){
  const left = Math.max(0, TOTAL - Math.floor((Date.now()-START)/1000));
  const m = Math.floor(left/60), sec = left%60;
  document.getElementById('timerVal').textContent = pad(m)+':'+pad(sec);
  const pct = TOTAL > 0 ? left/TOTAL : 0;
  document.getElementById('timerBar').style.transform = 'scaleX('+pct+')';
  if(left <= 0){
    location.reload();
  }
}
tick();
setInterval(tick, 1000);

function toast(msg){
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(()=>el.classList.remove('show'), 1800);
}

async function copyText(text, okMsg){
  try {
    await navigator.clipboard.writeText(text);
    toast(okMsg || 'کپی شد');
  } catch(e){
    const ta = document.createElement('textarea');
    ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); toast(okMsg || 'کپی شد'); } catch(e2){ toast('کپی نشد'); }
    document.body.removeChild(ta);
  }
}

function markPaid(){
  document.getElementById('btnPaid').style.display = 'none';
  document.getElementById('waiting').classList.add('on');
  document.getElementById('st-pay').classList.remove('on');
  document.getElementById('st-pay').classList.add('done');
  document.getElementById('st-pay').querySelector('.n').textContent = '✓';
  document.getElementById('st-match').classList.add('on');
  if(!polling){
    polling = true;
    pollStatus();
  }
}

async function pollStatus(){
  try {
    const r = await fetch('?t='+encodeURIComponent(TOKEN)+'&ajax=1&_='+Date.now());
    const j = await r.json();
    if(j && j.status === 'approved'){
      const isApp = !!j.is_app;
      const msg = j.message || (isApp
        ? 'پرداخت تأیید شد. اشتراک در اپ فعال شد.'
        : 'پرداخت تأیید شد. به ربات برگردید؛ سرویس در «سرویس‌های من» است.');
      const detail = j.message_detail || (isApp
        ? 'به اپ JET VPN برگردید و یک‌بار «بروزرسانی» بزنید. همان نام کاربری و رمز ورود را استفاده کنید.'
        : 'اگر پیام ربات را ندیدید، از منوی ربات «سرویس‌های من» را باز کنید.');
      const botBtn = isApp
        ? '<p style="margin-top:14px;color:#94a3b8;font-size:.9em">می‌توانید این صفحه را ببندید و به اپ برگردید.</p>'
        : '<a class="btn btn-primary btn-bot" href="'+(j.bot||'#')+'">بازگشت به ربات تلگرام</a>';
      document.body.innerHTML = '<div class="wrap"><div class="card"><div class="status-box"><div class="icon">✅</div><h2>پرداخت تأیید شد</h2><p>'+ msg +'</p><p style="margin-top:12px;color:var(--accent2)">'+ detail +'</p>'+ botBtn +'</div></div></div>';
      return;
    }
    if(j && (j.status === 'expired' || j.status === 'cancelled' || j.status === 'rejected')){
      location.reload();
      return;
    }
  } catch(e){}
  setTimeout(pollStatus, 3500);
}

async function cancelPay(){
  if(!confirm('فاکتور لغو شود؟')) return;
  const fd = new FormData();
  fd.append('t', TOKEN);
  fd.append('action', 'cancel');
  try {
    await fetch(location.pathname + '?t='+encodeURIComponent(TOKEN), { method:'POST', body: fd });
  } catch(e){}
  location.reload();
}
</script>
<?php endif; ?>
</body>
</html>
