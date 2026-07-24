import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"

import json
import torch
torch.set_num_threads(1)

from dotenv import load_dotenv
from PyPDF2 import PdfReader

from langchain_text_splitters import RecursiveCharacterTextSplitter
from fastembed import TextEmbedding


class DirectEmbeddings:
    """Minimal embeddings wrapper using fastembed (ONNX Runtime) instead
    of PyTorch -- avoids a persistent Windows access-violation crash seen
    when loading the embedding model through PyTorch-based paths."""

    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts):
        return [vec.tolist() for vec in self.model.embed(texts)]

    def embed_query(self, text):
        return list(self.model.embed([text]))[0].tolist()




from langchain_community.vectorstores import FAISS
from langchain_classic.memory import ConversationBufferMemory
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_groq import ChatGroq

load_dotenv()

PDF_FOLDER = "eval_pdfs"
EVAL_SET_FILE = "eval_set.json"
REPORT_FILE = "eval_report.md"
RESULTS_JSON = "eval_results.json"


def build_vectorstore(pdf_folder):
    
    print("Building vectorstore (first run downloads the embedding model, may take a minute)...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, length_function=len)
    
    all_chunks = []
    all_metadatas = []

    for filename in os.listdir(pdf_folder):
        if not filename.lower().endswith(".pdf"):
            continue

        reader = PdfReader(os.path.join(pdf_folder, filename))

        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if not page_text.strip():
                continue

            for chunk in splitter.split_text(page_text):
                all_chunks.append(chunk)
                all_metadatas.append({"source": filename, "page": page_num})

    print(f"Chunk count: {len(all_chunks)}")

    try:
        embeddings = DirectEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
        print("Embeddings model loaded.")

        vs = FAISS.from_texts(texts=all_chunks, embedding=embeddings, metadatas=all_metadatas)
        print("Vectorstore built.")
        return vs
    except Exception:
        import traceback
        traceback.print_exc()
        raise

def build_chain(vectorstore, llm):
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key="answer")
    return ConversationalRetrievalChain.from_llm(
        llm=llm, retriever=vectorstore.as_retriever(), memory=memory, return_source_documents=True
    )


def judge_answer(judge_llm, question, expected_answer, generated_answer):
    prompt = f"""You are an impartial evaluator grading a document Q&A system.

Question: {question}
Expected answer (ground truth): {expected_answer}
Generated answer (from the system being tested): {generated_answer}

Rate the generated answer on two dimensions, 1 (poor) to 5 (excellent):
- faithfulness: is everything in it supported by / consistent with the expected answer, with no fabricated claims?
- relevance: does it actually address the question asked?

Respond ONLY with JSON, no other text:
{{"faithfulness": <int 1-5>, "relevance": <int 1-5>, "reasoning": "<one short sentence>"}}
"""
    for attempt in range(3):
        raw = judge_llm.invoke(prompt).content.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json", "", 1).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    return {"faithfulness": None, "relevance": None, "reasoning": "judge failed to return valid JSON"}


def stars(score):
    if score is None:
        return "n/a"
    filled = round(score)
    return "⭐" * filled + "☆" * (5 - filled)


def main():
    with open(EVAL_SET_FILE, "r", encoding="utf-8") as f:
        eval_set = json.load(f)

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    judge_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.0)

    vectorstore = build_vectorstore(PDF_FOLDER)
    chain = build_chain(vectorstore, llm)

    results = []

    for i, item in enumerate(eval_set, start=1):
        print(f"[{i}/{len(eval_set)}] {item['question']}")

        chain.memory.clear()
        response = chain({"question": item["question"]})
        generated_answer = response["answer"]

        judgment = judge_answer(judge_llm, item["question"], item["expected_answer"], generated_answer)

        is_cross_doc = isinstance(item["source"], list)

        results.append({
            "question": item["question"],
            "expected_answer": item["expected_answer"],
            "generated_answer": generated_answer,
            "source": item["source"],
            "is_cross_doc": is_cross_doc,
            "faithfulness": judgment["faithfulness"],
            "relevance": judgment["relevance"],
            "reasoning": judgment["reasoning"],
        })

    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    write_report(results)
    print(f"\nDone. See {REPORT_FILE} and {RESULTS_JSON}.")


def write_report(results):
    valid = [r for r in results if r["faithfulness"] is not None]
    avg_faith = sum(r["faithfulness"] for r in valid) / len(valid)
    avg_rel = sum(r["relevance"] for r in valid) / len(valid)

    single_doc = [r for r in valid if not r["is_cross_doc"]]
    cross_doc = [r for r in valid if r["is_cross_doc"]]

    def avg(items, key):
        return sum(r[key] for r in items) / len(items) if items else 0

    lines = []
    lines.append("## 📊 Evaluation Results\n")
    lines.append(
        f"> **Overall: {avg_faith:.1f}/5 faithfulness · {avg_rel:.1f}/5 relevance** "
        f"across {len(valid)} questions ({len(single_doc)} single-document, {len(cross_doc)} cross-document).\n"
    )
    lines.append(
        "Evaluated using an LLM-as-judge methodology (Llama 3.3 70B via Groq). "
        "Since the judge shares a model family with the system under test, "
        "scores should be read as a relative quality signal rather than an absolute benchmark.\n"
    )

    lines.append("| Category | Faithfulness | Relevance | Count |")
    lines.append("|---|:---:|:---:|:---:|")
    lines.append(f"| All questions | {avg_faith:.1f}/5 | {avg_rel:.1f}/5 | {len(valid)} |")
    lines.append(f"| Single-document | {avg(single_doc, 'faithfulness'):.1f}/5 | {avg(single_doc, 'relevance'):.1f}/5 | {len(single_doc)} |")
    lines.append(f"| Cross-document (multi-PDF reasoning) | {avg(cross_doc, 'faithfulness'):.1f}/5 | {avg(cross_doc, 'relevance'):.1f}/5 | {len(cross_doc)} |")
    lines.append("")

    lines.append("<details>")
    lines.append("<summary><strong>Per-question breakdown</strong> (click to expand)</summary>\n")
    lines.append("| # | Question | Type | Faithfulness | Relevance |")
    lines.append("|---|---|:---:|:---:|:---:|")

    for i, r in enumerate(results, start=1):
        q_type = "Cross-doc" if r["is_cross_doc"] else "Single-doc"
        f_stars = stars(r["faithfulness"])
        r_stars = stars(r["relevance"])
        lines.append(f"| {i} | {r['question']} | {q_type} | {f_stars} | {r_stars} |")

    lines.append("\n</details>\n")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()