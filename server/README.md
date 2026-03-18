# li-toolkit — Server

FastAPI server that stores LinkedIn posts and provides analytics via REST API and MCP.

## Setup

```bash
uv run main.py
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/posts` | Save posts (from Chrome extension) |
| `GET` | `/api/posts` | List posts (`?limit=`, `?offset=`) |
| `GET` | `/api/posts/count` | Total post count |
| `GET` | `/api/analytics` | Full analytics |
| `GET` | `/api/strategy` | Current content strategy |
| `PUT` | `/api/strategy` | Update content strategy |
| `GET` | `/api/strategy/suggest` | Data-driven strategy suggestions |

Interactive docs: `http://127.0.0.1:9247/docs`

## MCP Server

Configure in your MCP client (Claude Desktop, Claude Code, Cursor, etc.):

```json
{
  "mcpServers": {
    "li-toolkit": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/server", "mcp_server.py"]
    }
  }
}
```

The MCP server is launched automatically by your LLM client — you don't run it manually.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LI_TOOLKIT_HOST` | `127.0.0.1` | Server bind address |
| `LI_TOOLKIT_PORT` | `9247` | Server port |
| `LI_TOOLKIT_DB` | `./linkedin_data.db` | Database file path |

## Running tests

```bash
uv run pytest -v
```
