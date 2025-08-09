import os
import json
import argparse
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
# from langchain.llms import OpenAI
from langchain.agents import initialize_agent, Tool
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate

# --- LLM Setup (Groq API, OpenAI-compatible) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MODEL_NAME = "llama-3.3-70b-versatile"

llm = ChatOpenAI(
    openai_api_key=GROQ_API_KEY,
    openai_api_base="https://api.groq.com/openai/v1",
    model_name=MODEL_NAME,
    temperature=0.2,
    max_tokens=2048,
)

# --- Tools ---
class FileReaderTool(BaseTool):
    name: str = "file_reader"
    description: str = "Reads a legal document from a file path."
    def _run(self, file_path):
        if file_path.lower().endswith('.pdf'):
            try:
                from PyPDF2 import PdfReader
            except ImportError:
                raise ImportError("PyPDF2 is required for PDF support. Please install it with 'pip install PyPDF2'.")
            reader = PdfReader(file_path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="ISO-8859-1") as f:
                return f.read()

class SummarizeTool(BaseTool):
    name: str = "summarize"
    description: str = "Summarizes a section of legal text."
    def _run(self, text):
        prompt = f"Summarize the following legal section in 2-3 bullet points:\n{text}"
        messages = [
            SystemMessage(content="You are a legal AI assistant."),
            HumanMessage(content=prompt)
        ]
        return llm.invoke(messages).content

class ClauseMatchTool(BaseTool):
    name: str = "clause_match"
    description: str = "Checks if a clause from the checklist is present in the document section."
    def _run(self, section, clause):
        prompt = f"Does the following section address this checklist item?\nSection: {section}\nChecklist: {clause}\nAnswer yes/no and explain."
        messages = [
            SystemMessage(content="You are a legal AI assistant."),
            HumanMessage(content=prompt)
        ]
        return llm.invoke(messages).content

class JSONReportTool(BaseTool):
    name: str = "json_report"
    description: str = "Writes a structured JSON report to a file."
    def _run(self, report, out_path):
        if out_path:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            return f"Report saved to {out_path}"
        return report

# --- Agent Reasoning Steps ---
def agent_reasoning(file_path, checklist_path, out_path):
    # Read files
    doc_text = FileReaderTool()._run(file_path)
    checklist = json.loads(FileReaderTool()._run(checklist_path))

    # Split document into sections (simple split by paragraphs)
    sections = [s.strip() for s in doc_text.split('\n\n') if s.strip()]
    if not sections:
        sections = [doc_text]

    # Summarize each section
    summaries = [SummarizeTool()._run(sec) for sec in sections]

    # Checklist validation
    validation = {}
    for clause_name, clause_text in checklist.items():
        found = False
        for sec in sections:
            match_result = ClauseMatchTool()._run(sec, clause_text)
            if "yes" in match_result.lower():
                validation[clause_name] = {
                    "status": "COMPLIANT",
                    "reason": match_result,
                    "suggested_fix": "",
                    "severity": "low"
                }
                found = True
                break
        if not found:
            validation[clause_name] = {
                "status": "MISSING",
                "reason": "Clause not found in document.",
                "suggested_fix": f"Add clause: {clause_text}",
                "severity": "high"
            }

    # Red flags and follow-up questions
    prompt_redflags = (
        "Read the following legal document and checklist validation. "
        "List any risky terms, missing clauses, or red flags. "
        "Suggest 3 follow-up questions for a lawyer."
        f"\nDocument Summary:\n{summaries}\nValidation:\n{json.dumps(validation, indent=2)}"
    )
    messages = [
        SystemMessage(content="You are a legal AI assistant."),
        HumanMessage(content=prompt_redflags)
    ]
    redflag_response = llm.invoke(messages).content
    # Simple extraction (could be improved with structured output)
    red_flags = []
    questions = []
    for line in redflag_response.split('\n'):
        if "red flag" in line.lower() or "risk" in line.lower():
            red_flags.append(line)
        if "?" in line:
            questions.append(line)

    # Build report
    report = {
        "summary": summaries,
        "validation": validation,
        "red_flags": red_flags,
        "questions": questions
    }
    JSONReportTool()._run(report, out_path)
    return report

# --- CLI Interface ---
def main():
    parser = argparse.ArgumentParser(description="Legal Document AI Agent")
    parser.add_argument("--file", required=True, help="Path to legal contract text file")
    parser.add_argument("--checklist", required=True, help="Path to checklist JSON file")
    parser.add_argument("--out", default="report.json", help="Path to save JSON report")
    args = parser.parse_args()

    if not GROQ_API_KEY:
        raise ValueError("Missing GROQ_API_KEY environment variable.")

    report = agent_reasoning(args.file, args.checklist, args.out)
    print(f"=== Report saved to {args.out} ===")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()