# ================================================================
# ALPHABOT — WEBSİTE SİNYAL GÖNDERİCİ
# ================================================================
# Bu dosyayı alhpabot.py'nin yanına koy ve import et:
#   from website_signal import send_to_website, init_website_sender
# ================================================================

import json
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime

# ================================================================
# ⚙️  AYARLAR — Kendi sitenle değiştir
# ================================================================

# Netlify Functions endpoint'in (aşağıda açıklandı)
WEBSITE_API_URL = "https://alphha.netlify.app/.netlify/functions/signal"

# Güvenlik için secret key — sitende de aynısı olmalı
WEBHOOK_SECRET  = "alphabot-secret-2024"

# Bağlantı zaman aşımı (saniye)
REQUEST_TIMEOUT = 6

# Hata durumunda tekrar deneme sayısı
MAX_RETRIES     = 2

# ================================================================
# SINYAL GÖNDERİCİ
# ================================================================

_send_queue   = []   # Gönderilmeyi bekleyen sinyaller
_send_lock    = threading.Lock()
_sender_ready = False

def init_website_sender():
    """Bot başladığında bir kez çağır."""
    global _sender_ready
    _sender_ready = True
    t = threading.Thread(target=_queue_worker, daemon=True, name="WebsiteSender")
    t.start()
    print("[WEBSITE] Sinyal gönderici başlatıldı →", WEBSITE_API_URL)


def send_to_website(event_type: str, data: dict):
    """
    Siteye asenkron sinyal gönderir — bot_loop'u bloklamaz.

    event_type örnekleri:
        "signal"   → Yeni işlem sinyali
        "result"   → İşlem sonucu (WIN/LOSS)
        "status"   → Bot durumu (start/stop)
        "news"     → Haber engeli bildirimi

    data: gönderilecek bilgiler (dict)
    """
    if not _sender_ready:
        return

    payload = {
        "event":     event_type,
        "timestamp": datetime.now().isoformat(),
        "data":      data
    }

    with _send_lock:
        _send_queue.append(payload)


def _queue_worker():
    """Arka planda çalışır, kuyruktaki sinyalleri sırayla gönderir."""
    while True:
        if _send_queue:
            with _send_lock:
                payload = _send_queue.pop(0)
            _do_send(payload)
        time.sleep(0.2)


def _do_send(payload: dict, attempt: int = 1):
    """HTTP POST ile siteye gönderir."""
    try:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            WEBSITE_API_URL,
            data=body,
            headers={
                "Content-Type":  "application/json",
                "X-Secret-Key":  WEBHOOK_SECRET,
                "User-Agent":    "AlphaBot/1.0",
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            status = resp.getcode()
            if status == 200:
                print(f"[WEBSITE] ✅ Gönderildi: {payload['event']}")
            else:
                print(f"[WEBSITE] ⚠️ HTTP {status}")

    except urllib.error.HTTPError as e:
        print(f"[WEBSITE] ❌ HTTP Hata: {e.code} — {payload['event']}")
        _retry(payload, attempt)

    except Exception as e:
        print(f"[WEBSITE] ❌ Bağlantı Hatası: {e}")
        _retry(payload, attempt)


def _retry(payload: dict, attempt: int):
    if attempt < MAX_RETRIES:
        time.sleep(2 * attempt)
        _do_send(payload, attempt + 1)


# ================================================================
# KULLANIM — alhpabot.py içine yapıştır
# ================================================================
#
# 1. Dosyanın en üstüne import ekle:
#
#       from website_signal import send_to_website, init_website_sender
#
# 2. OnInit kısmında (mt5.initialize()'ın hemen altına):
#
#       init_website_sender()
#
# 3. open_trade() fonksiyonu içinde send_signal(msg)'den SONRA:
#
#       send_to_website("signal", {
#           "symbol":    symbol_map.get(symbol, symbol),
#           "direction": direction,
#           "strategy":  strategy_name,
#           "entry":     live_price,
#           "stake":     stake,
#           "tp1":       tp1,
#           "tp2":       tp2,
#           "sl":        sl,
#           "mode":      MODE,
#           "ai_conf":   _ai_conf_val,
#       })
#
# 4. Sonuç gelince (bot_loop içinde result kısmında):
#
#       send_to_website("result", {
#           "symbol":    symbol_map.get(trade["symbol"], trade["symbol"]),
#           "direction": trade["type"],
#           "result":    result_str,   # "WIN" veya "LOSS"
#           "entry":     trade["entry"],
#           "exit":      exit_price,
#           "pnl":       round(current_stake * 0.85, 2) if win else -current_stake,
#       })
#
# ================================================================
