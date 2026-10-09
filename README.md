# Bio Studio

Bio Studio is a local web application for writing, testing, and previewing character bios for JanitorAI. It provides an isolated preview, an HTML/CSS sanitizer checker that matches JanitorAI's server rules, a local token decoder, and a version history system that saves drafts in your browser.

## Features

- **Live Sandbox Preview**: Renders your HTML and CSS inside an isolated iframe preloaded with JanitorAI fonts.
- **Sanitizer Rule Checker**: Flags disallowed tags (`<style>`, `<script>`), unsupported CSS properties (`position`, word `z-index`), and mobile layout issues before you publish.
- **One-Click Auto-Fix**: Automatically strips disallowed tags and adjusts broken markup to match JanitorAI's filter.
- **Local Token Decoder**: Decodes Supabase session tokens and JWTs directly in your browser. No data leaves your machine.
- **Draft History**: Automatically saves revisions to your browser's IndexedDB storage so you don't lose your work.
- **Publishing Methods**: Publish directly through the local companion server or copy a generated console snippet to run in your browser's developer tools on JanitorAI.

## Quick setup

### Online Web Version
Open [https://bio.domcord.org/](https://bio.domcord.org/) in your web browser.

### Standalone (No installation needed)
You can use Bio Studio locally without installing anything:
1. Download or clone this repository.
2. Double-click `index.html` to open it in your web browser (Chrome, Firefox, Safari, Edge, or Brave).

All editing, diagnostics, previews, template imports, and the token decoder run completely in your browser.

---

### Windows

#### Method A: Using Python (Full local companion proxy)
1. Install [Python 3](https://www.python.org/downloads/) (check the box to "Add python.exe to PATH" during installation).
2. Open PowerShell or Command Prompt.
3. Clone the repository and navigate into the folder:
   ```cmd
   git clone https://github.com/DomcordFr/bio-studio.git
   cd bio-studio
   ```
4. Start the companion server:
   ```cmd
   python server.py
   ```
   *(or `py server.py`)*
5. Open `http://127.0.0.1:8080` in your browser.

#### Method B: Standalone
1. Download the repository ZIP file from GitHub and extract it.
2. Double-click `index.html`.

---

### macOS

1. Open Terminal.
2. Clone the repository:
   ```bash
   git clone https://github.com/DomcordFr/bio-studio.git
   cd bio-studio
   ```
3. Start the server (Python 3 is included with Xcode command line tools or Homebrew):
   ```bash
   python3 server.py
   ```
4. Open `http://127.0.0.1:8080` in Safari, Chrome, or Firefox.

---

### Linux

1. Open your terminal.
2. Clone the repository:
   ```bash
   git clone https://github.com/DomcordFr/bio-studio.git
   cd bio-studio
   ```
3. Run the server using Python 3:
   ```bash
   python3 server.py
   ```
4. Open `http://127.0.0.1:8080` in your browser.

---

### Android (via Termux)

1. Open Termux.
2. Install git and python:
   ```bash
   pkg update && pkg install git python -y
   ```
3. Clone and start the server:
   ```bash
   git clone https://github.com/DomcordFr/bio-studio.git
   cd bio-studio
   python3 server.py
   ```
4. Open Chrome or your default mobile browser and visit `http://localhost:8080`.

*(Alternatively, copy `index.html` to your device storage and open it directly in a mobile browser).*

---

### iOS and iPadOS

1. Save the repository files to your Files app or open them in an app like Kodex, Runestone, or Working Copy.
2. Open `index.html` directly in Safari or through your editor's local web viewer.
3. All local editing, formatting, linter checks, and previews run in Safari without needing a server.

---

## Running tests

Run the verification suites using Node.js and Python:

```bash
node tests/test_e2e.js
node tests/test_phase3.js
node tests/test_integration.js
python3 tests/test_suite.py
```

## Privacy and data handling

Bio Studio is built around strict client-side privacy and data sovereignty:

- **Client-Side Storage**: Your session tokens, prompt drafts, and version history are stored exclusively inside your browser's private storage (`sessionStorage` and IndexedDB). They are never saved to disk cookies or persistent third-party accounts.
- **Hosted Mode (`bio.domcord.org`)**: When using the hosted web version, requests to JanitorAI pass through our HTTPS proxy backend (`biostudiobackend.domcord.org`) *strictly in-flight* to bridge browser CORS restrictions. No tokens, prompts, character definitions, or API responses are ever logged, saved to disk, or stored in databases.
- **Local Self-Hosted Mode (`server.py`)**: When running the local companion server on `localhost:8080`, all network traffic routes directly between your device's IP and JanitorAI's official API. Zero external servers or proxies are involved, providing 100% air-gapped autonomy.

## License

Bio Studio is open-source software released under the MIT License.
