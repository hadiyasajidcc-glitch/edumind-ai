import os
import re
import requests
import streamlit as st
import pypdf
import docx
import pptx
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SUPADATA_API_KEY = os.getenv("SUPADATA_API_KEY", "")

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="EduMind AI | Academic Hub",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Custom Styling
# ---------------------------------------------------------
st.markdown("""
    <style>
    .stApp {
        background-color: #0b1120;
        color: #f1f5f9;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #151e32 !important;
        border-right: 1px solid #1e293b;
    }

    .main-header {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.5rem;
        margin-bottom: 0.2rem;
    }

    .sub-header {
        color: #94a3b8;
        font-size: 1rem;
        margin-bottom: 2rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #151e32;
        padding: 8px 12px;
        border-radius: 12px;
        border: 1px solid #1e293b;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        border: none !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
    }

    .content-card {
        background-color: #151e32;
        border: 1px solid #1e293b;
        border-radius: 14px;
        padding: 24px;
        margin-top: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }

    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        font-weight: 600;
        border-radius: 10px;
        border: none;
        padding: 10px 24px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.4);
    }

    .stRadio label, .stTextInput label, .stFileUploader label {
        color: #cbd5e1 !important;
        font-weight: 500;
    }

    .stAlert {
        border-radius: 12px;
        border: 1px solid #1e293b;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def extract_text_from_file(file):
    name = file.name.lower()
    if name.endswith(".pdf"):
        reader = pypdf.PdfReader(file)
        return "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    elif name.endswith((".docx", ".doc")):
        doc = docx.Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif name.endswith((".pptx", ".ppt")):
        prs = pptx.Presentation(file)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        return "\n".join(text)
    elif name.endswith(".txt"):
        return str(file.read(), "utf-8")
    return ""

def extract_text_from_youtube(url):
    api_key = os.getenv("SUPADATA_API_KEY", "")
    if not api_key:
        return None, "Supadata API key missing. Please check your .env or Streamlit Secrets."

    endpoint = "https://api.supadata.ai/v1/youtube/transcript"
    headers = {"x-api-key": api_key}
    params = {"url": url, "text": "true"}
    
    try:
        response = requests.get(endpoint, headers=headers, params=params, timeout=20)
        data = response.json()
        
        if response.status_code == 200:
            content = data.get("content", "")
            if isinstance(content, str) and content.strip():
                return content.strip(), None
            elif isinstance(content, list):
                full_text = " ".join([item.get("text", "") for item in content if "text" in item])
                if full_text.strip():
                    return full_text.strip(), None
            return None, "No transcript text found for this video."
        else:
            error_msg = data.get("message", f"HTTP {response.status_code} Error")
            return None, f"Supadata API Error: {error_msg}"
            
    except Exception as e:
        return None, f"Network request failed: {str(e)}"

def ask_groq(client, prompt):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": "You are EduMind AI, a world-class academic tutor. Present information cleanly with headings, key points, and clear formatting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling Groq: {e}")
        return "An error occurred while generating content."

# ---------------------------------------------------------
# UI Header & API Check
# ---------------------------------------------------------
st.markdown('<div class="main-header">🎓 EduMind AI Study Partner</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Transform lengthy lectures, videos, and documents into instant notes & practice quizzes.</div>', unsafe_allow_html=True)

if not GROQ_API_KEY:
    st.error("❌ Groq API key not found! Please check your .env or Streamlit Secrets.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# ---------------------------------------------------------
# Sidebar Input Handling
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### 📥 Material Source")
    source_type = st.radio("Select Input Mode:", ["Document Upload", "YouTube Video Link"])
    st.markdown("---")
    
    extracted_text = ""
    source_identifier = ""

    if source_type == "Document Upload":
        uploaded_file = st.file_uploader(
            "Upload Document", 
            type=["pdf", "docx", "pptx", "txt"],
            help="Supports PDFs, Word documents, PowerPoints, and text files."
        )
        if uploaded_file:
            source_identifier = uploaded_file.name
            if "current_source" not in st.session_state or st.session_state.current_source != source_identifier:
                with st.spinner("📖 Processing document..."):
                    extracted_text = extract_text_from_file(uploaded_file)

    else:
        yt_url = st.text_input("YouTube Lecture URL:", placeholder="https://www.youtube.com/watch?v=...")
        if yt_url:
            source_identifier = yt_url
            if "current_source" not in st.session_state or st.session_state.current_source != source_identifier:
                with st.spinner("🎥 Extracting video transcript via Supadata..."):
                    text, err = extract_text_from_youtube(yt_url)
                    if err:
                        st.error(err)
                    else:
                        extracted_text = text

# ---------------------------------------------------------
# Session State Processing
# ---------------------------------------------------------
if source_identifier and extracted_text:
    if "current_source" not in st.session_state or st.session_state.current_source != source_identifier:
        st.session_state.doc_text = extracted_text[:8000]
        st.session_state.current_source = source_identifier
        st.session_state.chat_history = []
        
        with st.spinner("⚡ Synthesizing lecture notes & key takeaways..."):
            notes_prompt = f"Create structured, beautifully formatted student lecture notes with clear headings, bold definitions, and bullet points from this text:\n\n{st.session_state.doc_text}"
            st.session_state.notes = ask_groq(client, notes_prompt)

# ---------------------------------------------------------
# Workspaces
# ---------------------------------------------------------
if "doc_text" in st.session_state and st.session_state.doc_text:
    tab1, tab2, tab3 = st.tabs(["📝 Lecture Notes", "💬 AI Tutor & Voice", "🧩 Practice Quiz"])

    # TAB 1: NOTES
    with tab1:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.subheader("📌 Smart Lecture Notes")
        if "notes" in st.session_state:
            st.markdown(st.session_state.notes)
        st.markdown('</div>', unsafe_allow_html=True)

    # TAB 2: CHAT & VOICE
    with tab2:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.subheader("💬 Interactive Assistant")
        audio_in = st.audio_input("🎙️ Record Voice Query:")
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_input = st.chat_input("Ask anything about this lecture...")
        
        if user_input or audio_in:
            query = user_input if user_input else "Can you summarize the core points in my audio note?"
            
            with st.chat_message("user"):
                st.write(query)
            st.session_state.chat_history.append({"role": "user", "content": query})

            tutor_prompt = f"You are an expert tutor. Answer simply and concisely using this material:\n{st.session_state.doc_text}\n\nQuestion: {query}"
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    reply = ask_groq(client, tutor_prompt)
                    st.write(reply)
            
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.markdown('</div>', unsafe_allow_html=True)

    # TAB 3: QUIZ
    with tab3:
        st.markdown('<div class="content-card">', unsafe_allow_html=True)
        st.subheader("🧠 Self-Assessment Quiz")
        if st.button("⚡ Generate Practice Quiz"):
            with st.spinner("Drafting 5 targeted questions..."):
                quiz_prompt = f"Create a 5-question multiple-choice quiz with answer keys and brief explanations based on this material:\n\n{st.session_state.doc_text}"
                st.session_state.quiz = ask_groq(client, quiz_prompt)
        
        if "quiz" in st.session_state:
            st.markdown(st.session_state.quiz)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("👈 Upload a study document or paste a YouTube lecture link in the sidebar to get started!")