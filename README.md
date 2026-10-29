<div align="center">

# PaidPilot

**AI-powered, human-in-the-loop payment collections assistant for PayPal invoices**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-green.svg)](https://github.com/raman-codesX/PaidPilot/releases)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)

</div>

---

## Table of Contents

- [About](#about)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [How It Works](#how-it-works)
- [Risk and Action Policy](#risk-and-action-policy)
- [Human Review and Email Sending](#human-review-and-email-sending)
- [Customer Identity Check](#customer-identity-check)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## About

**PaidPilot** is a PayPal-focused payment follow-up assistant for freelancers and small businesses. It uses PayPal invoice data and payment history to estimate late-payment risk, recommend a collection action, and prepare a customer-facing email for review.

**The problem:** Chasing late invoices is time-consuming, and deciding when and how firmly to follow up is often guesswork.

**Who it's for:** Freelancers and small businesses that invoice customers through PayPal.

> **Core idea:** AI helps prioritize and draft payment follow-ups; the business owner remains responsible for the final customer-facing action.

**Status:** PaidPilot v0.1.0 is a hackathon-oriented prototype. It is not presented as a production-ready financial automation system.

---

## Features

- **PayPal integration**: Sandbox OAuth authentication, invoice creation and sending, invoice history retrieval, and webhook-based status sync.
- **Late-payment prediction**: A scikit-learn model estimates the probability that an invoice will be paid late.
- **Deterministic action policy**: Risk probability maps to a fixed collection action (`DO_NOTHING`, `FRIENDLY_REMINDER`, `FIRM_REMINDER`, `PAYMENT_PLAN`).
- **Email drafting**: Gemini-powered drafts, plus rule-based templates for each reminder type.
- **Human review**: Approval or rejection decisions are recorded before the user chooses to send.
- **Gmail sending**: Send reviewed drafts through the Gmail API.
- **Streamlit dashboard**: Overview, Recommendations, Invoices, Clients, and Review history pages.

---

## Tech Stack

| Layer            | Technology                           |
| ---------------- | ------------------------------------ |
| Language         | Python 3.13                          |
| Backend          | FastAPI, Uvicorn                     |
| Frontend         | Streamlit                            |
| Database         | SQLite (via SQLAlchemy)              |
| Machine learning | scikit-learn                         |
| AI drafting      | Google Gemini (`gemini-3.5-flash`)   |
| Integrations     | PayPal REST API (Sandbox), Gmail API |
| Testing          | pytest                               |

---

## How It Works

```text
PayPal invoice/history
        ↓
Late-payment prediction
        ↓
Deterministic action recommendation
        ↓
Email draft generation
        ↓
Dashboard review
        ↓
Approval / rejection is recorded
        ↓
User chooses whether to send
        ↓
Gmail
```

### Risk and Action Policy

The model returns a late-payment probability between 0 and 1. PaidPilot maps it to an action:

| Late-payment probability | Action              |
| ------------------------ | ------------------- |
| `0%–40%`                 | `DO_NOTHING`        |
| `>40%–70%`               | `FRIENDLY_REMINDER` |
| `>70%–80%`               | `FIRM_REMINDER`     |
| `>80%–100%`              | `PAYMENT_PLAN`      |

Exact boundaries: `DO_NOTHING` is `<= 0.40`, `FRIENDLY_REMINDER` is `> 0.40` and `<= 0.70`, `FIRM_REMINDER` is `> 0.70` and `<= 0.80`, and `PAYMENT_PLAN` is `> 0.80` and `<= 1.00`.

Additional rules:

- Closed invoices (`PAID`, `VOID`, `CANCELLED`) never receive a customer-contact action.
- Reminder actions are limited to three reminders by the policy.
- The model also reports a `risk_level` (`LOW`, `MEDIUM`, `HIGH`) using `40%` and `70%` thresholds.

**Model inputs** (loaded from `models/payment_risk.pkl`):

- `invoice_amount`
- `previous_invoices`
- `previous_late_payments`
- `previous_late_rate`
- `avg_previous_delay`

For recommendations, previous payment features are derived from earlier locally stored paid invoices for the same customer email, when the required dates are available.

### Human Review and Email Sending

The approval API stores `APPROVED` or `REJECTED` decisions together with the recommendation, action, probability, and draft message. The saved decision response reports `sent: false`. The email-send endpoint then sends the supplied recipient, subject, and body, and records the action as `SENT`.

> **Important:** The email-send endpoint does **not** currently verify that a matching saved approval exists before sending. The dashboard presents drafts as unsent until the user chooses to send, but the backend does not enforce approval as a prerequisite.

**AI drafting rules:** The deterministic action is passed to Gemini as final. The model is instructed not to change the action, invent deadlines, fees, or penalties, expose internal risk scores, or claim that an email was already sent.

### Customer Identity Check

Invoice creation performs a narrow consistency check:

1. Look up existing local invoices with the same recipient email.
2. If an existing invoice has a customer name that differs from the new one, creation is rejected.
3. If the existing invoice has no stored customer name, it is not rejected.

This is **not** comprehensive identity verification.

---

## Architecture

```text
                 ┌──────────────────┐
                 │   Streamlit UI   │
                 │                  │
                 │ Overview         │
                 │ Recommendations  │
                 │ Invoices         │
                 │ Clients          │
                 │ Review history   │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │     FastAPI      │
                 │                  │
                 │ Dashboard API    │
                 │ Recommendation   │
                 │ Approval API     │
                 │ PayPal Webhook   │
                 └───────┬──────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      ┌────────┐    ┌─────────┐    ┌─────────┐
      │ PayPal │    │ SQLite  │    │ ML Risk │
      │  API   │    │   DB    │    │  Model  │
      └────────┘    └─────────┘    └────┬────┘
                                        │
                                        ▼
                                 ┌────────────┐
                                 │   Policy   │
                                 │   Engine   │
                                 └─────┬──────┘
                                       │
                              ┌────────┴────────┐
                              ▼                 ▼
                         Gemini draft       Rule-based
                              │              templates
                              └────────┬────────┘
                                       ▼
                                  Gmail API
```

**PayPal webhooks:** The webhook endpoint verifies the signature with PayPal before processing. For `INVOICING.INVOICE.PAID`, it marks the matching local invoice as `PAID` and records the event to prevent duplicate processing.

---

## Getting Started

### Prerequisites

- Python 3.13
- A PayPal Developer account with Sandbox REST API credentials
- A Gemini API key (for AI email drafting)
- Gmail OAuth credentials (`credentials.json`) for sending email

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/raman-codesX/PaidPilot.git
   cd PaidPilot
   ```

2. Create and activate a virtual environment:

   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```

   On macOS/Linux, activate with `source .venv/bin/activate`.

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Install the Google packages that `requirements.txt` does not currently list:

   ```bash
   pip install google-genai google-auth google-auth-oauthlib google-api-python-client
   ```

5. Create your environment file from the example:

   ```bash
   cp .env.example .env
   ```

   On Windows, use `copy .env.example .env`.

### Configuration

Set the following variables in `.env`:

| Variable               | Description                                                  | Required | Default                            |
| ---------------------- | ------------------------------------------------------------ | -------- | ---------------------------------- |
| `PAYPAL_CLIENT_ID`     | PayPal REST API client ID                                    | Yes      | None                               |
| `PAYPAL_CLIENT_SECRET` | PayPal REST API client secret                                | Yes      | None                               |
| `PAYPAL_BASE_URL`      | PayPal API base URL                                          | No       | `https://api-m.sandbox.paypal.com` |
| `PAYPAL_WEBHOOK_ID`    | PayPal webhook ID used for signature verification            | Yes      | None                               |
| `GEMINI_API_KEY`       | Gemini API key for AI email drafting                         | Yes      | None                               |
| `PAIDPILOT_API_URL`    | Backend URL used by the Streamlit UI (not in `.env.example`) | No       | `http://127.0.0.1:8000`            |

**Gmail credentials:** Gmail sending reads OAuth credentials from `credentials.json` and `token.json` and requests the `gmail.send` scope. These are local credentials and must not be committed.

---

## Usage

Start the API:

```bash
uvicorn app.api.main:app --reload
```

Check that it is running:

```bash
curl http://127.0.0.1:8000/
```

```json
{"message": "PaidPilot API is running"}
```

In a second terminal, start the dashboard:

```bash
streamlit run ui/dashboard.py
```

Typical workflow in the dashboard:

1. **Invoices**: create and send a PayPal invoice.
2. **Recommendations**: review open invoices with their risk and recommended action.
3. Review the generated email draft and record an approval or rejection.
4. Choose whether to send the email through Gmail.
5. **Review history**: audit recorded actions.

To point the dashboard at a different backend:

```bash
PAIDPILOT_API_URL=http://your-host:8000 streamlit run ui/dashboard.py
```

On Windows (cmd):

```cmd
set PAIDPILOT_API_URL=http://your-host:8000
streamlit run ui/dashboard.py
```

---

## Project Structure

```text
PaidPilot/
├── app/
│   ├── agent/
│   │   ├── email_templates.py   # Rule-based email templates
│   │   ├── graph.py
│   │   ├── llm.py               # Gemini email drafting
│   │   └── policy.py            # Risk-to-action policy
│   ├── api/
│   │   ├── approvals.py         # Approval/rejection and email-send endpoints
│   │   ├── dashboard.py
│   │   ├── main.py              # FastAPI entry point
│   │   ├── recommendations.py
│   │   └── webhooks.py          # PayPal webhook handling
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   ├── gmail/
│   │   └── client.py            # Gmail API client
│   ├── ml/
│   │   ├── features.py
│   │   ├── predict.py
│   │   └── train.py
│   └── paypal/
│       ├── client.py            # OAuth and API client
│       ├── history.py           # Invoice history retrieval
│       └── invoices.py          # Invoice creation and sending
├── data/
├── models/
│   └── payment_risk.pkl         # Trained risk model
├── tests/
│   ├── test_action_history.py
│   ├── test_agent.py
│   ├── test_email_templates.py
│   ├── test_gmail.py
│   └── test_policy.py
├── ui/
│   └── dashboard.py             # Streamlit dashboard
├── manual_invoice.py
├── test_paypal.py               # Manual PayPal OAuth check
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Testing

Run the test suite:

```bash
pytest
```

The `tests/` directory covers recommendation and policy logic, email templates, Gmail integration, and action history.

`test_paypal.py` in the repository root is **not** a pytest unit test. It performs a real PayPal OAuth request and prints a success message, so it requires working PayPal credentials:

```bash
python test_paypal.py
```

---

## Known Limitations

- The email-send API does not enforce that a saved approval decision exists before sending.
- Customer identity handling is limited to an email/name consistency check during invoice creation.
- Gmail requires local OAuth credentials (`credentials.json` and `token.json`).
- `.env.example` does not include `PAIDPILOT_API_URL`, although the UI supports it.
- The app targets the PayPal Sandbox by default and has no authentication or authorization layer for production deployment.

---

## Roadmap

- [x] PayPal Sandbox integration (OAuth, invoices, history, webhooks)
- [x] Late-payment prediction and deterministic action policy
- [x] Gemini and rule-based email drafting
- [x] Streamlit review dashboard
- [ ] Enforce saved approval decisions at the email-send API boundary
- [ ] Add stronger customer identity and data validation
- [ ] Add API and integration tests for PayPal, webhooks, approvals, and email sending
- [ ] Add authentication and authorization for production deployment
- [ ] Improve persistent auditability of the recommendation → approval → send relationship

See the [open issues](https://github.com/raman-codesX/PaidPilot/issues) for the full list of proposed features and known bugs.

---

## Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/your-feature-name`
3. Commit your changes: `git commit -m "feat: short description"`
4. Push to your branch: `git push origin feat/your-feature-name`
5. Open a pull request.

Please make sure `pytest` passes and follow the existing code style. For larger changes, open an issue first to discuss the approach.

---

## License

Distributed under the **MIT** License. See [LICENSE](LICENSE) for more information.

---

## Contact

**Raman**

- Email: namansingh982150@gmail.com
- GitHub: [@raman-codesX](https://github.com/raman-codesX)
- Project link: https://github.com/raman-codesX/PaidPilot
