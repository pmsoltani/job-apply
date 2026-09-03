import asyncio
import json
import re
import subprocess
from logging import Logger

import aiohttp


# JINA does the tidying server-side. JSON output puts the page in `data.content`,
# without Jina's "Title:/URL Source:/Published Time:/Markdown Content:" preamble.
JINA_HEADERS = {
    "Accept": "application/json",
    "x-md-bullet-list-marker": "-",
    "x-md-link-style": "discarded",
    "x-retain-images": "none",
}


def _flatten_html(fragment: str) -> str:
    """Reduce an HTML fragment to readable text, keeping list items comma-separated."""
    text = re.sub(r"</li>\s*<li>", ", ", fragment)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


async def fetch_url(url: str, timeout: int) -> str:
    """Fetch a URL via Jina Reader and return the page's markdown content."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with (
        aiohttp.ClientSession() as session,
        session.get(url, headers=JINA_HEADERS, timeout=client_timeout) as response,
    ):
        response.raise_for_status()
        body = await response.text()

    try:
        data = json.loads(body).get("data")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Jina Reader returned non-JSON: {body[:200]}") from exc
    content = data.get("content") if isinstance(data, dict) else None
    if not isinstance(content, str):
        # A malformed remote response, not a caller passing a bad type.
        raise RuntimeError(f"Jina Reader returned no content: {body[:200]}")  # noqa: TRY004

    # The page title carries the job location, which the body often omits, and Jina
    # leaves it as raw HTML. Flatten it and keep it as a heading.
    title = _flatten_html(str(data.get("title") or ""))
    return f"# {title}\n\n{content}" if title else content


def clean_markdown(text: str) -> str:
    """Strip links and images from markdown, keeping readable text."""
    # Remove images: ![alt](url)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Inline links: [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Reference-style link definitions: [ref]: url "title"
    text = re.sub(r"^\[.*?\]:\s*\S+.*$", "", text, flags=re.MULTILINE)
    # Reference-style links: [text][ref] → text
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", text)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def start_tunnel(tunnel_name: str, lg: Logger) -> subprocess.Popen[bytes] | None:
    """Start a pre-configured Cloudflare tunnel with the given name."""
    try:
        if not tunnel_name:
            lg.warning("Cloudflare tunnel not started: No tunnel name provided")
            return None
        proc = await asyncio.to_thread(
            lambda: subprocess.Popen(
                ["cloudflared", "tunnel", "run", tunnel_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )
        lg.info("Cloudflare tunnel started: '%s'", tunnel_name)
        return proc
    except Exception as exc:
        lg.warning("Cloudflare tunnel not started: %s", exc)
        raise
