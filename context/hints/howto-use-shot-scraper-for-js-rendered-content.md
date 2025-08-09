# How to Use `shot-scraper` to Get JS-Rendered Content

`shot-scraper` is a versatile command-line tool that can be used to capture screenshots, extract HTML, and execute JavaScript on web pages. This guide focuses on how to retrieve JavaScript-rendered content from a website.

## Official Documentation

- **GitHub Repository:** https://github.com/simonw/shot-scraper
- **Documentation:** https://shot-scraper.datasette.io/

## Using `shot-scraper html`

The `shot-scraper html` command allows you to get the full HTML of a page after all JavaScript has been executed.

### Example: Get the rendered HTML of a page

```bash
shot-scraper html https://example.com
```

To save the output to a file:

```bash
shot-scraper html https://example.com -o rendered.html
```

## Using `shot-scraper javascript`

For more fine-grained control, you can use the `shot-scraper javascript` command to execute arbitrary JavaScript on the page and return the result.

### Example: Get the outer HTML of the document element

This will return the full HTML of the page after it has been rendered by the browser.

```bash
shot-scraper javascript https://example.com "document.documentElement.outerHTML"
```

### Example: Extract specific content

You can execute any JavaScript to extract specific parts of the rendered page. For example, to get the text content of the `<h1>` tag:

```bash
shot-scraper javascript https://example.com "document.querySelector('h1').innerText" -r
```

The `-r` or `--raw` flag outputs the result as a raw string instead of a JSON string.

By using these commands, you can effectively scrape content from dynamic websites that rely on JavaScript to render their content.

## Caveats

- **Content Security Policy (CSP):** Some websites use CSP headers to block the execution of inline or external scripts. If you encounter errors related to this, you can use the `--bypass-csp` flag with `shot-scraper` to ignore these security policies.

  ```bash
  shot-scraper javascript https://example.com "document.title" --bypass-csp
  ```

- **Waiting for Elements:** Pages may have content that loads asynchronously. You might need to wait for specific elements to be present in the DOM before you can extract them. `shot-scraper` provides `--wait-for` and `--wait` options for this purpose.

  ```bash
  # Wait for a CSS selector
  shot-scraper html https://example.com --wait-for "#dynamic-content"

  # Wait for a specific time in milliseconds
  shot-scraper html https://example.com --wait 5000
  ```
