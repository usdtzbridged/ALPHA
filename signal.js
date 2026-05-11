// ================================================================
// netlify/functions/signal.js
// ================================================================
// Bu dosyayı projenizde şu konuma koyun:
//   netlify/functions/signal.js
//
// Netlify otomatik olarak şu adreste yayınlar:
//   https://alphha.netlify.app/.netlify/functions/signal
// ================================================================

const WEBHOOK_SECRET = "alphabot-secret-2024"; // Python tarafıyla aynı olmalı

// Sinyalleri bellekte tut (son 100 adet)
// Not: Netlify Functions stateless — kalıcı depolama için Supabase/Firebase eklenebilir
let signalStore = [];

exports.handler = async (event) => {

  // CORS headers — sitenizin her sayfasından erişim için
  const headers = {
    "Access-Control-Allow-Origin":  "*",
    "Access-Control-Allow-Headers": "Content-Type, X-Secret-Key",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Content-Type": "application/json",
  };

  // OPTIONS (preflight) isteği
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 200, headers, body: "" };
  }

  // ── POST: Python botu sinyal gönderdi ──────────────────────────
  if (event.httpMethod === "POST") {

    // Güvenlik kontrolü
    const secret = event.headers["x-secret-key"] || event.headers["X-Secret-Key"];
    if (secret !== WEBHOOK_SECRET) {
      return {
        statusCode: 401,
        headers,
        body: JSON.stringify({ error: "Unauthorized" }),
      };
    }

    let payload;
    try {
      payload = JSON.parse(event.body);
    } catch {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: "Invalid JSON" }),
      };
    }

    // Sinyali kaydet
    signalStore.unshift({ ...payload, receivedAt: new Date().toISOString() });
    if (signalStore.length > 100) signalStore = signalStore.slice(0, 100);

    console.log(`[AlphaBot] ${payload.event} → ${JSON.stringify(payload.data)}`);

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({ ok: true, event: payload.event }),
    };
  }

  // ── GET: Web sayfası son sinyalleri çekiyor ───────────────────
  if (event.httpMethod === "GET") {
    const limit = parseInt(event.queryStringParameters?.limit || "20");
    const type  = event.queryStringParameters?.type; // filtre: "signal", "result" vb.

    let results = signalStore;
    if (type) results = results.filter(s => s.event === type);

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        ok:      true,
        count:   results.length,
        signals: results.slice(0, limit),
      }),
    };
  }

  return {
    statusCode: 405,
    headers,
    body: JSON.stringify({ error: "Method not allowed" }),
  };
};
