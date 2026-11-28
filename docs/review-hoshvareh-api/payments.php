<?php
declare(strict_types=1);
require_once __DIR__ . '/includes/bootstrap.php';
require_once __DIR__ . '/includes/layout.php';
require_once __DIR__ . '/includes/approve_lib.php';

webadmin_require_login();

$msg = '';
$err = '';

// ——— رد فیش ———
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['reject_id'])) {
    if (!webadmin_csrf_ok()) { $err = 'نشست امنیتی منقضی؛ رفرش کنید.'; }
    else {
    $pid = (int)$_POST['reject_id'];
    try {
        $db = webadmin_db();
        $st = $db->prepare("SELECT * FROM payments WHERE id = ? AND status = 'pending' LIMIT 1");
        $st->execute([$pid]);
        $pay = $st->fetch();
        if (!$pay) {
            $err = 'فیش یافت نشد یا دیگر در انتظار نیست.';
        } else {
            $db->prepare("UPDATE payments SET status = 'rejected' WHERE id = ? AND status = 'pending'")->execute([$pid]);
            $uid = (int)$pay['user_id'];
            webadmin_tg('sendMessage', [
                'chat_id' => $uid,
                'text' => "❌ متأسفانه فیش پرداخت شما (#{$pid}) رد شد.\nاگر اشتباهی بوده از پشتیبانی پیام بده.",
                'parse_mode' => 'HTML',
            ]);
            $msg = "فیش #{$pid} رد شد.";
        }
    } catch (Throwable $e) {
        $err = $e->getMessage();
    }
    }
}

// ——— تأیید کامل (خرید / تمدید / شارژ) ———
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['approve_id'])) {
    if (!webadmin_csrf_ok()) {
        $err = 'نشست امنیتی منقضی؛ رفرش کنید.';
    } else {
        $pid = (int)$_POST['approve_id'];
        try {
            $db = webadmin_db();
            $GLOBALS['db'] = $db;
            $res = wa_approve_payment($db, $pid);
            if (!empty($res['ok'])) {
                $msg = $res['msg'] ?? ('فیش #' . $pid . ' تأیید شد.');
            } else {
                $err = $res['error'] ?? 'تأیید ناموفق بود.';
            }
        } catch (Throwable $e) {
            $err = $e->getMessage();
        }
    }
}

$detailId = (int)($_GET['id'] ?? 0);
$detail = null;
$receiptUrl = null;
$list = [];

try {
    $db = webadmin_db();
    if ($detailId > 0) {
        $st = $db->prepare('SELECT p.*, u.username, u.balance, u.has_bought FROM payments p LEFT JOIN users u ON u.user_id = p.user_id WHERE p.id = ? LIMIT 1');
        $st->execute([$detailId]);
        $detail = $st->fetch() ?: null;
        if ($detail) {
            $fid = (string)($detail['photo_file_id'] ?? '');
            $pseudo = ['AWAITING_RECEIPT', 'WALLET_PAY', 'SMS_AUTO', 'ADMIN_CREDIT', 'ADMIN_DEBIT', ''];
            if ($fid !== '' && !in_array($fid, $pseudo, true) && strlen($fid) >= 15) {
                // پروکسی امن خودمان (قابل اعتمادتر از لینک مستقیم تلگرام)
                $receiptUrl = 'media.php?f=' . rawurlencode($fid);
            }
        }
    }
    $list = $db->query(
        "SELECT p.id, p.user_id, p.plan_key, p.price, p.action_type, p.status, p.photo_file_id, p.created_at, u.username
         FROM payments p
         LEFT JOIN users u ON u.user_id = p.user_id
         WHERE p.status = 'pending'
           AND p.photo_file_id IS NOT NULL
           AND p.photo_file_id NOT IN ('AWAITING_RECEIPT','WALLET_PAY','SMS_AUTO','ADMIN_CREDIT','ADMIN_DEBIT')
         ORDER BY p.id DESC
         LIMIT 50"
    )->fetchAll();
} catch (Throwable $e) {
    $err = $err ?: $e->getMessage();
}

