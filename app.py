"""
app.py

Legal Document Summarizer & Validator Agent (Groq/OpenAI-compatible chat completions style)

Provides:
- read_text_file / read_pdf
- summarize_document
- extract_clauses
- validate_clauses_externally
- generate_followups
- process_document(file_path, checklist_path) -> dict (used by Streamlit UI)

Usage (CLI):
  export GROQ_API_KEY="sk-..."
  python -c "from app import process_document; print(process_document('sample_contract.txt','checklist.json'))"

Note: This is a prototype/demo tool for hackathons. Not legal advice.
"""

import os
import json
import time
import requests
from typing import Dict, Any, Optional

# Optional PDF reading
try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

# === CONFIG ===
API_URL = "https://api.groq.com/openai/v1/chat/completions"  # Groq-style (OpenAI-compatible) endpoint
MODEL = "llama3-8b-8192"  # change to your available model
API_KEY_ENV = "GROQ_API_KEY"
TIMEOUT = 30  # seconds

# === Helper I/O ===
def read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="latin-1") as f:  # or encoding="cp1252"
            return f.read()

def read_pdf(path: str) -> str:
    if PdfReader is None:
        raise RuntimeError("PyPDF2 not installed. Install it from requirements or use a .txt input.")
    reader = PdfReader(path)
    texts = []
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            texts.append("")
    return "\n\n".join(texts)

def load_checklist(path: str = "checklist.json") -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# === LLM call wrapper ===
def call_groq_chat(prompt: str, system_prompt: Optional[str] = None) -> str:
    api_key = os.getenv(API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"Set environment variable {API_KEY_ENV} with your Groq API key.")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    data = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 1600
    }

    resp = requests.post(API_URL, headers=headers, json=data, timeout=TIMEOUT)
    resp.raise_for_status()
    j = resp.json()
    # Support common chat response shape
    try:
        return j["choices"][0]["message"]["content"]
    except Exception:
        # fallback
        return str(j)

# === System / prompts ===
SYSTEM_PROMPT = (
    "You are a helpful legal-document assistant for contract review. "
    "Be concise, factual, and produce JSON where requested. Do NOT give legal advice."
)

SUMMARY_PROMPT = (
    "Summarize the key purpose and business terms of the contract below in 3-5 bullet points.\n\n"
    "Contract:\n\n{doc}"
)

EXTRACTION_PROMPT = (
    "Extract the following clauses from the contract text exactly as they appear (or empty string if not present): "
    "Liability, Termination, Payment Terms, Confidentiality. "
    "Return a JSON object with keys: Liability, Termination, PaymentTerms, Confidentiality. "
    "For each, include the extracted clause text (or empty string). "
    "Contract:\n\n{doc}"
)

VALIDATION_PROMPT = (
    "You are given extracted clauses (JSON) and a checklist of compliance rules (JSON). "
    "For each checklist key, return a JSON object mapping the checklist key to an object with fields: "
    "status ('COMPLIANT', 'MISSING', 'RISKY'), reason (short), suggested_fix (short suggestion), severity ('low','medium','high'). "
    "Data:\n\nClauses: {clauses}\n\nChecklist: {checklist}"
)

FOLLOWUP_PROMPT = (
    "Given the validation results and the extracted clause texts, generate a JSON object with two keys: "
    "'follow_up_questions' (list, up to 5 concise questions to ask the counterparty) and "
    "'suggested_rewrites' (list, up to 3 short suggested clause rewrites or snippets). "
    "Validation Results:\n{validation}\n\nExtracted Clauses:\n{clauses}"
)

# === Core functions ===
def summarize_document(doc_text: str) -> str:
    prompt = SUMMARY_PROMPT.format(doc=doc_text[:8000])  # trim to avoid huge prompts
    return call_groq_chat(prompt, system_prompt=SYSTEM_PROMPT)

def extract_clauses(doc_text: str) -> Dict[str, str]:
    prompt = EXTRACTION_PROMPT.format(doc=doc_text[:16000])
    out = call_groq_chat(prompt, system_prompt=SYSTEM_PROMPT)
    # Try to parse JSON out of response
    parsed = {}
    try:
        start = out.find("{")
        end = out.rfind("}") + 1
        if start != -1 and end != -1:
            json_text = out[start:end]
            parsed = json.loads(json_text)
        else:
            parsed = json.loads(out)
    except Exception:
        # fallback best-effort: try to find lines starting with keys
        parsed = {
            "Liability": "",
            "Termination": "",
            "PaymentTerms": "",
            "Confidentiality": ""
        }
        # crude parse: look for key labels in text
        lower = out.lower()
        for key in parsed.keys():
            label = key.lower()
            # find snippets heuristically
            idx = lower.find(label)
            if idx != -1:
                snippet = out[idx: idx + 500]
                parsed[key] = snippet

    # Normalize keys & ensure presence
    normalized = {
        "Liability": parsed.get("Liability", parsed.get("liability", "")) or "",
        "Termination": parsed.get("Termination", parsed.get("termination", "")) or "",
        "PaymentTerms": parsed.get("PaymentTerms", parsed.get("payment_terms", parsed.get("PaymentTerms", ""))) or "",
        "Confidentiality": parsed.get("Confidentiality", parsed.get("confidentiality", "")) or ""
    }
    return normalized

