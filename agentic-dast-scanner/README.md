# Agentic DAST Scanner

This module contains the core logic for the Autonomous DAST (Dynamic Application Security Testing) Agent. The scanner utilizes Visual Language Models (VLM) to navigate web interfaces and detect vulnerabilities without relying on brittle, hardcoded selectors.

---

## 🛠 Research Journey: Iterative Development
The architecture underwent three phases to achieve the current evasion and mapping capabilities:

| Phase | Methodology | Outcome |
| :--- | :--- | :--- |
| **Phase 1** | Browser Emulation (Playwright) | **Blocked.** High-fidelity fingerprints (DOM/JS) triggered "JS Interrogation". |
| **Phase 2** | Engine Optimization | **Flagged.** Behavioral telemetry (mouse/asset loading) failed validation. |
| **Phase 3** | TLS Impersonation (`curl_cffi`) | **Success.** Cryptographic handshake mimicry granted "Edge Trust". |

---

## 🚀 Level 1: Autonomous Visual Mapping & Basic Telemetry

**Objective:** Establish the foundational architecture for an autonomous QA/DAST agent capable of "seeing" a web interface and interacting with it like a human user.

### Core Capabilities:
* **Set-of-Mark (SoM) Injection:** The agent injects a custom JavaScript snippet into the target DOM (מודל אובייקטי המסמך). This script identifies all interactive elements (inputs, textareas, buttons) and draws high-contrast bounding boxes (תיבות תוחמות) with unique IDs, bypassing hidden or non-interactive elements.
* **Visual Language Model (VLM) Integration:** A full-page screenshot of the marked UI is captured and sent to Gemini 2.5 Flash. The VLM acts as the agent's "eyes," performing OCR (זיהוי תווים אופטי) and logical deduction to extract the specific IDs of text input fields, actively ignoring buttons and irrelevant components.
* **Human-Simulated Interaction:** Using the scanner's core logic, the agent targets the elements identified by the VLM via custom data attributes (`data-diagnostic-id`). It simulates human behavior (typing delays, sequential key presses) to inject a benign diagnostic payload (מטען אבחון בסיסי) like `test_diag_reflection_123`.

### Current Limitations (The Level 1 Boundary)
At this stage, the agent performs "Blind Fuzzing". It injects payloads without context. As observed in testing, modern browsers implement strict Client-Side Validation (אימות בצד לקוח) – such as HTML5 `type="email"` rules. Because the basic payload lacks an `@` symbol, the browser intercepts the request before it reaches the backend. 

### Next Steps (Level 2)
To effectively test backend logic, the agent must either:
1. Generate **Context-Aware Payloads** (מטענים מודעי-הקשר) that satisfy frontend validation.
2. Actively manipulate the DOM to strip away client-side defenses before submission.
