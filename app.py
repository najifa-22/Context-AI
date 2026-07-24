import base64

import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from langchain_classic.memory import ConversationBufferMemory
from langchain_classic.chains import ConversationalRetrievalChain

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from ui_templates import css, bot_template, user_template


def get_text_chunks(text):

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks


def get_file_stat(pdf, pdf_reader, chunk_count):
    """Build the display stats for one uploaded PDF (pages, chunks, size, author)."""

    author = None
    try:
        meta = pdf_reader.metadata
        if meta and meta.author and meta.author.strip():
            author = meta.author.strip()
    except Exception:
        author = None

    size_kb = len(pdf.getvalue()) / 1024
    size_label = f"{size_kb / 1024:.1f}MB" if size_kb > 1024 else f"{size_kb:.0f}KB"

    return {
        "name": pdf.name,
        "pages": len(pdf_reader.pages),
        "chunks": chunk_count,
        "size": size_label,
        "author": author,
    }


def get_pdf_data(pdf_docs):
    """Chunk each PDF page-by-page so every chunk carries its source
    filename and page number as metadata."""

    all_chunks = []
    all_metadatas = []
    file_stats = []

    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        chunk_count = 0

        for page_num, page in enumerate(pdf_reader.pages, start=1):
            page_text = page.extract_text() or ""

            if not page_text.strip():
                continue

            for chunk in get_text_chunks(page_text):
                all_chunks.append(chunk)
                all_metadatas.append({"source": pdf.name, "page": page_num})
                chunk_count += 1

        file_stats.append(get_file_stat(pdf, pdf_reader, chunk_count))

    return all_chunks, all_metadatas, file_stats


def get_vectorstore(text_chunks, metadatas):

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = FAISS.from_texts(
        texts=text_chunks,
        embedding=embeddings,
        metadatas=metadatas
    )

    return vectorstore


def get_conversation_chain(vectorstore):

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.3
    )

    st.session_state.llm = llm

    memory = ConversationBufferMemory(
    memory_key='chat_history',
    return_messages=True,
    output_key='answer'
    )

    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory,
        return_source_documents=True
    )

    return conversation_chain


def render_status_line(message, kind="success"):
    """Compact inline status indicator -- icon + one line of text, no
    boxed banner. Shares one visual style between success and error,
    only the color/icon differ."""

    if kind == "success":
        icon_svg = (
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="10"></circle>'
            '<polyline points="8 12 11 15 16 9"></polyline></svg>'
        )
    else:
        icon_svg = (
            '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="10"></circle>'
            '<line x1="12" y1="8" x2="12" y2="12"></line>'
            '<line x1="12" y1="16" x2="12.01" y2="16"></line></svg>'
        )

    st.markdown(
        f'<div class="status-line {kind}"><span class="status-check">{icon_svg}</span> {message}</div>',
        unsafe_allow_html=True
    )


def mark_uploaded():
    st.session_state.just_uploaded = True
    st.session_state.just_processed = False


def clear_upload_status():
    st.session_state.just_uploaded = False


def get_logo_base64(path="logo.png"):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None


def render_sidebar_brand():
    """Icon and wordmark in a single row -- inline HTML instead of st.logo()
    because st.logo() only supports an image, not image + text together."""

    logo_b64 = get_logo_base64()
    logo_img = (
        f'<img src="data:image/png;base64,{logo_b64}" class="brand-logo">'
        if logo_b64 else ""
    )

    st.markdown(
        f'<div class="brand-row">{logo_img}'
        f'<span class="sidebar-title">ContextAI</span></div>',
        unsafe_allow_html=True
    )


