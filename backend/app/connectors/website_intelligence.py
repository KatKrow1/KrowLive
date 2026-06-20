"""Scrape company websites for leadership contacts and public contact details."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

ROLE_KEYWORDS = (
    "CEO",
    "Chief Executive Officer",
    "Chief Executive",
    "Founder",
    "Co-Founder",
    "Co Founder",
    "President",
    "Vice President",
    "VP",
    "Director",
    "Head of",
    "Manager",
    "Owner",
    "CTO",
    "CFO",
    "COO",
    "Managing Director",
    "General Manager",
)

TEAM_PATH_RE = re.compile(
    r"/(?:about(?:-us)?|team|leadership|contact(?:-us)?|people|our-team|"
    r"meet-the-team|who-we-are|management-team|executives?)(?:/|$)",
    re.IGNORECASE,
)

INVALID_NAME_TOKENS = frozenset(
    {
        "toronto",
        "president",
        "manager",
        "director",
        "owner",
        "coordinator",
        "operations",
        "support",
        "software",
        "service",
        "development",
        "applications",
        "site",
        "core",
        "values",
        "people",
    }
)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}(?:[\s.-]?\d{1,6})?"
)
NAME_RE = re.compile(r"^[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?(?:\s+[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?){0,3}$")
ROLE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in ROLE_KEYWORDS) + r")[^.\n]{0,80}",
    re.IGNORECASE,
)
JUNK_EMAIL_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")

SOCIAL_DOMAINS = {
    "linkedin": ("linkedin.com",),
    "twitter": ("twitter.com", "x.com"),
    "instagram": ("instagram.com",),
    "facebook": ("facebook.com", "fb.com"),
}

LINKEDIN_PROFILE_RE = re.compile(r"https?://(?:[\w.-]+\.)?linkedin\.com/(?:in|company)/[\w\-_%./]+", re.I)

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}


@dataclass
class ExecutiveContact:
    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    consent_status: str = "unknown"
    source_page: str | None = None


@dataclass
class WebsiteIntelResult:
    website: str
    success: bool
    pages_scraped: list[str] = field(default_factory=list)
    page_texts: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    executives: list[ExecutiveContact] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)
    error: str | None = None


def _is_linkedin_profile(url: str) -> bool:
    return bool(LINKEDIN_PROFILE_RE.match(url.strip()))


def _classify_social_url(url: str) -> str | None:
    lower = url.lower()
    for platform, domains in SOCIAL_DOMAINS.items():
        if any(domain in lower for domain in domains):
            return platform
    return None


def _extract_social_links(soup: BeautifulSoup) -> dict[str, str]:
    """Extract social URLs the company linked on their own site — do not visit them."""
    found: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href.startswith(("http://", "https://")):
            continue
        platform = _classify_social_url(href)
        if platform and platform not in found:
            found[platform] = href.split("?", 1)[0].rstrip("/")
    return found


def _linkedin_from_element(element: Any) -> str | None:
    if element.name == "a":
        href = element.get("href", "")
        if href and _is_linkedin_profile(href):
            return href.split("?", 1)[0].rstrip("/")
    parent_link = element.find_parent("a", href=True)
    if parent_link:
        href = parent_link.get("href", "")
        if href and _is_linkedin_profile(href):
            return href.split("?", 1)[0].rstrip("/")
    return None


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _same_domain(base: str, candidate: str) -> bool:
    return urlparse(base).netloc.replace("www.", "") == urlparse(candidate).netloc.replace("www.", "")


def _clean_email(email: str) -> str | None:
    email = email.strip().lower().rstrip("%20")
    if any(email.endswith(suffix) for suffix in JUNK_EMAIL_SUFFIXES):
        return None
    if email.startswith(("noreply@", "no-reply@", "donotreply@", "mailer-daemon@")):
        return None
    return email


def _clean_phone(phone: str) -> str | None:
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10:
        return None
    return re.sub(r"\s+", " ", phone.strip())


def _extract_emails(text: str, soup: BeautifulSoup | None = None) -> set[str]:
    found: set[str] = set()
    for match in EMAIL_RE.findall(text):
        cleaned = _clean_email(match)
        if cleaned:
            found.add(cleaned)
    if soup:
        for anchor in soup.select("a[href^='mailto:']"):
            href = anchor.get("href", "")
            email = href.split("mailto:", 1)[-1].split("?", 1)[0].strip()
            cleaned = _clean_email(email)
            if cleaned:
                found.add(cleaned)
    return found


def _extract_phones(text: str, soup: BeautifulSoup | None = None) -> set[str]:
    found: set[str] = set()
    for match in PHONE_RE.findall(text):
        cleaned = _clean_phone(match)
        if cleaned:
            found.add(cleaned)
    if soup:
        for anchor in soup.select("a[href^='tel:']"):
            href = anchor.get("href", "")
            phone = href.split("tel:", 1)[-1].strip()
            cleaned = _clean_phone(phone)
            if cleaned:
                found.add(cleaned)
    return found


def _looks_like_name(value: str) -> bool:
    value = value.strip()
    if not value or len(value) > 50:
        return False
    if any(ch.isdigit() for ch in value):
        return False
    lower = value.lower()
    if lower in INVALID_NAME_TOKENS:
        return False
    words = lower.split()
    if any(word in INVALID_NAME_TOKENS for word in words):
        return False
    if any(re.search(rf"\b{re.escape(keyword)}\b", value, re.I) for keyword in ROLE_KEYWORDS):
        return False
    return bool(NAME_RE.match(value))


def _extract_role_title(text: str) -> str | None:
    for keyword in sorted(ROLE_KEYWORDS, key=len, reverse=True):
        match = re.search(rf"\b{re.escape(keyword)}\b", text, re.IGNORECASE)
        if not match:
            continue
        start = match.start()
        snippet = text[start : start + 80].strip(" ,-|")
        snippet = re.split(r"[|\n]", snippet, maxsplit=1)[0].strip()
        if len(snippet) <= 60:
            return snippet
    return None


def _name_from_text(text: str) -> str | None:
    for part in re.split(r"[|\n,–—-]", text):
        candidate = part.strip()
        if _looks_like_name(candidate):
            return candidate
    words = text.split()
    for size in (4, 3, 2):
        if len(words) >= size:
            candidate = " ".join(words[:size])
            if _looks_like_name(candidate):
                return candidate
    return None


def _extract_team_cards(soup: BeautifulSoup, page_url: str) -> list[ExecutiveContact]:
    executives: list[ExecutiveContact] = []
    card_selectors = (
        "[class*='team-member']",
        "[class*='team_member']",
        "[class*='member-card']",
        "[class*='staff-member']",
        "[class*='leadership']",
        "[class*='person-card']",
    )
    cards: list[Any] = []
    for selector in card_selectors:
        cards.extend(soup.select(selector))

    for card in cards:
        heading = card.find(["h2", "h3", "h4", "h5", "strong"])
        if not heading:
            continue
        name = heading.get_text(" ", strip=True)
        if not _looks_like_name(name):
            continue
        title_text = card.get_text(" ", strip=True)
        title = _extract_role_title(title_text.replace(name, "", 1))
        if not title:
            continue
        linkedin = _linkedin_from_element(heading)
        executives.append(
            ExecutiveContact(
                name=name,
                title=title,
                linkedin_url=linkedin,
                source_page=page_url,
            )
        )
    return executives


def _extract_executives(soup: BeautifulSoup, page_url: str) -> list[ExecutiveContact]:
    if not TEAM_PATH_RE.search(urlparse(page_url).path):
        return []

    executives = _extract_team_cards(soup, page_url)
    seen = {(e.name.lower(), (e.title or "").lower()) for e in executives}

    for tag in soup.find_all(["h2", "h3", "h4", "p", "li"]):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if not text or not ROLE_PATTERN.search(text):
            continue
        title = _extract_role_title(text)
        if not title:
            continue
        name = _name_from_text(text.replace(title, "", 1))
        if not name:
            continue
        key = (name.lower(), title.lower())
        if key in seen:
            continue
        seen.add(key)
        linkedin = _linkedin_from_element(tag)
        executives.append(
            ExecutiveContact(
                name=name,
                title=title,
                linkedin_url=linkedin,
                source_page=page_url,
            )
        )

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if not _is_linkedin_profile(href):
            continue
        name = anchor.get_text(" ", strip=True)
        if not _looks_like_name(name):
            continue
        parent_text = anchor.find_parent(["li", "div", "article"])
        title = _extract_role_title(parent_text.get_text(" ", strip=True) if parent_text else name)
        key = (name.lower(), (title or "").lower())
        if key in seen:
            continue
        seen.add(key)
        executives.append(
            ExecutiveContact(
                name=name,
                title=title,
                linkedin_url=href.split("?", 1)[0].rstrip("/"),
                source_page=page_url,
            )
        )

    return executives[:20]


def _discover_pages(base_url: str, soup: BeautifulSoup, max_pages: int = 4) -> list[str]:
    pages = [base_url]
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        if not _same_domain(base_url, absolute):
            continue
        path = urlparse(absolute).path.lower()
        if TEAM_PATH_RE.search(path):
            if absolute not in pages:
                pages.append(absolute.split("#")[0])
        if len(pages) >= max_pages:
            break
    return pages[:max_pages]


async def _fetch_with_httpx(url: str, timeout: float = 15.0) -> str | None:
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers=HTTP_HEADERS,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None
            return response.text
    except (httpx.HTTPError, UnicodeDecodeError):
        return None


async def _fetch_with_playwright(url: str, timeout_ms: int = 20000) -> str | None:
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=HTTP_HEADERS["User-Agent"])
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(1500)
            html = await page.content()
            await browser.close()
            return html
    except Exception:
        return None


async def _fetch_page(url: str) -> str | None:
    html = await _fetch_with_httpx(url)
    if html and len(html) > 500:
        return html
    return await _fetch_with_playwright(url)


def _parse_page(html: str, page_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    excerpt = text[:2500].strip()
    return {
        "soup": soup,
        "text": text,
        "excerpt": excerpt,
        "emails": _extract_emails(text, soup),
        "phones": _extract_phones(text, soup),
        "executives": _extract_executives(soup, page_url),
        "social_links": _extract_social_links(soup),
    }


async def scrape_website(website: str, *, max_pages: int = 4) -> WebsiteIntelResult:
    """Scrape a company website; return partial/empty data instead of raising."""
    base_url = _normalize_url(website)
    result = WebsiteIntelResult(website=base_url, success=False)

    try:
        homepage_html = await _fetch_page(base_url)
        if not homepage_html:
            result.error = "Site failed to load (httpx and Playwright both failed)"
            return result

        homepage_soup = BeautifulSoup(homepage_html, "html.parser")
        pages = _discover_pages(base_url, homepage_soup, max_pages=max_pages)

        all_emails: set[str] = set()
        all_phones: set[str] = set()
        all_social: dict[str, str] = {}
        page_texts: list[str] = []
        executives: list[ExecutiveContact] = []
        seen_exec: set[tuple[str, str | None]] = set()

        for page_url in pages:
            html = homepage_html if page_url == base_url else await _fetch_page(page_url)
            if not html:
                continue
            parsed = _parse_page(html, page_url)
            result.pages_scraped.append(page_url)
            if parsed["excerpt"]:
                page_texts.append(parsed["excerpt"])
            all_emails.update(parsed["emails"])
            all_phones.update(parsed["phones"])
            for platform, url in parsed["social_links"].items():
                all_social.setdefault(platform, url)
            for exec_contact in parsed["executives"]:
                key = (exec_contact.name.lower(), (exec_contact.title or "").lower())
                if key in seen_exec:
                    continue
                seen_exec.add(key)
                executives.append(exec_contact)

        result.page_texts = page_texts
        result.emails = sorted(all_emails)
        result.phones = sorted(all_phones)
        result.social_links = all_social
        result.executives = executives
        result.success = bool(result.pages_scraped)
        if not result.success:
            result.error = "No pages could be scraped"
        return result
    except Exception as exc:  # noqa: BLE001 — intentional graceful fallback for scraper
        result.error = f"Unexpected scrape error: {exc}"
        return result


def scrape_website_sync(website: str, *, max_pages: int = 4) -> WebsiteIntelResult:
    """Synchronous wrapper for scripts and non-async callers."""
    return asyncio.run(scrape_website(website, max_pages=max_pages))
