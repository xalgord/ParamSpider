<h1 align="center">
    paramspider
  <br>
</h1>

<h4 align="center">  Mining URLs from dark corners of Web Archives for bug hunting/fuzzing/further probing </h4>

<p align="center">
  <a href="#about">📖 About</a> •
  <a href="#installation">🏗️ Installation</a> •
  <a href="#sources">🌐 Sources</a> •
  <a href="#configuration">⚙️ Configuration</a> •
  <a href="#usage">⛏️ Usage</a> •
  <a href="#examples">🚀 Examples</a> •
  <a href="#contributing">🤝 Contributing</a>
</p>


![paramspider](https://github.com/xalgord/ParamSpider/blob/master/static/paramspider.png?raw=true)

## About

`paramspider` allows you to fetch URLs related to any domain or a list of domains from multiple web archive and threat intelligence sources. It filters out "boring" URLs, allowing you to focus on the ones that matter the most.

## Installation

To install `paramspider`, follow these steps:

```sh
git clone https://github.com/xalgord/ParamSpider
cd paramspider
pip install .
```

## Sources

`paramspider` fetches URLs from **4 sources** by default — no API keys required:

| Source | Description | API Key |
|--------|-------------|---------|
| `wayback` | Wayback Machine (web.archive.org) | Not needed |
| `commoncrawl` | Common Crawl (commoncrawl.org) | Not needed |
| `otx` | AlienVault OTX (otx.alienvault.com) | Not needed |
| `urlscan` | URLScan.io (urlscan.io) | Optional (higher rate limits) |

All sources are enabled by default and work without any configuration.

## Configuration

API keys are read from environment variables. This is **optional** — all sources work without keys, but authenticated requests get higher rate limits.

Add to your `~/.zshrc` or `~/.bashrc`:

```sh
export URLSCAN_API_KEY="your-urlscan-api-key"
export OTX_API_KEY="your-otx-api-key"
```

Then reload your shell:

```sh
source ~/.zshrc   # or source ~/.bashrc
```

| Variable | Source | How to get |
|----------|--------|-----------|
| `URLSCAN_API_KEY` | URLScan.io | [urlscan.io/user/signup](https://urlscan.io/user/signup/) |
| `OTX_API_KEY` | OTX AlienVault | [otx.alienvault.com](https://otx.alienvault.com/) → Settings → API Key |

## Usage

```sh
paramspider -d example.com
```

### Options

```
  -d, --domain            Domain name to fetch related URLs for
  -l, --list              File containing a list of domain names
  -s, --stream            Stream URLs on the terminal
  -p, --placeholder       Placeholder for parameter values (default: FUZZ)
  --proxy                 Set the proxy address for web requests
  --sources               Comma-separated list of sources to use (default: all)
  --exclude-sources       Comma-separated list of sources to exclude
```

## Examples

- Discover URLs for a single domain (uses all 4 sources):

  ```sh
  paramspider -d example.com
  ```

- Discover URLs for multiple domains from a file:

  ```sh
  paramspider -l domains.txt
  ```

- Use only specific sources:

  ```sh
  paramspider -d example.com --sources wayback,otx
  ```

- Exclude slow sources:

  ```sh
  paramspider -d example.com --exclude-sources commoncrawl
  ```

- Stream URLs on the terminal:

  ```sh
  paramspider -d example.com -s
  ```

- Set up web request proxy:

  ```sh
  paramspider -d example.com --proxy '127.0.0.1:7890'
  ```

- Custom placeholder for URL parameter values (default: "FUZZ"):

  ```sh
  paramspider -d example.com -p '"><h1>reflection</h1>'
  ```


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=xalgord/ParamSpider&type=Date)](https://star-history.com/#xalgord/ParamSpider&Date)
