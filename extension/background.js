// background.js — Service Worker (Manifest V3)
// Receives post data from the popup/content script and sends it to the local server.

// =============================================================================
// SERVER CONFIG — change this if your server runs on a different port
// =============================================================================
const SERVER_URL = 'http://localhost:9247/api/posts';

// =============================================================================
// MESSAGE LISTENER
// =============================================================================
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SEND_TO_SERVER') {
    console.log(`[LI Collector] Received ${message.data.length} posts.`);
    sendToServer(message.data);
  }
});

/**
 * Send extracted posts to the local Python server via POST.
 * @param {Array<Object>} posts - Array of extracted post objects
 */
async function sendToServer(posts) {
  try {
    const response = await fetch(SERVER_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(posts),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log('[LI Collector] Server response:', data);
    notifyPopup({ type: 'SERVER_RESPONSE', success: true, data });

  } catch (error) {
    let errorMessage = error.message;

    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      errorMessage = 'Server unreachable. Make sure the server is running on localhost:9247';
    }

    console.error('[LI Collector] Error:', errorMessage);
    notifyPopup({ type: 'SERVER_RESPONSE', success: false, error: errorMessage });
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
