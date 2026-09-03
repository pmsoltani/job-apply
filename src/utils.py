import asyncio
import re
import subprocess
from logging import Logger

import aiohttp


async def fetch_url(url: str, timeout: int) -> str:
    """Fetch a URL via Jina Reader and return raw markdown."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    async with (
        aiohttp.ClientSession() as session,
        session.get(url, timeout=client_timeout) as response,
    ):
        response.raise_for_status()
        return await response.text()


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
