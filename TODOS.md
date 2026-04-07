# TODOs

## Workstream 2: Re-scraping + Engagement Velocity

**What:** Track how engagement grows over time per post by re-scraping recent posts and storing snapshots.

**Why:** Enables velocity analysis ("this post is gaining engagement 2.5x faster than average"), viral trajectory detection, and time-series trending. Gives the LLM temporal data it can't get from a single scrape.

**Details:**
- New `post_snapshots` table (post_id FK, likes, comments, reposts, impressions, scraped_at)
- `last_scraped_at` + `edited` columns on PostRecord
- Extension re-scraping: existing posts < 14 days old get updated if last scraped > 6h ago
- Velocity analysis functions: compute_velocity, compare_velocity, detect_viral_trajectory
- New MCP tools: get_engagement_velocity, get_trends
- Cap: 10 snapshots per post, minimum intervals (1h, 6h, 12h, 24h, etc.)

**Depends on:** Workstream 1 (this PR) for updated engagement formula

---

## Workstream 3: Extended Scraping

**What:** Extract additional data points from LinkedIn DOM: post type (text/image/video/carousel), hashtags, mentions, media count, link detection.

**Why:** More data = better LLM analysis. Post type is a high-signal feature (carousels vs text-only perform very differently). Hashtags and mentions enable network analysis.

**Details:**
- Extension changes only (popup.js) + new nullable columns on PostRecord
- Each new selector wrapped in try/catch, returns null on failure
- **Critical: validate all selectors against actual LinkedIn DOM before implementing**
- Server treats null fields as absent (graceful degradation)

**Depends on:** Nothing (independent of WS1 and WS2)
