// popup.js — Extension popup logic
// Scraping runs via chrome.scripting.executeScript on ALL frames,
// because LinkedIn loads posts inside an internal iframe (/preload/).

const btnScrape = document.getElementById('btn-scrape');
const btnDiagnostics = document.getElementById('btn-diagnostics');
const statusDiv = document.getElementById('status');
const reportDiv = document.getElementById('report');

function setStatus(msg, type = 'loading') {
  statusDiv.textContent = msg;
  statusDiv.className = `status-${type}`;
}

async function getLinkedInTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.url?.includes('linkedin.com')) return null;
  return tab;
}

// =============================================================================
// SCRAPER FUNCTION — injected into the page via executeScript
// Contains all logic: selectors, cleanup, extraction.
// =============================================================================
function scraperFunction() {
  // --- CSS SELECTORS — update here if LinkedIn changes its DOM ---
  const SEL = {
    postContainer: '.feed-shared-update-v2',
    postText: '.update-components-text .break-words',
    reactions: 'span.social-details-social-counts__reactions-count',
    comments: '.social-details-social-counts__comments',
    reposts: '.social-details-social-counts__reposts',
    impressions: '.ca-entry-point__num-views strong',
    analyticsLink: 'a.analytics-entry-point',
  };

  const containers = document.querySelectorAll(SEL.postContainer);
  if (containers.length === 0) return { found: false, frameUrl: location.href };

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

  function getText(container, sel) {
    const el = container.querySelector(sel);
    return el ? el.innerText || el.textContent || '' : '';
  }

  // Convert LinkedIn relative time ("1 anno", "3 gg", "2w") to ISO datetime
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

  // --- Extended field extractors (each wrapped in try/catch) ---

  function detectPostType(container) {
    try {
      if (container.querySelector('.update-components-linkedin-video, video, .feed-shared-external-video')) return 'video';
      if (container.querySelector('.update-components-carousel, .feed-shared-carousel')) return 'carousel';
      if (container.querySelector('.feed-shared-document, .update-components-document')) return 'document';
      if (container.querySelector('.feed-shared-poll, .update-components-poll')) return 'poll';
      if (container.querySelector('.update-components-article, .feed-shared-article')) return 'article';
      if (container.querySelector('.update-components-image, .feed-shared-image, img.feed-shared-image__image')) return 'image';
      return 'text';
    } catch (e) { return null; }
  }

  function extractHashtags(text) {
    try {
      const matches = text.match(/#[\w\u00C0-\u024F]+/g);
      return matches ? [...new Set(matches.map(h => h.toLowerCase()))] : [];
    } catch (e) { return []; }
  }

  function detectHasLink(container) {
    try {
      const links = container.querySelectorAll('.update-components-text a[href]');
      for (const a of links) {
        const href = a.getAttribute('href') || '';
        if (href.startsWith('http') && !href.includes('linkedin.com/feed/hashtag')) return true;
      }
      return false;
    } catch (e) { return null; }
  }

  const posts = [];
  containers.forEach((c) => {
    try {
      const txt = cleanText(getText(c, SEL.postText));
      if (!txt) return;

      // Extract publish date from relative time text (e.g., "1y", "3d", "2w")
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
        likes: parseNumber(getText(c, SEL.reactions)),
        comments: parseNumber(getText(c, SEL.comments)),
        reposts: parseNumber(getText(c, SEL.reposts)),
        impressions: parseNumber(getText(c, SEL.impressions)),
        published_at: publishedAt,
        post_type: detectPostType(c),
        hashtags: extractHashtags(txt),
        has_link: detectHasLink(c),
      });
    } catch (e) { /* skip posts that fail to parse */ }
  });

  return { found: true, posts, frameUrl: location.href };
}

// =============================================================================
// EXTRACT button — runs scraping across all frames
// =============================================================================
btnScrape.addEventListener('click', async () => {
  btnScrape.disabled = true;
  reportDiv.style.display = 'none';
  setStatus('Scraping...', 'loading');

  const tab = await getLinkedInTab();
  if (!tab) {
    setStatus('Open a LinkedIn page first.', 'err');
    btnScrape.disabled = false;
    return;
  }

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      func: scraperFunction,
    });

    const frameWithPosts = results
      ?.map(r => r.result)
      .find(r => r?.found && r.posts?.length > 0);

    if (!frameWithPosts) {
      setStatus('No posts found. Are you on your activity page?', 'err');
      btnScrape.disabled = false;
      return;
    }

    const posts = frameWithPosts.posts;
    setStatus(`Found ${posts.length} posts! Sending to server...`, 'loading');

    chrome.runtime.sendMessage(
      { type: 'SEND_TO_SERVER', data: posts },
      () => {}
    );

    chrome.runtime.onMessage.addListener(function listener(msg) {
      if (msg.type === 'SERVER_RESPONSE') {
        chrome.runtime.onMessage.removeListener(listener);
        if (msg.success) {
          setStatus(`${posts.length} posts sent to server!`, 'ok');
        } else {
          setStatus(`Server error: ${msg.error}`, 'err');
        }
        btnScrape.disabled = false;
      }
    });

    setTimeout(() => {
      if (btnScrape.disabled) {
        setStatus(`${posts.length} posts extracted. Server unreachable?`, 'err');
        btnScrape.disabled = false;
      }
    }, 10000);

  } catch (err) {
    setStatus(`Error: ${err.message}`, 'err');
    btnScrape.disabled = false;
  }
});

// =============================================================================
// DIAGNOSTICS button — inspect the DOM across all frames
// =============================================================================
btnDiagnostics.addEventListener('click', async () => {
  btnDiagnostics.disabled = true;
  reportDiv.style.display = 'none';
  setStatus('Analyzing DOM...', 'loading');

  const tab = await getLinkedInTab();
  if (!tab) {
    setStatus('Open a LinkedIn page first.', 'err');
    btnDiagnostics.disabled = false;
    return;
  }

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id, allFrames: true },
      func: () => {
        const selectors = [
          '.feed-shared-update-v2',
          '.feed-shared-update-v2__control-menu-container',
          '.update-components-text',
          '.break-words',
          '.ca-entry-point__num-views',
          'span.social-details-social-counts__reactions-count',
          '.social-details-social-counts__comments',
          '.social-details-social-counts__reposts',
          '.update-components-actor__sub-description span[aria-hidden="true"]',
          'time[datetime]',
        ];
        const counts = {};
        selectors.forEach(s => { counts[s] = document.querySelectorAll(s).length; });
        const total = Object.values(counts).reduce((a, b) => a + b, 0);
        if (total === 0) return null;

        const firstPost = document.querySelector('.feed-shared-update-v2');
        let headerHtml = '';
        if (firstPost) {
          const header = firstPost.querySelector('.update-components-actor__sub-description')
            || firstPost.querySelector('.update-components-actor');
          headerHtml = header ? header.innerHTML.substring(0, 500) : 'HEADER NOT FOUND';
        }

        return { url: location.href, selectors: counts, headerSample: headerHtml };
      },
    });

    const report = results?.map(r => r.result).filter(Boolean);
    if (report?.length) {
      setStatus(`Found ${report.length} frame(s) with content.`, 'ok');
      reportDiv.style.display = 'block';
      reportDiv.textContent = JSON.stringify(report, null, 2);
    } else {
      setStatus('No content found in any frame.', 'err');
    }
  } catch (err) {
    setStatus(`Error: ${err.message}`, 'err');
  }

  btnDiagnostics.disabled = false;
});