webadmin_layout_header('فیش‌ها');
?>
<style>
table.users { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
table.users th, table.users td { border-bottom: 1px solid var(--border); padding: 10px 8px; text-align: right; }
table.users th { color: var(--muted); }
.mono { font-family: ui-monospace, monospace; direction: ltr; }
.receipt { max-width: 320px; border-radius: 12px; border: 1px solid var(--border); margin: 12px 0; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
</style>

<h1>فیش‌های در انتظار</h1>
<p class="muted">تأیید فیش از وب: شارژ کیف، خرید جدید و تمدید. جزئیات کامل (پلن، تخفیف، هشدار مبلغ) با باز کردن هر فیش دیده می‌شود.</p>

<?php if ($err !== ''): ?><div class="alert"><?= webadmin_h($err) ?></div><?php endif; ?>
<?php if ($msg !== ''): ?><div class="alert alert-ok"><?= webadmin_h($msg) ?></div><?php endif; ?>

<?php if ($detail):
  $review = function_exists('buildPaymentReviewInfo') ? buildPaymentReviewInfo($db, $detail) : null;
  $f = $review['fields'] ?? [];
  $warn = !empty($review['warn']);
?>
<div class="card">
  <p><a href="payments.php">← بازگشت به لیست</a></p>
  <h2>فیش #<?= (int)$detail['id'] ?><?php if ($warn): ?> <span style="color:#f59e0b;font-size:0.85em">⚠️ مبلغ غیرعادی</span><?php endif; ?></h2>
  <?php if ($warn && !empty($review['warn_text'])): ?>
    <div class="alert" style="border-color:#f59e0b;background:rgba(245,158,11,0.12)"><?= webadmin_h($review['warn_text']) ?></div>
  <?php endif; ?>
  <div class="pay-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;font-size:0.95rem;margin:12px 0">
    <div>👤 کاربر: <a href="user.php?id=<?= (int)$detail['user_id'] ?>"><span class="mono"><?= (int)$detail['user_id'] ?></span></a>
      <?php $un = $f['tg_username'] ?? ltrim((string)($detail['username'] ?? ''), '@'); if ($un !== ''): ?> @<?= webadmin_h($un) ?><?php endif; ?>
    </div>
    <div>🏷 وضعیت: <b><?= webadmin_h((string)($f['customer_label'] ?? '—')) ?></b></div>
    <div>💼 کیف پول: <b><?= number_format((int)($f['balance'] ?? $detail['balance'] ?? 0)) ?></b> ت</div>
    <div>📊 سرویس‌ها: <b><?= (int)($f['order_count'] ?? 0) ?></b></div>
    <div>📦 نوع: <b><?= webadmin_h((string)($f['action_label'] ?? $detail['action_type'])) ?></b></div>
    <div>🔑 پلن: <code><?= webadmin_h((string)($f['plan_key'] ?? $detail['plan_key'] ?? '')) ?></code></div>
    <?php if (!empty($f['plan_title'])): ?>
    <div style="grid-column:1/-1">🏷 عنوان پلن: <b><?= webadmin_h($f['plan_title']) ?></b></div>
    <?php endif; ?>
    <?php if ((int)($f['plan_price'] ?? 0) > 0): ?>
    <div>💰 قیمت پلن: <b><?= number_format((int)$f['plan_price']) ?></b> ت</div>
    <?php endif; ?>
    <div>🎟 تخفیف: <?php
      $c = (string)($f['coupon'] ?? $detail['coupon_code'] ?? '');
      if ($c === '') echo '—';
      else {
        echo '<code>' . webadmin_h($c) . '</code>';
        if ((int)($f['discount_pct'] ?? 0) > 0) {
          echo ' (' . (int)$f['discount_pct'] . '٪)';
          if ((int)($f['after_discount'] ?? 0) > 0) echo ' → ' . number_format((int)$f['after_discount']) . ' ت';
        }
      }
    ?></div>
    <div>🔢 مبلغ قابل پرداخت: <b style="font-size:1.15em"><?= number_format((int)($f['price'] ?? $detail['price'])) ?></b> ت</div>
    <div>💵 ریال: <code class="mono"><?= number_format((int)($f['rial'] ?? ((int)$detail['price'] * 10))) ?></code></div>
    <?php if (!empty($f['target']) && ($f['target'] ?? '') !== 'wallet'): ?>
    <div>👤 کانفیگ: <code class="mono"><?= webadmin_h((string)$f['target']) ?></code></div>
    <?php endif; ?>
    <div>📥 منبع: <?= webadmin_h((string)($f['source'] ?? '—')) ?></div>
    <div>⏱ زمان: <?= webadmin_h((string)($f['created_fa'] ?? webadmin_jalali((string)($detail['created_at'] ?? '')))) ?></div>
    <div>وضعیت فیش: <code><?= webadmin_h((string)$detail['status']) ?></code></div>
  </div>
  <?php
    $fidShow = (string)($detail['photo_file_id'] ?? '');
    $pseudoMap = [
      'SMS_AUTO' => 'تأیید خودکار با پیامک بانک — عکس فیش وجود ندارد (طبیعی است).',
      'WALLET_PAY' => 'پرداخت از کیف پول — فیش کارت‌به‌کارت ندارد.',
      'AWAITING_RECEIPT' => 'هنوز عکس فیش ارسال نشده.',
      'ADMIN_CREDIT' => 'شارژ دستی ادمین — بدون فیش.',
      'ADMIN_DEBIT' => 'کسر دستی ادمین — بدون فیش.',
    ];
  ?>
  <?php if ($receiptUrl): ?>
    <p><img class="receipt" src="<?= webadmin_h($receiptUrl) ?>" alt="فیش" loading="lazy"
         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"></p>
    <p class="muted" style="display:none">لود عکس ناموفق (file_id منقضی یا توکن).</p>
    <p class="muted" style="font-size:0.8rem">منبع: تلگرام file_id</p>
  <?php elseif (isset($pseudoMap[$fidShow])): ?>
    <p class="muted"><?= webadmin_h($pseudoMap[$fidShow]) ?></p>
  <?php elseif ($fidShow !== ''): ?>
    <p class="muted">فیش ثبت شده ولی پیش‌نمایش در دسترس نیست.</p>
  <?php else: ?>
    <p class="muted">عکس فیش ثبت نشده.</p>
  <?php endif; ?>

  <?php if (($detail['status'] ?? '') === 'pending'): ?>
  <div class="actions">
    <form method="post" onsubmit="return confirm('تأیید این فیش و اعمال سرویس/شارژ؟');">
      <?= webadmin_csrf_field() ?>
      <input type="hidden" name="approve_id" value="<?= (int)$detail['id'] ?>">
      <button class="btn btn-ok" type="submit">✅ تأیید فیش</button>
    </form>
    <form method="post" onsubmit="return confirm('رد این فیش؟');">
      <?= webadmin_csrf_field() ?>
      <input type="hidden" name="reject_id" value="<?= (int)$detail['id'] ?>">
      <button class="btn btn-danger" type="submit">❌ رد فیش</button>
    </form>
  </div>
  <?php endif; ?>
</div>
<?php endif; ?>

<div class="card">
  <h2>لیست در انتظار (حداکثر ۵۰)</h2>
  <?php if (!$list): ?>
    <p class="muted">فیش در انتظاری نیست.</p>
  <?php else: ?>
  <div style="overflow-x:auto">
  <table class="users">
    <thead>
      <tr>
        <th>#</th>
        <th>کاربر</th>
        <th>مبلغ</th>
        <th>نوع</th>
        <th>پلن</th>
        <th>تاریخ</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
    <?php foreach ($list as $p): ?>
      <tr>
        <td><?= (int)$p['id'] ?></td>
        <td class="mono"><?= (int)$p['user_id'] ?>
          <?= !empty($p['username']) ? '<br><span class="muted">@' . webadmin_h(ltrim((string)$p['username'], '@')) . '</span>' : '' ?>
        </td>
        <td><?= number_format((int)$p['price']) ?></td>
        <td><?= webadmin_h((string)$p['action_type']) ?></td>
        <td><?= webadmin_h((string)($p['plan_key'] ?? '')) ?></td>
        <td class="muted"><?= webadmin_h(webadmin_jalali((string)($p['created_at'] ?? ''))) ?></td>
        <td><a href="payments.php?id=<?= (int)$p['id'] ?>">جزئیات</a></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
  <?php endif; ?>
</div>
<?php webadmin_layout_footer(); ?>
