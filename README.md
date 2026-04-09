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

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/posts` | List posts (`?limit=`, `?offset=`) |
| `GET` | `/api/posts/count` | Total stored posts |
| `GET` | `/api/posts/top` | Top posts by engagement (`?count=`) |
| `GET` | `/api/posts/search` | Search posts by keyword (`?query=`, `?limit=`) |
| `GET` | `/api/posts/{id}/velocity` | Engagement velocity for a specific post |
| `GET` | `/api/velocity/recent` | Velocity for recently re-scraped posts |
| `GET` | `/api/analytics` | Full analytics |
| `GET` | `/api/recommendations` | Data-driven posting recommendations |
| `POST` | `/api/analyze-draft` | Analyze a draft's readability vs your history |
| `GET` | `/api/trends` | Weekly engagement trends (`?days=`) |
| `GET` | `/api/strategy` | Content strategy |
| `PUT` | `/api/strategy` | Update strategy |
| `GET` | `/api/strategy/suggest` | Data-driven strategy suggestions |
| `POST` | `/api/posts` | Save posts (used by extension) |

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
| `get_post_analytics` | Full analytics: engagement, readability, topics, timing, post types, recommendations |
| `get_posts` | Browse your stored posts with readability metrics and metadata |
| `get_top_posts` | Best-performing posts ranked by engagement |
| `get_posting_recommendations` | Data-driven advice on when, what, and how to post |
| `search_posts` | Search posts by keyword |
| `get_post_count` | Total number of stored posts |
| `analyze_draft` | Analyze a draft post's readability against your historical averages |
| `get_engagement_velocity` | How fast engagement is growing on recent posts |
| `get_trends` | Weekly engagement trends over time |
| `get_strategy` | Read your current content strategy |
| `update_strategy` | Save strategy choices (topics, audience, goals, tone, frequency, languages) |
| `suggest_strategy_from_data` | Analyze your posts and suggest a strategy based on what works |

## Getting started (full walkthrough)

Once the server is running, the extension is installed, and your MCP client is configured:

### Step 1: Collect your posts

1. Go to your LinkedIn activity page (`linkedin.com/in/YOUR-NAME/recent-activity/all/`)
2. Scroll down to load as many posts as you want to analyze
3. Click the extension icon → **Extract my posts**
4. Repeat scrolling + extracting if you want more history (duplicates are handled automatically, and recent posts get their engagement numbers updated)

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
- **"Check my draft before I post"** — analyzes readability and compares against your best-performing posts
- **"What should I post about this week?"** — checks your analytics and strategy to suggest topics
- **"How are my posts performing?"** — returns full analytics with readability and post type breakdowns
- **"How is my latest post doing?"** — shows engagement velocity and trajectory
- **"Find my posts about Y"** — searches your post history
- **"Show me my engagement trends"** — weekly engagement trends over time

## Content strategy

The toolkit stores your content goals and preferences so your LLM has context without you repeating yourself every time.

Strategy fields: **topics**, **audience**, **goals**, **frequency**, **tone**, **languages**, **notes**, **custom_topics** (your own topic clusters for analytics).

## Analytics included

- **Engagement metrics** — averages for likes, comments, impressions, engagement rate (weighted: reposts 3x, comments 2x, likes 1x)
- **Engagement distribution** — how your posts spread across engagement buckets
- **Readability analysis** — Flesch-Kincaid grade, sentence length, vocabulary richness, and how they correlate with engagement
- **Emoji analysis** — emoji density vs engagement performance
- **Post type analysis** — engagement by post type (text, image, video, carousel, document, poll, article)
- **Post length analysis** — which length performs best
- **Language detection** — Italian vs English performance comparison
- **Top keywords** — words most correlated with high engagement
- **Topic classification** — performance by topic (AI/ML, Data, Leadership, Career, Startup, Engineering, Personal, plus custom topics)
- **Timing analysis** — best day of week and hour to post
- **Engagement velocity** — how fast engagement grows on recent posts, trajectory detection (accelerating, peaked, steady, declining)
- **Weekly trends** — engagement averages over time to track growth
- **Recommendations** — actionable insights derived from all the above
- **Top/bottom posts** — your best and worst performers

## CLI

li-toolkit includes a command-line interface for interacting with your data without running a server. All commands output JSON by default (pipe-friendly for agents and scripts). Add `--pretty` for human-readable text.

```bash
cd server

# List posts
uv run li-toolkit posts --limit 10

# Top posts by engagement
uv run li-toolkit top --count 5 --pretty

# Search posts
uv run li-toolkit search "remote work"

# Full analytics
uv run li-toolkit analytics

# Analyze a draft before posting
uv run li-toolkit draft "Your draft post text here"
echo "draft from pipe" | uv run li-toolkit draft --stdin

# Engagement trends
uv run li-toolkit trends --days 90

# Posting recommendations
uv run li-toolkit recommendations

# Engagement velocity (recent posts)
uv run li-toolkit velocity

# Content strategy
uv run li-toolkit strategy

# Post count
uv run li-toolkit count
```

## MCP resources

MCP resources are discoverable data endpoints that agents can browse without calling tools:

| Resource URI | Description |
|---|---|
| `resource://posts` | Recent posts (last 50) |
| `resource://analytics` | Full analytics snapshot |
| `resource://strategy` | Current content strategy |
| `resource://top-posts` | Top 10 posts by engagement |

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
│   ├── database.py       # SQLAlchemy models + SQLite setup + migrations
│   ├── models.py         # Pydantic schemas + typed response models
│   ├── services.py       # Business logic (shared between REST, MCP, and CLI)
│   ├── analytics.py      # Analytics engine + velocity analysis
│   ├── readability.py    # Readability metrics (Flesch-Kincaid, etc.)
│   ├── strategy.py       # Content strategy storage + suggestions
│   ├── routes.py         # REST API endpoints (typed responses)
│   ├── mcp_server.py     # MCP server + resources for LLM integration
│   ├── cli.py            # CLI for server-free interaction
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

## Re-scraping and engagement tracking

When you scrape posts that already exist in the database, the server automatically updates engagement numbers (likes, comments, impressions) for posts less than 14 days old. Each update creates a snapshot of the previous state, enabling engagement velocity tracking.

To build velocity data, scrape your activity page periodically (every 6+ hours). Over time, this lets the toolkit show you how fast engagement grows on each post and whether posts are accelerating, peaking, or declining.

## Known limitations

- **LinkedIn DOM selectors are fragile.** LinkedIn frequently updates their HTML structure. If the extension stops finding posts, the CSS selectors in `popup.js` and `content.js` need updating. Use the **Diagnostics** button to inspect what's available.
- **Relative timestamps are approximate.** LinkedIn shows "2w" or "3d" instead of exact dates, so `published_at` is computed as an estimate from the scrape time.
- **Post type detection depends on LinkedIn's DOM.** The extension detects post types (image, video, carousel, etc.) using CSS class patterns that may change. If a post type is undetectable, it defaults to "unknown" and analytics still work.
- **The server has no authentication.** It's designed to run locally. Don't expose it to the internet without adding auth.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.
