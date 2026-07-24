css = '''
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Spectral:wght@500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stHeader"],
.stApp {
    background-color: #0E1117 !important;
}

[data-testid="stSidebar"] {
    background-color: #131316;
    border-right: 1px solid #232327;
}

[data-testid="stSidebar"] .block-container {
    padding-left: 1.25rem;
    padding-right: 1.25rem;
}

.main .block-container {
    max-width: 760px;
    padding-top: 2.5rem;
}

/* ---------- Type scale (sidebar): 3 sizes total, nothing else ----------
   1. brand wordmark   2. eyebrow section label   3. body (names, buttons) */
.brand-row {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin: -2rem 0 2.5rem 0;
}
.brand-logo {
    width: 26px;
    height: 26px;
}
.sidebar-title {
    font-family: 'Spectral', Georgia, serif;
    font-size: 1.3rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: #ECECEC;
}
.eyebrow {
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8FA8D9;
    margin: 1rem 0 0.6rem 0;

    display: flex;
    align-items: center;
    gap: 7px;
}

.eyebrow::before {
    content: "";
    width: 2.45px;
    height: 12.5px;
    background: #8FA8D9;
    border-radius: 2px;
}
.chat-eyebrow {
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8FA8D9;
    margin: 1rem 0 0.6rem 0;
}
.eyebrow:first-of-type {
    margin-top: 0;
}
.eyebrow-pushed {
    margin-top: 2rem !important;
}

/* ---------- Sidebar section spacing -- plain whitespace, no visible line ---------- */
.section-spacer {
    height: 2.5rem;
}

/* ---------- "Indexed" section placeholder, shown before anything's processed ---------- */
.empty-indexed {
    font-size: 0.8rem;
    color: #6E6E7A;
    padding: 0.4rem 0;
}

/* ---------- Inline status line (upload/process success, or error) ----------
   One shared component, no filled box -- color is the only thing that
   changes between success and error states. */
.status-line {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.78rem;
    margin: -0.5rem 0 0 0;
    color: #5B8DEF;
}
.status-line.error {
    color: #E0645B;
}
.status-check {
    display: inline-flex;
    line-height: 1;
    color: inherit;
}
.status-check svg {
    stroke: currentColor;
    display: block;
}

/* One consistent look for every button in the sidebar -- this is what
   actually makes Upload and Process match, since both are native
   Streamlit buttons under the hood. Auto-width, not stretched. Bordered
   with the muted navy accent to tie back to the brand color. */
[data-testid="stSidebar"] button {
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    border-radius: 0.6rem !important;
    border: 1px solid #3A4A6B !important;
}

/* ---------- Welcome / empty state ---------- */
.welcome-panel {
    border: 1px solid #232327;
    border-radius: 1rem;
    background: #131316;
    padding: 2.75rem 2rem;
    margin-top: 2.5rem;
    text-align: center;
}
.welcome-title {
    font-family: 'Spectral', Georgia, serif;
    font-size: 1.5rem;
    font-weight: 600;
    color: #ECECEC;
    margin-bottom: 0.4rem;
}
.welcome-sub {
    color: #8E8EA0;
    font-size: 0.92rem;
    margin-bottom: 1.9rem;
}
.welcome-steps {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    max-width: 300px;
    margin: 0 auto;
    text-align: left;
}
.welcome-step {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    font-size: 0.92rem;
    color: #ECECEC;
}
.welcome-step-icon {
    width: 1.5rem;
    text-align: center;
    opacity: 0.85;
}

/* ---------- Chat bubbles ---------- */
.chat-row {
    display: flex;
    margin: 1.1rem 0;
    width: 100%;
}
.chat-row.user { justify-content: flex-end; }
.chat-row.assistant { justify-content: flex-start; }

.bubble.user {
    max-width: 75%;
    padding: 0.6rem 1rem;
    border-radius: 1.1rem;
    border-bottom-right-radius: 0.3rem;
    background: #1F2023;
    border: 1px solid #2A2B2E;
    color: #ECECEC;
    font-size: 0.95rem;
    line-height: 1.55;
}
.bubble.assistant {
    max-width: 100%;
    padding: 0.15rem 0;
    color: #ECECEC;
    font-size: 0.97rem;
    line-height: 1.65;
}

/* ---------- Sidebar: un-truncate the native file list ----------
   Broad, attribute-contains selectors so this survives Streamlit version
   bumps that rename the exact testid. min-width:0 matters -- flex children
   won't wrap text no matter what overflow/white-space say without it. */
[data-testid="stFileUploader"] section {
    padding-left: 0 !important;
}
[data-testid*="FileUploaderFile"],
[data-testid*="FileUploaderFile"] *,
[class*="uploadedFile"],
[class*="uploadedFile"] * {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    max-width: none !important;
    min-width: 0 !important;
}

/* ---------- Post-processing document stat cards ---------- */
.doc-stat-card {
    padding: 0.55rem 0.7rem;
    margin: 0.4rem 0;
    background: #17171A;
    border: 1px solid #232327;
    border-radius: 0.65rem;
}
.doc-stat-name {
    font-size: 0.83rem;
    color: #ECECEC;
    word-break: break-word;
    line-height: 1.35;
}
.doc-stat-meta {
    font-size: 0.73rem;
    color: #8E8EA0;
    margin-top: 0.2rem;
}

/* ---------- Chat input: flatten Streamlit's built-in blur/gradient footer ---------- */
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
[data-testid="stChatInputContainer"] {
    background: #0E1117 !important;
    background-image: none !important;
    backdrop-filter: none !important;
    box-shadow: none !important;
    border: none !important;
}
[data-testid="stBottom"]::before,
[data-testid="stBottom"]::after,
[data-testid="stBottomBlockContainer"]::before,
[data-testid="stBottomBlockContainer"]::after {
    content: none !important;
    background: none !important;
    backdrop-filter: none !important;
}
[data-testid="stChatInput"] {
    max-width: 760px;
    margin: 0 auto;
}
/* Nuclear reset: strip every layer inside the input area down to nothing,
   so no leftover wrapper can carry its own color -- then paint ONE box back. */
[data-testid="stChatInput"] * {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}
[data-testid="stChatInput"] {
    background-color: #1A1A1D !important;
    border: 1px solid #2A2B2E !important;
    border-radius: 1rem !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #5B8DEF !important;
}
[data-testid="stChatInput"] textarea {
    color: #ECECEC !important;
    padding: 0.75rem 1rem !important;
}
[data-testid="stChatInput"] button {
    background-color: #5B8DEF !important;
    border-radius: 50% !important;
}
</style>
'''

user_template = '''
<div class="chat-row user">
    <div class="bubble user">{{MSG}}</div>
</div>
'''

bot_template = '''
<div class="chat-row assistant">
    <div class="bubble assistant">{{MSG}}</div>
</div>
'''