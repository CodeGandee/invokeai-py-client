# How to Use Essential CLI Tools for Web API Analysis and Automation

This guide provides an overview of essential command-line tools for any developer or QA engineer working with web APIs. These tools will help you with analysis, testing, and automation.

## `curl`

**Documentation:**
- **Context7 Library ID:** `/curl/curl`
- **Official Documentation:** https://curl.se/docs/
- **Manual:** https://curl.se/docs/manpage.html

`curl` is a powerful command-line tool for transferring data with URLs. It's your go-to for quick API requests.

### Example: Make a simple GET request

```bash
curl https://api.example.com/data
```

### Example: POST JSON data with headers

```bash
curl -X POST -H "Content-Type: application/json" -H "Accept: application/json" \
     -d '{"key":"value"}' https://api.example.com/data
```

### Example: Send JSON using --json shortcut

```bash
curl --json '{"drink": "coffee"}' https://api.example.com/data
```

### Example: Include response headers in output

```bash
curl -i https://api.example.com/data
```

### Example: Send basic authentication

```bash
curl -u username:password https://api.example.com/protected
```

## `jq`

**Documentation:**
- **Context7 Library ID:** `/jqlang/jq`
- **Official Documentation:** https://jqlang.github.io/jq/
- **Manual:** https://jqlang.github.io/jq/manual/
- **Tutorial:** https://jqlang.github.io/jq/tutorial/

`jq` is a lightweight and flexible command-line JSON processor. It's like `sed` for JSON data; you can use it to slice, filter, map, and transform structured data.

### Example: Pretty-print JSON

```bash
curl https://api.example.com/data | jq '.'
```

### Example: Extract a specific field

```bash
curl https://api.example.com/data | jq '.fieldName'
```

### Example: Filter array elements

```bash
echo '[1,2,3,4,5]' | jq 'map(select(. > 2))'
```

### Example: Transform object structure

```bash
echo '{"users":[{"name":"John","age":30}]}' | jq '.users[] | {username: .name, years: .age}'
```

### Example: Extract multiple fields

```bash
echo '{"name":"John","age":30,"city":"NYC"}' | jq '{name, age}'
```

## `httpie`

**Documentation:**
- **Context7 Library ID:** `/httpie/cli`
- **Official Documentation:** https://httpie.io/docs/cli
- **GitHub Repository:** https://github.com/httpie/cli
- **Examples:** https://httpie.io/docs/cli/examples

`httpie` is a user-friendly command-line HTTP client. It's a great alternative to `curl` with a more intuitive syntax and beautiful output.

### Example: Make a GET request

```bash
http https://api.example.com/data
```

### Example: POST JSON data (implicit)

```bash
http POST api.example.com/data name=John age:=30 active:=true
```

### Example: Send custom headers

```bash
http GET api.example.com/data Authorization:"Bearer token123" User-Agent:MyApp/1.0
```

### Example: Upload a file

```bash
http --form POST api.example.com/upload file@/path/to/file.txt
```

### Example: Authentication

```bash
http -a username:password GET api.example.com/protected
```

### Example: Save response to file

```bash
http GET api.example.com/data > response.json
```

## Node.js

**Documentation:**
- **Official Documentation:** https://nodejs.org/en/docs/
- **API Reference:** https://nodejs.org/api/
- **NPM Documentation:** https://docs.npmjs.com/
- **Getting Started:** https://nodejs.org/en/learn/getting-started/introduction-to-nodejs

Node.js is a JavaScript runtime built on Chrome's V8 JavaScript engine, essential for running Playwright and Puppeteer.

### Example: Check Node.js version

```bash
node --version
```

### Example: Run a JavaScript file

```bash
node script.js
```

### Example: Install packages globally

```bash
npm install -g package-name
```

### Example: Initialize a new project

```bash
npm init -y
```

## Playwright

**Documentation:**
- **Official Documentation:** https://playwright.dev/
- **API Reference:** https://playwright.dev/docs/api/class-playwright
- **Getting Started:** https://playwright.dev/docs/intro
- **Examples:** https://playwright.dev/docs/examples

Playwright is a Node.js library for browser automation that supports multiple browsers (Chrome, Firefox, Safari).

