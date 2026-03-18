// content.js — Fallback content script for LinkedIn post extraction
// Primary scraping happens via popup.js -> executeScript (all frames).
// This content script runs in all frames as a backup listener.

// =============================================================================
// CSS SELECTORS — update here if LinkedIn changes its DOM
// =============================================================================
const SEL = {
  postContainer: '.feed-shared-update-v2',
  postText: '.update-components-text .break-words',
  reactions: 'span.social-details-social-counts__reactions-count',
  comments: '.social-details-social-counts__comments',
  reposts: '.social-details-social-counts__reposts',
  impressions: '.ca-entry-point__num-views strong',
  analyticsLink: 'a.analytics-entry-point',
};

function cleanText(t) {
  return t ? t.replace(/\s+/g, ' ').trim() : '';
}

function parseNumber(s) {
  if (!s) return 0;
  let p = s.trim().toLowerCase();
  const mK = p.match(/([\d.,]+)\s*k/);
  if (mK) return Math.round(parseFloat(mK[1].replace(',', '.')) * 1000);
  const mM = p.match(/([\d.,]+)\s*m/);
  if (mM) return Math.round(parseFloat(mM[1].replace(',', '.')) * 1000000);
  p = p.replace(/[^\d.,]/g, '');
  if (p.includes('.') && p.includes(',')) {
    if (p.lastIndexOf('.') > p.lastIndexOf(',')) p = p.replace(/,/g, '');
    else p = p.replace(/\./g, '').replace(',', '.');
  } else if (p.includes('.')) {
    const pp = p.split('.');
    if (pp.length === 2 && pp[1].length === 3) p = p.replace('.', '');
  } else if (p.includes(',')) {
    const pp = p.split(',');
    if (pp.length === 2 && pp[1].length === 3) p = p.replace(',', '');
    else p = p.replace(',', '.');
  }
  const n = parseInt(p, 10);
  return isNaN(n) ? 0 : n;
}

// Convert LinkedIn relative time ("1y", "3d", "2w", "1 anno", "3 gg") to ISO datetime
function parseRelativeTime(raw) {
  if (!raw) return null;
  const t = raw.toLowerCase().trim();
  const now = new Date();
  const m = t.match(/^(\d+)\s*/);
  const num = m ? parseInt(m[1], 10) : 1;

  if (/ann[oi]/i.test(t) || /\by\b/.test(t))  now.setFullYear(now.getFullYear() - num);
  else if (/mes[ei]/i.test(t) || /\bmo\b/.test(t)) now.setMonth(now.getMonth() - num);
  else if (/sett/i.test(t) || /\bw\b/.test(t)) now.setDate(now.getDate() - num * 7);
  else if (/\bgg?\b/i.test(t) || /giorn/i.test(t) || /\bd\b/.test(t)) now.setDate(now.getDate() - num);
  else if (/or[ea]/i.test(t) || /\bh\b/.test(t)) now.setHours(now.getHours() - num);
  else if (/min/i.test(t)) now.setMinutes(now.getMinutes() - num);
  else if (/adesso|ora|now|just/i.test(t)) { /* now */ }
  else return null;

  return now.toISOString();
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action !== 'START_SCRAPING') return;

  const containers = document.querySelectorAll(SEL.postContainer);
  if (containers.length === 0) return;

  const posts = [];
  containers.forEach((c) => {
    try {
      const el = c.querySelector(SEL.postText);
      const txt = cleanText(el?.innerText || '');
      if (!txt) return;

      let publishedAt = null;
      const subDesc = c.querySelector('.update-components-actor__sub-description span[aria-hidden="true"]');
      if (subDesc) {
        let rawTime = '';
        for (const node of subDesc.childNodes) {
          if (node.nodeType === 3 && node.textContent.trim()) {
            rawTime = node.textContent.trim().replace(/\s*[•·].*/, '');
            break;
          }
        }
        publishedAt = parseRelativeTime(rawTime);
      }

      posts.push({
        text: txt,
        likes: parseNumber((c.querySelector(SEL.reactions)?.innerText) || ''),
        comments: parseNumber((c.querySelector(SEL.comments)?.innerText) || ''),
        reposts: parseNumber((c.querySelector(SEL.reposts)?.innerText) || ''),
        impressions: parseNumber((c.querySelector(SEL.impressions)?.innerText) || ''),
        published_at: publishedAt,
      });
    } catch (e) { /* skip */ }
  });

  if (posts.length > 0) {
    chrome.runtime.sendMessage({ type: 'SEND_TO_SERVER', data: posts });
    sendResponse({ success: true, postCount: posts.length });
  }

  return true;
});

// Log only if this frame contains posts
if (document.querySelectorAll('.feed-shared-update-v2').length > 0) {
  console.log(`[LI Collector] Content script active — ${document.querySelectorAll('.feed-shared-update-v2').length} posts found.`);
}
