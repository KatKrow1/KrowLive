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

NAME_DENYLIST = frozenset(
    {
        "follow",
        "linkedin",
        "twitter",
        "facebook",
        "instagram",
        "youtube",
        "menu",
        "home",
        "about",
        "contact",
        "services",
        "blog",
        "news",
        "login",
        "subscribe",
        "share",
        "project",
        "team",
        "careers",
        "privacy",
        "terms",
        "cookie",
        "cookies",
        "copyright",
        "read",
        "more",
        "learn",
        "view",
        "click",
        "here",
        "email",
        "phone",
        "search",
        "close",
        "open",
        "solutions",
        "agency",
        "digital",
        "marketing",
        "media",
        "toronto",
        "ottawa",
        "canada",
        "people",
        "values",
        "core",
        "site",
        "support",
        "software",
        "service",
        "development",
        "applications",
        "operations",
        "coordinator",
        "local",
        "business",
        "app",
        "executive",
        "producer",
        "video",
        "creative",
        "production",
        "design",
        "designs",
        "web",
        "senior",
        "junior",
        "assistant",
        "specialist",
        "consultant",
        "strategist",
        "developer",
        "engineer",
        "designer",
    }
)

COMMON_SINGLE_NOUNS = frozenset(
    {
        "president",
        "manager",
        "director",
        "owner",
        "founder",
        "partner",
        "lead",
        "head",
        "chief",
        "executive",
        "officer",
        "project",
        "follow",
        "linkedin",
    }
)

TEAM_CONTAINER_HINTS = (
    "team",
    "staff",
    "leadership",
    "people",
    "founder",
    "bio",
    "member",
    "executive",
    "management",
)

NAME_CLASS_HINTS = ("name", "person", "member", "author", "profile")
TITLE_CLASS_HINTS = ("title", "role", "position", "job", "designation")

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}(?:[\s.-]?\d{1,6})?"
)
# 2–4 capitalized name parts (Jane Smith, Mary-Jane O'Brien)
HUMAN_NAME_RE = re.compile(
    r"^[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?(?:\s+[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?){1,3}$"
)
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

LINKEDIN_PERSON_RE = re.compile(r"https?://(?:[\w.-]+\.)?linkedin\.com/in/[\w\-_%./]+", re.I)
LINKEDIN_COMPANY_RE = re.compile(r"https?://(?:[\w.-]+\.)?linkedin\.com/company/[\w\-_%./]+", re.I)
LINKEDIN_PROFILE_RE = LINKEDIN_PERSON_RE  # legacy alias

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
    extraction_confidence: str = "low"


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


def _is_linkedin_person(url: str) -> bool:
    return bool(LINKEDIN_PERSON_RE.match(url.strip()))


def _is_linkedin_company(url: str) -> bool:
    return bool(LINKEDIN_COMPANY_RE.match(url.strip()))


def _is_linkedin_profile(url: str) -> bool:
    return _is_linkedin_person(url) or _is_linkedin_company(url)


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


def _linkedin_from_element(element: Any, *, person_only: bool = False) -> str | None:
    def _pick(href: str) -> str | None:
        if not href:
            return None
        if person_only and not _is_linkedin_person(href):
            return None
        if not person_only and not _is_linkedin_profile(href):
            return None
        return href.split("?", 1)[0].rstrip("/")

    if element.name == "a":
        picked = _pick(element.get("href", ""))
        if picked:
            return picked
    for anchor in element.find_all("a", href=True):
        picked = _pick(anchor["href"])
        if picked:
            return picked
    parent_link = element.find_parent("a", href=True)
    if parent_link:
        return _pick(parent_link.get("href", ""))
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
    """Reject nav/UI text; require a plausible human name (2+ capitalized words)."""
    value = " ".join(value.split())
    if not value or len(value) > 60:
        return False
    if any(ch.isdigit() for ch in value):
        return False
    lower = value.lower()
    if lower in NAME_DENYLIST:
        return False
    words = value.split()
    if len(words) < 2:
        return False
    if any(word.lower() in NAME_DENYLIST for word in words):
        return False
    if any(word.lower() in COMMON_SINGLE_NOUNS for word in words):
        return False
    if not HUMAN_NAME_RE.match(value):
        return False
    return True


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


def _element_hints(element: Any) -> str:
    parts: list[str] = []
    for attr in ("class", "id"):
        raw = element.get(attr)
        if isinstance(raw, list):
            parts.extend(str(x).lower() for x in raw)
        elif raw:
            parts.append(str(raw).lower())
    return " ".join(parts)


def _is_team_container(element: Any) -> bool:
    hints = _element_hints(element)
    return any(token in hints for token in TEAM_CONTAINER_HINTS)


