"""
URL sources for ParamSpider.

Fetches URLs from multiple web archive and threat intelligence sources:
  - Wayback Machine (web.archive.org)
  - Common Crawl (commoncrawl.org)
  - OTX AlienVault (otx.alienvault.com)
  - URLScan.io (urlscan.io)
  - VirusTotal (virustotal.com)

All endpoints verified against official API documentation (April 2026).
"""

import json
import logging
from colorama import Fore, Style
from . import client

# All available source names
AVAILABLE_SOURCES = ["wayback", "commoncrawl", "otx", "urlscan", "virustotal"]
DEFAULT_SOURCES = AVAILABLE_SOURCES  # Use all by default


def fetch_wayback(domain, proxy, **kwargs):
    """
    Fetch URLs from the Wayback Machine CDX API.

    Endpoint: https://web.archive.org/cdx/search/cdx
    Docs: https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server

    Uses output=txt with collapse=urlkey and fl=original to get unique original URLs.
    The CDX server returns up to 150,000 results per query by default.

    Args:
        domain (str): Target domain.
        proxy (str or None): Proxy address.

    Returns:
        list: List of discovered URLs.
    """
    source_name = "Wayback Machine"
    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"Querying {Fore.MAGENTA}{source_name}{Style.RESET_ALL} for {Fore.CYAN}{domain}{Style.RESET_ALL}"
    )

    url = (
        f"https://web.archive.org/cdx/search/cdx"
        f"?url={domain}/*&output=txt&collapse=urlkey&fl=original"
    )
    response = client.fetch_url_content(url, proxy)

    if response is None:
        logging.warning(
            f"{Fore.RED}[WARN]{Style.RESET_ALL} "
            f"Failed to fetch from {source_name} for {Fore.CYAN}{domain}{Style.RESET_ALL}"
        )
        return []

    urls = response.text.split()
    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"{Fore.MAGENTA}{source_name}{Style.RESET_ALL} → "
        f"{Fore.GREEN}{len(urls)}{Style.RESET_ALL} URLs"
    )
    return urls


def fetch_commoncrawl(domain, proxy, **kwargs):
    """
    Fetch URLs from the Common Crawl CDX API.
    Uses the latest available index with pagination support.

    Endpoint: https://index.commoncrawl.org/collinfo.json → {cdx-api}?url={domain}/*&output=json&fl=url
    Pagination: Appends &showNumPages=true to get page count, then iterates pages.

    Args:
        domain (str): Target domain.
        proxy (str or None): Proxy address.

    Returns:
        list: List of discovered URLs.
    """
    source_name = "Common Crawl"
    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"Querying {Fore.MAGENTA}{source_name}{Style.RESET_ALL} for {Fore.CYAN}{domain}{Style.RESET_ALL}"
    )

    # Step 1: Get available indexes
    index_url = "https://index.commoncrawl.org/collinfo.json"
    response = client.fetch_url_content(index_url, proxy)

    if response is None:
        logging.warning(
            f"{Fore.RED}[WARN]{Style.RESET_ALL} "
            f"Failed to fetch Common Crawl index list"
        )
        return []

    try:
        indexes = response.json()
    except Exception:
        logging.warning(
            f"{Fore.RED}[WARN]{Style.RESET_ALL} "
            f"Failed to parse Common Crawl index list"
        )
        return []

    if not indexes:
        logging.warning(
            f"{Fore.RED}[WARN]{Style.RESET_ALL} "
            f"No Common Crawl indexes available"
        )
        return []

    # Use the cdx-api URL from the latest index (first in the list)
    api_url = indexes[0].get("cdx-api", "")
    if not api_url:
        logging.warning(
            f"{Fore.RED}[WARN]{Style.RESET_ALL} "
            f"Common Crawl index missing cdx-api field"
        )
        return []

    # Step 2: Get number of pages
    pagination_url = f"{api_url}?url={domain}/*&output=json&fl=url&showNumPages=true"
    response = client.fetch_url_content(pagination_url, proxy)

    num_pages = 1  # Default to 1 page if pagination fails
    if response is not None:
        try:
            pagination_data = response.json()
            pages = pagination_data.get("pages", 1) if isinstance(pagination_data, dict) else 1
            num_pages = min(pages, 25)  # Cap at 25 pages to avoid excessive requests
        except Exception:
            num_pages = 1

    # Step 3: Fetch all pages
    urls = []
    for page in range(num_pages):
        cc_url = f"{api_url}?url={domain}/*&output=json&fl=url&page={page}"
        response = client.fetch_url_content(cc_url, proxy)

        if response is None:
            if page == 0:
                logging.warning(
                    f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                    f"Failed to fetch from {source_name} for {Fore.CYAN}{domain}{Style.RESET_ALL}"
                )
            break

        for line in response.text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    url_val = data.get("url", "")
                    if url_val:
                        urls.append(url_val)
                    # Check for API-level errors
                    if data.get("error"):
                        logging.warning(
                            f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                            f"Common Crawl error: {data['error']}"
                        )
                        break
            except (json.JSONDecodeError, ValueError):
                continue

    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"{Fore.MAGENTA}{source_name}{Style.RESET_ALL} → "
        f"{Fore.GREEN}{len(urls)}{Style.RESET_ALL} URLs"
    )
    return urls


