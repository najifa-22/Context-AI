import json
import os

from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_groq import ChatGroq

load_dotenv()

PDF_FOLDER = "eval_pdfs"   # put your PDFs in a folder with this name
OUTPUT_FILE = "eval_set.json"
QUESTIONS_PER_PDF = 5


def extract_text(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text



MAX_CHARS = 6000  # keeps prompt + response comfortably under Groq's free-tier TPM limit


def truncate_text(text, max_chars=MAX_CHARS):
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...document truncated for length...]"




def generate_qa_pairs(llm, pdf_name, text):
    prompt = f"""You are creating an evaluation dataset for a document Q&A system.

Based ONLY on the text below (from a document called "{pdf_name}"), generate {QUESTIONS_PER_PDF} realistic question-answer pairs a curious reader might ask about this document.

Rules:
- Answers must be fully supported by the text below -- do not add outside knowledge.
- Vary the question types: some factual, some "why/how", one comparison or synthesis question if possible.
- Keep answers concise (2-4 sentences).
- Do not use double quotes inside question or answer text (paraphrase instead of quoting the source directly). Use only straight apostrophes, never curly/smart quotes.

Respond ONLY with a JSON array, no other text, in this exact format:
[
  {{"question": "...", "expected_answer": "..."}}
]

Document text:
{truncate_text(text)}
"""

    response = llm.invoke(prompt)
    raw = response.content.strip()

    # Strip markdown code fences if the model added them anyway
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json", "", 1).strip()

    return json.loads(raw)


def main():
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)

    all_qa_pairs = []

    for filename in os.listdir(PDF_FOLDER):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(PDF_FOLDER, filename)
        print(f"Processing {filename}...")

        text = extract_text(pdf_path)

        qa_pairs = None
        for attempt in range(1, 4):
            try:
                qa_pairs = generate_qa_pairs(llm, filename, text)
                break
            except json.JSONDecodeError as e:
                print(f"  Attempt {attempt} failed for {filename} -- invalid JSON ({e}).")

        if qa_pairs is None:
            print(f"  Giving up on {filename} after 3 attempts.")
            continue

        for pair in qa_pairs:
            pair["source"] = filename
            all_qa_pairs.append(pair)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_qa_pairs, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(all_qa_pairs)} Q&A pairs to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()