def render_file_stats():
    """Real per-document stats after processing -- pages/chunks are computed
    values, author is shown only when the PDF's own metadata actually has
    one. Nothing here is guessed. Always visible: shows a placeholder
    before anything has been indexed yet."""

    st.markdown('<div class="eyebrow">Indexed Documents</div>', unsafe_allow_html=True)

    file_stats = st.session_state.get("file_stats")

    if not file_stats:
        st.markdown(
            '<div class="empty-indexed">No documents indexed yet.</div>',
            unsafe_allow_html=True
        )
        return

    for stat in file_stats:
        meta_line = f'{stat["pages"]} pages &middot; {stat["chunks"]} chunks &middot; {stat["size"]}'
        if stat["author"]:
            meta_line += f'<br>by {stat["author"]}'

        st.markdown(
            f"""
            <div class="doc-stat-card">
                <div class="doc-stat-name">📄 {stat["name"]}</div>
                <div class="doc-stat-meta">{meta_line}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_welcome():
    """Empty-state panel shown before the first question is asked."""

    st.markdown(
        '''
        <div class="welcome-panel">
            <div class="welcome-title">Ask Your Documents Anything</div>
            <div class="welcome-sub">
                Upload your PDFs and ask questions in natural language. 
                <br> Every answer includes source references so you can verify where the information came from.
            </div>
            <div class="welcome-steps">
                <div class="welcome-step">
                    <span class="welcome-step-icon">1</span>
                    Upload PDFs in the sidebar
                </div>
                <div class="welcome-step">
                    <span class="welcome-step-icon">2</span>
                    Process your documents
                </div>
                <div class="welcome-step">
                    <span class="welcome-step-icon">3</span>
                    Start asking questions
                </div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )


def render_chat_history():
    """Render every message currently in memory as right/left chat bubbles,
    with the sources block shown right after each AI answer."""

    if not st.session_state.chat_history:
        return

    ai_index = 0

    for message in st.session_state.chat_history:
        is_user = isinstance(message, HumanMessage)
        template = user_template if is_user else bot_template

        st.markdown(
            template.replace("{{MSG}}", message.content),
            unsafe_allow_html=True
        )

        if not is_user:
            if ai_index < len(st.session_state.sources_history):
                render_sources(st.session_state.sources_history[ai_index])
            ai_index += 1


def render_sources(entry):
    """Render the 'X of Y PDFs relevant' line plus a per-PDF summary
    card for the most recent (or a given) answer."""

    st.markdown(
        f'<div class="chat-eyebrow">{entry["relevant_count"]} of {entry["total_count"]} uploaded PDFs relevant</div>',
        unsafe_allow_html=True
    )

    for s in entry["summaries"]:
        pages_label = ", ".join(str(p) for p in s["pages"]) if s["pages"] else "n/a"

        st.markdown(
            f"""
            <div class="doc-stat-card">
                <div class="doc-stat-name">📄 {s["name"]} (p. {pages_label})</div>
                <div class="doc-stat-meta">{s["summary"]}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


def group_sources_by_document(source_documents):
    """Group retrieved chunks by their source PDF, keeping track of
    which pages each relevant chunk came from."""

    grouped = {}

    for doc in source_documents:
        source_name = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page")

        grouped.setdefault(source_name, {"chunks": [], "pages": set()})
        grouped[source_name]["chunks"].append(doc.page_content)

        if page:
            grouped[source_name]["pages"].add(page)

    return grouped


def summarize_source(llm, question, source_name, chunks):
    """Summarize one PDF's relevant chunks re: the question. Length
    scales with how much relevant material there is -- a PDF with a
    few chunks gets a couple sentences, a PDF with many gets a full
    paragraph, so nothing important gets compressed away."""

    chunk_count = len(chunks)

    if chunk_count <= 3:
        length_instruction = "Answer in 1-2 concise sentences."
    elif chunk_count <= 8:
        length_instruction = "Answer in a short paragraph (3-5 sentences)."
    else:
        length_instruction = "Answer thoroughly in a full paragraph (6-10 sentences), covering the range of relevant points -- don't compress everything into one or two lines."

    combined_excerpts = "\n\n".join(chunks)

    prompt = f"""Based only on the following excerpts from "{source_name}", answer the question below.
{length_instruction}
Write it as a direct answer -- don't say "the text" or "the excerpts", just answer.

Question: {question}

Excerpts:
{combined_excerpts}
"""

    response = llm.invoke(prompt)
    return response.content


def handle_userinput(user_question):

    with st.spinner("Thinking..."):
        response = st.session_state.conversation({
            'question': user_question
        })

    st.session_state.chat_history = response['chat_history']

    grouped = group_sources_by_document(response['source_documents'])

    source_summaries = []
    for source_name, data in grouped.items():
        summary = summarize_source(
            st.session_state.llm,
            user_question,
            source_name,
            data["chunks"]
        )
        source_summaries.append({
            "name": source_name,
            "pages": sorted(data["pages"]),
            "summary": summary
        })

    st.session_state.sources_history.append({
        "summaries": source_summaries,
        "relevant_count": len(source_summaries),
        "total_count": len(st.session_state.get("file_stats", []))
    })


def main():

    load_dotenv()

    st.set_page_config(
        page_title="ContextAI",
        page_icon="logo.png"
    )

    st.write(css, unsafe_allow_html=True)

    if "conversation" not in st.session_state:
        st.session_state.conversation = None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "sources_history" not in st.session_state:
        st.session_state.sources_history = []

    if "just_uploaded" not in st.session_state:
        st.session_state.just_uploaded = False

    # Captured here (not at the bottom of the function) so the flags below
    # can be cleared BEFORE the sidebar renders below -- st.chat_input still
    # docks visually at the bottom of the page regardless of where in the
    # script it's called, so this doesn't move it on screen. Clearing the
    # flags here, rather than after the sidebar has already rendered, is
    # what makes the "Processing complete" status disappear on the very
    # next render instead of one submission late.
    user_question = st.chat_input("Start asking questions about your docs...")

    if user_question:
        st.session_state.just_processed = False
        st.session_state.just_uploaded = False

    with st.sidebar:

        render_sidebar_brand()

        st.markdown('<div class="eyebrow eyebrow-pushed">Your Documents</div>', unsafe_allow_html=True)

        pdf_docs = st.file_uploader(
            "Upload your PDFs here and click on 'Process'",
            accept_multiple_files=True,
            label_visibility="collapsed",
            on_change=mark_uploaded
        )

        if st.session_state.get("just_uploaded"):
            render_status_line("Upload complete! Start processing.")

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

        st.markdown('<div class="eyebrow">Build Your Index</div>', unsafe_allow_html=True)

        already_processed = st.session_state.conversation is not None
        button_label = "Reprocess" if already_processed else "Process"
        button_icon = ":material/refresh:" if already_processed else ":material/play_arrow:"

        if st.button(button_label, icon=button_icon, on_click=clear_upload_status):

            if not pdf_docs:
                render_status_line("Please upload at least one PDF first.", kind="error")

            else:
                with st.spinner("Processing"):

                    all_chunks, all_metadatas, file_stats = get_pdf_data(pdf_docs)

                    vectorstore = get_vectorstore(all_chunks, all_metadatas)

                    st.session_state.conversation = get_conversation_chain(
                        vectorstore
                    )

                    st.session_state.chat_history = []
                    st.session_state.sources_history = []
                    st.session_state.file_stats = file_stats

                st.session_state.just_processed = True
                st.rerun()

        if st.session_state.get("just_processed"):
            render_status_line("Processing complete! Ask a question now.")

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

        render_file_stats()

    # Replay existing conversation every rerun; show an empty state before that
    if st.session_state.chat_history:
        render_chat_history()
    else:
        render_welcome()

    if user_question:

        if st.session_state.conversation is None:
            render_status_line("Please upload and process PDFs first.", kind="error")

        else:
            st.markdown(
                user_template.replace("{{MSG}}", user_question),
                unsafe_allow_html=True
            )

            handle_userinput(user_question)

            st.markdown(
                bot_template.replace(
                    "{{MSG}}", st.session_state.chat_history[-1].content
                ),
                unsafe_allow_html=True
            )
            render_sources(st.session_state.sources_history[-1])


if __name__ == '__main__':
    main()