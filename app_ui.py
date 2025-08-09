import streamlit as st
import json
from app import agent_reasoning
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

st.set_page_config(page_title="Legal Document Chatbot & Summarizer", layout="wide")
st.title("📜 Legal Document Chatbot & Summarizer")
st.write("Upload a legal document and checklist, then chat with the AI agent about your contract.")

GROQ_API_KEY = None
MODEL_NAME = "llama-3.3-70b-versatile"
try:
    import os
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
except Exception:
    pass
llm = ChatOpenAI(
    openai_api_key=GROQ_API_KEY,
    openai_api_base="https://api.groq.com/openai/v1",
    model_name=MODEL_NAME,
    temperature=0.2,
    max_tokens=2048,
)

uploaded_file = st.file_uploader("Upload Contract (required)", type=["txt", "pdf"], accept_multiple_files=False)
checklist_file = st.file_uploader("Upload Compliance Checklist (JSON, required)", type=["json"], accept_multiple_files=False)

if "doc_path" not in st.session_state:
    st.session_state.doc_path = None
if "checklist_path" not in st.session_state:
    st.session_state.checklist_path = None
if "report" not in st.session_state:
    st.session_state.report = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if uploaded_file and checklist_file:
    contract_path = "temp_contract.pdf" if uploaded_file.name.lower().endswith('.pdf') else "temp_contract.txt"
    with open(contract_path, "wb") as f:
        f.write(uploaded_file.read())
    with open("temp_checklist.json", "wb") as f:
        f.write(checklist_file.read())
    st.session_state.doc_path = contract_path
    st.session_state.checklist_path = "temp_checklist.json"
    with st.spinner("Processing document and checklist..."):
        st.session_state.report = agent_reasoning(contract_path, "temp_checklist.json", out_path=None)
    st.success("✅ Document processed! You can now chat with the agent below.")

if st.session_state.report:
    st.subheader("📄 Structured Summary")
    summary = st.session_state.report.get("summary", "No summary generated.")
    if isinstance(summary, list):
        for i, bullet in enumerate(summary, 1):
            st.markdown(f"**{i}.** {bullet}")
    else:
        st.markdown(summary)
    st.subheader("✅ Validation Results")
    validation = st.session_state.report.get("validation", {})
    if validation:
        for key, val in validation.items():
            display_key = key if not str(key).isdigit() else f"Clause {key}"
            if isinstance(val, dict):
                status = val.get("status", "")
                reason = val.get("reason", "")
                suggested_fix = val.get("suggested_fix", "")
                severity = val.get("severity", "")
                sev_color = {'high': '#ff4c4c', 'medium': '#ffa500', 'low': '#4caf50'}.get(severity, '#888')
                st.markdown(f"<div style='background-color:#181818;padding:12px;border-radius:8px;margin-bottom:10px'>"
                            f"<span style='font-weight:bold;font-size:1.05em'>{display_key}</span>: "
                            f"<span style='color:{sev_color};font-weight:bold'>{status}</span><br>"
                            f"<span style='font-size:0.98em'><i>Reason:</i> {reason}</span><br>"
                            f"<span style='font-size:0.98em'><i>Suggested fix:</i> {suggested_fix}</span><br>"
                            f"<span style='font-size:0.98em'><i>Severity:</i> <span style='color:{sev_color}'>{severity}</span></span>"
                            f"</div>", unsafe_allow_html=True)
            elif isinstance(val, list):
                for item in val:
                    st.markdown(f"<div style='background-color:#181818;padding:12px;border-radius:8px;margin-bottom:10px'>"
                                f"<span style='font-weight:bold;font-size:1.05em'>{display_key}</span>: "
                                f"{item}"
                                f"</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color:#181818;padding:12px;border-radius:8px;margin-bottom:10px'>"
                            f"<span style='font-weight:bold;font-size:1.05em'>{display_key}</span>: "
                            f"{val}"
                            f"</div>", unsafe_allow_html=True)
    else:
        st.info("No validation results found.")

    st.subheader("💬 Chat with the Legal Agent")
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])
    user_input = st.chat_input("Ask a legal question about your contract or checklist...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        # Compose context from uploaded document and checklist
        context = f"Contract: {open(st.session_state.doc_path, 'r', encoding='utf-8', errors='ignore').read()}\n\nChecklist: {open(st.session_state.checklist_path, 'r', encoding='utf-8', errors='ignore').read()}"
        prompt = f"You are a legal AI assistant. Here is the contract and checklist context.\n{context}\n\nUser question: {user_input}"
        messages = [
            SystemMessage(content="You are a legal AI assistant."),
            HumanMessage(content=prompt)
        ]
        response = llm.invoke(messages).content
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.chat_message("assistant").write(response)
else:
    st.info("Please upload both the contract and checklist to begin.")
