// background.js — Service Worker (Manifest V3)
// Receives post data from the popup/content script and sends it to the local server.

// =============================================================================
// SERVER CONFIG — posts are sent to ALL configured servers in parallel.
// Add/remove URLs to change targets.
// =============================================================================
const SERVERS = [
  'http://localhost:9247/api/posts',               // Virgil (mac-lavoro)
  'https://hermes.taild0289.ts.net/api/posts',     // Otto (hermes)
];

// =============================================================================
// MESSAGE LISTENER
// =============================================================================
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SEND_TO_SERVER') {
    console.log(`[LI Collector] Received ${message.data.length} posts.`);
    sendToServers(message.data);
  }
});

/**
 * Send extracted posts to ALL configured servers in parallel.
 * Each server gets the same payload. Failures on one server don't block others.
 * Popup shows combined results.
 * @param {Array<Object>} posts - Array of extracted post objects
 */
async function sendToServers(posts) {
  const results = await Promise.allSettled(
    SERVERS.map(async (url) => {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(posts),
      });

      if (!response.ok) {
        throw new Error(`${url} → HTTP ${response.status}`);
      }

      const data = await response.json();
      return { url, data };
    })
  );

  const succeeded = results.filter(r => r.status === 'fulfilled');
  const failed = results.filter(r => r.status === 'rejected');

  console.log('[LI Collector]', succeeded.length, 'server(s) OK,', failed.length, 'failed');

  if (succeeded.length === 0) {
    const errors = failed.map(r => r.reason.message).join('; ');
    console.error('[LI Collector] All servers failed:', errors);
    notifyPopup({ type: 'SERVER_RESPONSE', success: false, error: errors });
  } else {
    // Report the first success to the popup, but log all
    const first = succeeded[0].value;
    notifyPopup({ type: 'SERVER_RESPONSE', success: true, data: first.data });
    // Also report failures silently in console
    failed.forEach(r => console.warn('[LI Collector] Failed:', r.reason.message));
  }
}

/**
 * Send a notification to the popup (if open).
 * @param {Object} message - Message to send
 */
function notifyPopup(message) {
  chrome.runtime.sendMessage(message).catch(() => {
    // Popup may already be closed — ignore
  });
}

console.log('[LI Collector] Service worker started.');