def validate_clauses_externally(clauses: Dict[str, str], checklist: Dict[str, str]) -> Dict[str, Any]:
    # Use the LLM to produce a nuanced validation per checklist item.
    # Map checklist keys to clause dictionary keys
    prompt = VALIDATION_PROMPT.format(clauses=json.dumps(clauses, indent=2), checklist=json.dumps(checklist, indent=2))
    out = call_groq_chat(prompt, system_prompt=SYSTEM_PROMPT)
    # Try to parse JSON
    try:
        start = out.find("{")
        end = out.rfind("}") + 1
        if start != -1 and end != -1:
            json_text = out[start:end]
            validated = json.loads(json_text)
        else:
            validated = json.loads(out)
    except Exception:
        # If parsing fails, provide a simple rule-based validation
        validated = {}
        # Accept checklist keys such as "Payment Terms" but clauses dict uses "PaymentTerms"
        for key, rule in checklist.items():
            lookup_key = key
            if key.lower() == "payment terms":
                lookup_key = "PaymentTerms"
            clause_text = clauses.get(lookup_key, "")
            if not clause_text.strip():
                validated[key] = {"status": "MISSING", "reason": "Clause not found.", "suggested_fix": rule, "severity": "high"}
            else:
                # heuristics
                low_keywords = ["limit", "cap", "$", "days", "notice", "terminate", "termination", "invoice", "due"]
                found_kw = any(k in clause_text.lower() for k in low_keywords)
                if found_kw:
                    validated[key] = {"status": "COMPLIANT", "reason": "Clause appears present and specific.", "suggested_fix": "", "severity": "low"}
                else:
                    validated[key] = {"status": "RISKY", "reason": "Clause present but may be vague.", "suggested_fix": "Clarify specifics per checklist.", "severity": "medium"}
    return validated

def generate_followups(clauses: Dict[str, str], validation: Dict[str, Any]) -> Dict[str, Any]:
    prompt = FOLLOWUP_PROMPT.format(validation=json.dumps(validation, indent=2), clauses=json.dumps(clauses, indent=2))
    out = call_groq_chat(prompt, system_prompt=SYSTEM_PROMPT)
    # Parse JSON or return text under key 'raw'
    try:
        start = out.find("{")
        end = out.rfind("}") + 1
        if start != -1 and end != -1:
            json_text = out[start:end]
            parsed = json.loads(json_text)
            return parsed
    except Exception:
        # return raw text if not JSON
        return {"raw": out.strip()}

# === Public process function used by UI ===
def process_document(file_path: str, checklist_path: str = "checklist.json") -> Dict[str, Any]:
    """
    Processes a contract (txt or pdf) and returns:
      {
        "summary": str,
        "clauses": {Liability, Termination, PaymentTerms, Confidentiality},
        "validation": { ... per checklist ... },
        "followups": { follow_up_questions: [...], suggested_rewrites: [...] } (or raw string)
        "timestamp": epoch
      }
    """
    # Read file
    if file_path.lower().endswith(".pdf"):
        doc_text = read_pdf(file_path)
    else:
        doc_text = read_text_file(file_path)

    checklist = load_checklist(checklist_path)

    # Run steps
    summary = summarize_document(doc_text)
    clauses = extract_clauses(doc_text)
    validation = validate_clauses_externally(clauses, checklist)
    followups = generate_followups(clauses, validation)

    report = {
        "summary": summary,
        "clauses": clauses,
        "validation": validation,
        "followups": followups,
        "timestamp": time.time()
    }
    return report

# === Optional CLI for quick runs ===
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Legal Document Summarizer & Validator Agent")
    parser.add_argument("--file", "-f", required=True, help="Path to contract text (.txt) or PDF (.pdf)")
    parser.add_argument("--checklist", "-c", default="checklist.json", help="Path to checklist JSON")
    parser.add_argument("--out", "-o", default="report.json", help="Path to output JSON report")
    args = parser.parse_args()

    path = args.file
    if path.lower().endswith(".pdf"):
        doc_text = read_pdf(path)
    else:
        doc_text = read_text_file(path)

    report = process_document(path, checklist_path=args.checklist)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n=== Report saved to", args.out, "===\n")
    print("Summary:\n", report["summary"][:2000])
    print("\nValidation (short):")
    for k, v in report["validation"].items():
        print(f"- {k}: {v.get('status','UNKNOWN')} — {v.get('reason','')}")
