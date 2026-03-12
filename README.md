# The AI Chronicle — AI News Analyzer

An intelligent Flask web app that analyzes news articles using AI. Paste any article URL and instantly get a structured summary, sentiment analysis, authenticity verification, and related coverage — all powered by free-tier LLMs.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask)
![Groq](https://img.shields.io/badge/LLM-Groq%20(Free)-F55036)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Features

| Feature | Description |
|---|---|
| **Bullet-Point Summary** | 5–10 key facts extracted from the article |
| **Sentiment Analysis** | Positive / Neutral / Negative tone detection with color-coded display |
| **Authenticity Check** | Cross-references the story via DuckDuckGo search and rates reliability (High / Medium / Low) |
| **Related Articles** | Links to 3–5 articles covering the same story from other outlets |
| **Parallel Execution** | Summary + verification run simultaneously for fast results |
| **Dark Modern UI** | Responsive dark theme with SVG icons and purple accents |

## Screenshots

<img width="1919" height="955" alt="image" src="https://github.com/user-attachments/assets/80cec5fa-aaa5-46fe-9ab6-699067d4fad4" />

> Paste a URL → click **Analyze** → get instant AI-powered insights.

<img width="1919" height="956" alt="image" src="https://github.com/user-attachments/assets/feaf9954-a884-4409-a94d-aefdf7733101" />


## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Flask (Python) |
| **LLM** | [Groq](https://groq.com) — free tier, 14,400 requests/day |
| **Models** | `llama-3.3-70b-versatile` (summary/sentiment), `llama-3.1-8b-instant` (agent) |
| **Agent** | LangChain classic agent with DuckDuckGo search tool |
| **Scraping** | Requests + BeautifulSoup4 |
| **Rendering** | Markdown → HTML via `markdown` library |
| **Concurrency** | `ThreadPoolExecutor` — parallel LLM + agent calls |
| **Frontend** | Jinja2 template, CSS custom properties, inline SVG icons |

## Quick Start

### 1. Clone

```bash
git clone <repo-url>
cd pro_news
```

### 2. Virtual environment (recommended)

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your **free** Groq API key:

```env
GROQ_API_KEY=gsk_your-key-here
GROQ_MODEL=llama-3.3-70b-versatile
SECRET_KEY=any-random-string
```

Get a free key (no credit card) at **[console.groq.com/keys](https://console.groq.com/keys)**.

### 5. Run

```bash
python app.py
```

Open **[http://localhost:5000](http://localhost:5000)** in your browser.

## How It Works

```
User pastes URL
       │
       ▼
  Fetch & parse HTML (requests + BeautifulSoup)
       │
       ├──────────────────────────────┐
       ▼                              ▼
  LLM Call (Groq)               Agent Call (LangChain)
  ┌──────────────┐              ┌──────────────────────┐
  │ Summary      │              │ DuckDuckGo search    │
  │ Sentiment    │              │ Authenticity rating  │
  └──────────────┘              │ Related articles     │
       │                        └──────────────────────┘
       └──────────────────────────────┘
                      │
                      ▼
              Render results page
```

Both LLM and agent calls run **in parallel** using `ThreadPoolExecutor` with timeouts (30s / 45s) so the page loads as fast as possible.

## Project Structure

```
pro_news/
├── app.py                 # Flask app — routes, LLM calls, scraping, parsing
├── templates/
│   └── index.html         # Dark-themed responsive UI with SVG icons
├── requirements.txt       # Pinned Python dependencies
├── .env                   # API keys (git-ignored)
├── .env.example           # Template for environment variables
├── .gitignore
└── README.md
```

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | — | Your Groq API key (required) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Model for summary/sentiment |
| `SECRET_KEY` | random | Flask session secret key |

## License

MIT
