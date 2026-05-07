import streamlit as st
import google.generativeai as genai
import json
from gtts import gTTS
import io

# --- 1. ページ設定 ---
st.set_page_config(page_title="Gemini English Coach", page_icon="🎧", layout="wide")

# --- 2. デザイン (CSS) ---
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; padding: 12px; text-align: left; margin-bottom: 5px; }
    .translation-text { color: #888; font-size: 0.85em; margin-top: 5px; border-top: 1px dashed #ccc; padding-top: 5px; }
    .correction-box { background-color: #f0f2f6; padding: 15px; border-radius: 12px; margin-bottom: 15px; border-left: 5px solid #ff4b4b; }
    .vocab-detail-box { background-color: #fdfdfe; border: 1px solid #e1e4e8; padding: 15px; border-radius: 10px; margin-top: 10px; }
    .explanation-text { background-color: #fff3cd; color: #856404; padding: 10px; border-radius: 8px; font-size: 0.9em; margin-bottom: 10px; border: 1px solid #ffeeba; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Gemini APIの設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"], transport='grpc')
else:
    st.error("Secretsに 'GEMINI_API_KEY' を設定してください。")

model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

# --- 4. 便利関数 ---
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
        return json.loads(res.text.replace('```json', '').replace('```', '').strip())
    except: return {"en": res.text, "jp": ""}

# --- 5. セッション初期化 ---
if "messages" not in st.session_state: st.session_state.messages = []
if "options" not in st.session_state: st.session_state.options = []
if "vocab_list" not in st.session_state: st.session_state.vocab_list = []
if "vocab_detail" not in st.session_state: st.session_state.vocab_detail = ""

# --- 6. サイドバー（単語・述語帳） ---
with st.sidebar:
    st.title("📚 Phrase & Vocab List")
    st.caption("保存したメッセージから述語や重要単語を抽出します")
    
    if not st.session_state.vocab_list:
        st.info("チャット内の ⭐ボタン で保存してください")
    else:
        for i, item in enumerate(st.session_state.vocab_list):
            # ボタンにはフレーズの冒頭を表示
            if st.button(f"📖 {item[:25]}...", key=f"vocab_{i}"):
                with st.spinner("Analyzing phrases & verbs..."):
                    # 述語(Predicates)と重要単語を抽出するプロンプト
                    analysis_prompt = (
                        f"Extract and explain 3-4 key items from this sentence: '{item}'.\n"
                        "Focus on:\n"
                        "1. Important predicates (verbs/phrasal verbs)\n"
                        "2. Useful idioms\n"
                        "3. Essential vocabulary\n"
                        "Format the output in Japanese with: 【項目】(発音) 意味 / 例文"
                    )
                    res = model.generate_content(analysis_prompt)
                    st.session_state.vocab_detail = res.text
        
        if st.session_state.vocab_detail:
            st.markdown("---")
            st.markdown("### 💡 Analysis Result")
            st.markdown(f"<div class='vocab-detail-box'>{st.session_state.vocab_detail}</div>", unsafe_allow_html=True)
            if st.button("詳細を閉じる"):
                st.session_state.vocab_detail = ""
                st.rerun()

    st.markdown("---")
    st.title("Coach Settings")
    show_translation = st.checkbox("和訳を表示", value=True)
    auto_speak = st.checkbox("音声を自動生成", value=True)
    if st.button("会話をリセット"):
        st.session_state.messages = []; st.session_state.options = []; st.session_state.vocab_list = []; st.rerun()

# --- 7. メイン画面（チャット） ---
if not st.session_state.messages:
    ai_data = get_ai_chat_response("Hello!")
    st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["en"])
        if show_translation and msg["role"] == "assistant":
            st.markdown(f"<div class='translation-text'>{msg['jp']}</div>", unsafe_allow_html=True)
        
        if msg["role"] == "assistant":
            col_a, col_b = st.columns([0.7, 0.3])
            with col_a:
                if auto_speak: st.audio(speak(msg["en"]), format='audio/mp3')
            with col_b:
                if st.button("⭐ 保存", key=f"save_{hash(msg['en'])}"):
                    if msg["en"] not in st.session_state.vocab_list:
                        st.session_state.vocab_list.append(msg["en"])
                        st.toast("フレーズを保存しました！")

# --- 8. 入力と提案ロジック ---
user_input = st.chat_input("英語で返信...")

if user_input:
    with st.spinner("Checking..."):
        prompt = f"Learner input: '{user_input}'. If natural, return []. Else, suggest 3 versions. Return ONLY JSON list: [{\"en\": \"...\", \"jp\": \"...\", \"why\": \"...\"}, ...]"
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
        st.rerun()

# 提案・選択エリア
if st.session_state.options:
    st.write("---")
    st.markdown("<div class='correction-box'>💡 表現をブラッシュアップしましょう</div>", unsafe_allow_html=True)
    if st.button(f"そのまま送信: {st.session_state.get('current_draft', '')}"):
        txt = st.session_state.current_draft
        st.session_state.messages.append({"role": "user", "en": txt, "jp": ""})
        ai_data = get_ai_chat_response(txt)
        st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
        st.session_state.options = []; st.rerun()

    for i, opt in enumerate(st.session_state.options):
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            if st.button(f"{opt['en']}\n({opt['jp']})", key=f"btn_{i}"):
                st.session_state.messages.append({"role": "user", "en": f"✅ {opt['en']}", "jp": ""})
                ai_data = get_ai_chat_response(opt['en'])
                st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
                st.session_state.options = []; st.rerun()
        with col2:
            if st.button("❓", key=f"exp_{i}"):
                st.info(opt['why'])
