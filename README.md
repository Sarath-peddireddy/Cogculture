# 🔍 FactCheck Agent

> **AI-powered PDF fact-checking web app** — Upload any document, and the agent automatically extracts claims, cross-references them against live web data, and flags inaccuracies.


---

## 🚀 Live Demo

👉 **[View Live App]([https://your-app.streamlit.app](https://cogculture-factcheck69.streamlit.app/))

---

## 🧠 How It Works

```
PDF Upload
    ↓
Text Extraction (PyMuPDF)
    ↓
Claim Identification (GPT-4o)
    ↓
Live Web Search per Claim (Serper API)
    ↓
Verdict Judgement (GPT-4o)
    ↓
Colour-coded Report
```

Each claim is flagged as:
| Verdict | Meaning |
|---|---|
| ✅ **Verified** | Claim matches live web data |
| ⚠️ **Inaccurate** | Partially correct but has wrong numbers/dates |
| ❌ **False** | Contradicted by evidence or no evidence found |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Claim Extraction | OpenAI GPT-4o |
| Claim Verification | OpenAI GPT-4o |
| Live Web Search | Serper API (Google Search) |
| PDF Parsing | PyMuPDF (fitz) |
| Deployment | Streamlit Cloud |

---

## ⚙️ Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/your-username/factcheck-agent.git
cd factcheck-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
```
Open `.env` and fill in your API keys:
```
OPENAI_API_KEY=sk-your-openai-key-here
SERPER_API_KEY=your-serper-api-key-here
```

### 4. Run the app
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## ☁️ Deploy to Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"** → select your repo → set `app.py` as the main file
4. Go to **Settings → Secrets** and add:
```toml
OPENAI_API_KEY = "sk-your-openai-key-here"
SERPER_API_KEY = "your-serper-api-key-here"
```
5. Click **Deploy** — your app will be live in ~2 minutes.

> ℹ️ On Streamlit Cloud, secrets are loaded as environment variables automatically. No `.env` file needed.

---

## 🔑 API Keys

### OpenAI
- Get key at: https://platform.openai.com/api-keys
- Model used: `gpt-4o`
- Estimated cost: ~$0.01–0.05 per PDF (depends on length and number of claims)

### Serper (Google Search API)
- Get free key at: https://serper.dev
- Free tier: **2,500 searches/month** — plenty for testing
- Used for: live web search to verify each extracted claim

---

## 📁 Project Structure

```
factcheck-agent/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── README.md           # This file
```

---

## 🧪 Testing with a Trap Document

The app is designed to catch intentional lies. To test it:
1. Create a PDF with a mix of real and fake stats (e.g., "Apple's revenue in 2023 was $10 billion")
2. Upload it to the app
3. The agent will flag the fake stat as **❌ False** and provide the correct figure

---

*Built by sarath· 2026 · [cogculture.agency](https://www.cogculture.agency)*