### Example: Install Playwright

```bash
npm install -g playwright
npx playwright install
```

### Example: Basic screenshot script

```javascript
// screenshot.js
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('https://example.com');
  await page.screenshot({ path: 'example.png' });
  await browser.close();
})();
```

### Example: Run the script

```bash
node screenshot.js
```

### Example: Command-line screenshot

```bash
npx playwright screenshot --browser=chromium https://example.com screenshot.png
```

## Puppeteer

**Documentation:**
- **Official Documentation:** https://pptr.dev/
- **API Reference:** https://pptr.dev/api
- **Getting Started:** https://pptr.dev/guides/getting-started
- **Examples:** https://pptr.dev/guides

Puppeteer is a Node.js library for controlling headless Chrome or Chromium browsers.

### Example: Install Puppeteer

```bash
npm install -g puppeteer
```

### Example: Basic Puppeteer script

```javascript
// scrape.js
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.goto('https://example.com');
  const title = await page.title();
  console.log('Page title:', title);
  await browser.close();
})();
```

### Example: Run the script

```bash
node scrape.js
```

## `mitmproxy`

**Documentation:**
- **Official Documentation:** https://docs.mitmproxy.org/
- **Installation Guide:** https://docs.mitmproxy.org/stable/overview-installation/
- **User Guide:** https://docs.mitmproxy.org/stable/overview-getting-started/
- **API Reference:** https://docs.mitmproxy.org/stable/api/mitmproxy.html

`mitmproxy` is a free and open-source interactive HTTPS proxy. It allows you to inspect, modify, and replay web traffic.

### Example: Start interactive proxy

```bash
mitmproxy -p 8080
```

### Example: Start web interface

```bash
mitmweb -p 8080
```

### Example: Command-line dump mode

```bash
mitmdump -p 8080
```

### Example: Save traffic to file

```bash
mitmdump -p 8080 -w traffic.dump
```

### Example: Filter specific hosts

```bash
mitmdump -p 8080 --set confdir=~/.mitmproxy "~d api.example.com"
```

Configure your browser or application to use `http://localhost:8080` as its HTTP proxy to start intercepting traffic.

## `shot-scraper`

**Documentation:**
- **PyPI Package:** https://pypi.org/project/shot-scraper/
- **GitHub Repository:** https://github.com/simonw/shot-scraper
- **Documentation:** https://shot-scraper.datasette.io/
- **Getting Started:** https://shot-scraper.datasette.io/en/stable/

`shot-scraper` is a command-line tool for taking screenshots of websites. It's built on top of Playwright and provides a simple interface for capturing web pages.

### Example: Take a screenshot of a website

```bash
shot-scraper https://example.com
```

### Example: Take a screenshot with custom dimensions

```bash
shot-scraper https://example.com --width 1280 --height 720
```

### Example: Take a full-page screenshot

```bash
shot-scraper https://example.com --full-page
```

### Example: Save to a specific file

```bash
shot-scraper https://example.com --output screenshot.png
```

### Example: Take a screenshot with custom selector

```bash
shot-scraper https://example.com --selector ".main-content"
```

### Example: Wait for element before taking screenshot

```bash
shot-scraper https://example.com --wait-for ".loading-complete"
```

### Example: Multiple screenshots from a text file

```bash
shot-scraper multi urls.txt
```

## `yq`

**Documentation:**
- **Context7 Library ID:** `/mikefarah/yq`
- **Official Documentation:** https://mikefarah.gitbook.io/yq/
- **GitHub Repository:** https://github.com/mikefarah/yq
- **Usage Examples:** https://mikefarah.gitbook.io/yq/usage/basic

`yq` is a command-line YAML processor that uses jq-like syntax. It's the `jq` equivalent for YAML files.

### Example: Read a value from YAML

```bash
yq '.database.host' config.yaml
```

### Example: Convert YAML to JSON

```bash
yq -o json '.' config.yaml
```

### Example: Update a YAML value

```bash
yq '.database.port = 5432' -i config.yaml
```

### Example: Filter array elements

```bash
yq '.users[] | select(.active == true)' users.yaml
```

### Example: Pretty-print YAML

```bash
yq '.' messy-config.yaml
