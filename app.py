import streamlit as st
import google.generativeai as genai
import json
from gtts import gTTS
import io
from streamlit_javascript import st_javascript

# --- 1. ページ設定 ---
st.set_page_config(page_title="Gemini English Coach", page_icon="🎧", layout="wide")

# --- 2. ブラウザ保存 (LocalStorage) ---
def save_local(key, value):
    val = json.dumps(value, ensure_ascii=False)
    st_javascript(f"localStorage.setItem('{key}', JSON.stringify({val}));")

def load_local(key):
    return st_javascript(f"JSON.parse(localStorage.getItem('{key}'));")

# --- 3. デザイン ---
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; padding: 10px; text-align: left; margin-bottom: 5px; }
    .translation-text { color: #888; font-size: 0.85em; margin-top: 5px; border-top: 1px dashed #ccc; padding-top: 5px; }
    .correction-box { background-color: #f0f2f6; padding: 15px; border-radius: 12px; margin-bottom: 15px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. API設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key missing.")

model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

# --- 5. 機能関数 ---
@st.cache_data(show_spinner=False)
def get_audio(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except: return None

def get_ai_response(user_text):
    # 直近の履歴に絞ってレスポンス速度を維持
    history = "\n".join([f"{m['role']}: {m['en']}" for m in st.session_state.messages[-5:]])
    prompt = "Friendly English coach. Respond briefly. JSON ONLY: {\"en\": \"...\", \"jp\": \"...\"}"
    res = model.generate_content(f"{prompt}\n\nHistory:\n{history}\nUser: {user_text}")
    clean_text = res.text.replace('```json', '').replace('```', '').strip()
    return json.loads(clean_text)

# --- 6. 初期化と永続化 ---
if "initialized" not in st.session_state:
    st.session_state.messages = []
    st.session_state.vocab_list = []
    st.session_state.options = []
    st.session_state.initialized = True

# JS読み込み
if st.session_state.initialized and not st.session_state.messages:
    stored_msgs = load_local("msgs_v3")
    if stored_msgs: 
        st.session_state.messages = stored_msgs
        st.rerun()

if st.session_state.initialized and not st.session_state.vocab_list:
    stored_vocab = load_local("vocab_v3")
    if stored_vocab: st.session_state.vocab_list = stored_vocab

# --- 7. サイドバー ---
with st.sidebar:
    st.title("📚 Vocabulary")
    if st.session_state.vocab_list:
        for i, item in enumerate(st.session_state.vocab_list):
            col_v1, col_v2 = st.columns([0.8, 0.2])
            with col_v1:
                if st.button(f"📖 {item[:15]}...", key=f"v_{i}"):
                    res = model.generate_content(f"Analyze predicates in: '{item}' in Japanese.")
                    st.info(res.text)
            with col_v2:
                if st.button("🗑️", key=f"dv_{i}"):
                    st.session_state.vocab_list.pop(i)
                    save_local("vocab_v3", st.session_state.vocab_list)
                    st.rerun()
    
    st.write("---")
    st.title("Coach Settings")
    # 和文オンオフスイッチの復活
    show_translation = st.checkbox("和訳を表示", value=True)
    auto_speak = st.checkbox("音声を自動再生", value=True)
    
    st.write("---")
    if st.button("👋 新しい会話を始める"):
        st.session_state.messages = []
        save_local("msgs_v3", [])
        st.rerun()

# --- 8. チャット表示 ---
if not st.session_state.messages:
    first_ai = get_ai_response("Hello!")
    st.session_state.messages.append({"role": "assistant", "en": first_ai["en"], "jp": first_ai["jp"]})
    save_local("msgs_v3", st.session_state.messages)

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["en"])
        
        # 和訳表示スイッチがONの時だけ表示
        if show_translation and msg.get("jp"):
            st.markdown(f"<div class='translation-text'>{msg['jp']}</div>", unsafe_allow_html=True)
            
        if msg["role"] == "assistant" and auto_speak:
            audio = get_audio(msg["en"])
            if audio: st.audio(audio, format='audio/mp3')
        
        # 操作パネル (⭐は自分・AI両方に表示)
        c1, c2 = st.columns([0.1, 0.1])
        with c1:
            if st.button("⭐", key=f"s_{i}"):
                if msg["en"] not in st.session_state.vocab_list:
