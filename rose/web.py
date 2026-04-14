"""
ROSE Web Utilities — HTTP requests, scraping, downloads with source citation.
"""

import json
from pathlib import Path

from rose.config import DOWNLOADS_DIR
from rose import formatter


def fetch_url(url: str, method: str = "GET", headers: dict = None,
              body: str = None, timeout: int = 30) -> dict:
    """
    Fetch content from a URL. Returns dict with status, body, headers.
    """
    try:
        import httpx
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            if method.upper() == "GET":
                resp = client.get(url, headers=headers)
            elif method.upper() == "POST":
                resp = client.post(url, headers=headers, content=body)
            else:
                return {"error": f"Unsupported method: {method}"}

            return {
                "status_code": resp.status_code,
                "body": resp.text[:20000],
                "content_type": resp.headers.get("content-type", ""),
                "url": str(resp.url),
            }
    except Exception as e:
        return {"error": str(e)}


def scrape_text(url: str) -> str:
    """
    Fetch a URL and extract readable text content (strips HTML).
    """
    try:
        import httpx
        from bs4 import BeautifulSoup

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove scripts, styles, nav elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse multiple blank lines
        lines = [line for line in text.splitlines() if line.strip()]
        result = "\n".join(lines[:500])  # Limit output

        formatter.source(url)
        return result

    except ImportError:
        return "Error: beautifulsoup4 not installed. Run: pip install beautifulsoup4"
    except Exception as e:
        return f"Error scraping {url}: {e}"


def download_file(url: str, filename: str = None, dest_dir: Path = None) -> Path | None:
    """
    Download a file to the workspace downloads directory.
    Returns the path to the downloaded file, or None on failure.
    """
    try:
        import httpx

        target_dir = dest_dir or DOWNLOADS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        if not filename:
            filename = url.split("/")[-1].split("?")[0] or "download"

        dest = target_dir / filename

        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0

                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = int(downloaded / total * 100)
                            print(f"\r  Downloading: {pct}%", end="", flush=True)

                if total > 0:
                    print()  # Newline after progress

        size_kb = dest.stat().st_size / 1024
        formatter.rose(f"Downloaded: {dest} ({size_kb:.1f} KB)")
        return dest

    except Exception as e:
        formatter.err(f"Download failed: {e}")
        return None
