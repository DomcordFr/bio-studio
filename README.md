# Bio Studio — JanitorAI Character Bio Editor & Engine

An open-source, local-first design environment for JanitorAI creators to create, inspect, preview, and publish custom inline HTML/CSS character bios adhering strictly to server sanitizer constraints.

---

## 🌟 Core Features

- **Real JanitorAI Character Retrieval**: Paste any character URL (`https://janitorai.com/characters/{uuid}_{slug}`) or raw UUID to instantly fetch the live bot description, metadata, and avatar art.
- **Isolated Sandboxed Iframe Preview**: Renders untrusted character HTML in an isolated `<iframe>` sandbox (`sandbox="allow-same-origin"`), preloaded with all 14 official Google Fonts and mobile 375px responsive containment.
- **Real Sanitizer Diagnostics & Auto-Fixer**: Real-time parser checking for stripped `<style>` / `<script>` tags, disallowed `position` rules, `z-index` word tokens, `100vw` mobile overflow, and unclosed HTML tag trees with one-click automatic fixes.
- **Zero-Leak In-Memory Authentication**: Supabase JWT session tokens remain strictly in active memory. Never logged, sent to external services, or leaked in URLs.
- **Dual-Path Publishing Engine**:
  1. **Companion Proxy**: 1-click update via local companion server (`PATCH /api/janitor/characters/{id}`).
  2. **DevTools Console Bridge**: When running in CORS-restricted browser environments, generates a 1-click executable JavaScript snippet for direct execution in the creator's logged-in JanitorAI tab console.

---

## 🚀 Quick Start

### Option 1: Using the Companion Server (Recommended)

Run the lightweight companion server (Python 3.8+):

```bash
python3 server.py
```

Then open [`http://127.0.0.1:8080`](http://127.0.0.1:8080) in your web browser.

### Option 2: Standalone Browser Mode

Open `index.html` directly in any modern browser (or host on GitHub Pages / static hosting). All features, offline editing, linter, isolated preview, and the DevTools Console Bridge work without a backend.

---

## 🧪 Running Automated Tests

Run the test suites to verify URL parsing, JWT decoding, linter accuracy, and companion endpoints:

```bash
# Node.js Integration Test Suite
node tests/test_integration.js

# Python End-to-End Verification Suite
python3 tests/test_suite.py
```

---

## 🔒 Security Architecture

| Security Domain | Implementation |
|---|---|
| **Token Storage** | Stored in active browser memory by default. Optional tab-scoped `sessionStorage`. |
| **Token Transmission** | Never transmitted to third-party servers or telemetry. |
| **Preview Context** | Sandboxed in `<iframe sandbox="allow-same-origin">` with no access to parent DOM or session tokens. |
| **Proxy Scope** | Companion proxy restricts outbound destinations to verified JanitorAI gateway hosts. |

---

## 📜 License & Credits

- Open-source under the MIT License.
- Technical sanitizer rules based on community documentation by DelightfulTempe.
