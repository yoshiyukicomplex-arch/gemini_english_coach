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
    # JavaScriptの非同期実行に対応
    return st_javascript(f"JSON.parse(localStorage.getItem('{key}'));")

# --- 3. デザイン ---
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; padding: 10px; text-align: left; margin-bottom: 5px; }
    .translation-text { color: #888; font-size: 0.85em; margin-top: 5px; border-top: 1px dashed #ccc; padding-top: 5px; }
    .correction-box { background-color: #f0f2f6; padding: 15px; border-radius: 12px; margin-bottom: 15px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. API設定 (モデルは固定) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key missing.")

# モデルは変えずにそのまま使用
model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

# --- 5. 機能関数 (キャッシュで高速化) ---
@st.cache_data(show_spinner=False)
def get_audio(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except: return None

def get_ai_response(user_text):
    history = "\n".join([f"{m['role']}: {m['en']}" for m in st.session_state.messages[-5:]]) # 直近5件に絞って高速化
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

# JS読み込み（表示崩れ防止のため、空の時だけ実行）
if st.session_state.initialized and not st.session_state.messages:
    stored_msgs = load_local("msgs_v2")
    if stored_msgs: 
        st.session_state.messages = stored_msgs
        st.rerun()

if st.session_state.initialized and not st.session_state.vocab_list:
    stored_vocab = load_local("vocab_v2")
    if stored_vocab: st.session_state.vocab_list = stored_vocab

# --- 7. サイドバー ---
with st.sidebar:
    st.title("📚 Vocabulary")
    if st.session_state.vocab_list:
        for i, item in enumerate(st.session_state.vocab_list):
            col_v1, col_v2 = st.columns([0.8, 0.2])
            with col_v1:
                if st.button(f"📖 {item[:15]}...", key=f"v_{i}"):
                    res = model.generate_content(f"Explain predicates in: '{item}' in Japanese.")
                    st.info(res.text)
            with col_v2:
                if st.button("🗑️", key=f"dv_{i}"):
                    st.session_state.vocab_list.pop(i)
                    save_local("vocab_v2", st.session_state.vocab_list)
                    st.rerun()
    
    st.write("---")
    if st.button("👋 新しい会話を始める"):
        st.session_state.messages = []
        save_local("msgs_v2", [])
        st.rerun()

# --- 8. チャット表示 ---
if not st.session_state.messages:
    first_ai = get_ai_response("Hello!")
    st.session_state.messages.append({"role": "assistant", "en": first_ai["en"], "jp": first_ai["jp"]})
    save_local("msgs_v2", st.session_state.messages)

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["en"])
        if msg["role"] == "assistant" and msg.get("jp"):
            st.markdown(f"<div class='translation-text'>{msg['jp']}</div>", unsafe_allow_html=True)
            audio = get_audio(msg["en"])
            if audio: st.audio(audio, format='audio/mp3')
        
        # 操作パネル (⭐は自分の発言でも表示)
        c1, c2 = st.columns([0.1, 0.1])
        with c1:
            if st.button("⭐", key=f"s_{i}"):
                if msg["en"] not in st.session_state.vocab_list:
                    st.session_state.vocab_list.append(msg["en"])
                    save_local("vocab_v2", st.session_state.vocab_list)
                    st.toast("単語帳に保存しました！")
        with c2:
            if st.button("🗑️", key=f"d_{i}"):
                st.session_state.messages.pop(i)
                save_local("msgs_v2", st.session_state.messages)
                st.rerun()

# --- 9. 入力と添削 ---
user_input = st.chat_input("英語で話しかけてください")

if user_input:
    check_prompt = f'''Analyze: "{user_input}". If natural, return []. Else, 3 suggestions. JSON ONLY: [{{"en": "...", "jp": "...", "why": "..."}}]'''
    res = model.generate_content(check_prompt)
    try:
        suggestions = json.loads(res.text.replace('```json', '').replace('```', '').strip())
    except: suggestions = []

    if suggestions:
        st.session_state.options = suggestions
        st.session_state.current_draft = user_input
        st.rerun()
    else:
        st.session_state.messages.append({"role": "user", "en": user_input})
        ai = get_ai_response(user_input)
        st.session_state.messages.append({"role": "assistant", "en": ai["en"], "jp": ai["jp"]})
        save_local("msgs_v2", st.session_state.messages)
        st.rerun()

# 添削オプション
if st.session_state.options:
    st.write("---")
    if st.button(f"そのまま送信: {st.session_state.current_draft}"):
        txt = st.session_state.current_draft
        st.session_state.messages.append({"role": "user", "en": txt})
        ai = get_ai_response(txt)
        st.session_state.messages.append({"role": "assistant", "en": ai["en"], "jp": ai["jp"]})
        save_local("msgs_v2", st.session_state.messages)
        st.session_state.options = []; st.rerun()

    for i, opt in enumerate(st.session_state.options):
        if st.button(f"{opt['en']} ({opt['jp']})", key=f"opt_{i}"):
            st.session_state.messages.append({"role": "user", "en": opt['en']})
            ai = get_ai_response(opt['en'])
            st.session_state.messages.append({"role": "assistant", "en": ai["en"], "jp": ai['jp']})
            save_local("msgs_v2", st.session_state.messages)
            st.session_state.options = []; st.rerun()
