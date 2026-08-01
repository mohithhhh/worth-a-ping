# worth-a-ping

An intelligent email-to-Telegram urgency filter that watches your inbox, judges each message for genuine urgency using AI, and proactively alerts you via Telegram only when something actually warrants an interruption.

Built for people drowning in email who need their attention protected, not just their notifications filtered.

## Why This Needs Two Channels + Real Judgment

Most notification systems are binary: all or nothing. Email filters and rules are static — they can't understand context, urgency, or whether "the third follow-up today from this person" means something different than the first.

**worth-a-ping** solves this by:

1. **Watching a noisy channel (email)** where anyone can reach you
2. **Judging each message contextually** using Gemini, which considers:
   - Message content and tone
   - Sender identity
   - Recent conversation history (is this the 3rd follow-up today?)
   - Time-sensitive signals (production down, hard deadlines)
3. **Alerting on a clean channel (Telegram)** that you actually check, only when something genuinely needs you right now

This isn't message routing — it's intelligent triage. The agent learns from your conversation patterns, defaults to silence, and only interrupts when precision is high.

## Tech Stack

- **caspian-sdk** — Unified messaging layer across email + Telegram through a single identity
- **Gemini API** (gemini-3.5-flash-lite) — Low-latency, cost-effective urgency classification
- **SQLite** — Conversation history for context-aware judgments
- **Python 3.11+** — Single long-running backend process

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get API Keys

**Caspian API:**
- Sign up at [trycaspianai.com](https://trycaspianai.com)
- Get your API key from the dashboard

**Gemini API:**
- Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
- Create a free API key

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `CASPIAN_API_KEY` — Your Caspian API key
- `GEMINI_API_KEY` — Your Gemini API key
- `MY_TELEGRAM_HANDLE` — Your Telegram username (e.g., `@yourusername`) or chat ID

### 4. Connect Channels

Initialize your Caspian identity:
```bash
caspian init
```

Connect email:
```bash
caspian connect email
```

Connect Telegram:
```bash
caspian connect telegram
```

Follow the prompts to authenticate each channel. Both channels will be linked to your single Caspian identity.

### 5. Run the Agent

```bash
python main.py
```

You should see:
```
🔌 Initializing worth-a-ping agent...
✅ Agent ready. Listening for messages...
```

### 6. Test It

Send yourself a test email with something that sounds urgent (e.g., "URGENT: Production database is down").

Watch the terminal for the judgment:
```
[inbound] "URGENT: Production database is down" → ALERT → Telegram sent
```

Check your Telegram — you should receive the alert within seconds.

Then send a routine email (e.g., "Hey, are we still on for lunch?"):
```
[inbound] "Hey, are we still on for lunch?" → SKIP (casual social message, not time-critical)
```

No Telegram alert — the agent correctly identified this as non-urgent.

## How the Judgment Works

Every inbound email is evaluated by Gemini using a carefully designed prompt that:

1. **Defaults to NOT urgent** — Precision over recall. False alarms defeat the purpose.
2. **Considers conversation context** — If this is the 3rd message today from someone, that matters.
3. **Looks for genuine urgency signals**:
   - Production outages, system failures, security incidents
   - Time-sensitive opportunities with hard deadlines (today/tonight)
   - Critical personal emergencies
   - Explicit "need you now" from VIPs
4. **Filters out noise**:
   - Newsletters, marketing, automated notifications
   - Meeting invites for future dates
   - FYI updates without time pressure
   - Routine follow-ups
   - Social messages that can wait

The model returns structured JSON with a boolean urgency flag and a one-line reason. The reason is logged to the database and included in Telegram alerts so you can see why the agent thought something was urgent.

### Precision Over Recall

The system is intentionally biased toward **not** interrupting you. A false negative (missing an urgent message) is recoverable — you'll see it eventually when you check email. A false positive (getting pinged for non-urgent stuff) trains you to ignore the alerts, which defeats the entire purpose.

This is reflected in the prompt design, the default-to-skip logic, and the fallback behavior (if the AI fails to parse, assume not urgent).

## Project Structure

```
worth-a-ping/
├── main.py              # Entrypoint: client setup, message handler, event loop
├── triage.py            # Gemini judgment logic (isolated for easy tuning)
├── db.py                # SQLite helpers: logging, context retrieval, alert tracking
├── requirements.txt     # Python dependencies
├── .env.example         # Template for configuration
├── .gitignore           # Excludes .env and *.db
└── README.md            # This file
```

## Demo Video

[Link to demo video will be added here]

## How to Tune the Judgment

If you're getting too many or too few alerts, edit the `SYSTEM_PROMPT` in [triage.py](triage.py) to adjust the criteria. The model is instruction-following, so clear natural language changes (e.g., "Be more conservative about what counts as urgent") will directly affect behavior.

You can also test the judgment in isolation:
```bash
python triage.py
```

This runs a few hardcoded test cases and prints the model's verdicts.

## License

MIT
