import re
import httpx


ARXIV_ID_PATTERN = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")
ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"
ARXIV_API_URL = "http://export.arxiv.org/api/query?id_list={arxiv_id}"


def parse_arxiv_id(url_or_id: str) -> str:
    """Extract arXiv ID from a URL or raw ID string."""
    match = ARXIV_ID_PATTERN.search(url_or_id)
    if not match:
        raise ValueError(f"Could not parse arXiv ID from: {url_or_id}")
    return match.group(0)


async def fetch_arxiv_pdf(arxiv_id: str) -> bytes:
    """Download PDF bytes from arXiv."""
    url = ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


async def fetch_arxiv_metadata(arxiv_id: str) -> dict:
    """Fetch basic metadata (title, authors) from the arXiv API."""
    url = ARXIV_API_URL.format(arxiv_id=arxiv_id)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    # Simple XML parsing — good enough for title + authors
    text = resp.text
    title = _extract_xml_tag(text, "title")
    # First <title> is the feed title, second is the paper title
    titles = re.findall(r"<title[^>]*>(.*?)</title>", text, re.DOTALL)
    paper_title = titles[1].strip().replace("\n", " ") if len(titles) > 1 else "Untitled"

    authors = re.findall(r"<name>(.*?)</name>", text)

    return {
        "title": paper_title,
        "authors": authors,
    }


def _extract_xml_tag(xml: str, tag: str) -> str:
    match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", xml, re.DOTALL)
    return match.group(1).strip() if match else ""
