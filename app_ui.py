import streamlit as st
import json
import os
from app import agent_reasoning
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

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
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MODEL_NAME = "llama-3.3-70b-versatile"
llm = ChatOpenAI(
    openai_api_key=GROQ_API_KEY,
    openai_api_base="https://api.groq.com/openai/v1",
    model_name=MODEL_NAME,
    temperature=0.2,
    max_tokens=2048,
)

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

    # Summary Section
    st.markdown("## 📄 Structured Summary")
    with st.container():
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        if isinstance(summary, list):
            for i, bullet in enumerate(summary, 1):
                st.markdown(f"**{i}.** {bullet}")
        else:
            st.write(summary)
        st.markdown("</div>", unsafe_allow_html=True)

    # Validation Section
    st.markdown("## ✅ Validation Results")
    for key, val in validation.items():
        display_key = f"Clause {key}" if str(key).isdigit() else key
        with st.expander(f"📌 {display_key}", expanded=False):
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            if isinstance(val, dict):
                severity = val.get("severity", "").capitalize()
                status = val.get("status", "")
                reason = val.get("reason", "")
                suggested_fix = val.get("suggested_fix", "")
                sev_color = {'High': '#ff4c4c', 'Medium': '#ffa500', 'Low': '#4caf50'}.get(severity, '#888')
                st.markdown(
                    f"<b>Status:</b> <span style='color:{sev_color}'>{status}</span><br>"
                    f"<b>Severity:</b> <span style='color:{sev_color}'>{severity}</span><br>"
                    f"<b>Reason:</b> {reason}<br>"
                    f"<b>Suggested Fix:</b> {suggested_fix}",
                    unsafe_allow_html=True
                )
            elif isinstance(val, list):
                for item in val:
                    st.write(f"- {item}")
            else:
                st.write(val)
            st.markdown("</div>", unsafe_allow_html=True)

    # Chat Section
    st.markdown("## 💬 Chat with the AI Agent")
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])

    user_input = st.chat_input("Type your legal question...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        context = f"Contract: {open(st.session_state.doc_path, 'r', encoding='utf-8', errors='ignore').read()}\n\nChecklist: {open(st.session_state.checklist_path, 'r', encoding='utf-8', errors='ignore').read()}"
        prompt = f"You are a legal AI assistant. Here is the contract and checklist.\n{context}\n\nUser: {user_input}"
        messages = [
            SystemMessage(content="You are a legal AI assistant."),
            HumanMessage(content=prompt)
        ]
        response = llm.invoke(messages).content
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)

else:
    st.info("📌 Please upload both the contract and checklist to start.")