def fetch_otx(domain, proxy, **kwargs):
    """
    Fetch URLs from AlienVault OTX (Open Threat Exchange).
    Paginates through all available results.

    Endpoint: https://otx.alienvault.com/api/v1/indicators/domain/{domain}/url_list
    Pagination: Uses page= parameter with has_next field.
    Auth: Pass otx_api_key via kwargs for higher rate limits.

    Args:
        domain (str): Target domain.
        proxy (str or None): Proxy address.
        **kwargs: Optional. otx_api_key (str) for authenticated requests.

    Returns:
        list: List of discovered URLs.
    """
    source_name = "OTX AlienVault"
    api_key = kwargs.get("otx_api_key")

    auth_status = f" {Fore.GREEN}(authenticated){Style.RESET_ALL}" if api_key else ""
    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"Querying {Fore.MAGENTA}{source_name}{Style.RESET_ALL} for "
        f"{Fore.CYAN}{domain}{Style.RESET_ALL}{auth_status}"
    )

    # Per OTX docs: header must be exactly "X-OTX-API-KEY"
    extra_headers = {}
    if api_key:
        extra_headers["X-OTX-API-KEY"] = api_key

    urls = []
    page = 1
    max_pages = 50  # Safety limit to avoid infinite loops

    while page <= max_pages:
        otx_url = (
            f"https://otx.alienvault.com/api/v1/indicators/domain/"
            f"{domain}/url_list?limit=200&page={page}"
        )
        response = client.fetch_url_content(otx_url, proxy, extra_headers=extra_headers or None)

        if response is None:
            if page == 1:
                logging.warning(
                    f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                    f"Failed to fetch from {source_name} for {Fore.CYAN}{domain}{Style.RESET_ALL}"
                )
            break

        try:
            data = response.json()
        except Exception:
            logging.warning(
                f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                f"Failed to parse {source_name} response for {Fore.CYAN}{domain}{Style.RESET_ALL}"
            )
            break

        url_list = data.get("url_list", [])
        if not url_list:
            break

        for entry in url_list:
            url = entry.get("url", "")
            if url:
                urls.append(url)

        # Check if there are more pages
        if not data.get("has_next", False):
            break

        page += 1

    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"{Fore.MAGENTA}{source_name}{Style.RESET_ALL} → "
        f"{Fore.GREEN}{len(urls)}{Style.RESET_ALL} URLs"
    )
    return urls


def fetch_urlscan(domain, proxy, **kwargs):
    """
    Fetch URLs from URLScan.io Search API with cursor-based pagination.

    Endpoint: https://urlscan.io/api/v1/search/?q=domain:{domain}&size=100
    Pagination: Uses search_after= parameter with sort values from last result.
    Auth: Pass urlscan_api_key via kwargs for higher rate limits.
    Docs: https://urlscan.io/docs/api/#search

    Args:
        domain (str): Target domain.
        proxy (str or None): Proxy address.
        **kwargs: Optional. urlscan_api_key (str) for authenticated requests.

    Returns:
        list: List of discovered URLs.
    """
    source_name = "URLScan.io"
    api_key = kwargs.get("urlscan_api_key")

    auth_status = f" {Fore.GREEN}(authenticated){Style.RESET_ALL}" if api_key else ""
    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"Querying {Fore.MAGENTA}{source_name}{Style.RESET_ALL} for "
        f"{Fore.CYAN}{domain}{Style.RESET_ALL}{auth_status}"
    )

    # Per URLScan docs: header must be exactly "API-Key"
    extra_headers = {}
    if api_key:
        extra_headers["API-Key"] = api_key

    urls = set()
    search_after = ""
    max_pages = 50  # Safety limit

    for page_num in range(max_pages):
        urlscan_url = f"https://urlscan.io/api/v1/search/?q=domain:{domain}&size=100"
        if search_after:
            urlscan_url += f"&search_after={search_after}"

        response = client.fetch_url_content(urlscan_url, proxy, extra_headers=extra_headers or None)

        if response is None:
            if page_num == 0:
                logging.warning(
                    f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                    f"Failed to fetch from {source_name} for {Fore.CYAN}{domain}{Style.RESET_ALL}"
                )
            break

        try:
            data = response.json()
        except Exception:
            logging.warning(
                f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                f"Failed to parse {source_name} response for {Fore.CYAN}{domain}{Style.RESET_ALL}"
            )
            break

        # Check for rate limiting (HTTP 429 is returned in the JSON body as status)
        if data.get("status") == 429:
            hint = " Use --urlscan-api to authenticate." if not api_key else ""
            logging.warning(
                f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                f"{source_name} rate limited.{hint}"
            )
            break

        results = data.get("results", [])
        if not results:
            break

        for result in results:
            page_url = result.get("page", {}).get("url", "")
            if page_url:
                urls.add(page_url)

        # Get search_after cursor from the last result's sort field
        last_result = results[-1]
        sort_values = last_result.get("sort", [])
        if sort_values:
            # Convert sort values to comma-separated string for the query parameter
            search_after = ",".join(str(v) for v in sort_values)
        else:
            break

        # Check if there are more results
        if not data.get("has_more", False):
            break

    urls = list(urls)
    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"{Fore.MAGENTA}{source_name}{Style.RESET_ALL} → "
        f"{Fore.GREEN}{len(urls)}{Style.RESET_ALL} URLs"
    )
    return urls

