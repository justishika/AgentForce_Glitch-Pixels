import streamlit as st
import json
import os
import io
from fpdf import FPDF
from app import agent_reasoning, gemini_chat

# ========== PAGE SETUP ==========
st.set_page_config(page_title="⚡ Legal AI Agent", layout="wide", initial_sidebar_state="collapsed")

# ========== CUSTOM CSS FOR MIND-BLOWING UI ==========
st.markdown("""
<style>
/* Background gradient animation */
@keyframes gradientBG {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}
body {
    background: linear-gradient(-45deg, #0f0c29, #302b63, #24243e);
    background-size: 400% 400%;
    animation: gradientBG 12s ease infinite;
    color: white !important;
}

/* Glassmorphism Card */
.block-container {
    padding-top: 2rem;
}
.glass-card {
    background: rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0px 4px 30px rgba(0,0,0,0.2);
    transition: transform 0.2s ease-in-out;
}
.glass-card:hover {
    transform: scale(1.01);
}

/* Neon Titles */
h1, h2, h3, .stMarkdown h1, .stMarkdown h2 {
    font-family: 'Orbitron', sans-serif;
    letter-spacing: 1px;
    color: #00e6e6 !important;
    text-shadow: 0px 0px 8px rgba(0,230,230,0.7);
}

/* Chat bubbles */
.stChatMessage[data-testid="stChatMessage-user"] {
    background-color: rgba(0,230,230,0.2);
    border-radius: 12px;
}
.stChatMessage[data-testid="stChatMessage-assistant"] {
    background-color: rgba(255,105,180,0.2);
    border-radius: 12px;
}

/* Expander styling */
.streamlit-expanderHeader {
    font-weight: bold;
    color: #00e6e6 !important;
}

/* Upload box */
.css-1cpxqw2 {
    background: rgba(255,255,255,0.1);
    border-radius: 12px;
    border: 1px dashed rgba(255,255,255,0.3);
}

/* Sidebar glass style */
.css-1d391kg {
    background: rgba(0,0,0,0.5) !important;
    backdrop-filter: blur(8px);
}
</style>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ========== HEADER ==========
st.markdown("<h1 style='text-align:center;'>⚡ Legal AI Agent</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; font-size:1.1em;'>AI-powered contract analysis & clause validation — futuristic and fast ⚡</p>", unsafe_allow_html=True)

# ========== LLM SETUP ==========
# We are using the gemini_chat function imported from app.py

# ========== FILE UPLOAD ==========
st.markdown("### 📂 Upload Your Documents")
col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Contract", type=["txt", "pdf"])
with col2:
    checklist_file = st.file_uploader("Checklist (JSON)", type=["json"])

# Initialize states
for key in ["doc_path", "checklist_path", "report", "chat_history"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "chat_history" else []

# ========== PROCESS DOCUMENT ==========
if uploaded_file and checklist_file:
    contract_path = "temp_contract.pdf" if uploaded_file.name.lower().endswith('.pdf') else "temp_contract.txt"
    with open(contract_path, "wb") as f:
        f.write(uploaded_file.read())
    with open("temp_checklist.json", "wb") as f:
        f.write(checklist_file.read())
    st.session_state.doc_path = contract_path
    st.session_state.checklist_path = "temp_checklist.json"

    with st.spinner("🚀 Analyzing your document with AI agent..."):
        st.session_state.report = agent_reasoning(contract_path, "temp_checklist.json", out_path=None)
    st.success("✅ Analysis Complete!")

# ========== DISPLAY RESULTS ==========
if st.session_state.report:
    summary = st.session_state.report.get("summary", "No summary available.")
    validation = st.session_state.report.get("validation", {})
    warning = st.session_state.report.get("warning")

    # Summary Section (no pill/bubble panel)
    st.markdown("## 📄 Structured Summary")
    if warning:
        st.markdown(
            f"<div style='font-size:0.9rem; opacity:.7;'>ℹ️ {warning}</div>",
            unsafe_allow_html=True,
        )
    if isinstance(summary, list):
        for i, bullet in enumerate(summary, 1):
            st.markdown(f"**{i}.** {bullet}")
    else:
        st.write(summary)

    # Validation Section (clean, no bubble panels)
    st.markdown("## ✅ Validation Results")
    for key, val in validation.items():
        display_key = f"Clause {key}" if str(key).isdigit() else key
        with st.expander(f"📌 {display_key}", expanded=False):
            if isinstance(val, dict):
                severity = val.get("severity", "").capitalize()
                status = val.get("status", "")
                reason = val.get("reason", "")
                suggested_fix = val.get("suggested_fix", "")
                sev_color = {'High': '#ff4c4c', 'Medium': '#ffa500', 'Low': '#4caf50'}.get(severity, '#888')
                st.markdown(
                    f"**Status:** <span style='color:{sev_color}'>{status}</span>  "+
                    f"**Severity:** <span style='color:{sev_color}'>{severity}</span>\n\n",
                    unsafe_allow_html=True,
                )
                if reason:
                    st.markdown(f"- **Reason:** {reason}")
                if suggested_fix:
                    st.markdown(f"- **Suggested Fix:** {suggested_fix}")
            elif isinstance(val, list):
                for item in val:
                    st.write(f"- {item}")
            else:
                st.write(val)

    # Download Section (after validation)
    st.markdown("### ⬇️ Download Report")

    def build_text_report() -> str:
        lines: list[str] = []
        lines.append("Structured Summary:\n")
        if isinstance(summary, list):
            for i, b in enumerate(summary, 1):
                lines.append(f"{i}. {b}")
        else:
            lines.append(str(summary))
        lines.append("\n\nValidation Results:\n")
        for k, v in validation.items():
            if isinstance(v, dict):
                lines.append(f"- {k}: {v.get('status')} (Severity: {v.get('severity')})")
                if v.get("reason"):
                    lines.append(f"  Reason: {v.get('reason')}")
                if v.get("suggested_fix"):
                    lines.append(f"  Suggested Fix: {v.get('suggested_fix')}")
            else:
                lines.append(f"- {k}: {v}")
        red_flags = st.session_state.report.get("red_flags", [])
        questions = st.session_state.report.get("questions", [])
        if red_flags:
            lines.append("\nRed Flags:")
            for r in red_flags:
                lines.append(f"- {r}")
        if questions:
            lines.append("\nFollow-up Questions:")
            for q in questions:
                lines.append(f"- {q}")
        return "\n".join(lines)

    txt_report: str = build_text_report()

    # TXT download
    st.download_button(
        label="Download Report (TXT)",
        data=txt_report,
        file_name="legal_ai_report.txt",
        mime="text/plain",
        use_container_width=True,
    )

    # PDF download (simple text PDF)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in txt_report.splitlines():
        # Ensure we don't crash on very long lines
        pdf.multi_cell(0, 6, line)
    pdf_bytes: bytes = pdf.output(dest='S').encode('latin-1')

    st.download_button(
        label="Download Report (PDF)",
        data=pdf_bytes,
        file_name="legal_ai_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    # Chat Section (fast response, dialog formatting)
    st.markdown("## 💬 Chat with the AI Agent")
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])

    user_input = st.chat_input("Type your legal question…")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        # Show the just-asked question immediately (so the user sees it in the dialog)
        st.chat_message("user").write(user_input)

        # Build concise context for the assistant
        summary_text = "\n".join(summary) if isinstance(summary, list) else str(summary)
        # Compact validation context for faster responses
        missing_items = [k for k, v in validation.items() if isinstance(v, dict) and v.get("status") == "MISSING"]
        risky_items = [k for k, v in validation.items() if isinstance(v, dict) and v.get("status") == "RISKY"]
        total_items = len(validation)
        compliant = sum(1 for v in validation.values() if isinstance(v, dict) and v.get("status") == "COMPLIANT")
        missing = len(missing_items)
        risky = len(risky_items)
        compact_validation = {
            "totals": {"total": total_items, "compliant": compliant, "missing": missing, "risky": risky},
            "missing": missing_items[:6],
            "risky": risky_items[:6],
        }
        validation_text = json.dumps(compact_validation, indent=2, ensure_ascii=False)
        # Use only the last 2 turns to cut prompt size
        history = st.session_state.chat_history[-4:]
        transcript = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in history if m])

        system_style = (
            "You are a precise legal assistant. Write in clean Markdown using short paragraphs and bullet lists. "
            "Adopt a conversational, helpful tone similar to a modern chat assistant. Bold key terms and headings."
        )
        prompt = (
            f"System: {system_style}\n"
            f"Document summary:\n{summary_text}\n\nValidation (JSON):\n{validation_text}\n\n"
            f"Conversation so far:\n{transcript}\n\n"
            f"User: {user_input}\nAssistant:"
        )

        # Fast, non-streaming call with small token cap for snappy UX
        try:
            # Ultra-fast path for responsiveness
            from app import gemini_chat_quick
            response = gemini_chat_quick(messages=[prompt], max_tokens=380)
        except Exception:
            # Last-resort fallback: show relevant excerpts from the contract
            doc_text = open(st.session_state.doc_path, 'r', encoding='utf-8', errors='ignore').read()
            q_words = [w for w in user_input.lower().split() if len(w) > 3]
            hits = []
            for ln in [l.strip() for l in doc_text.split('\n') if l.strip()]:
                low = ln.lower()
                if any(w in low for w in q_words):
                    hits.append(ln)
                if len(hits) >= 6:
                    break
            response = (
                "I’m temporarily offline. Relevant excerpts I found:\n\n" + "\n".join([f"- {h}" for h in hits])
            ) if hits else "I’m temporarily offline. Please try again in a moment."

        st.session_state.chat_history.append({"role": "assistant", "content": response})

else:
    st.info("📌 Please upload both the contract and checklist to start.")
