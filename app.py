import os
import requests
import streamlit as st
from groq import Groq
import pypdf
import docx
import pptx

# Page configuration
st.set_page_config(
    page_title="EduMind AI | Academic Hub",
    page_icon="🎓",
    layout="wide"
)

# Custom Pink Styling (Light Pink Background & Dark Pink Accent Elements)
st.markdown("""
    <style>
    .stApp {
        background-color: #FFF0F5;
        color: #2D2D2D;
    }
    div[data-testid="stSidebar"] {
        background-color: #FFE4E1;
        border-right: 2px solid #FFB6C1;
    }
    h1, h2, h3, .stTitle {
        color: #C71585 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stButton>button {
        background-color: #D87093;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #C71585;
        color: white;
    }
    .stTextInput>div>div>input {
        border: 1px solid #FFB6C1;
        border-radius: 6px;
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #C71585 !important;
        border-bottom-color: #C71585 !important;
    }
    </style>
""", unsafe_allow_html=True)

# API Keys Initialization
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
SUPADATA_API_KEY = st.secrets.get("SUPADATA_API_KEY") or os.getenv("SUPADATA_API_KEY")

if not GROQ_API_KEY:
    st.error("❌ Groq API key not found! Please check your Streamlit Secrets.")
    st.stop()

groq_client = Groq(api_key=GROQ_API_KEY)

# Helper: Extract YouTube Transcript via Supadata
def get_youtube_transcript(url):
    if not SUPADATA_API_KEY:
        st.error("❌ Supadata API key is missing in Streamlit Secrets.")
        return None
    endpoint = f"https://api.supadata.ai/v1/youtube/transcript?url={url}"
    headers = {"x-api-key": SUPADATA_API_KEY}
    try:
        res = requests.get(endpoint, headers=headers)
        if res.status_code == 200:
            data = res.json()
            content = data.get("content", [])
            full_text = " ".join([item.get("text", "") for item in content])
            return full_text if full_text.strip() else None
        else:
            st.error(f"Supadata API Error ({res.status_code}): {res.text}")
            return None
    except Exception as e:
        st.error(f"Failed to fetch YouTube transcript: {e}")
        return None

# Helper: Document Text Extractors
def extract_pdf(file):
    reader = pypdf.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def extract_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_pptx(file):
    prs = pptx.Presentation(file)
    text = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text

# Helper: Groq Inference Call
def ask_groq(client, prompt):
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
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

# Sidebar Input Options
st.sidebar.title("🌸 Material Source")
input_mode = st.sidebar.radio("Select Input Mode:", ["Document Upload", "YouTube Video Link"])

extracted_text = ""

if input_mode == "Document Upload":
    uploaded_file = st.sidebar.file_uploader("Upload study file (.pdf, .docx, .pptx)", type=["pdf", "docx", "pptx"])
    if uploaded_file:
        file_ext = uploaded_file.name.split(".")[-1].lower()
        if file_ext == "pdf":
            extracted_text = extract_pdf(uploaded_file)
        elif file_ext == "docx":
            extracted_text = extract_docx(uploaded_file)
        elif file_ext == "pptx":
            extracted_text = extract_pptx(uploaded_file)

elif input_mode == "YouTube Video Link":
    yt_url = st.sidebar.text_input("YouTube Lecture URL:")
    if yt_url:
        with st.spinner("Fetching transcript via Supadata..."):
            extracted_text = get_youtube_transcript(yt_url)
            if extracted_text:
                st.sidebar.success("Transcript loaded successfully!")

# Main Dashboard Interface
st.title("🎓 EduMind AI Study Partner")
st.write("Transform lengthy lectures, videos, and documents into instant notes & practice quizzes.")

if extracted_text:
    tab1, tab2, tab3 = st.tabs(["📝 Lecture Notes", "💬 AI Tutor", "🧩 Practice Quiz"])

    with tab1:
        st.subheader("📌 Smart Lecture Notes")
        if st.button("Generate Summary Notes"):
            with st.spinner("Summarizing material..."):
                prompt = f"Provide detailed, structured study notes with bullet points and key takeaways for this content:\n\n{extracted_text[:12000]}"
                notes = ask_groq(groq_client, prompt)
                st.markdown(notes)

    with tab2:
        st.subheader("💬 Ask Your Material Anything")
        user_q = st.text_input("Type your question about the content:")
        if user_q:
            with st.spinner("Thinking..."):
                prompt = f"Context:\n{extracted_text[:10000]}\n\nQuestion: {user_q}\nAnswer concisely and accurately."
                ans = ask_groq(groq_client, prompt)
                st.write(ans)

    with tab3:
        st.subheader("🧩 Practice Quiz")
        if st.button("⚡ Generate Practice Quiz"):
            with st.spinner("Creating 5-question quiz..."):
                prompt = f"Generate a 5-question multiple choice quiz based on this text, complete with answer keys and explanations:\n\n{extracted_text[:10000]}"
                quiz = ask_groq(groq_client, prompt)
                st.markdown(quiz)
else:
    st.info("👈 Please upload a document or paste a YouTube URL in the sidebar to begin.")