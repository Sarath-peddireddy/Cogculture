import streamlit as st
import fitz  # PyMuPDF
import json
import os
import requests
from openai import OpenAI

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FactCheck Agent | CogCulture",
    page_icon="🔍",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #0D1B2A 0%, #0A7E8C 100%);
        padding: 2rem 2.5rem;
        border-radius: 14px;
        margin-bottom: 2rem;
        color: white;
    }
    .main-header h1 { font-size: 2.2rem; font-weight: 700; margin: 0; }
    .main-header p  { opacity: 0.8; margin: 0.4rem 0 0; font-size: 1rem; }

    .badge-verified   { background:#D1FAE5; color:#065F46; padding:4px 12px; border-radius:20px; font-weight:600; font-size:0.82rem; }
    .badge-inaccurate { background:#FEF3C7; color:#92400E; padding:4px 12px; border-radius:20px; font-weight:600; font-size:0.82rem; }
    .badge-false      { background:#FEE2E2; color:#991B1B; padding:4px 12px; border-radius:20px; font-weight:600; font-size:0.82rem; }
    .badge-unknown    { background:#F1F5F9; color:#475569; padding:4px 12px; border-radius:20px; font-weight:600; font-size:0.82rem; }

    .claim-card {
        background: #fff;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .claim-card.verified   { border-left: 5px solid #10B981; }
    .claim-card.inaccurate { border-left: 5px solid #F59E0B; }
    .claim-card.false      { border-left: 5px solid #EF4444; }
    .claim-card.unknown    { border-left: 5px solid #94A3B8; }

    .claim-text { font-size: 1rem; font-weight: 600; color: #0F172A; margin-bottom: 0.5rem; }
    .verdict-reason { font-size: 0.9rem; color: #475569; margin-top: 0.4rem; }
    .real-fact { font-size: 0.88rem; color: #065F46; background:#D1FAE5; border-radius:6px; padding:6px 10px; margin-top:0.5rem; }
    .source-link { font-size: 0.82rem; color:#0A7E8C; margin-top:0.4rem; }

    .summary-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.5rem;
    }
    .stat-num { font-size: 2rem; font-weight: 700; }
    .stat-label { font-size: 0.8rem; color: #64748B; margin-top: -4px; }

    div[data-testid="stFileUploader"] { border: 2px dashed #0A7E8C; border-radius: 12px; padding: 1rem; }
    .stButton > button {
        background: linear-gradient(135deg, #0A7E8C, #6C3FC5);
        color: white; border: none; border-radius: 8px;
        padding: 0.6rem 2rem; font-weight: 600; font-size: 1rem;
        width: 100%; cursor: pointer;
    }
    .stButton > button:hover { opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🔍 FactCheck Agent</h1>
    <p>Upload a PDF · AI extracts claims · Live web verification · Instant truth report</p>
</div>
""", unsafe_allow_html=True)

# ── API Key setup ──────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

# Allow override via sidebar (useful for Streamlit Cloud secrets or local testing)
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.markdown("Keys are loaded from environment variables. You can override here for testing.")
    openai_key_input  = st.text_input("OpenAI API Key",  value=OPENAI_API_KEY,  type="password", placeholder="sk-...")
    serper_key_input  = st.text_input("Serper API Key",  value=SERPER_API_KEY,  type="password", placeholder="your-serper-key")
    if openai_key_input:  OPENAI_API_KEY = openai_key_input
    if serper_key_input:  SERPER_API_KEY = serper_key_input

    st.markdown("---")
    st.markdown("**How it works**")
    st.markdown("""
1. Upload any PDF
2. GPT-4o extracts all factual claims
3. Each claim is searched on the live web (Serper)
4. GPT-4o judges: Verified / Inaccurate / False
5. Full colour-coded report generated
    """)
    st.markdown("---")
    st.caption("Built by CogCulture SPM · 2025")


# ── Helper: Extract text from PDF ─────────────────────────────────────────────
def extract_pdf_text(uploaded_file) -> str:
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()


# ── Helper: Extract claims via OpenAI ─────────────────────────────────────────
def extract_claims(text: str, client: OpenAI) -> list[dict]:
    prompt = f"""
You are a fact-checking assistant. Analyze the following document and extract ALL specific, verifiable factual claims.

Focus on:
- Statistics and percentages (e.g., "revenue grew 42%")
- Named figures and financial data (e.g., "market cap of $2.3 trillion")
- Dates and timelines (e.g., "launched in Q3 2022")
- Technical specifications or numerical facts
- Named study results or survey findings

For each claim return a JSON object with:
- "claim": the exact claim as stated in the document (keep it concise, under 200 chars)
- "category": one of [statistic, financial, date, technical, study_finding]
- "search_query": an optimal Google search query (5-8 words) to verify this claim

Return ONLY a valid JSON array. No markdown, no commentary, no backticks.

Document:
\"\"\"
{text[:6000]}
\"\"\"
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2000,
    )
    raw = response.choices[0].message.content.strip()
    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── Helper: Web search via Serper ─────────────────────────────────────────────
def web_search(query: str, serper_key: str) -> str:
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": 5}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = []
        # Answer box
        if "answerBox" in data:
            ab = data["answerBox"]
            results.append(f"[Answer Box] {ab.get('title','')}: {ab.get('answer', ab.get('snippet',''))}")
        # Organic results
        for item in data.get("organic", [])[:4]:
            results.append(f"[{item.get('title','')}] {item.get('snippet','')} — {item.get('link','')}")
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Search error: {str(e)}"


# ── Helper: Verify a single claim ─────────────────────────────────────────────
def verify_claim(claim: dict, search_results: str, client: OpenAI) -> dict:
    prompt = f"""
You are a rigorous fact-checker. A document makes the following claim:

CLAIM: "{claim['claim']}"

Here are live web search results retrieved to verify this claim:
---
{search_results}
---

Based ONLY on the search results above, evaluate the claim and respond with a JSON object:
{{
  "verdict": "Verified" | "Inaccurate" | "False",
  "reason": "1-2 sentence explanation of your verdict",
  "real_fact": "The correct/current fact if the claim is Inaccurate or False (empty string if Verified)",
  "source": "The most relevant source URL from the search results (empty string if none)"
}}

Verdict definitions:
- Verified: the search results support the claim
- Inaccurate: the claim is partially correct but has wrong numbers/dates/details
- False: the search results directly contradict the claim OR no credible evidence exists

Return ONLY valid JSON. No markdown, no backticks.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=400,
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    result = json.loads(raw.strip())
    result["claim"]    = claim["claim"]
    result["category"] = claim.get("category", "general")
    return result


# ── Helper: Render a single claim card ────────────────────────────────────────
def render_claim_card(item: dict, index: int):
    verdict = item.get("verdict", "Unknown")
    css_class = verdict.lower() if verdict.lower() in ["verified","inaccurate","false"] else "unknown"
    badge_class = f"badge-{css_class}"

    emoji = {"Verified": "✅", "Inaccurate": "⚠️", "False": "❌"}.get(verdict, "❓")
    cat_label = item.get("category", "general").replace("_", " ").title()

    real_fact_html = ""
    if item.get("real_fact"):
        real_fact_html = f'<div class="real-fact">💡 <strong>Correct fact:</strong> {item["real_fact"]}</div>'

    source_html = ""
    if item.get("source"):
        source_html = f'<div class="source-link">🔗 <a href="{item["source"]}" target="_blank">Source</a></div>'

    st.markdown(f"""
<div class="claim-card {css_class}">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
        <div class="claim-text">#{index} {item['claim']}</div>
        <div>
            <span class="{badge_class}">{emoji} {verdict}</span>
            &nbsp;
            <span style="background:#F1F5F9;color:#475569;padding:4px 10px;border-radius:20px;font-size:0.78rem;">{cat_label}</span>
        </div>
    </div>
    <div class="verdict-reason">{item.get('reason','')}</div>
    {real_fact_html}
    {source_html}
</div>
""", unsafe_allow_html=True)


# ── Main App UI ────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("### 📄 Upload PDF Document")
    uploaded_file = st.file_uploader(
        "Drag & drop or click to browse",
        type=["pdf"],
        label_visibility="collapsed"
    )

with col2:
    st.markdown("### 🎯 What gets checked?")
    st.markdown("""
- **Statistics** — percentages, growth rates, rankings
- **Financial data** — revenue, valuations, market size
- **Dates & timelines** — product launches, historical events
- **Technical specs** — speeds, capacities, versions
- **Study findings** — survey results, research claims
    """)

st.markdown("---")

if uploaded_file:
    if not OPENAI_API_KEY:
        st.error("❌ OpenAI API key is missing. Add it in the sidebar or set OPENAI_API_KEY env variable.")
        st.stop()
    if not SERPER_API_KEY:
        st.error("❌ Serper API key is missing. Add it in the sidebar or set SERPER_API_KEY env variable.")
        st.stop()

    client = OpenAI(api_key=OPENAI_API_KEY)

    run_btn = st.button("🚀 Run Fact Check")

    if run_btn:
        # Step 1: Extract PDF text
        with st.spinner("📖 Reading PDF..."):
            try:
                pdf_text = extract_pdf_text(uploaded_file)
                if len(pdf_text) < 50:
                    st.error("Could not extract meaningful text from this PDF. It may be scanned/image-based.")
                    st.stop()
                st.success(f"✅ PDF loaded — {len(pdf_text):,} characters extracted")
            except Exception as e:
                st.error(f"PDF read error: {e}")
                st.stop()

        # Step 2: Extract claims
        with st.spinner("🧠 AI is identifying factual claims..."):
            try:
                claims = extract_claims(pdf_text, client)
                if not claims:
                    st.warning("No verifiable claims found in this document.")
                    st.stop()
                st.success(f"✅ {len(claims)} claims identified")
            except Exception as e:
                st.error(f"Claim extraction error: {e}")
                st.stop()

        # Step 3 & 4: Search + Verify each claim
        results = []
        progress_bar = st.progress(0, text="Verifying claims against live web...")

        for i, claim in enumerate(claims):
            progress_bar.progress(
                (i + 1) / len(claims),
                text=f"Verifying claim {i+1} of {len(claims)}: {claim['claim'][:60]}..."
            )
            try:
                search_results = web_search(claim["search_query"], SERPER_API_KEY)
                verdict        = verify_claim(claim, search_results, client)
                results.append(verdict)
            except Exception as e:
                results.append({
                    "claim":    claim["claim"],
                    "category": claim.get("category","general"),
                    "verdict":  "Unknown",
                    "reason":   f"Verification error: {str(e)}",
                    "real_fact":"",
                    "source":   ""
                })

        progress_bar.empty()

        # ── Results Summary ────────────────────────────────────────────────────
        st.markdown("## 📊 Fact-Check Report")

        counts = {
            "Verified":   sum(1 for r in results if r["verdict"] == "Verified"),
            "Inaccurate": sum(1 for r in results if r["verdict"] == "Inaccurate"),
            "False":      sum(1 for r in results if r["verdict"] == "False"),
            "Unknown":    sum(1 for r in results if r["verdict"] == "Unknown"),
        }
        total = len(results)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
<div class="summary-box" style="border-left:5px solid #10B981;">
<div class="stat-num" style="color:#10B981;">{counts['Verified']}</div>
<div class="stat-label">✅ Verified</div>
</div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
<div class="summary-box" style="border-left:5px solid #F59E0B;">
<div class="stat-num" style="color:#F59E0B;">{counts['Inaccurate']}</div>
<div class="stat-label">⚠️ Inaccurate</div>
</div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
<div class="summary-box" style="border-left:5px solid #EF4444;">
<div class="stat-num" style="color:#EF4444;">{counts['False']}</div>
<div class="stat-label">❌ False</div>
</div>""", unsafe_allow_html=True)
        with c4:
            accuracy = round((counts['Verified'] / total) * 100) if total else 0
            st.markdown(f"""
<div class="summary-box" style="border-left:5px solid #6C3FC5;">
<div class="stat-num" style="color:#6C3FC5;">{accuracy}%</div>
<div class="stat-label">📈 Accuracy Rate</div>
</div>""", unsafe_allow_html=True)

        # ── Filter tabs ────────────────────────────────────────────────────────
        st.markdown("### 🗂️ Claims Detail")
        tab_all, tab_false, tab_inaccurate, tab_verified = st.tabs([
            f"All ({total})",
            f"❌ False ({counts['False']})",
            f"⚠️ Inaccurate ({counts['Inaccurate']})",
            f"✅ Verified ({counts['Verified']})",
        ])

        with tab_all:
            for i, item in enumerate(results, 1):
                render_claim_card(item, i)

        with tab_false:
            false_items = [r for r in results if r["verdict"] == "False"]
            if false_items:
                for i, item in enumerate(false_items, 1):
                    render_claim_card(item, i)
            else:
                st.success("No false claims detected! 🎉")

        with tab_inaccurate:
            inaccurate_items = [r for r in results if r["verdict"] == "Inaccurate"]
            if inaccurate_items:
                for i, item in enumerate(inaccurate_items, 1):
                    render_claim_card(item, i)
            else:
                st.success("No inaccurate claims detected! 🎉")

        with tab_verified:
            verified_items = [r for r in results if r["verdict"] == "Verified"]
            if verified_items:
                for i, item in enumerate(verified_items, 1):
                    render_claim_card(item, i)
            else:
                st.info("No verified claims found.")

        # ── JSON Download ──────────────────────────────────────────────────────
        st.markdown("---")
        st.download_button(
            label="📥 Download Full Report (JSON)",
            data=json.dumps(results, indent=2),
            file_name="factcheck_report.json",
            mime="application/json",
        )

else:
    # Empty state
    st.markdown("""
<div style="text-align:center; padding:3rem; background:#F8FAFC; border-radius:14px; border:2px dashed #CBD5E1;">
    <div style="font-size:3rem;">📄</div>
    <h3 style="color:#475569;">Upload a PDF to get started</h3>
    <p style="color:#94A3B8;">The agent will extract all factual claims and verify them against live web data.</p>
</div>
""", unsafe_allow_html=True)
