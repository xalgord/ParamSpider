import argparse
import os
import logging
import colorama
from colorama import Fore, Style
from . import client
from .sources import fetch_urls_from_sources, AVAILABLE_SOURCES, DEFAULT_SOURCES
from urllib.parse import urlparse, parse_qs, urlencode

yellow_color_code = "\033[93m"
reset_color_code = "\033[0m"

colorama.init(autoreset=True)

log_format = '%(message)s'
logging.basicConfig(format=log_format, level=logging.INFO)
logging.getLogger('').handlers[0].setFormatter(logging.Formatter(log_format))

HARDCODED_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".gif", ".pdf", ".svg", ".json",
    ".css", ".js", ".webp", ".woff", ".woff2", ".eot", ".ttf", ".otf", ".mp4", ".txt"
]

def has_extension(url, extensions):
    """
    Check if the URL has a file extension matching any of the provided extensions.

    Args:
        url (str): The URL to check.
        extensions (list): List of file extensions to match against.

    Returns:
        bool: True if the URL has a matching extension, False otherwise.
    """
    parsed_url = urlparse(url)
    path = parsed_url.path
    extension = os.path.splitext(path)[1].lower()

    return extension in extensions

def clean_url(url):
    """
    Clean the URL by removing redundant port information for HTTP and HTTPS URLs.

    Args:
        url (str): The URL to clean.

    Returns:
        str: Cleaned URL.
    """
    parsed_url = urlparse(url)
    
    if (parsed_url.port == 80 and parsed_url.scheme == "http") or (parsed_url.port == 443 and parsed_url.scheme == "https"):
        parsed_url = parsed_url._replace(netloc=parsed_url.netloc.rsplit(":", 1)[0])

    return parsed_url.geturl()

def clean_urls(urls, extensions, placeholder):
    """
    Clean a list of URLs by removing unnecessary parameters and query strings.
    Only returns URLs that contain query parameters.

    Args:
        urls (list): List of URLs to clean.
        extensions (list): List of file extensions to check against.
        placeholder (str): Placeholder value for parameter values.

    Returns:
        list: List of cleaned URLs that contain query parameters.
    """
    cleaned_urls = set()
    for url in urls:
        cleaned_url = clean_url(url)
        if not has_extension(cleaned_url, extensions):
            parsed_url = urlparse(cleaned_url)
            query_params = parse_qs(parsed_url.query)

            if not query_params:
                continue

            cleaned_params = {key: placeholder for key in query_params}
            cleaned_query = urlencode(cleaned_params, doseq=True)
            cleaned_url = parsed_url._replace(query=cleaned_query).geturl()
            cleaned_urls.add(cleaned_url)
    return list(cleaned_urls)

def fetch_and_clean_urls(domain, extensions, stream_output, proxy, placeholder, sources=None, urlscan_api_key=None):
    """
    Fetch URLs from multiple sources, clean them, and save to file.

    Args:
        domain (str): The domain name to fetch URLs for.
        extensions (list): List of file extensions to check against.
        stream_output (bool): True to stream URLs to the terminal.
        proxy (str or None): Proxy address for web requests.
        placeholder (str): Placeholder value for parameter values.
        sources (list or None): List of source names to use.
        urlscan_api_key (str or None): API key for URLScan.io.

    Returns:
        bool: True if URLs were fetched and saved successfully, False otherwise.
    """
    logging.info(
        f"\n{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"Mining URLs for {Fore.CYAN}{domain}{Style.RESET_ALL} "
        f"[sources: {Fore.MAGENTA}{', '.join(sources or DEFAULT_SOURCES)}{Style.RESET_ALL}]"
    )

    urls = fetch_urls_from_sources(domain, proxy, sources, urlscan_api_key=urlscan_api_key)

    if not urls:
        logging.info(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} No URLs found for {Fore.CYAN}{domain}{Style.RESET_ALL}")
        return True

    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"Total: {Fore.GREEN}{len(urls)}{Style.RESET_ALL} raw URLs from all sources"
    )

    cleaned_urls = clean_urls(urls, extensions, placeholder)
    logging.info(
        f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} "
        f"Found {Fore.GREEN}{len(cleaned_urls)}{Style.RESET_ALL} unique URLs with parameters after cleaning"
    )

    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    # Sanitize domain for use as filename
    safe_domain = domain.replace("/", "_").replace("*", "_wildcard_")
    result_file = os.path.join(results_dir, f"{safe_domain}.txt")

    with open(result_file, "w") as f:
        for url in cleaned_urls:
            f.write(url + "\n")
            if stream_output:
                print(url)
    
    logging.info(f"{Fore.YELLOW}[INFO]{Style.RESET_ALL} Saved cleaned URLs to {Fore.CYAN}{result_file}{Style.RESET_ALL}")
    return True

