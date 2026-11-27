<?php


/**
 * تأیید فیش و ساخت/تمدید سرویس — مستقل از include کردن bot.php
 * منطق هم‌تراز با adm_app_ در ربات (نسخه محافظه‌کارانه)
 */
declare(strict_types=1);

if (is_readable(__DIR__ . '/reseller_lib.php')) {
    require_once __DIR__ . '/reseller_lib.php';
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

        $customerLabel = ($hasBought > 0 || $orderCount > 0)
            ? 'مشتری قبلی'
            : 'خرید اول / کاربر جدید';
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


if (!function_exists('serviceInfoChipRow')) {
    function remainingTimeChipLabel($daysTxt) {
        $d = trim((string)$daysTxt);
        if ($d === '') return '⏰ —';
        if (mb_strpos($d, 'منقضی') !== false) return '⏰ منقضی شده';
        if (mb_strpos($d, 'بدون انقضا') !== false || stripos($d, 'VIP') !== false) return '⏰ بدون انقضا';
        if (preg_match('/(\d+)\s*روز مانده/u', $d, $m)) return '⏰ ' . $m[1] . ' روز مانده';
        if (preg_match('/(\d+)\s*روز/u', $d, $m)) return '⏰ ' . $m[1] . ' روز';
        return '⏰ ' . (mb_strlen($d) > 40 ? mb_substr($d, 0, 37) . '…' : $d);
    }
    function remainingVolumeChipLabel($totalGb, $usedGb = 0) {
        $totalGb = (float)$totalGb;
        $usedGb = (float)$usedGb;
        if ($totalGb <= 0) return '📦 نامحدود';
        $remain = max(0.0, $totalGb - $usedGb);
        if ($totalGb <= 1.0 || $remain < 1.0) {
            $mb = round($remain * 1024, 1);
            if ($mb < 0.1) $mb = 0;
            $mbTxt = (abs($mb - (int)$mb) < 0.05) ? (string)(int)$mb : rtrim(rtrim(number_format($mb, 1, '.', ''), '0'), '.');
            return '📦 ' . $mbTxt . ' مگابایت مانده';
        }
        if (function_exists('formatVolumeGb')) {
            return '📦 ' . formatVolumeGb($remain) . ' مانده';
        }
        return '📦 ' . rtrim(rtrim(number_format($remain, 2, '.', ''), '0'), '.') . ' گیگ مانده';
    }
    function serviceInfoChipRow($timeLabel, $volumeLabel) {
        $t = trim((string)$timeLabel);
        $v = trim((string)$volumeLabel);
        if ($t === '') $t = '⏰ —';
        if ($v === '') $v = '📦 —';
        if (mb_strpos($t, '⏰') === false) $t = '⏰ ' . $t;
        if (mb_strpos($v, '📦') === false) $v = '📦 ' . $v;
        if (mb_strlen($t) > 60) $t = mb_substr($t, 0, 57) . '…';
        if (mb_strlen($v) > 60) $v = mb_substr($v, 0, 57) . '…';
        return [[['text' => $t, 'callback_data' => 'noop_status'], ['text' => $v, 'callback_data' => 'noop_status']]];
    }
}



function wa_setting(PDO $db, string $key, string $default = ''): string
{
    try {
        $st = $db->prepare('SELECT setting_val FROM settings WHERE setting_key = ?');
        $st->execute([$key]);
        $res = $st->fetchColumn();
        return $res !== false ? (string)$res : $default;
    } catch (Throwable $e) {
        return $default;
    }
}

/**
 * ۵٪ حجم اضافه برای اولین خرید دعوت‌شده (هم‌تراز ربات)
 */
function wa_invitee_volume(PDO $db, int $userId, float $vol): float
{
    if ($vol <= 0 || $userId <= 0) {
        return $vol;
    }
    try {
        $st = $db->prepare('SELECT inviter_id, has_bought FROM users WHERE user_id = ? LIMIT 1');
        $st->execute([$userId]);
        $u = $st->fetch(PDO::FETCH_ASSOC);
        if (!$u || empty($u['inviter_id']) || (int)$u['has_bought'] === 1) {
            return $vol;
        }
        $pct = (int)wa_setting($db, 'ref_invitee_vol_percent', '5');
        if ($pct < 1) {
            $pct = 5;
        }
        return round($vol * (1 + $pct / 100.0), 3);
    } catch (Throwable $e) {
        return $vol;
    }
}

/**
 * پاداش معرف: ۱۰٪ مبلغ فاکتور، سقف ۵۰٬۰۰۰ — فقط اولین خرید
 */
function wa_reward_referral(PDO $db, int $buyerId, int $purchasePrice = 0): void
{
    try {
        $st = $db->prepare('SELECT inviter_id, has_bought, username FROM users WHERE user_id = ? LIMIT 1');
        $st->execute([$buyerId]);
        $user = $st->fetch(PDO::FETCH_ASSOC);
        if ($user && (int)$user['has_bought'] === 0 && !empty($user['inviter_id'])) {
            $inviterId = (int)$user['inviter_id'];
            $pct = (int)wa_setting($db, 'ref_reward_percent', '10');
            $cap = (int)wa_setting($db, 'ref_reward_cap', '50000');
            if ($pct < 1) {
                $pct = 10;
            }
            if ($cap < 1000) {
                $cap = 50000;
            }
            if ($purchasePrice > 0) {
                $reward = (int)round($purchasePrice * $pct / 100.0);
            } else {
                $reward = (int)wa_setting($db, 'ref_reward', '20000');
            }
            $reward = max(0, min($reward, $cap));
            if ($reward > 0) {
                $okAdj = false;
                $ledger = dirname(WEBADMIN_ROOT) . '/wallet_ledger.php';
                if (is_readable($ledger)) {
                    require_once $ledger;
                    if (function_exists('adjustWalletBalance')) {
                        $adj = adjustWalletBalance($db, $inviterId, $reward, 'referral_reward', 'user', (string)$buyerId, 'پاداش دعوت وب');
                        $okAdj = !empty($adj['ok']);
                    }
                }
                if (!$okAdj) {
                    $db->prepare('UPDATE users SET balance = balance + ? WHERE user_id = ?')->execute([$reward, $inviterId]);
                    $okAdj = true;
                }
                if ($okAdj) {
                    try {
                        $db->prepare('UPDATE users SET total_ref_earned = total_ref_earned + ? WHERE user_id = ?')
                            ->execute([$reward, $inviterId]);
                    } catch (Throwable $e) {
                    }
                }
                $buyerName = (string)($user['username'] ?? '');
                $who = $buyerName !== '' ? '@' . ltrim($buyerName, '@') : ('کد ' . $buyerId);
                webadmin_tg('sendMessage', [
                    'chat_id' => $inviterId,
                    'text' => "🎉 <b>آفرین! پاداش دعوتت نشست</b>\n"
                        . "──────────────────\n"
                        . "{$who} اولین خریدش رو زد.\n\n"
                        . "💰 <b>" . number_format($reward) . " تومان</b> ({$pct}٪ خرید، سقف " . number_format($cap) . ")\n"
                        . "رفت تو کیف پولت — می‌تونی باهاش خرید آنی بزنی ⚡️",
                    'parse_mode' => 'HTML',
                ]);
            }
            $db->prepare('UPDATE users SET has_bought = 1 WHERE user_id = ?')->execute([$buyerId]);
        } else {
            $db->prepare('UPDATE users SET has_bought = 1 WHERE user_id = ?')->execute([$buyerId]);
        }
    } catch (Throwable $e) {
    }
}

function wa_plans(PDO $db): array
{
    try {
        $rows = $db->query('SELECT * FROM bot_plans')->fetchAll(PDO::FETCH_ASSOC);
        $out = [];
        foreach ($rows as $r) {
            $k = (string)($r['plan_key'] ?? '');
            if ($k === '') {
                continue;
            }
            // سازگاری نام ستون‌ها
            if (!isset($r['vol']) && isset($r['volume_gb'])) {
                $r['vol'] = $r['volume_gb'];
            }
            if (!isset($r['days']) && isset($r['day'])) {
                $r['days'] = $r['day'];
            }
            $out[$k] = $r;
        }
        return $out;
    } catch (Throwable $e) {
        return [];
    }
}

function wa_default_panel(PDO $db): array
{
    try {
        $row = $db->query('SELECT * FROM bot_panels WHERE is_default = 1 AND is_active = 1 ORDER BY id ASC LIMIT 1')->fetch(PDO::FETCH_ASSOC);
        if ($row) {
            return $row;
        }
        $row = $db->query('SELECT * FROM bot_panels WHERE is_active = 1 ORDER BY id ASC LIMIT 1')->fetch(PDO::FETCH_ASSOC);
        if ($row) {
            return $row;
        }
    } catch (Throwable $e) {
    }
    return [
        'id' => 0,
        'name' => 'config',
        'base_url' => defined('PANEL_URL') ? rtrim((string)PANEL_URL, '/') : '',
        'public_url' => defined('PANEL_URL') ? rtrim((string)PANEL_URL, '/') : '',
        'username' => defined('PANEL_USER') ? (string)PANEL_USER : '',
        'password' => defined('PANEL_PASS') ? (string)PANEL_PASS : '',
        'use_worker' => (defined('WORKER_URL') && WORKER_URL) ? 1 : 0,
        'is_default' => 1,
    ];
}

function wa_panel_by_id(PDO $db, int $id): array
{
    if ($id <= 0) {
        return wa_default_panel($db);
    }
    try {
        $st = $db->prepare('SELECT * FROM bot_panels WHERE id = ? LIMIT 1');
        $st->execute([$id]);
        $row = $st->fetch(PDO::FETCH_ASSOC);
        if ($row) {
            return $row;
        }
    } catch (Throwable $e) {
    }
    return wa_default_panel($db);
}

function wa_panel_from_plan(PDO $db, array $plan): array
{
    $pid = (int)($plan['panel_id'] ?? 0);
    return wa_panel_by_id($db, $pid);
}

function wa_panel_cache_key(array $panel): string
{
    $id = (int)($panel['id'] ?? 0);
    $base = rtrim((string)($panel['base_url'] ?? ''), '/');
    $user = (string)($panel['username'] ?? '');
    return $id . '|' . md5($base . '|' . $user);
}

function wa_panel_api_base(array $panel): string
{
    // اگر در این درخواست base موفقی داریم همان را برگردان
    $ck = wa_panel_cache_key($panel);
    if (!empty($GLOBALS['_wa_panel_last_base'][$ck])) {
        return rtrim((string)$GLOBALS['_wa_panel_last_base'][$ck], '/');
    }
    $useWorker = !empty($panel['use_worker']) || (!empty($panel['is_default']) && defined('WORKER_URL') && WORKER_URL);
    if ($useWorker && defined('WORKER_URL') && WORKER_URL) {
        $base = rtrim((string)($panel['base_url'] ?? ''), '/');
        $cfg = defined('PANEL_URL') ? rtrim((string)PANEL_URL, '/') : '';
        if ($base === '' || $base === $cfg || !empty($panel['is_default'])) {
            return rtrim((string)WORKER_URL, '/') . '/panel';
        }
    }
    $base = rtrim((string)($panel['base_url'] ?? ''), '/');
    if ($base === '' && defined('PANEL_URL')) {
        $base = rtrim((string)PANEL_URL, '/');
    }
    return $base;
}

function wa_panel_public_base(array $panel): string
{
    if (!empty($panel['public_url'])) {
        return rtrim((string)$panel['public_url'], '/');
    }
    if (!empty($panel['base_url'])) {
        return rtrim((string)$panel['base_url'], '/');
    }
    return defined('PANEL_URL') ? rtrim((string)PANEL_URL, '/') : '';
}

/** لیست base: آخرین موفق (settings) → مستقیم → Worker */
function wa_panel_bases_list(array $panel, ?PDO $db = null): array
{
    $direct = rtrim((string)($panel['base_url'] ?? ''), '/');
    if ($direct === '' && defined('PANEL_URL')) {
        $direct = rtrim((string)PANEL_URL, '/');
    }
    $worker = '';
    if (defined('WORKER_URL') && WORKER_URL) {
        $worker = rtrim((string)WORKER_URL, '/') . '/panel';
    }

    $ck = 'panel_last_base_' . wa_panel_cache_key($panel);
    $last = '';
    if (!empty($GLOBALS['_wa_panel_last_base'][$ck])) {
        $last = (string)$GLOBALS['_wa_panel_last_base'][$ck];
    }
    if ($last === '' && $db instanceof PDO) {
        try {
            $last = trim(wa_setting($db, $ck, ''));
        } catch (Throwable $e) {
            $last = '';
        }
    }
    // کلید کوتاه‌تر هم امتحان (سازگار با ربات اگر همان DB باشد)
    if ($last === '' && $db instanceof PDO) {
        try {
            // ربات: panel_last_base_{id}|md5...
            $rows = $db->query("SELECT setting_val FROM settings WHERE setting_key LIKE 'panel_last_base_%' ORDER BY setting_key DESC LIMIT 5")->fetchAll(PDO::FETCH_COLUMN);
            foreach ($rows as $v) {
                $v = trim((string)$v);
                if ($v !== '') {
                    $last = $v;
                    break;
                }
            }
        } catch (Throwable $e) {
        }
    }

    $bases = [];
    if ($last !== '') {
        $bases[] = rtrim($last, '/');
    }
    if ($direct !== '' && !in_array($direct, $bases, true)) {
        $bases[] = $direct;
    }
    if ($worker !== '' && !in_array($worker, $bases, true)) {
        $bases[] = $worker;
    }
    $legacy = rtrim(wa_panel_api_base($panel), '/');
    if ($legacy !== '' && !in_array($legacy, $bases, true)) {
        $bases[] = $legacy;
    }
    return array_values(array_filter($bases));
}

function wa_remember_panel_base(array $panel, string $base, ?PDO $db = null): void
{
    $base = rtrim($base, '/');
    if ($base === '') {
        return;
    }
    $ck = 'panel_last_base_' . wa_panel_cache_key($panel);
    $GLOBALS['_wa_panel_last_base'][$ck] = $base;
    // short key for api_base helper
    $GLOBALS['_wa_panel_last_base'][wa_panel_cache_key($panel)] = $base;
    if ($db instanceof PDO) {
        try {
            wa_set_setting($db, $ck, $base);
        } catch (Throwable $e) {
        }
    } elseif (isset($GLOBALS['db']) && $GLOBALS['db'] instanceof PDO) {
        try {
            wa_set_setting($GLOBALS['db'], $ck, $base);
        } catch (Throwable $e) {
        }
    }
}

function wa_panel_token_once(string $apiBase, string $user, string $pass, int $timeout = 12): array
{
    $url = rtrim($apiBase, '/') . '/api/admin/token';
    if ($apiBase === '' || $user === '') {
        return ['token' => null, 'http' => 0, 'error' => 'empty_base_or_user', 'url' => $url];
    }
    $timeout = max(3, min(20, $timeout));
    $ch = curl_init();
    $opts = [
        CURLOPT_URL => $url,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => http_build_query(['username' => $user, 'password' => $pass]),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Content-Type: application/x-www-form-urlencoded'],
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_TIMEOUT => $timeout,
        CURLOPT_CONNECTTIMEOUT => min(5, $timeout),
        CURLOPT_FOLLOWLOCATION => true,
    ];
    if (defined('CURL_IPRESOLVE_V4')) {
        $opts[CURLOPT_IPRESOLVE] = CURL_IPRESOLVE_V4;
    }
    curl_setopt_array($ch, $opts);
    $res = curl_exec($ch);
    $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $cerr = curl_error($ch);
    curl_close($ch);
    $decoded = json_decode((string)$res, true);
    $token = is_array($decoded) ? ($decoded['access_token'] ?? $decoded['token'] ?? null) : null;
    return [
        'token' => $token ?: null,
        'http' => $http,
        'error' => $cerr ?: null,
        'url' => $url,
        'body' => mb_substr((string)$res, 0, 200),
    ];
}

/**
 * توکن هوشمند مثل ربات: آخرین base موفق → مستقیم → Worker + کش ۱۰ دقیقه‌ای
 * @return array{token:?string,debug:string,api_base:?string}
 */
function wa_panel_token_ex(array $panel, ?PDO $db = null): array
{
    $user = (string)($panel['username'] ?? (defined('PANEL_USER') ? PANEL_USER : ''));
    $pass = (string)($panel['password'] ?? (defined('PANEL_PASS') ? PANEL_PASS : ''));
    $ck = wa_panel_cache_key($panel);

    if (!empty($GLOBALS['_wa_panel_token_cache'][$ck])) {
        $ent = $GLOBALS['_wa_panel_token_cache'][$ck];
        if (!empty($ent['token']) && !empty($ent['exp']) && (int)$ent['exp'] > time()) {
            if (!empty($ent['base'])) {
                wa_remember_panel_base($panel, (string)$ent['base'], $db);
            }
            return [
                'token' => $ent['token'],
                'debug' => 'cache_hit',
                'api_base' => $ent['base'] ?? null,
            ];
        }
    }

    if ($user === '') {
        return ['token' => null, 'debug' => 'empty_user', 'api_base' => null];
    }

    $bases = wa_panel_bases_list($panel, $db ?? ($GLOBALS['db'] ?? null));
    $fast = !empty($GLOBALS['wa_panel_fast']);
    $tokTimeout = $fast ? 5 : 12;
    $maxTries = $fast ? 1 : 2;
    $maxBases = $fast ? 2 : 6;
    $debugParts = [];
    $nBase = 0;
    foreach ($bases as $base) {
        if ($nBase >= $maxBases) {
            break;
        }
        $nBase++;
        for ($try = 1; $try <= $maxTries; $try++) {
            $r = wa_panel_token_once($base, $user, $pass, $tokTimeout);
            $debugParts[] = sprintf('try%d %s http=%d err=%s', $try, $r['url'], (int)$r['http'], (string)($r['error'] ?? '-'));
            if (!empty($r['token'])) {
                wa_remember_panel_base($panel, $base, $db ?? ($GLOBALS['db'] ?? null));
                $GLOBALS['_wa_panel_token_cache'][$ck] = [
                    'token' => $r['token'],
                    'base' => rtrim($base, '/'),
                    'exp' => time() + 600,
                ];
                return [
                    'token' => $r['token'],
                    'debug' => implode(' | ', $debugParts),
                    'api_base' => rtrim($base, '/'),
                ];
            }
            if ($try < $maxTries) {
                usleep($fast ? 50000 : 150000);
            }
        }
    }
    return ['token' => null, 'debug' => implode(' | ', $debugParts), 'api_base' => null];
}

function wa_panel_token(array $panel): ?string
{
    $ex = wa_panel_token_ex($panel, $GLOBALS['db'] ?? null);
    return $ex['token'];
}

function wa_panel_error_username_taken(string $detail): bool
{
    $d = mb_strtolower($detail);
    return (strpos($d, 'already exists') !== false
        || strpos($d, 'user exists') !== false
        || strpos($d, 'duplicate') !== false
        || strpos($d, 'وجود دارد') !== false
        || strpos($d, 'تکراری') !== false);
}

function wa_create_panel_user_once(string $username, float $volumeGb, int $days, array $panel, PDO $db): array
{
    $tok = wa_panel_token_ex($panel, $db);
    $token = $tok['token'];
    $apiBase = $tok['api_base'] ?? null;
    if (!$token || !$apiBase) {
        return ['_error' => 'token_failed', 'detail' => $tok['debug'] ?? ''];
    }
    $url = rtrim($apiBase, '/') . '/api/user';
    $days = (int)$days;
    $dataLimitBytes = (int)round($volumeGb * 1024 * 1024 * 1024);
    $groupIds = [];
    $raw = wa_setting($db, 'pasargad_group_ids', '');
    if ($raw !== '') {
        $groupIds = array_values(array_filter(array_map('intval', explode(',', $raw)), static function ($v) {
            return $v > 0;
        }));
    }
    $payload = [
        'username' => $username,
        'data_limit' => $dataLimitBytes,
        'proxies' => [
            'vless' => new stdClass(),
            'vmess' => new stdClass(),
            'trojan' => new stdClass(),
            'shadowsocks' => new stdClass(),
        ],
        'inbounds' => new stdClass(),
    ];
    if ($days > 0) {
        $payload['status'] = 'on_hold';
        $payload['expire'] = 0;
        $payload['on_hold_expire_duration'] = $days * 86400;
        // بدون on_hold_timeout — حذف خودکار پس از ۹۰ روز اعمال نمی‌شود
    } else {
        $payload['expire'] = 0;
    }
    if ($groupIds) {
        $payload['group_ids'] = $groupIds;
    }
    $ch = curl_init();
    $opts = [
        CURLOPT_URL => $url,
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Content-Type: application/json'],
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
    $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $cerr = curl_error($ch);
    curl_close($ch);
    $decoded = json_decode((string)$res, true);
    if (!is_array($decoded) || $http >= 400) {
        $detail = $cerr ?: mb_substr((string)$res, 0, 400);
        if (is_array($decoded)) {
            $m = $decoded['detail'] ?? $decoded['message'] ?? null;
            if ($m !== null) {
                $detail = is_array($m) ? json_encode($m, JSON_UNESCAPED_UNICODE) : (string)$m;
            }
        }
        return ['_error' => 'create_failed', 'http' => $http, 'detail' => $detail];
    }
    return $decoded;
}

/** نام‌های نزدیک به درخواست (bahram → bahram1, bahram123, …) */
function wa_build_username_candidates(string $preferredUsername, int $userId = 0): array
{
    $preferredUsername = preg_replace('/[^a-zA-Z0-9_\-\.]/', '', $preferredUsername) ?? '';
    $uid = max(1, $userId);
    if ($preferredUsername === '' || preg_match('/^user_\d+_\d+$/', $preferredUsername)) {
        $out = [];
        for ($i = 0; $i < 8; $i++) {
            $out[] = 'user_' . $uid . '_' . random_int(1000, 9999);
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
        $candidates[] = 'user_' . $uid . '_' . random_int(1000, 9999);
    }
    $out = [];
    foreach ($candidates as $c) {
        $c = preg_replace('/[^a-zA-Z0-9_\-\.]/', '', (string)$c) ?? '';
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

/** ساخت کاربر؛ در صورت تکراری بودن نام، نام نزدیک به درخواست می‌سازد */
function wa_create_panel_user(string $username, float $volumeGb, int $days, array $panel, PDO $db, int $userId = 0): array
{
    $candidates = wa_build_username_candidates($username, $userId);
    $last = ['_error' => 'no_attempt', 'detail' => 'نام خالی'];
    foreach ($candidates as $uname) {
        try {
            $st = $db->prepare('SELECT id FROM orders WHERE config_username = ? LIMIT 1');
            $st->execute([$uname]);
            if ($st->fetch()) {
                continue;
            }
        } catch (Throwable $e) {
        }
        $res = wa_create_panel_user_once($uname, $volumeGb, $days, $panel, $db);
        if (empty($res['_error'])) {
            $res['_final_username'] = $uname;
            return $res;
        }
        $last = $res;
        if (!wa_panel_error_username_taken((string)($res['detail'] ?? ''))) {
            $last['_final_username'] = $uname;
            return $last;
        }
    }
    $last['_final_username'] = (string)($candidates[0] ?? $username);
    return $last;
}

function wa_parse_expire($value): int
{
    if ($value === null || $value === '' || $value === false) {
        return 0;
    }
    if (is_numeric($value)) {
        $n = (float)$value;
        if ($n > 1e12) {
            return (int)floor($n / 1000);
        }
        return (int)$n;
    }
    $ts = strtotime((string)$value);
    return $ts !== false ? (int)$ts : 0;
}

function wa_panel_curl_opts(int $timeout = 10): array
{
    $opts = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_SSL_VERIFYHOST => 0,
        CURLOPT_TIMEOUT => $timeout,
        CURLOPT_CONNECTTIMEOUT => min(6, $timeout),
        CURLOPT_FOLLOWLOCATION => true,
    ];
    if (defined('CURL_IPRESOLVE_V4')) {
        $opts[CURLOPT_IPRESOLVE] = CURL_IPRESOLVE_V4;
    }
    return $opts;
}

/**
 * توکن با کش درخواست + api_base واقعی که توکن از آن گرفته شد
 * @return array{token:?string,api_base:?string,debug:string}
 */
function wa_panel_token_cached(array $panel): array
{
    static $cache = [];
    $key = md5(json_encode([
        $panel['id'] ?? 0,
        $panel['base_url'] ?? '',
        $panel['username'] ?? '',
    ]));
    if (!empty($cache[$key]['token']) && !empty($cache[$key]['exp']) && $cache[$key]['exp'] > time()) {
        return $cache[$key];
    }
    $ex = wa_panel_token_ex($panel, $GLOBALS['db'] ?? null);
    $out = [
        'token' => $ex['token'] ?? null,
        'api_base' => $ex['api_base'] ?? null,
        'debug' => (string)($ex['debug'] ?? ''),
        'exp' => time() + 600,
    ];
    if (!empty($out['token'])) {
        $cache[$key] = $out;
    }
    return $out;
}

function wa_get_panel_user_ex(string $username, string $token, string $apiBase): ?array
{
    $url = rtrim($apiBase, '/') . '/api/user/' . rawurlencode($username);
    $ch = curl_init();
    $to = !empty($GLOBALS['wa_panel_fast']) ? 5 : 10;
    $opts = wa_panel_curl_opts($to);
    $opts[CURLOPT_URL] = $url;
    $opts[CURLOPT_HTTPHEADER] = ['Authorization: Bearer ' . $token, 'Accept: application/json'];
    curl_setopt_array($ch, $opts);
    $res = curl_exec($ch);
    $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($http === 404) {
        return null;
    }
    $decoded = json_decode((string)$res, true);
    return is_array($decoded) && empty($decoded['detail']) ? $decoded : (is_array($decoded) ? $decoded : null);
}

function wa_get_panel_user(string $username, array $panel): ?array
{
    $tok = wa_panel_token_cached($panel);
    if (empty($tok['token']) || empty($tok['api_base'])) {
        return null;
    }
    return wa_get_panel_user_ex($username, $tok['token'], $tok['api_base']);
}

/**
 * تمدید/افزایش حجم و روز — یک بار توکن، همان base برای GET و PUT
 * @return array{ok:bool,error?:string,detail?:string,volume_gb?:float,expire?:int,raw?:mixed}
 */
function wa_renew_panel_user(string $username, float $volumeGb, int $days, array $panel): array
{
    $tok = wa_panel_token_cached($panel);
    $token = $tok['token'] ?? null;
    $apiBase = $tok['api_base'] ?? null;
    if (!$token || !$apiBase) {
        return ['ok' => false, 'error' => 'token_failed', 'detail' => $tok['debug'] ?? 'توکن پنل گرفته نشد'];
    }

    $current = wa_get_panel_user_ex($username, $token, $apiBase);
    $hasCurrent = is_array($current) && (isset($current['username']) || isset($current['data_limit']) || isset($current['expire']));

    // اگر فقط روز می‌دهیم و وضعیت فعلی را نخواندیم → فقط expire را با time+days بفرست، data_limit را دست نزن
    // اگر حجم می‌دهیم و current نداریم → خطا (تا سقف صفر نشود)
    if ($volumeGb > 0 && !$hasCurrent) {
        return [
            'ok' => false,
            'error' => 'user_not_found',
            'detail' => 'کاربر در پنل پیدا نشد؛ نمی‌توان حجم را بدون وضعیت فعلی اضافه کرد.',
        ];
    }

    $panelStatus = $hasCurrent ? (string)($current['status'] ?? 'active') : 'active';
    $holdDur = $hasCurrent ? (int)($current['on_hold_expire_duration'] ?? 0) : 0;
    $payload = [];
    $newVolGb = null;

    $remainingBeforeGb = 0.0;
    $volumeCycleGb = null;
    if ($hasCurrent && $volumeGb > 0) {
        $used = (float)($current['used_traffic'] ?? 0);
        $oldLimit = (float)($current['data_limit'] ?? 0);
        if ($oldLimit > 0) {
            $remainingBeforeGb = max(0.0, ($oldLimit - $used) / (1024 * 1024 * 1024));
        }
        $addBytes = (float)round($volumeGb * 1024 * 1024 * 1024);
        $newLimit = ($oldLimit <= 0) ? (int)round($addBytes) : (int)round($oldLimit + $addBytes);
        $payload['data_limit'] = $newLimit;
        $newVolGb = round($newLimit / (1024 * 1024 * 1024), 3);
        // ظرفیت دوره نمایش برای اپ = مانده قبل تمدید + بسته جدید
        $volumeCycleGb = round($remainingBeforeGb + (float)$volumeGb, 3);
    } elseif ($hasCurrent && $volumeGb <= 0) {
        $oldLimit = (float)($current['data_limit'] ?? 0);
        $used = (float)($current['used_traffic'] ?? 0);
        if ($oldLimit > 0) {
            $remainingBeforeGb = max(0.0, ($oldLimit - $used) / (1024 * 1024 * 1024));
        }
        $newVolGb = $oldLimit > 0 ? round($oldLimit / (1024 * 1024 * 1024), 3) : 0.0;
    }

    if ($days > 0 && $panelStatus === 'on_hold') {
        $payload['status'] = 'on_hold';
        $payload['expire'] = 0;
        $payload['on_hold_expire_duration'] = max(0, $holdDur) + ($days * 86400);
    } elseif ($days > 0) {
        $currentExpire = $hasCurrent ? wa_parse_expire($current['expire'] ?? 0) : 0;
        $baseTime = ($currentExpire > time()) ? $currentExpire : time();
        $payload['expire'] = $baseTime + ($days * 86400);
        $payload['status'] = 'active';
    } elseif ($hasCurrent) {
        $payload['status'] = ($panelStatus === 'on_hold') ? 'on_hold' : 'active';
        $currentExpire = wa_parse_expire($current['expire'] ?? 0);
        if ($currentExpire > 0) {
            $payload['expire'] = $currentExpire;
        }
    } else {
        $payload['status'] = 'active';
    }

    $editUrl = rtrim($apiBase, '/') . '/api/user/' . rawurlencode($username);
    $ch = curl_init($editUrl);
    $opts = wa_panel_curl_opts(12);
    $opts[CURLOPT_CUSTOMREQUEST] = 'PUT';
    $opts[CURLOPT_POSTFIELDS] = json_encode($payload);
    $opts[CURLOPT_HTTPHEADER] = [
        'Authorization: Bearer ' . $token,
        'Content-Type: application/json',
        'Accept: application/json',
    ];
    curl_setopt_array($ch, $opts);
    $res = curl_exec($ch);
    $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $cerr = curl_error($ch);
    curl_close($ch);
    $decoded = json_decode((string)$res, true);

    $ok = $http >= 200 && $http < 300 && is_array($decoded) && empty($decoded['detail']);
    // بعضی پنل‌ها body خالی با 200 می‌دهند
    if (!$ok && $http >= 200 && $http < 300 && ($res === '' || $res === false || $decoded === null)) {
        $ok = ($cerr === '');
    }

    if (!$ok) {
        $detail = is_array($decoded) ? ($decoded['detail'] ?? json_encode($decoded, JSON_UNESCAPED_UNICODE)) : ($cerr ?: substr((string)$res, 0, 200));
        if (is_array($detail)) {
            $detail = json_encode($detail, JSON_UNESCAPED_UNICODE);
        }
        return ['ok' => false, 'error' => 'panel_put_failed', 'detail' => (string)$detail, 'http' => $http, 'raw' => $decoded];
    }

    return [
        'ok' => true,
        'volume_gb' => $newVolGb,
        'expire' => $payload['expire'] ?? null,
        'remaining_bytes' => (int)round($remainingBeforeGb * 1024 * 1024 * 1024),
        'remaining_before_gb' => round($remainingBeforeGb, 3),
        'volume_cycle_gb' => $volumeCycleGb,
        'raw' => $decoded,
        'api_base' => $apiBase,
    ];
}

function wa_approve_payment(PDO $db, int $paymentId): array
{
    $st = $db->prepare("SELECT * FROM payments WHERE id = ? LIMIT 1");
    $st->execute([$paymentId]);
    $pay = $st->fetch(PDO::FETCH_ASSOC);
    if (!$pay) {
        return ['ok' => false, 'error' => 'فیش یافت نشد.'];
    }
    if (($pay['status'] ?? '') !== 'pending') {
        return ['ok' => false, 'error' => 'این فیش دیگر در انتظار نیست.'];
    }

    $action = (string)($pay['action_type'] ?? '');
    $uid = (int)$pay['user_id'];

    // ——— شارژ اعتبار نمایندگی ———
        if ($action === 'reseller_deposit' || strtolower((string)($pay['target_username'] ?? '')) === 'reseller_wallet') {
        $creditAmount = (is_numeric($pay['plan_key']) && (int)$pay['plan_key'] > 0)
            ? (int)$pay['plan_key']
            : (int)$pay['price'];
        // اول شارژ اتمیک؛ فقط در صورت موفقیت فاکتور approved می‌شود
        if (!function_exists('reseller_credit_from_payment')) {
            return ['ok' => false, 'error' => 'reseller_credit_unavailable'];
        }
        $rc = reseller_credit_from_payment($db, $pay);
        if (empty($rc['ok'])) {
            return ['ok' => false, 'error' => 'شارژ اعتبار ناموفق: ' . (string)($rc['error'] ?? 'unknown')];
        }
        $upd = $db->prepare("UPDATE payments SET status = 'approved' WHERE id = ? AND status = 'pending'");
        $upd->execute([$paymentId]);
        // اگر قبلاً approved شده بود (مسابقه) ولی شارژ duplicate بود، ok است
        $bal = (int)($rc['balance'] ?? 0);
        $pay['status'] = 'approved';
        if (function_exists('webadmin_tg')) {
            webadmin_tg('sendMessage', [
                'chat_id' => $uid,
                'text' => "✅ اعتبار نمایندگی شارژ شد

مبلغ: <b>" . number_format($creditAmount) . " تومان</b>
موجودی: <b>" . number_format($bal) . " تومان</b>",
                'parse_mode' => 'HTML',
            ]);
        }
        return ['ok' => true, 'type' => 'reseller_deposit', 'amount' => $creditAmount, 'balance' => $bal, 'duplicate' => !empty($rc['duplicate'])];
    }// ——— شارژ کیف ———
    if ($action === 'deposit') {
        $creditAmount = (is_numeric($pay['plan_key']) && (int)$pay['plan_key'] > 0)
            ? (int)$pay['plan_key']
            : (int)$pay['price'];
        $db->beginTransaction();
        try {
            $db->prepare("UPDATE payments SET status = 'approved' WHERE id = ? AND status = 'pending'")->execute([$paymentId]);
            $db->prepare('UPDATE users SET balance = balance + ? WHERE user_id = ?')->execute([$creditAmount, $uid]);
            $db->commit();
        } catch (Throwable $e) {
            if ($db->inTransaction()) {
                $db->rollBack();
            }
            return ['ok' => false, 'error' => $e->getMessage()];
        }
        $ledger = dirname(WEBADMIN_ROOT) . '/wallet_ledger.php';
        $acc = dirname(WEBADMIN_ROOT) . '/accounting.php';
        if (is_readable($ledger)) {
            require_once $ledger;
        }
        if (is_readable($acc)) {
            require_once $acc;
            if (function_exists('recordAccountingFromPayment')) {
                $pay['status'] = 'approved';
                try {
                    recordAccountingFromPayment($db, $pay, 'webadmin');
                } catch (Throwable $e) {
                }
            }
        }
        webadmin_tg('sendMessage', [
            'chat_id' => $uid,
            'text' => "✅ کیف پولت شارژ شد 💰\n\nمبلغ: <b>" . number_format($creditAmount) . " تومان</b>\nحالا می‌تونی خرید آنی بزنی ⚡️",
            'parse_mode' => 'HTML',
        ]);
        return ['ok' => true, 'msg' => 'شارژ کیف پول تأیید شد (' . number_format($creditAmount) . ' تومان).'];
    }

    // ——— خرید / تمدید ———
    $plans = wa_plans($db);
    $planKey = (string)($pay['plan_key'] ?? '');
    if ($planKey === '' || empty($plans[$planKey])) {
        return ['ok' => false, 'error' => 'پلن «' . $planKey . '» در bot_plans پیدا نشد.'];
    }
    $p = $plans[$planKey];
    $volBase = (float)($p['vol'] ?? $p['volume_gb'] ?? 0);
    $vol = wa_invitee_volume($db, $uid, $volBase);
    $days = (int)($p['days'] ?? 0);
    $title = (string)($p['title'] ?? $planKey);
    $targetUser = (string)($pay['target_username'] ?? '');
    if ($targetUser === '') {
        return ['ok' => false, 'error' => 'نام کانفیگ (target_username) خالی است.'];
    }

    if (!empty($pay['coupon_code'])) {
        try {
            $db->prepare('UPDATE coupons SET used_count = used_count + 1 WHERE code = ?')->execute([(string)$pay['coupon_code']]);
        } catch (Throwable $e) {
        }
    }

    $panel = wa_panel_from_plan($db, $p);
    $payPrice = (int)($pay['price'] ?? 0);

    if ($action === 'renew') {
        $ren = wa_renew_panel_user($targetUser, $vol, $days, $panel);
        if (empty($ren['ok'])) {
            $extra = !empty($ren['detail']) ? (' — ' . $ren['detail']) : (!empty($ren['error']) ? (' — ' . $ren['error']) : '');
            return ['ok' => false, 'error' => 'تمدید در پنل ناموفق بود' . $extra];
        }
        $newVol = $ren['volume_gb'] ?? $vol;
        $daysStore = (int)$days;
        if ($daysStore > 0 && !empty($ren['expire']) && (int)$ren['expire'] > time()) {
            $daysStore = max($daysStore, (int)ceil(((int)$ren['expire'] - time()) / 86400));
        }
        try {
            try { $db->exec('ALTER TABLE orders ADD COLUMN last_renew_gb DOUBLE NULL DEFAULT NULL'); } catch (Throwable $eCol) {}
            try { $db->exec('ALTER TABLE orders ADD COLUMN volume_cycle_gb DOUBLE NULL DEFAULT NULL'); } catch (Throwable $eCol2) {}
            $cycleGb = null;
            if (is_array($ren) && isset($ren['volume_cycle_gb']) && (float)$ren['volume_cycle_gb'] > 0) {
                $cycleGb = (float)$ren['volume_cycle_gb'];
            } elseif (is_array($ren) && isset($ren['remaining_before_gb'])) {
                $cycleGb = round(max(0.0, (float)$ren['remaining_before_gb']) + (float)$vol, 3);
            } else {
                $cycleGb = round((float)$vol, 3);
            }
            try {
                $db->prepare('UPDATE orders SET volume_gb = ?, days = ?, last_renew_gb = ?, volume_cycle_gb = ?, warned_volume = 0, warned_expire = 0 WHERE config_username = ?')
                    ->execute([$newVol, $daysStore, (float)$vol, $cycleGb, $targetUser]);
            } catch (Throwable $eCycle) {
                $db->prepare('UPDATE orders SET volume_gb = ?, days = ?, last_renew_gb = ?, warned_volume = 0, warned_expire = 0 WHERE config_username = ?')
                    ->execute([$newVol, $daysStore, (float)$vol, $targetUser]);
            }
        } catch (Throwable $e) {
            try {
                $db->prepare('UPDATE orders SET volume_gb = ?, days = ?, warned_volume = 0, warned_expire = 0 WHERE config_username = ?')
                    ->execute([$newVol, $daysStore, $targetUser]);
            } catch (Throwable $e2) {
                $db->prepare('UPDATE orders SET volume_gb = ?, days = ? WHERE config_username = ?')
                    ->execute([$newVol, $daysStore, $targetUser]);
            }
        }
        $db->prepare("UPDATE payments SET status = 'approved' WHERE id = ?")->execute([$paymentId]);
        $acc = dirname(WEBADMIN_ROOT) . '/accounting.php';
        if (is_readable($acc)) {
            require_once $acc;
            if (function_exists('recordAccountingFromPayment')) {
                $pay['status'] = 'approved';
                try {
                    recordAccountingFromPayment($db, $pay, 'webadmin');
                } catch (Throwable $e) {
                }
            }
        }
        wa_reward_referral($db, $uid, $payPrice);
        webadmin_tg('sendMessage', [
            'chat_id' => $uid,
            'text' => "✅ <b>تمدید انجام شد!</b>\n\nسرویس: <code>{$targetUser}</code>\nحجم کل: {$newVol} گیگ\n\nتو اپ یک‌بار <b>Update Sub / Refresh</b> بزن 🚀",
            'parse_mode' => 'HTML',
        ]);
        return ['ok' => true, 'msg' => 'تمدید تأیید و در پنل اعمال شد.'];
    }

    // new (و سایر غیر deposit/renew)
    $existOrd = $db->prepare('SELECT * FROM orders WHERE config_username = ? ORDER BY id DESC LIMIT 1');
    $existOrd->execute([$targetUser]);
    $existRow = $existOrd->fetch(PDO::FETCH_ASSOC);

    if ($existRow) {
        $exPk = strtolower(trim((string)($existRow['plan_key'] ?? '')));
        $exCn = strtolower(trim((string)($existRow['config_username'] ?? '')));
        $isTestOrd = ($exPk === 'test_free' || strpos($exPk, 'test') !== false || strpos($exCn, 'test_') === 0
            || ((float)($existRow['volume_gb'] ?? 0) > 0 && (float)($existRow['volume_gb'] ?? 0) <= 0.2 && (int)($existRow['days'] ?? 0) <= 3));

        if (!$isTestOrd) {
            $subUrl = (string)($existRow['sub_link'] ?? '');
            $orderPassword = (string)($existRow['password'] ?? '');
            $dupMsg = "✅ این سرویس از قبل فعاله؛ فیش تکراری بسته شد.\n\n👤 نام کاربری: <code>{$targetUser}</code>\n";
            if ($orderPassword !== '') {
                $dupMsg .= "🔑 رمز اپ: <code>{$orderPassword}</code>\n";
            }
            if ($subUrl !== '') {
                $dupMsg .= "🔗 لینک:\n<code>{$subUrl}</code>";
            }
            $db->prepare("UPDATE payments SET status = 'approved' WHERE id = ?")->execute([$paymentId]);
            webadmin_tg('sendMessage', [
                'chat_id' => $uid,
                'text' => $dupMsg,
                'parse_mode' => 'HTML',
            ]);
            return ['ok' => true, 'msg' => 'سرویس از قبل وجود داشت؛ فیش تأیید شد.'];
        }

        // تبدیل تست → پلن واقعی: حذف تست پنل و ساخت با حجم/روز پلن خریداری‌شده
        try { wa_delete_panel_user($targetUser, $panel); } catch (Throwable $e) {}
        $res = wa_create_panel_user($targetUser, $vol, $days, $panel, $db, $uid);
        if (!empty($res['_error'])) {
            return ['ok' => false, 'error' => 'ارتقا تست به پلن واقعی ناموفق: ' . ($res['detail'] ?? $res['_error'])];
        }
        $targetUser = (string)($res['_final_username'] ?? $targetUser);
        $subUrl = (string)($res['subscription_url'] ?? '');
        if ($subUrl !== '' && strpos($subUrl, 'http') !== 0) {
            $subUrl = rtrim(wa_panel_public_base($panel), '/') . '/' . ltrim($subUrl, '/');
        }
        $orderPassword = (string)($existRow['password'] ?? '');
        if ($orderPassword === '') {
            $orderPassword = (string)random_int(1000, 9999);
        }
        $panelId = (int)($panel['id'] ?? 0);
        $pCat = strtolower(trim((string)($p['cat'] ?? '')));
        if ($pCat === '') {
            $pCat = ($days === 0) ? 'vip' : 'monthly';
        }
        try {
            try { $db->exec('ALTER TABLE orders ADD COLUMN volume_cycle_gb DOUBLE NULL DEFAULT NULL'); } catch (Throwable $eCol) {}
            try {
                $db->prepare('UPDATE orders SET volume_gb = ?, days = ?, sub_link = ?, panel_id = ?, plan_key = ?, cat = ?, last_renew_gb = ?, volume_cycle_gb = ?, warned_volume = 0, warned_expire = 0 WHERE id = ?')
                   ->execute([$vol, $days, $subUrl, $panelId > 0 ? $panelId : null, $planKey, $pCat, (float)$vol, (float)$vol, (int)$existRow['id']]);
            } catch (Throwable $eUp) {
                $db->prepare('UPDATE orders SET volume_gb = ?, days = ?, sub_link = ?, panel_id = ?, plan_key = ?, cat = ?, warned_volume = 0, warned_expire = 0 WHERE id = ?')
                   ->execute([$vol, $days, $subUrl, $panelId > 0 ? $panelId : null, $planKey, $pCat, (int)$existRow['id']]);
            }
        } catch (Throwable $e) {
            try {
                $db->prepare('UPDATE orders SET volume_gb = ?, days = ?, sub_link = ? WHERE id = ?')
                   ->execute([$vol, $days, $subUrl, (int)$existRow['id']]);
            } catch (Throwable $e2) {}
        }
        try {
            $db->prepare('UPDATE payments SET target_username = ? WHERE id = ?')->execute([$targetUser, $paymentId]);
        } catch (Throwable $e) {}
        $db->prepare("UPDATE payments SET status = 'approved' WHERE id = ?")->execute([$paymentId]);
        try {
            $db->prepare('UPDATE users SET has_bought = 1 WHERE user_id = ?')->execute([$uid]);
        } catch (Throwable $e) {}
        $acc = dirname(WEBADMIN_ROOT) . '/accounting.php';
        if (is_readable($acc)) {
            require_once $acc;
            if (function_exists('recordAccountingFromPayment')) {
                $pay['status'] = 'approved';
                try { recordAccountingFromPayment($db, $pay, 'webadmin'); } catch (Throwable $e) {}
            }
        }
        wa_reward_referral($db, $uid, $payPrice);
        $approveMsg = "🎉 <b>پرداختت تایید شد — اشتراکت آماده‌ست!</b>\n\n"
            . "👤 نام کاربری: <code>{$targetUser}</code>\n"
            . "🔑 رمز اپ: <code>{$orderPassword}</code>\n"
            . "📦 پلن: {$title}\n";
        if ($subUrl !== '') {
            $approveMsg .= "🔗 لینک:\n<code>{$subUrl}</code>\n\n";
        }
        $approveMsg .= "تو اپ یک‌بار بروزرسانی سابسکریپشن بزن 🚀";
        webadmin_tg('sendMessage', [
            'chat_id' => $uid,
            'text' => $approveMsg,
            'parse_mode' => 'HTML',
        ]);
        return ['ok' => true, 'msg' => 'تست به پلن واقعی ارتقا یافت و فیش تأیید شد.'];
    }

    $res = wa_create_panel_user($targetUser, $vol, $days, $panel, $db, $uid);
    if (!empty($res['_error'])) {
        return ['ok' => false, 'error' => 'ساخت در پنل ناموفق: ' . ($res['detail'] ?? $res['_error'])];
    }
    $targetUser = (string)($res['_final_username'] ?? $targetUser);
    try {
        $db->prepare('UPDATE payments SET target_username = ? WHERE id = ?')->execute([$targetUser, $paymentId]);
    } catch (Throwable $e) {
    }
    $subUrl = (string)($res['subscription_url'] ?? '');
    if ($subUrl !== '' && strpos($subUrl, 'http') !== 0) {
        $subUrl = rtrim(wa_panel_public_base($panel), '/') . '/' . ltrim($subUrl, '/');
    }
    $orderPassword = (string)random_int(1000, 9999);
    if ($uid >= 700000000000) {
        try {
            $rowsA = $db->query('SELECT config_username, password FROM app_accounts')->fetchAll(PDO::FETCH_ASSOC) ?: [];
            foreach ($rowsA as $ar) {
                $su = 700000000000 + (abs(crc32(strtolower((string)$ar['config_username']))) % 999999999);
                if ($su === $uid && !empty($ar['password'])) {
                    $orderPassword = (string)$ar['password'];
                    break;
                }
            }
        } catch (Throwable $e) {}
    }
    $panelId = (int)($panel['id'] ?? 0);
    $db->prepare(
        'INSERT INTO orders (user_id, config_username, password, sub_link, volume_gb, days, panel_id) VALUES (?, ?, ?, ?, ?, ?, ?)'
    )->execute([$uid, $targetUser, $orderPassword, $subUrl, $vol, $days, $panelId]);
    // خرید جدید: ظرفیت دوره نمایش = حجم پلن
    try {
        try { $db->exec('ALTER TABLE orders ADD COLUMN last_renew_gb DOUBLE NULL DEFAULT NULL'); } catch (Throwable $eCol) {}
        try { $db->exec('ALTER TABLE orders ADD COLUMN volume_cycle_gb DOUBLE NULL DEFAULT NULL'); } catch (Throwable $eCol2) {}
        $oidNew = (int)$db->lastInsertId();
        if ($oidNew > 0) {
            $db->prepare('UPDATE orders SET last_renew_gb = ?, volume_cycle_gb = ? WHERE id = ?')
               ->execute([(float)$vol, (float)$vol, $oidNew]);
        }
    } catch (Throwable $e) {}

    $db->prepare("UPDATE payments SET status = 'approved' WHERE id = ?")->execute([$paymentId]);

    $acc = dirname(WEBADMIN_ROOT) . '/accounting.php';
    if (is_readable($acc)) {
        require_once $acc;
        if (function_exists('recordAccountingFromPayment')) {
            $pay['status'] = 'approved';
            try {
                recordAccountingFromPayment($db, $pay, 'webadmin');
            } catch (Throwable $e) {
            }
        }
    }

    wa_reward_referral($db, $uid, $payPrice);

    $bonusNote = ($vol > $volBase) ? "\n🎁 هدیه دعوت: حجم {$vol} گیگ (+۵٪)\n" : "\n";
    $approveMsg = "🎉 <b>پرداختت تایید شد — اشتراکت آماده‌ست!</b>\n\n"
        . "👤 نام کاربری: <code>{$targetUser}</code>\n"
        . "🔑 رمز اپ: <code>{$orderPassword}</code>{$bonusNote}"
        . "📦 پلن: {$title}\n";
    if ($subUrl !== '') {
        $approveMsg .= "🔗 لینک:\n<code>{$subUrl}</code>\n\n";
    }
    $approveMsg .= "تو اپ یک‌بار بروزرسانی سابسکریپشن بزن 🚀";

    webadmin_tg('sendMessage', [
        'chat_id' => $uid,
        'text' => $approveMsg,
        'parse_mode' => 'HTML',
    ]);

    return ['ok' => true, 'msg' => 'خرید تأیید شد؛ سرویس ساخته و برای کاربر ارسال شد.'];
}

/**
 * فیش‌های approved بدون سفارش (معمولاً SMS با پنل قطع)
 * @return array{ok:bool,error?:string,msg?:string}
 */
function wa_retry_stuck_payment(PDO $db, int $paymentId): array
{
    $st = $db->prepare('SELECT * FROM payments WHERE id = ? LIMIT 1');
    $st->execute([$paymentId]);
    $pay = $st->fetch(PDO::FETCH_ASSOC);
    if (!$pay) {
        return ['ok' => false, 'error' => 'فیش یافت نشد.'];
    }
    if (($pay['status'] ?? '') !== 'approved') {
        // اگر هنوز pending است همان مسیر عادی
        if (($pay['status'] ?? '') === 'pending') {
            return wa_approve_payment($db, $paymentId);
        }
        return ['ok' => false, 'error' => 'وضعیت فیش برای تحویل مجدد مناسب نیست.'];
    }
    $action = (string)($pay['action_type'] ?? '');
    if ($action === 'deposit') {
        return ['ok' => false, 'error' => 'این فیش شارژ کیف است؛ تحویل سرویس ندارد.'];
    }
    $target = (string)($pay['target_username'] ?? '');
    if ($target === '') {
        return ['ok' => false, 'error' => 'target_username خالی است.'];
    }
    $ex = $db->prepare('SELECT id FROM orders WHERE config_username = ? LIMIT 1');
    $ex->execute([$target]);
    if ($ex->fetch()) {
        return ['ok' => true, 'msg' => 'سرویس از قبل در orders هست؛ نیازی به تحویل مجدد نیست.'];
    }

    // موقتاً pending تا wa_approve_payment کار کند، بعد اگر شکست به approved برنگردانیم؟
    // امن‌تر: منطق ساخت را مستقیم تکرار می‌کنیم بدون تغییر status در شکست
    $db->prepare("UPDATE payments SET status = 'pending' WHERE id = ?")->execute([$paymentId]);
    $res = wa_approve_payment($db, $paymentId);
    if (empty($res['ok'])) {
        // برگرداندن به approved تا حسابداری قبلی حفظ شود ولی بدون سفارش
        $db->prepare("UPDATE payments SET status = 'approved' WHERE id = ?")->execute([$paymentId]);
        return $res;
    }
    return $res;
}

/**
 * لیست فیش‌های گیرکرده: approved + new/renew بدون ردیف orders
 */
function wa_list_stuck_payments(PDO $db, int $limit = 50): array
{
    try {
        $sql = "SELECT p.*
                FROM payments p
                LEFT JOIN orders o ON o.config_username = p.target_username AND p.target_username IS NOT NULL AND p.target_username != ''
                WHERE p.status = 'approved'
                  AND p.action_type IN ('new', 'renew')
                  AND p.target_username IS NOT NULL
                  AND p.target_username != ''
                  AND o.id IS NULL
                ORDER BY p.id DESC
                LIMIT " . (int)$limit;
        return $db->query($sql)->fetchAll(PDO::FETCH_ASSOC) ?: [];
    } catch (Throwable $e) {
        return [];
    }
}

/**
 * وضعیت اتصال پنل(ها) برای داشبورد
 * @return list<array{name:string,ok:bool,ms:int,detail:string,id:int}>
 */
function wa_panel_health(PDO $db, int $timeoutSec = 10): array
{
    // کش کوتاه تا با نوسان لحظه‌ای پنل، داشبورد هی قرمز/سبز نشود
    $cacheDir = (defined('WEBADMIN_ROOT') ? WEBADMIN_ROOT : __DIR__ . '/..') . '/cache';
    if (!is_dir($cacheDir)) {
        @mkdir($cacheDir, 0755, true);
    }
    $cacheFile = $cacheDir . '/panel_health.json';
    $force = !empty($GLOBALS['wa_panel_health_force']);
    if (!$force && is_readable($cacheFile)) {
        $raw = @file_get_contents($cacheFile);
        $cached = json_decode((string)$raw, true);
        if (is_array($cached) && !empty($cached['ts']) && (time() - (int)$cached['ts']) < 45 && !empty($cached['rows']) && is_array($cached['rows'])) {
            return $cached['rows'];
        }
    }

    $panels = [];
    try {
        $panels = $db->query('SELECT * FROM bot_panels WHERE is_active = 1 ORDER BY is_default DESC, id ASC LIMIT 5')->fetchAll(PDO::FETCH_ASSOC) ?: [];
    } catch (Throwable $e) {
        $panels = [];
    }
    if (!$panels) {
        try {
            $panels = [wa_default_panel($db)];
        } catch (Throwable $e) {
            return [['id' => 0, 'name' => 'panel', 'ok' => false, 'ms' => 0, 'detail' => 'config: ' . $e->getMessage()]];
        }
    }
    $out = [];
    foreach ($panels as $panel) {
        $name = (string)($panel['name'] ?? $panel['driver'] ?? 'panel');
        $id = (int)($panel['id'] ?? 0);
        $user = (string)($panel['username'] ?? (defined('PANEL_USER') ? PANEL_USER : ''));
        $pass = (string)($panel['password'] ?? (defined('PANEL_PASS') ? PANEL_PASS : ''));
        $bases = [];
        try {
            $bases[] = wa_panel_api_base($panel);
            $direct = rtrim((string)($panel['base_url'] ?? ''), '/');
            if ($direct !== '' && !in_array($direct, $bases, true)) {
                $bases[] = $direct;
            }
        } catch (Throwable $e) {
            $out[] = ['id' => $id, 'name' => $name, 'ok' => false, 'ms' => 0, 'detail' => $e->getMessage()];
            continue;
        }
        $ok = false;
        $detail = 'no_attempt';
        $ms = 0;
        foreach ($bases as $base) {
            if ($base === '' || $user === '') {
                $detail = 'empty_url_or_user';
                continue;
            }
            $url = rtrim($base, '/') . '/api/admin/token';
            $t0 = microtime(true);
            $ch = curl_init();
            curl_setopt_array($ch, [
                CURLOPT_URL => $url,
                CURLOPT_POST => true,
                CURLOPT_POSTFIELDS => http_build_query(['username' => $user, 'password' => $pass]),
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_HTTPHEADER => ['Content-Type: application/x-www-form-urlencoded'],
                CURLOPT_SSL_VERIFYPEER => false,
                CURLOPT_SSL_VERIFYHOST => 0,
                CURLOPT_TIMEOUT => max(3, $timeoutSec),
                CURLOPT_CONNECTTIMEOUT => min(4, $timeoutSec),
                CURLOPT_IPRESOLVE => CURL_IPRESOLVE_V4,
            ]);
            $body = curl_exec($ch);
            $cerr = curl_error($ch);
            $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            $ms = (int)round((microtime(true) - $t0) * 1000);
            if ($body === false || $cerr) {
                $detail = 'curl: ' . ($cerr ?: 'fail') . " ({$ms}ms)";
                continue;
            }
            $j = json_decode((string)$body, true);
            $token = is_array($j) ? ($j['access_token'] ?? $j['token'] ?? null) : null;
            if ($token) {
                $ok = true;
                $detail = 'توکن OK — ' . $ms . 'ms';
                break;
            }
            $detail = 'http=' . $http . ' no_token — ' . $ms . 'ms';
        }
        if (mb_strlen($detail) > 140) {
            $detail = mb_substr($detail, 0, 137) . '…';
        }
        $out[] = [
            'id' => $id,
            'name' => $name,
            'ok' => $ok,
            'ms' => $ms,
            'detail' => $detail,
        ];
    }
    @file_put_contents($cacheFile, json_encode(['ts' => time(), 'rows' => $out], JSON_UNESCAPED_UNICODE));
    return $out;
}


function wa_set_setting(PDO $db, string $key, string $val): void
{
    $db->prepare('INSERT INTO settings (setting_key, setting_val) VALUES (?, ?) ON DUPLICATE KEY UPDATE setting_val = VALUES(setting_val)')
       ->execute([$key, $val]);
}

/**
 * حذف کاربر از پنل
 * @return array{ok:bool,http?:int,detail?:string}
 */
function wa_delete_panel_user(string $username, array $panel): array
{
    $tok = wa_panel_token_ex($panel, $GLOBALS['db'] ?? null);
    $token = $tok['token'] ?? null;
    $apiBase = $tok['api_base'] ?? null;
    if (!$token || !$apiBase) {
        return ['ok' => false, 'http' => 0, 'detail' => 'توکن پنل ناموفق: ' . ($tok['debug'] ?? '')];
    }
    $url = rtrim($apiBase, '/') . '/api/user/' . rawurlencode($username);
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST => 'DELETE',
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token, 'Accept: application/json'],
        CURLOPT_SSL_VERIFYPEER => false,
        CURLOPT_TIMEOUT => 15,
    ]);
    if (defined('CURL_IPRESOLVE_V4')) {
        curl_setopt($ch, CURLOPT_IPRESOLVE, CURL_IPRESOLVE_V4);
    }
    $res = curl_exec($ch);
    $http = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err = curl_error($ch);
    curl_close($ch);
    if (in_array($http, [200, 204, 404], true)) {
        return ['ok' => true, 'http' => $http, 'detail' => $http === 404 ? 'در پنل نبود' : 'حذف شد'];
    }
    return ['ok' => false, 'http' => $http, 'detail' => $err ?: mb_substr((string)$res, 0, 200)];
}

/**
 * افزودن حجم (GB) و/یا روز به سرویس موجود در پنل + به‌روز orders
 * @return array{ok:bool,error?:string,volume_gb?:float,msg?:string}
 */
function wa_gift_panel_service(PDO $db, string $configUsername, float $addGb, int $addDays, ?int $orderId = null): array
{
    $configUsername = trim($configUsername);
    if ($configUsername === '') {
        return ['ok' => false, 'error' => 'نام کانفیگ خالی است.'];
    }
    if ($addGb <= 0 && $addDays <= 0) {
        return ['ok' => false, 'error' => 'حداقل حجم یا روز را وارد کنید.'];
    }
    $panel = wa_default_panel($db);
    if ($orderId) {
        try {
            $st = $db->prepare('SELECT panel_id FROM orders WHERE id = ? LIMIT 1');
            $st->execute([$orderId]);
            $pid = (int)($st->fetchColumn() ?: 0);
            if ($pid > 0) {
                $panel = wa_panel_by_id($db, $pid);
            }
        } catch (Throwable $e) {
        }
    }
    $ren = wa_renew_panel_user($configUsername, max(0.0, $addGb), max(0, $addDays), $panel);
    if (empty($ren['ok'])) {
        $why = (string)($ren['detail'] ?? $ren['error'] ?? 'unknown');
        return ['ok' => false, 'error' => 'اعمال در پنل ناموفق: ' . mb_substr($why, 0, 180)];
    }
    $newVol = $ren['volume_gb'] ?? null;
    try {
        if ($orderId) {
            try { $db->exec('ALTER TABLE orders ADD COLUMN last_renew_gb DOUBLE NULL DEFAULT NULL'); } catch (Throwable $eCol) {}
            if ($newVol !== null && $addDays > 0) {
                if ($addGb > 0) {
                    // هدیه ادمین: volume_cycle_gb را دست نزن (دوره نمایش تمدید کاربر حفظ شود)
                    $db->prepare('UPDATE orders SET volume_gb = ?, days = IFNULL(days,0) + ?, warned_volume = 0, warned_expire = 0 WHERE id = ?')
                       ->execute([$newVol, $addDays, $orderId]);
                } else {
                    $db->prepare('UPDATE orders SET volume_gb = ?, days = IFNULL(days,0) + ?, warned_volume = 0, warned_expire = 0 WHERE id = ?')
                       ->execute([$newVol, $addDays, $orderId]);
                }
            } elseif ($newVol !== null) {
                if ($addGb > 0) {
                    $db->prepare('UPDATE orders SET volume_gb = ?, warned_volume = 0 WHERE id = ?')->execute([$newVol, $orderId]);
                } else {
                    $db->prepare('UPDATE orders SET volume_gb = ?, warned_volume = 0 WHERE id = ?')->execute([$newVol, $orderId]);
                }
            } elseif ($addDays > 0) {
                $db->prepare('UPDATE orders SET days = IFNULL(days,0) + ?, warned_expire = 0 WHERE id = ?')->execute([$addDays, $orderId]);
            }
        } else {
            try { $db->exec('ALTER TABLE orders ADD COLUMN last_renew_gb DOUBLE NULL DEFAULT NULL'); } catch (Throwable $eCol) {}
            if ($newVol !== null && $addDays > 0) {
                if ($addGb > 0) {
                    $db->prepare('UPDATE orders SET volume_gb = ?, days = IFNULL(days,0) + ?, warned_volume = 0, warned_expire = 0 WHERE config_username = ?')
                       ->execute([$newVol, $addDays, $configUsername]);
                } else {
                    $db->prepare('UPDATE orders SET volume_gb = ?, days = IFNULL(days,0) + ?, warned_volume = 0, warned_expire = 0 WHERE config_username = ?')
                       ->execute([$newVol, $addDays, $configUsername]);
                }
            } elseif ($newVol !== null) {
                if ($addGb > 0) {
                    $db->prepare('UPDATE orders SET volume_gb = ?, warned_volume = 0 WHERE config_username = ?')->execute([$newVol, $configUsername]);
                } else {
                    $db->prepare('UPDATE orders SET volume_gb = ?, warned_volume = 0 WHERE config_username = ?')->execute([$newVol, $configUsername]);
                }
            } elseif ($addDays > 0) {
                $db->prepare('UPDATE orders SET days = IFNULL(days,0) + ?, warned_expire = 0 WHERE config_username = ?')->execute([$addDays, $configUsername]);
            }
        }
    } catch (Throwable $e) {
        // پنل OK بود؛ دیتابیس فرعی
    }
    $parts = [];
    if ($addGb > 0) {
        $parts[] = $addGb . ' گیگ';
    }
    if ($addDays > 0) {
        $parts[] = $addDays . ' روز';
    }
    return [
        'ok' => true,
        'volume_gb' => $newVol,
        'msg' => 'اعمال شد: ' . implode(' + ', $parts),
    ];
}


/**
 * ساخت دستی سرویس برای کاربر (مثل adm_manual در ربات)
 * @return array{ok:bool,error?:string,msg?:string,username?:string,password?:string,sub?:string}
 */
function wa_manual_create_service(
    PDO $db,
    int $uid,
    float $volGb,
    int $days,
    ?string $cfgUsername = null,
    bool $notifyUser = true,
    int $panelId = 0
): array {
    if ($uid <= 0) {
        return ['ok' => false, 'error' => 'شناسه کاربر نامعتبر.'];
    }
    if ($volGb < 0 || $days < 0) {
        return ['ok' => false, 'error' => 'حجم یا روز نامعتبر.'];
    }
    $st = $db->prepare('SELECT user_id FROM users WHERE user_id = ? LIMIT 1');
    $st->execute([$uid]);
    if (!$st->fetch()) {
        return ['ok' => false, 'error' => 'کاربر در دیتابیس ربات یافت نشد.'];
    }

    // پنل انتخاب‌شده الزامی است؛ اگر id داده شده ولی پیدا نشود، به پیش‌فرض سوییچ نکن
    if ($panelId > 0) {
        $panel = wa_panel_by_id($db, $panelId);
        if ((int)($panel['id'] ?? 0) !== $panelId) {
            return ['ok' => false, 'error' => "پنل انتخاب‌شده (id={$panelId}) در دیتابیس پیدا نشد."];
        }
    } else {
        $panel = wa_default_panel($db);
    }
    $GLOBALS['db'] = $db;

    $name = trim((string)$cfgUsername);
    if ($name === '') {
        $name = 'man_' . $uid . '_' . random_int(10, 99);
        for ($i = 0; $i < 5; $i++) {
            $exists = wa_get_panel_user($name, $panel);
            if (!$exists || (is_array($exists) && empty($exists['username']) && empty($exists['id']))) {
                break;
            }
            $name = 'man_' . $uid . '_' . random_int(100, 999);
        }
    } else {
        $name = preg_replace('/[^a-zA-Z0-9_\-\.]/', '', $name) ?? '';
        if ($name === '') {
            return ['ok' => false, 'error' => 'نام کانفیگ نامعتبر.'];
        }
    }

    // ساخت دستی: فقط حجم هدیه دعوت در صورت واجد شرایط (بدون پاداش پولی معرف)
    $volFinal = wa_invitee_volume($db, $uid, (float)$volGb);
    $res = wa_create_panel_user($name, $volFinal, $days, $panel, $db);
    if (!empty($res['_error'])) {
        return ['ok' => false, 'error' => 'ساخت در پنل ناموفق: ' . mb_substr((string)($res['detail'] ?? $res['_error']), 0, 200)];
    }

    $subUrl = (string)($res['subscription_url'] ?? '');
    if ($subUrl !== '' && strpos($subUrl, 'http') !== 0) {
        $subUrl = rtrim(wa_panel_public_base($panel), '/') . '/' . ltrim($subUrl, '/');
    }
    $password = (string)random_int(1000, 9999);
    $panelId = (int)($panel['id'] ?? 0);
    try {
        $db->prepare(
            'INSERT INTO orders (user_id, config_username, password, sub_link, volume_gb, days, panel_id) VALUES (?,?,?,?,?,?,?)'
        )->execute([$uid, $name, $password, $subUrl, $volFinal, $days, $panelId > 0 ? $panelId : null]);
    } catch (Throwable $e) {
        // ستون panel_id ممکن است نباشد
        try {
            $db->prepare(
                'INSERT INTO orders (user_id, config_username, password, sub_link, volume_gb, days) VALUES (?,?,?,?,?,?)'
            )->execute([$uid, $name, $password, $subUrl, $volFinal, $days]);
        } catch (Throwable $e2) {
            return ['ok' => false, 'error' => 'در پنل ساخته شد ولی ثبت در دیتابیس خطا: ' . $e2->getMessage()];
        }
    }

    try {
        $db->prepare('UPDATE users SET has_bought = 1 WHERE user_id = ?')->execute([$uid]);
    } catch (Throwable $e) {
    }
    $volGb = $volFinal;

    if ($notifyUser) {
        $volTxt = $volGb > 0 ? (rtrim(rtrim(number_format($volGb, 3, '.', ''), '0'), '.') . ' گیگ') : 'نامحدود';
        $dayTxt = $days > 0 ? ($days . ' روز') : 'بدون انقضا';
        $msg = "✅ <b>سرویس جدید برای شما فعال شد</b>\n\n"
            . "👤 نام کاربری: <code>{$name}</code>\n"
            . "🔑 رمز اپ: <code>{$password}</code>\n"
            . "📊 حجم: <b>{$volTxt}</b> · ⏱ اعتبار: <b>{$dayTxt}</b>\n\n";
        if ($subUrl !== '') {
            $msg .= "🔗 لینک ساب:\n<code>{$subUrl}</code>\n\n";
        }
        $msg .= "📱 با همین اطلاعات وارد اپ JET VPN شو؛ یا لینک را در برنامه‌های دیگر Import کن.\n"
            . "یک‌بار Update Sub / Refresh را بزن 🚀";
        $kbChips = serviceInfoChipRow(
            remainingTimeChipLabel($dayTxt),
            remainingVolumeChipLabel((float)$volGb, 0)
        );
        webadmin_tg('sendMessage', [
            'chat_id' => $uid,
            'text' => $msg,
            'parse_mode' => 'HTML',
            'reply_markup' => json_encode(['inline_keyboard' => $kbChips], JSON_UNESCAPED_UNICODE),
        ]);
    }

    return [
        'ok' => true,
        'msg' => "سرویس ساخته شد: {$name} | پنل: " . (string)($panel['name'] ?? '') . " (id=" . (int)($panel['id'] ?? 0) . ")",
        'username' => $name,
        'password' => $password,
        'sub' => $subUrl,
    ];
}

/**
 * ساخت دستی از روی پلن موجود (برای پرداخت خارج از ربات)
 */
function wa_manual_create_from_plan(
    PDO $db,
    int $uid,
    string $planKey,
    ?string $cfgUsername = null,
    bool $notifyUser = true
): array {
    $planKey = trim($planKey);
    if ($planKey === '') {
        return ['ok' => false, 'error' => 'پلن انتخاب نشده.'];
    }
    $plans = wa_plans($db);
    if (empty($plans[$planKey])) {
        return ['ok' => false, 'error' => 'پلن «' . $planKey . '» پیدا نشد.'];
    }
    $p = $plans[$planKey];
    $vol = (float)($p['vol'] ?? 0);
    $days = (int)($p['days'] ?? 0);
    $panelId = (int)($p['panel_id'] ?? 0);
    $title = (string)($p['title'] ?? $planKey);
    $cat = (string)($p['cat'] ?? '');

    $res = wa_manual_create_service($db, $uid, $vol, $days, $cfgUsername, $notifyUser, $panelId);
    if (empty($res['ok'])) {
        return $res;
    }

    // به‌روزرسانی سفارش با plan_key / cat در صورت وجود ستون
    $uname = (string)($res['username'] ?? '');
    if ($uname !== '') {
        try {
            $db->prepare('UPDATE orders SET plan_key = ?, cat = ? WHERE config_username = ? AND user_id = ? ORDER BY id DESC LIMIT 1')
               ->execute([$planKey, $cat !== '' ? $cat : null, $uname, $uid]);
        } catch (Throwable $e) {
            try {
                $db->prepare('UPDATE orders SET plan_key = ? WHERE config_username = ? AND user_id = ? ORDER BY id DESC LIMIT 1')
                   ->execute([$planKey, $uname, $uid]);
            } catch (Throwable $e2) {
            }
        }
    }

    $res['msg'] = 'از پلن «' . $title . '» ساخته شد: ' . $uname
        . ' | پنل_id=' . $panelId;
    $res['plan_key'] = $planKey;
    return $res;
}
