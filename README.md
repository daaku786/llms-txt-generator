# llms.txt Generator

Generate an [`llms.txt`](https://llmstxt.org) file for any website from its XML sitemap.

`llms.txt` is a Markdown file at the root of your site that gives AI tools (ChatGPT, Claude, Perplexity, coding agents) a clean map of your most important pages, with a title and one line description each. This script builds it for you in seconds instead of writing it by hand.

* Zero dependencies, one Python file (3.8+)
* Finds the sitemap from robots.txt automatically (sitemap index, plain sitemap and `.xml.gz` all work)
* Fetches each page's title and meta description in parallel
* Skips `noindex` pages, tag/author/feed archives and URLs with query strings
* Groups pages into sections by URL folder (`/blog/` → `## Blog`)
* Puts main pages first so `--max-pages` never cuts your key pages
* Move low priority sections under `## Optional`, as the spec suggests

## Usage

```bash
python llms_txt_generator.py https://example.com
python llms_txt_generator.py https://example.com --max-pages 100 --optional Blog
python llms_txt_generator.py https://example.com --sitemap https://example.com/page-sitemap.xml -o -
```

| Option | Default | What it does |
|---|---|---|
| `--sitemap URL` | auto | Sitemap to read, if auto detection fails |
| `--name TEXT` | home page title | Site name used for the `# H1` |
| `--summary TEXT` | home page meta description | The `> summary` line |
| `--max-pages N` | 200 | Maximum pages to include |
| `--exclude GLOB` | | Skip matching URLs, repeatable (`--exclude "*/landing/*"`) |
| `--optional NAME` | | Move a section under `## Optional`, repeatable |
| `--workers N` | 8 | Parallel requests |
| `-o FILE` | `llms.txt` | Output file, `-` for stdout |

## Example output

```markdown
# Example Plumbing Co

> Licensed plumbers in Austin, TX for emergency repairs, drain cleaning and water heaters.

## Pages

- [Emergency Plumbing](https://example.com/emergency-plumbing/): 24/7 emergency plumbers across Austin.
- [Water Heater Installation](https://example.com/water-heaters/): Tank and tankless installs with same day service.
- [Contact Us](https://example.com/contact/): Call, email or book online.

## Optional

- [How to Choose a Water Heater](https://example.com/blog/choose-water-heater/): Tank vs tankless explained.
```

## Publishing it

Upload the file so it is served at `https://yourdomain.com/llms.txt`.

* **WordPress:** upload to the site root by FTP / file manager, or use a plugin that serves custom root files.
* **Shopify / Wix:** they don't allow arbitrary root files; host it on a subdomain or use an app if available.

Review the file before publishing. Rewrite weak meta descriptions; AI tools will read them as your page summaries.

## Tests

```bash
python -m unittest -v
```

## License

MIT
