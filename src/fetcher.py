import re

import aiohttp

from src.configs import bc


async def fetch_url(url: str) -> str:
    """Fetch a URL via Jina Reader and return raw markdown."""
    timeout = aiohttp.ClientTimeout(total=bc.TIMEOUT_SECONDS)
    async with aiohttp.ClientSession() as session:
        full_url = f"{bc.JINA_BASE_URL}/{url}"
        async with session.get(full_url, timeout=timeout) as response:
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
