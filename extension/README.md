# LI Post Collector — Chrome Extension

Chrome extension that extracts your LinkedIn posts and sends them to the li-toolkit local server.

## Installation

1. Open `chrome://extensions/` in Chrome
2. Enable **Developer mode** (top right toggle)
3. Click **Load unpacked** and select this `extension/` folder
4. The extension icon should appear in your toolbar

## Usage

1. Navigate to your LinkedIn activity page: `linkedin.com/in/YOUR-NAME/recent-activity/all/`
2. Scroll down to load more posts (the extension only sees what's currently in the DOM)
3. Click the extension icon
4. Click **Extract my posts**
5. Posts are sent to the local server at `http://localhost:9247/api/posts`

## Configuration

The server URL is set in `background.js`:

```js
const SERVER_URL = 'http://localhost:9247/api/posts';
```

Change this if your server runs on a different port.

## Diagnostics

If extraction fails, click **Diagnostics** to inspect which CSS selectors match in the current page. This helps identify when LinkedIn has changed their DOM structure.

## How it works

The extension runs a scraper function across all page frames (LinkedIn loads posts in an internal iframe). For each post container it finds, it extracts:

- **Post text** — the content of your post
- **Likes** — reaction count
- **Comments** — comment count
- **Reposts** — repost/share count
- **Impressions** — view count (when available via analytics link)
- **Published date** — estimated from relative timestamps ("2w", "3d", etc.)

Numbers are parsed from various formats: `1.2k`, `1,200`, `1.200` (European notation).

## Updating selectors

LinkedIn frequently changes their HTML. Key selectors to update (in both `popup.js` and `content.js`):

```js
const SEL = {
  postContainer: '.feed-shared-update-v2',
  postText: '.update-components-text .break-words',
  reactions: 'span.social-details-social-counts__reactions-count',
  comments: '.social-details-social-counts__comments',
  reposts: '.social-details-social-counts__reposts',
  impressions: '.ca-entry-point__num-views strong',
  analyticsLink: 'a.analytics-entry-point',
};
```

## Known issue: `chrome-extension://invalid/` errors after uninstalling

### What happens

After removing this extension (or similar LinkedIn-targeting extensions) from `chrome://extensions`, LinkedIn may flood the console with thousands of `net::ERR_FAILED` errors for `chrome-extension://invalid/`. This happens even when the extension was removed properly through the Chrome UI.

### Why

This extension uses `"all_frames": true` in its content script config, injecting into every iframe on LinkedIn. LinkedIn loads dozens of iframes and caches references to injected extension resources. After the extension is removed, Chrome invalidates these URLs to `chrome-extension://invalid/`, but LinkedIn's cached state keeps retrying them in a loop — generating thousands of errors per minute.

### How to fix

If you see this after removing the extension:

1. Close all LinkedIn tabs
2. Go to `chrome://settings/content/all`, find `linkedin.com`, and delete all its site data
3. Restart Chrome completely (quit and reopen, not just close the window)

If that doesn't work:

1. Re-add the extension temporarily: `chrome://extensions/` → **Load unpacked** → select this `extension/` folder
2. Reload LinkedIn to let the extension re-establish its content scripts
3. Remove the extension again from `chrome://extensions/`
4. Restart Chrome
