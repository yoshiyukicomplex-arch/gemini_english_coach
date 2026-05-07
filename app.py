import streamlit as st
import google.generativeai as genai
import json
from gtts import gTTS
import io
from streamlit_javascript import st_javascript

# --- 1. ページ設定 ---
st.set_page_config(page_title="Gemini English Coach", page_icon="🎧", layout="wide")

# --- 2. ブラウザ保存用の関数 ---
def save_to_local(key, value):
    json_value = json.dumps(value, ensure_ascii=False)
    st_javascript(f"localStorage.setItem('{key}', JSON.stringify({json_value}));")

def load_from_local(key):
    result = st_javascript(f"JSON.parse(localStorage.getItem('{key}'));")
    return result

# --- 3. デザイン (CSS) ---
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; padding: 12px; text-align: left; margin-bottom: 5px; }
    .translation-text { color: #888; font-size: 0.85em; margin-top: 5px; border-top: 1px dashed #ccc; padding-top: 5px; }
    .correction-box { background-color: #f0f2f6; padding: 15px; border-radius: 12px; margin-bottom: 15px; border-left: 5px solid #ff4b4b; }
    .vocab-detail-box { background-color: #fdfdfe; border: 1px solid #e1e4e8; padding: 15px; border-radius: 10px; margin-top: 10px; white-space: pre-wrap; }
    .delete-btn > button { color: #ff4b4b; border: 1px solid #ff4b4b; padding: 2px 8px; font-size: 0.8em; width: auto; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. Gemini APIの設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"], transport='grpc')
else:
    st.error("Secretsに 'GEMINI_API_KEY' を設定してください。")

model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

# --- 5. 便利関数 ---
def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

def get_ai_chat_response(user_text):
    history = "\n".join([f"{m['role']}: {m['en']}" for m in st.session_state.messages])
    prompt = "You are a friendly English coach. Respond to the user naturally. Return ONLY a JSON object: {\"en\": \"English response\", \"jp\": \"日本語の訳\"}"
    try:
        res = model.generate_content(f"{prompt}\n\nHistory:\n{history}\nUser: {user_text}")
        clean_text = res.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except: return {"en": "Error occurred.", "jp": ""}

# --- 6. セッションとデータの初期化 ---
if "initialized" not in st.session_state:
    st.session_state.messages = []
    st.session_state.vocab_list = []
    st.session_state.options = []
    st.session_state.vocab_detail = ""
    st.session_state.initialized = True

# ブラウザからデータを読み込む（JSの実行を待つために1度だけ試行）
if not st.session_state.messages:
    stored_msgs = load_from_local("eng_coach_messages")
    if stored_msgs: st.session_state.messages = stored_msgs

if not st.session_state.vocab_list:
    stored_vocab = load_from_local("eng_coach_vocab")
    if stored_vocab: st.session_state.vocab_list = stored_vocab

# --- 7. サイドバー（単語・述語帳 & 設定） ---
with st.sidebar:
    st.title("📚 Phrase List")
    if st.session_state.vocab_list:
        for i, item in enumerate(st.session_state.vocab_list):
            col_v1, col_v2 = st.columns([0.8, 0.2])
            with col_v1:
                if st.button(f"📖 {item[:20]}...", key=f"vocab_{i}"):
                    with st.spinner("Analyzing..."):
                        res = model.generate_content(f"Extract key predicates and idioms from: '{item}'. Explain in Japanese.")
                        st.session_state.vocab_detail = res.text
            with col_v2:
                # 単語帳の個別削除
                if st.button("🗑️", key=f"del_v_{i}"):
                    st.session_state.vocab_list.pop(i)
                    save_to_local("eng_coach_vocab", st.session_state.vocab_list)
                    st.rerun()
        
        if st.session_state.vocab_detail:
            st.markdown(f"<div class='vocab-detail-box'>{st.session_state.vocab_detail}</div>", unsafe_allow_html=True)
            if st.button("詳細を閉じる"):
                st.session_state.vocab_detail = ""; st.rerun()

    st.markdown("---")
    st.title("Coach Settings")
    show_translation = st.checkbox("和訳を表示", value=True)
    auto_speak = st.checkbox("音声を自動生成", value=True)
    
    if st.button("👋 新しい会話を始める"):
        st.session_state.messages = []
        save_to_local("eng_coach_messages", [])
        st.rerun()

# --- 8. メイン画面（チャット） ---
if not st.session_state.messages:
    ai_data = get_ai_chat_response("Hello!")
    st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
    save_to_local("eng_coach_messages", st.session_state.messages)

# チャット履歴の描画
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.write(msg["en"])
        if show_translation and msg["role"] == "assistant":
            st.markdown(f"<div class='translation-text'>{msg['jp']}</div>", unsafe_allow_html=True)
        
        # 操作パネル（音声・保存・削除）
        col_c1, col_c2, col_c3 = st.columns([0.6, 0.2, 0.2])
        with col_c1:
            if msg["role"] == "assistant" and auto_speak:
                st.audio(speak(msg["en"]), format='audio/mp3')
        with col_c2:
            if msg["role"] == "assistant":
                if st.button("⭐", key=f"save_{i}", help="単語帳へ"):
                    if msg["en"] not in st.session_state.vocab_list:
                        st.session_state.vocab_list.append(msg["en"])
                        save_to_local("eng_coach_vocab", st.session_state.vocab_list)
                        st.toast("保存！")
        with col_c3:
            # 個別削除ボタン
            if st.button("🗑️", key=f"del_msg_{i}", help="このメッセージを削除"):
                st.session_state.messages.pop(i)
                save_to_local("eng_coach_messages", st.session_state.messages)
                st.rerun()

# --- 9. 入力と提案ロジック ---
user_input = st.chat_input("英語で返信...")

if user_input:
    with st.spinner("Checking..."):
        prompt = f'''Learner input: "{user_input}". If natural, return []. Else, suggest 3 versions. Return ONLY JSON list: [{{"en": "...", "jp": "...", "why": "..."}}, ...]'''
        try:
            res = model.generate_content(prompt)
            suggestions = json.loads(res.text.replace('```json', '').replace('```', '').strip())
        except: suggestions = []
    
    if suggestions:
        st.session_state.options = suggestions
        st.session_state.current_draft = user_input
        st.rerun()
    else:
        st.session_state.messages.append({"role": "user", "en": user_input, "jp": ""})
        ai_data = get_ai_chat_response(user_input)
        st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
        save_to_local("eng_coach_messages", st.session_state.messages)
        st.rerun()

# 提案エリア
if st.session_state.options:
    st.write("---")
    if st.button(f"そのまま送信: {st.session_state.current_draft}"):
        txt = st.session_state.current_draft
        st.session_state.messages.append({"role": "user", "en": txt, "jp": ""})
        ai_data = get_ai_chat_response(txt)
        st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
        save_to_local("eng_coach_messages", st.session_state.messages)
        st.session_state.options = []; st.rerun()

    for i, opt in enumerate(st.session_state.options):
        col_opt1, col_opt2 = st.columns([0.85, 0.15])
        with col_opt1:
            if st.button(f"{opt['en']}\n({opt['jp']})", key=f"btn_{i}"):
                st.session_state.messages.append({"role": "user", "en": f"✅ {opt['en']}", "jp": ""})
                ai_data = get_ai_chat_response(opt['en'])
                st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
                save_to_local("eng_coach_messages", st.session_state.messages)
                st.session_state.options = []; st.rerun()
        with col_opt2:
            if st.button("❓", key=f"exp_{i}"): st.info(opt['why'])
