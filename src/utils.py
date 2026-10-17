import asyncio
import functools
import json
import re
import subprocess
from collections.abc import Callable, Coroutine
from logging import Logger
from typing import Any

import httpx2


# JINA does the tidying server-side. JSON output puts the page in `data.content`,
# without Jina's "Title:/URL Source:/Published Time:/Markdown Content:" preamble.
JINA_HEADERS = {
    "Accept": "application/json",
    "x-md-bullet-list-marker": "-",
    "x-md-link-style": "discarded",
    "x-retain-images": "none",
}


def in_thread[**P, R](fn: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    """Run a blocking function in a worker thread, so it doesn't block the event loop.

    The thread gets a copy of the current context, so log records keep the task id.
    """

    @functools.wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(fn, *args, **kwargs)

    return wrapper


def _flatten_html(fragment: str) -> str:
    """Reduce an HTML fragment to readable text, keeping list items comma-separated."""
    text = re.sub(r"</li>\s*<li>", ", ", fragment)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


async def fetch_url(url: str, timeout: int) -> str:
    """Fetch a URL via Jina Reader and return the page's markdown content."""
    async with httpx2.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers=JINA_HEADERS)
        response.raise_for_status()
        body = response.text

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
