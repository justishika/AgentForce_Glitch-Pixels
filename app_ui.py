import streamlit as st
import json
from app import process_document  # Import your function that runs summarization & validation

st.set_page_config(page_title="Legal Document Summarizer & Validator", layout="wide")

st.title("📜 Legal Document Summarizer & Validator")
st.write("Upload a legal document, and the AI agent will summarize it, validate clauses, and flag risks.")

uploaded_file = st.file_uploader("Upload Contract", type=["txt", "pdf"])
checklist_file = st.file_uploader("Upload Compliance Checklist (JSON)", type=["json"])

if uploaded_file and checklist_file:
    with st.spinner("Processing... ⏳"):
        # Save uploaded files temporarily
        with open("temp_contract.txt", "wb") as f:
            f.write(uploaded_file.read())
        with open("temp_checklist.json", "wb") as f:
            f.write(checklist_file.read())

        # Call your processing logic
        result = process_document("temp_contract.txt", "temp_checklist.json")

    st.success("✅ Processing complete!")

    # Display Summary
    st.subheader("📄 Summary")
    st.write(result["summary"])

    # Display Validation Results
    st.subheader("✅ Validation Results")
    for clause, status in result["validation"].items():
        st.write(f"- **{clause}**: {status}")

    # Display Suggested Questions
    if "questions" in result:
        st.subheader("💡 Suggested Questions")
        for q in result["questions"]:
            st.write(f"- {q}")

    # Download JSON report
    st.download_button("⬇ Download Full Report", data=json.dumps(result, indent=4), file_name="legal_report.json")

else:
    st.info("Please upload both the contract and checklist to begin.")
