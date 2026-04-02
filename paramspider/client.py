import requests
import random
import logging
import time
import sys

MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

def load_user_agents():
    """
    Loads user agents for request rotation.
    """
    return [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/603.3.8 (KHTML, like Gecko) Version/10.1.2 Safari/603.3.8",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36 Edg/89.0.774.45",
        "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.96 Safari/537.36 Edge/16.16299",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 OPR/45.0.2552.898",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Vivaldi/1.8.770.50",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/15.15063",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.81 Safari/537.36"
    ]

def fetch_url_content(url, proxy, extra_headers=None):
    """
    Fetches the content of a URL using a random user agent.
    Retries up to MAX_RETRIES times if the request fails.

    Args:
        url (str): The URL to fetch.
        proxy (str or None): Proxy address.
        extra_headers (dict or None): Additional headers to include (e.g., API keys).

    Returns:
        requests.Response or None: The response object, or None if all retries failed.
    """
    user_agents = load_user_agents()

    proxies = None
    if proxy is not None:
        proxies = {
            'http': proxy,
            'https': proxy
        }

    for i in range(MAX_RETRIES):
        user_agent = random.choice(user_agents)
        headers = {
            "User-Agent": user_agent
        }
        if extra_headers:
            headers.update(extra_headers)

        try:
            response = requests.get(url, proxies=proxies, headers=headers, timeout=REQUEST_TIMEOUT)

            # 404 means no results — don't retry, just return None
            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if i < MAX_RETRIES - 1:
                logging.warning(f"HTTP {status} for {url}. Retrying in 3s... ({i + 1}/{MAX_RETRIES})")
                time.sleep(3)
            else:
                logging.warning(f"HTTP {status} for {url}. All retries exhausted.")
        except requests.exceptions.Timeout:
            if i < MAX_RETRIES - 1:
                logging.warning(f"Timeout for {url}. Retrying in 3s... ({i + 1}/{MAX_RETRIES})")
                time.sleep(3)
            else:
                logging.warning(f"Timeout for {url}. All retries exhausted.")
        except requests.exceptions.ConnectionError:
            if i < MAX_RETRIES - 1:
                logging.warning(f"Connection error for {url}. Retrying in 3s... ({i + 1}/{MAX_RETRIES})")
                time.sleep(3)
            else:
                logging.warning(f"Connection error for {url}. All retries exhausted.")
        except requests.exceptions.RequestException as e:
            if i < MAX_RETRIES - 1:
                logging.warning(f"Error fetching {url}: {e}. Retrying in 3s... ({i + 1}/{MAX_RETRIES})")
                time.sleep(3)
            else:
                logging.warning(f"Error fetching {url}: {e}. All retries exhausted.")
        except KeyboardInterrupt:
            logging.warning("Keyboard Interrupt received. Exiting gracefully...")
            sys.exit()

    return None
