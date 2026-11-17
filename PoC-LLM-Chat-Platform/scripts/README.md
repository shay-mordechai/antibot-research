# Advanced API Evasion & Automation Framework (PoC)

## Overview
This repository contains a complete, asynchronous Proof of Concept (PoC) designed for advanced Bug Bounty vulnerability reports. Its primary goal is to test and mathematically prove **Account-Level Rate Limit Bypasses** in target APIs, while successfully evading modern enterprise anti-bot mechanisms.

Instead of relying on official API endpoints, this tool simulates authentic browser behavior by dynamically intercepting network traffic and injecting required security tokens directly into the HTTP headers at runtime.

---

## Technical Architecture Breakdown

### 1. Configuration & Setup
* The script targets specific API endpoints (`TARGET_URL` and `KEEPALIVE_URL`).
* It sets an `EXPECTED_ACCOUNT_LIMIT` (the maximum number of messages the server is supposed to allow per account globally).
* It parses a centralized `session_ready.json` file to load pre-authenticated session data (cookies and tokens), allowing it to act as real, verified users rather than unauthenticated bots.

### 2. The Worker Class & JA3 Spoofing
Each worker acts as an isolated, lightweight HTTP state.
* **State Management:** Instead of launching memory-heavy web browsers for every request, each worker holds its own `conversation_id`, `cookies`, and authentication `token`.
* **Dynamic Header Interception:** Uses Playwright to intercept outbound requests (`**/backend-api/**`) and inject valid proof-of-work and turnstile tokens.
* **JA3 Spoofing:** Disguises its TLS fingerprint, making the automated Python script look exactly like a legitimate web browser to evade Web Application Firewalls (WAF).

### 3. Concurrency Control
The script uses an `asyncio.Semaphore` set to a strict limit (e.g., `MAX_CONCURRENT_SESSIONS = 5`).
* Even if 100 sessions are loaded, only a controlled batch will actively send requests at the exact same time.
* This prevents overwhelming the server with a volumetric DDoS attack, ensuring the test remains a precise logical exploit. 

### 4. JWT Maintenance
* **Keepalive Loop:** Modern APIs expire idle sessions. The script can spawn a background task that sends a lightweight ping to the server at calculated intervals.
* This keeps the JSON Web Token (JWT) active without requiring the worker to perform the full authentication handshake again.

### 5. Resilient Execution & Rate Limits
* **Jitter:** Adds a random sleep timer between requests to simulate human behavior and bypass heuristic bot detection.
* **Fault Tolerance:** If a standard network error occurs (like a timeout), it only kills the worker after consecutive failures, preventing crashes due to bad internet connections.
* **Proper Termination:** If the server returns a `429 Too Many Requests` or `403 Forbidden`, the worker recognizes it has hit its local limit, marks itself as exhausted, and cleanly exits.

### 6. Bug Bounty Telemetry
At the end of the execution, the main function logs exploit metrics into a dedicated CSV file:
* It tracks Trace IDs, Worker IDs, and execution status.
* By demonstrating that individual sessions completely ignored the global account limit, the script provides undeniable, mathematical proof that the backend logic is flawed.

---

## Prerequisites & Setup

* **Python 3.9+**
* **Playwright** (with Chromium binaries installed)

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium

```

---

## Data Harvest & Usage

To make the PoC fully operational, you must perform manual data harvesting using Developer Tools to bridge the gap between the Python logic and the target server.

### Step 1: Capture Network Traffic

1. Open the browser's **Network Tab** and filter by **Fetch/XHR**.
2. Perform the target action (e.g., send a message) and locate the relevant POST request.
3. Right-click the requests responsible for the execution flow (e.g., prepare, finalize, conversation) and select **Copy as cURL (bash)**.
4. Save them locally as `.curl` files.

### Step 2: Generate Session Configuration

Use the included custom parser utility to sanitize and extract complex payloads, cookies, and Bash-escaped (תווי מילוט) strings from the raw captures.

```bash
# Run the extraction engine
python parse_curl.py

```

*Note: This generates the structured `session_ready.json` file required by the workers.*

### Step 3: Run the Automation Workers

```bash
# Execute the asynchronous exploit framework
python new_worked.py

```

*Execution logs, DOM traces, and screenshots of successful iterations will be automatically saved in the `success/`, `fails/`, and `traces/` directories.*

---

## Important Checklist

* **Format Validation:** Ensure your generated JSON configuration is valid.
* **Cookie Format:** The engine expects cookies as a structured dictionary, not a raw semicolon-separated string.
* **Endpoint Accuracy:** Double-check the target API URLs in the script against the Request URLs found in the DevTools Headers tab.

---

## Disclaimer

This project was developed strictly for educational and professional security research purposes. It is designed to demonstrate API trust boundaries, execution flow analysis, and rate-limit testing within authorized environments or bug bounty programs.