def main():
    """
    Main function to handle command-line arguments and start URL mining process.
    """
    log_text = r"""
           
                                      _    __       
   ___  ___ ________ ___ _  ___ ___  (_)__/ /__ ____
  / _ \/ _ `/ __/ _ `/  ' \(_-</ _ \/ / _  / -_) __/
 / .__/\_,_/_/  \_,_/_/_/_/___/ .__/_/\_,_/\__/_/   
/_/                          /_/                    

                              with <3 by @0xasm0d3us           
    """
    colored_log_text = f"{yellow_color_code}{log_text}{reset_color_code}"
    print(colored_log_text)
    parser = argparse.ArgumentParser(description="Mining URLs from dark corners of Web Archives ")
    parser.add_argument("-d", "--domain", help="Domain name to fetch related URLs for.")
    parser.add_argument("-l", "--list", help="File containing a list of domain names.")
    parser.add_argument("-s", "--stream", action="store_true", help="Stream URLs on the terminal.")
    parser.add_argument("--proxy", help="Set the proxy address for web requests.", default=None)
    parser.add_argument("-p", "--placeholder", help="placeholder for parameter values", default="FUZZ")
    parser.add_argument(
        "--sources",
        help=f"Comma-separated list of sources to use. Available: {', '.join(AVAILABLE_SOURCES)} (default: all)",
        default=None
    )
    parser.add_argument(
        "--exclude-sources",
        help=f"Comma-separated list of sources to exclude. Available: {', '.join(AVAILABLE_SOURCES)}",
        default=None
    )
    args = parser.parse_args()

    if not args.domain and not args.list:
        parser.error("Please provide either the -d option or the -l option.")

    if args.domain and args.list:
        parser.error("Please provide either the -d option or the -l option, not both.")

    # Resolve sources
    if args.sources and args.exclude_sources:
        parser.error("Please provide either --sources or --exclude-sources, not both.")

    sources = None
    if args.sources:
        sources = [s.strip().lower() for s in args.sources.split(",")]
        invalid = [s for s in sources if s not in AVAILABLE_SOURCES]
        if invalid:
            parser.error(f"Unknown source(s): {', '.join(invalid)}. Available: {', '.join(AVAILABLE_SOURCES)}")
    elif args.exclude_sources:
        excluded = [s.strip().lower() for s in args.exclude_sources.split(",")]
        invalid = [s for s in excluded if s not in AVAILABLE_SOURCES]
        if invalid:
            parser.error(f"Unknown source(s): {', '.join(invalid)}. Available: {', '.join(AVAILABLE_SOURCES)}")
        sources = [s for s in DEFAULT_SOURCES if s not in excluded]
        if not sources:
            parser.error("All sources have been excluded. At least one source must remain.")

    extensions = HARDCODED_EXTENSIONS

    # Load API keys from environment (.env file)
    urlscan_api_key = os.environ.get("URLSCAN_API_KEY")

    if args.list:
        if not os.path.isfile(args.list):
            logging.error(f"{Fore.RED}[ERROR]{Style.RESET_ALL} File not found: {args.list}")
            return

        with open(args.list, "r") as f:
            domains = [line.strip().lower().replace('https://', '').replace('http://', '') for line in f.readlines()]
            domains = [domain for domain in domains if domain]  # Remove empty lines
            domains = list(set(domains))  # Remove duplicates

        for domain in domains:
            fetch_and_clean_urls(domain, extensions, args.stream, args.proxy, args.placeholder, sources, urlscan_api_key=urlscan_api_key)

    if args.domain:
        # Sanitize domain the same way as -l mode
        domain = args.domain.strip().lower().replace('https://', '').replace('http://', '')
        fetch_and_clean_urls(domain, extensions, args.stream, args.proxy, args.placeholder, sources, urlscan_api_key=urlscan_api_key)

if __name__ == "__main__":
    main()