def fetch_virustotal(domain, proxy, **kwargs):
    """
    Fetch URLs from VirusTotal API v3.
    Uses cursor-based pagination via links.next.

    Endpoint: https://www.virustotal.com/api/v3/domains/{domain}/urls
    Auth: Requires x-apikey header (free signup at virustotal.com).
    Rate limit: 4 req/min, 500 req/day (free tier).
    Docs: https://docs.virustotal.com/reference/domain-urls

    Args:
        domain (str): Target domain.
        proxy (str or None): Proxy address.
        **kwargs: Required. virustotal_api_key (str) for authentication.

    Returns:
        list: List of discovered URLs.
    """
    source_name = "VirusTotal"
    api_key = kwargs.get("virustotal_api_key")

    if not api_key:
        logging.info(
            f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
            f"Skipping {Fore.MAGENTA}{source_name}{Style.RESET_ALL} "
            f"(VIRUSTOTAL_API_KEY not set)"
        )
        return []

    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"Querying {Fore.MAGENTA}{source_name}{Style.RESET_ALL} for "
        f"{Fore.CYAN}{domain}{Style.RESET_ALL} {Fore.GREEN}(authenticated){Style.RESET_ALL}"
    )

    extra_headers = {"X-Apikey": api_key}

    urls = set()
    api_url = f"https://www.virustotal.com/api/v3/domains/{domain}/urls?limit=40"
    max_pages = 25  # Safety limit (40 * 25 = 1000 URLs max)

    for page_num in range(max_pages):
        response = client.fetch_url_content(api_url, proxy, extra_headers=extra_headers)

        if response is None:
            if page_num == 0:
                logging.warning(
                    f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                    f"Failed to fetch from {source_name} for {Fore.CYAN}{domain}{Style.RESET_ALL}"
                )
            break

        try:
            data = response.json()
        except Exception:
            logging.warning(
                f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                f"Failed to parse {source_name} response for {Fore.CYAN}{domain}{Style.RESET_ALL}"
            )
            break

        # Check for API errors
        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            logging.warning(
                f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                f"{source_name} API error: {error_msg}"
            )
            break

        results = data.get("data", [])
        if not results:
            break

        for entry in results:
            url = entry.get("attributes", {}).get("url", "")
            if url:
                urls.add(url)

        # Cursor-based pagination: follow links.next
        next_url = data.get("links", {}).get("next")
        if not next_url:
            break
        api_url = next_url

    urls = list(urls)
    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"{Fore.MAGENTA}{source_name}{Style.RESET_ALL} → "
        f"{Fore.GREEN}{len(urls)}{Style.RESET_ALL} URLs"
    )
    return urls


# Map source names to their fetch functions
SOURCE_FUNCTIONS = {
    "wayback": fetch_wayback,
    "commoncrawl": fetch_commoncrawl,
    "otx": fetch_otx,
    "urlscan": fetch_urlscan,
    "virustotal": fetch_virustotal,
}


def fetch_urls_from_sources(domain, proxy, sources=None, urlscan_api_key=None, otx_api_key=None, virustotal_api_key=None):
    """
    Fetch URLs from multiple sources and aggregate the results.

    Args:
        domain (str): Target domain.
        proxy (str or None): Proxy address.
        sources (list or None): List of source names to use. If None, uses all sources.
        urlscan_api_key (str or None): API key for URLScan.io (higher rate limits).
        otx_api_key (str or None): API key for OTX AlienVault (higher rate limits).
        virustotal_api_key (str or None): API key for VirusTotal (required for access).

    Returns:
        list: Aggregated, deduplicated list of URLs from all sources.
    """
    if sources is None:
        sources = DEFAULT_SOURCES

    # Build kwargs per source
    source_kwargs = {
        "urlscan": {"urlscan_api_key": urlscan_api_key} if urlscan_api_key else {},
        "otx": {"otx_api_key": otx_api_key} if otx_api_key else {},
        "virustotal": {"virustotal_api_key": virustotal_api_key} if virustotal_api_key else {},
    }

    all_urls = set()

    for source_name in sources:
        fetch_fn = SOURCE_FUNCTIONS.get(source_name)
        if fetch_fn is None:
            logging.warning(
                f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                f"Unknown source: {Fore.CYAN}{source_name}{Style.RESET_ALL}. "
                f"Available: {', '.join(AVAILABLE_SOURCES)}"
            )
            continue

        try:
            kwargs = source_kwargs.get(source_name, {})
            urls = fetch_fn(domain, proxy, **kwargs)
            all_urls.update(urls)
        except Exception as e:
            logging.warning(
                f"{Fore.RED}[WARN]{Style.RESET_ALL} "
                f"Error fetching from {source_name}: {e}"
            )
            continue

    return list(all_urls)