def _find_team_sections(soup: BeautifulSoup) -> list[Any]:
    sections: list[Any] = []
    seen: set[int] = set()
    for element in soup.find_all(["section", "div", "ul", "article"]):
        if id(element) in seen:
            continue
        if _is_team_container(element):
            seen.add(id(element))
            sections.append(element)
    return sections


def _split_name_title(text: str) -> tuple[str | None, str | None]:
    """Parse 'Jane Smith, CEO' or 'Jane Smith | CEO' in one line."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return None, None
    for sep in (",", "|", " – ", " — ", " - "):
        if sep in cleaned:
            left, right = cleaned.split(sep, 1)
            name = left.strip()
            title = _extract_role_title(right.strip())
            if _looks_like_name(name) and title:
                return name, title
    name = _name_from_text(cleaned)
    if name:
        remainder = cleaned.replace(name, "", 1).strip(" ,-|")
        title = _extract_role_title(remainder) if remainder else None
        if title:
            return name, title
    return None, None


def _find_name_element(container: Any) -> Any | None:
    for tag in container.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "strong", "span", "p"]):
        hints = _element_hints(tag)
        text = tag.get_text(" ", strip=True)
        if any(h in hints for h in NAME_CLASS_HINTS):
            if _looks_like_name(text):
                return tag
            name, title = _split_name_title(text)
            if name and title:
                return tag
        if tag.name in {"h2", "h3", "h4", "h5", "strong"}:
            if _looks_like_name(text):
                return tag
            name, title = _split_name_title(text)
            if name and title:
                return tag
    return None


def _find_title_element(container: Any, name: str) -> str | None:
    for tag in container.find_all(["p", "span", "div", "h5", "h6", "em", "small"]):
        hints = _element_hints(tag)
        if any(h in hints for h in TITLE_CLASS_HINTS):
            title = _extract_role_title(tag.get_text(" ", strip=True))
            if title:
                return title
    for tag in container.find_all(["p", "span", "em", "small"]):
        text = tag.get_text(" ", strip=True)
        if name in text:
            continue
        title = _extract_role_title(text)
        if title and len(text) <= 80:
            return title
    blob = container.get_text(" ", strip=True).replace(name, "", 1)
    return _extract_role_title(blob)


def _contacts_in_container(container: Any) -> tuple[str | None, str | None, str | None]:
    email = phone = linkedin = None
    for anchor in container.find_all("a", href=True):
        href = anchor["href"].strip()
        if href.startswith("mailto:") and not email:
            cleaned = _clean_email(href.split("mailto:", 1)[-1].split("?", 1)[0])
            if cleaned:
                email = cleaned
        elif href.startswith("tel:") and not phone:
            cleaned = _clean_phone(href.split("tel:", 1)[-1])
            if cleaned:
                phone = cleaned
        elif _is_linkedin_person(href) and not linkedin:
            linkedin = href.split("?", 1)[0].rstrip("/")
    if not email:
        for match in EMAIL_RE.findall(container.get_text(" ", strip=True)):
            cleaned = _clean_email(match)
            if cleaned:
                email = cleaned
                break
    if not phone:
        for match in PHONE_RE.findall(container.get_text(" ", strip=True)):
            cleaned = _clean_phone(match)
            if cleaned:
                phone = cleaned
                break
    return email, phone, linkedin


def _confidence(structural: bool, email: str | None, phone: str | None, linkedin: str | None) -> str:
    if structural and (email or phone or linkedin):
        return "high"
    if structural:
        return "medium"
    return "low"


def _extract_structural_pairs(container: Any, page_url: str) -> list[ExecutiveContact]:
    results: list[ExecutiveContact] = []
    card_tags = container.find_all(["div", "li", "article"], recursive=True)
    candidates = [c for c in card_tags if _is_team_container(c)] or [container]

    for card in candidates:
        name_el = _find_name_element(card)
        if not name_el:
            continue
        raw_name_text = name_el.get_text(" ", strip=True)
        name, combined_title = _split_name_title(raw_name_text)
        if not name:
            name = raw_name_text
        if not _looks_like_name(name):
            continue
        title = combined_title or _find_title_element(card, name)
        if not title:
            continue
        email, phone, linkedin = _contacts_in_container(card)
        if not linkedin:
            linkedin = _linkedin_from_element(name_el, person_only=True)
        results.append(
            ExecutiveContact(
                name=name,
                title=title,
                email=email,
                phone=phone,
                linkedin_url=linkedin,
                source_page=page_url,
                extraction_confidence=_confidence(True, email, phone, linkedin),
            )
        )
    return results


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


def _card_is_reasonable(card: Any) -> bool:
    """Skip page wrappers; keep card-sized blocks likely to hold one person."""
    nested = card.find_all(["div", "li", "article"])
    if len(nested) > 25:
        return False
    text = card.get_text(" ", strip=True)
    return 10 <= len(text) <= 600


def _extract_inline_name_title(soup: BeautifulSoup, page_url: str) -> list[ExecutiveContact]:
    """Handle 'Jane Smith, CEO' in a single heading/strong element."""
    results: list[ExecutiveContact] = []
    for tag in soup.find_all(["strong", "h2", "h3", "h4", "h5", "h6"]):
        name, title = _split_name_title(tag.get_text(" ", strip=True))
        if not name or not title:
            continue
        parent = tag.find_parent(["li", "div", "article", "section"]) or tag
        email, phone, linkedin = _contacts_in_container(parent)
        if not linkedin:
            linkedin = _linkedin_from_element(tag, person_only=True)
        results.append(
            ExecutiveContact(
                name=name,
                title=title,
                email=email,
                phone=phone,
                linkedin_url=linkedin,
                source_page=page_url,
                extraction_confidence=_confidence(True, email, phone, linkedin),
            )
        )
    return results


def _extract_team_cards(soup: BeautifulSoup, page_url: str) -> list[ExecutiveContact]:
    executives: list[ExecutiveContact] = []
    executives.extend(_extract_inline_name_title(soup, page_url))
    for section in _find_team_sections(soup):
        executives.extend(_extract_structural_pairs(section, page_url))

    card_selectors = (
        "[class*='team-member']",
        "[class*='team_member']",
        "[class*='member-card']",
        "[class*='staff-member']",
        "[class*='leadership']",
        "[class*='person-card']",
        "[class*='bio']",
    )
    for selector in card_selectors:
        for card in soup.select(selector):
            executives.extend(_extract_structural_pairs(card, page_url))

    on_team_path = bool(TEAM_PATH_RE.search(urlparse(page_url).path))
    if on_team_path:
        for card in soup.find_all(["div", "li", "article"]):
            if not _card_is_reasonable(card):
                continue
            executives.extend(_extract_structural_pairs(card, page_url))
    return executives


def _extract_proximity_fallback(soup: BeautifulSoup, page_url: str) -> list[ExecutiveContact]:
    executives: list[ExecutiveContact] = []
    for tag in soup.find_all(["h2", "h3", "h4", "p", "li"]):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if not text or not ROLE_PATTERN.search(text):
            continue
        title = _extract_role_title(text)
        if not title:
            continue
        name = _name_from_text(text.replace(title, "", 1))
        structural = False
        if not name:
            name = _name_from_text(text)
            if name and title and name not in title:
                structural = True
        if not name:
            continue
        parent = tag.find_parent(["li", "div", "article"]) or tag
        if not structural:
            name_el = _find_name_element(parent)
            if name_el and name_el.get_text(" ", strip=True) == name and _find_title_element(parent, name):
                structural = True
        email, phone, linkedin = _contacts_in_container(parent)
        if not linkedin:
            linkedin = _linkedin_from_element(tag, person_only=True)
        executives.append(
            ExecutiveContact(
                name=name,
                title=title,
                email=email,
                phone=phone,
                linkedin_url=linkedin,
                source_page=page_url,
                extraction_confidence=_confidence(structural, email, phone, linkedin),
            )
        )

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        if not _is_linkedin_person(href):
            continue
        name = anchor.get_text(" ", strip=True)
        if not _looks_like_name(name):
            continue
        parent = anchor.find_parent(["li", "div", "article"])
        title = _extract_role_title(parent.get_text(" ", strip=True) if parent else name)
        email, phone, linkedin = _contacts_in_container(parent) if parent else (None, None, None)
        linkedin = linkedin or href.split("?", 1)[0].rstrip("/")
        executives.append(
            ExecutiveContact(
                name=name,
                title=title,
                email=email,
                phone=phone,
                linkedin_url=linkedin,
                source_page=page_url,
                extraction_confidence=_confidence(bool(parent), email, phone, linkedin),
            )
        )
    return executives


def _extract_executives(soup: BeautifulSoup, page_url: str) -> list[ExecutiveContact]:
    on_team_path = bool(TEAM_PATH_RE.search(urlparse(page_url).path))
    if not on_team_path and not _find_team_sections(soup):
        return []

    executives = _extract_team_cards(soup, page_url)
    seen = {(e.name.lower(), (e.title or "").lower()) for e in executives}

    for candidate in _extract_proximity_fallback(soup, page_url):
        key = (candidate.name.lower(), (candidate.title or "").lower())
        if key in seen:
            continue
        seen.add(key)
        executives.append(candidate)

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
