# li-toolkit

Collect your LinkedIn posts, analyze their performance, and feed the data to any LLM for content strategy assistance.

> **Disclaimer:** This project is not affiliated with, endorsed by, or associated with LinkedIn Corporation. "LinkedIn" is a trademark of LinkedIn Corporation. This tool is designed for personal use only — to extract and analyze **your own** posts from your own LinkedIn profile. It does not access other users' data, bypass authentication, or violate LinkedIn's Terms of Service when used as intended.

**li-toolkit** is a two-part open-source tool:

1. **Chrome Extension** — extracts your posts from your LinkedIn activity page
2. **Local Server** — stores posts in SQLite, computes analytics, and exposes everything via REST API and MCP (Model Context Protocol)

The server has no built-in AI. Instead, it's designed to be plugged into any LLM — via MCP, direct API calls, or by simply telling your LLM to call the endpoints.

## How it works

```
LinkedIn Activity Page
    ↓  Chrome Extension scrapes visible posts
    ↓  POST /api/posts
Local Server (FastAPI + SQLite)
    ↓  Stores posts, computes analytics
    ↓
REST API  ←→  Your scripts, tools, dashboards
MCP Server  ←→  Claude Desktop, Claude Code, Cursor, etc.
```

## Setup

There are three things to set up: the server, the Chrome extension, and the MCP connection to your LLM. You only need to do this once.

### Prerequisites

- [Python 3.11+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- Chrome or Chromium-based browser

### 1. Install and start the server

```bash
cd server
uv run main.py
```

That's it. `uv` handles creating the virtual environment and installing dependencies automatically. The server starts on `http://127.0.0.1:9247`.

The server needs to be running whenever you use the Chrome extension to collect posts. Your LLM can access data even when the server is stopped (the MCP server reads directly from the database).

### 2. Install the Chrome extension

1. Open `chrome://extensions/` in Chrome
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** and select the `extension/` folder

That's it. The extension icon will appear in your toolbar.

### 3. Connect your LLM via MCP

Add this to your MCP client config (Claude Desktop, Claude Code, Cursor, etc.):

```json
{
  "mcpServers": {
    "li-toolkit": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/li-toolkit/server", "mcp_server.py"]
    }
  }
}
```

> **You don't start the MCP server yourself.** Your LLM client launches it automatically as a subprocess when it needs it. It reads directly from the SQLite database, so it works independently of the REST server.

**Where to put the config:**
- **Claude Desktop:** `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)
- **Claude Code:** `~/.claude.json` or run `/mcp add`
- **Cursor:** Settings → MCP

### Alternative: REST API without MCP

If your LLM client doesn't support MCP, you can point it at the REST API directly (server must be running):

- `GET /api/posts` — list posts (`?limit=`, `?offset=`)
- `GET /api/posts/count` — total stored posts
- `GET /api/analytics` — full analytics
- `GET /api/strategy` — content strategy
- `PUT /api/strategy` — update strategy
- `GET /api/strategy/suggest` — data-driven strategy suggestions
- `POST /api/posts` — save posts (used by extension)

Full interactive API docs at `http://127.0.0.1:9247/docs`.

### Configuration

| Variable | Default | Description |
|---|---|---|
| `LI_TOOLKIT_HOST` | `127.0.0.1` | Server bind address |
| `LI_TOOLKIT_PORT` | `9247` | Server port |
| `LI_TOOLKIT_DB` | `./linkedin_data.db` | SQLite database path |

## MCP tools

| Tool | Description |
|---|---|
| `get_post_analytics` | Full analytics: engagement averages, distribution, topics, timing, recommendations |
| `get_posts` | Browse your stored posts with pagination |
| `get_top_posts` | Best-performing posts ranked by engagement |
| `get_posting_recommendations` | Data-driven advice on when, what, and how to post |
| `search_posts` | Search posts by keyword |
| `get_post_count` | Total number of stored posts |
| `get_strategy` | Read your current content strategy |
| `update_strategy` | Save strategy choices (topics, audience, goals, tone, frequency, languages) |
| `suggest_strategy_from_data` | Analyze your posts and suggest a strategy based on what works |

## Getting started (full walkthrough)

Once the server is running, the extension is installed, and your MCP client is configured:

### Step 1: Collect your posts

1. Go to your LinkedIn activity page (`linkedin.com/in/YOUR-NAME/recent-activity/all/`)
2. Scroll down to load as many posts as you want to analyze
3. Click the extension icon → **Extract my posts**
4. Repeat scrolling + extracting if you want more history (duplicates are handled automatically)

### Step 2: Set up your content strategy

Ask your LLM something like:

> "Help me set up my LinkedIn content strategy"

The LLM will:
1. Call `suggest_strategy_from_data` to analyze your post history
2. Show you what's working — which topics get the most engagement, your best posting times, ideal post length
3. Walk you through each section, asking about your goals, target audience, topics you want to focus on, preferred tone, and posting frequency
4. Save your choices with `update_strategy`

You can revisit and refine your strategy anytime by asking the LLM to update it.

### Step 3: Use it

Now when you ask your LLM to help with LinkedIn content, it has everything it needs:

- **"Draft a post about X"** — pulls your strategy (tone, audience, topics) and top-performing posts as reference
- **"What should I post about this week?"** — checks your analytics and strategy to suggest topics
- **"How are my posts performing?"** — returns full analytics
- **"Find my posts about Y"** — searches your post history

## Content strategy

The toolkit stores your content goals and preferences so your LLM has context without you repeating yourself every time.

Strategy fields: **topics**, **audience**, **goals**, **frequency**, **tone**, **languages**, **notes**.

## Analytics included

- **Engagement metrics** — averages for likes, comments, impressions, engagement rate
- **Engagement distribution** — how your posts spread across engagement buckets
- **Post length analysis** — which length performs best
- **Language detection** — Italian vs English performance comparison
- **Top keywords** — words most correlated with high engagement
- **Topic classification** — performance by topic (AI/ML, Data, Leadership, Career, Startup, Engineering, Personal)
- **Timing analysis** — best day of week and hour to post
- **Recommendations** — actionable insights derived from all the above
- **Top/bottom posts** — your best and worst performers

## Development

### Running tests

```bash
cd server
uv run pytest -v
```

### Project structure

```
li-toolkit/
├── server/
│   ├── main.py           # FastAPI application
│   ├── database.py       # SQLAlchemy models + SQLite setup
│   ├── models.py         # Pydantic schemas
│   ├── analytics.py      # Analytics engine
│   ├── strategy.py       # Content strategy storage + suggestions
│   ├── routes.py         # REST API endpoints
│   ├── mcp_server.py     # MCP server for LLM integration
│   └── tests/
├── extension/
│   ├── manifest.json     # Chrome extension manifest (V3)
│   ├── popup.html/js     # Extension popup UI + scraping logic
│   ├── background.js     # Service worker — sends data to server
│   └── content.js        # Fallback content script
├── LICENSE
├── CONTRIBUTING.md
└── README.md
```

## Known limitations

- **LinkedIn DOM selectors are fragile.** LinkedIn frequently updates their HTML structure. If the extension stops finding posts, the CSS selectors in `popup.js` and `content.js` need updating. Use the **Diagnostics** button to inspect what's available.
- **Relative timestamps are approximate.** LinkedIn shows "2w" or "3d" instead of exact dates, so `published_at` is computed as an estimate from the scrape time.
- **The server has no authentication.** It's designed to run locally. Don't expose it to the internet without adding auth.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.
