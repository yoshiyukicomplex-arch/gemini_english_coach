import streamlit as st
import google.generativeai as genai
import json

# --- 1. ページ設定 ---
st.set_page_config(page_title="Gemini English Coach", page_icon="🎧")

# --- 2. デザイン (CSS) ---
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; padding: 12px; text-align: left; margin-bottom: 10px; }
    .translation-text { color: #888; font-size: 0.9em; margin-top: 5px; border-top: 1px dashed #ccc; padding-top: 5px; }
    .correction-box { background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Gemini APIの設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"], transport='grpc')
else:
    st.error("Secretsに 'GEMINI_API_KEY' を設定してください。")

model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

# --- 4. サイドバー / 設定スイッチ ---
with st.sidebar:
    st.title("Coach Settings")
    show_translation = st.checkbox("和訳を表示 (Show Translation)", value=True)
    if st.button("会話をリセット"):
        st.session_state.messages = []
        st.session_state.options = []
        st.rerun()

# --- 5. セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "options" not in st.session_state:
    st.session_state.options = []

# --- 6. AIの返信生成（会話用） ---
def get_ai_chat_response(user_text):
    chat_history = ""
    for m in st.session_state.messages:
        chat_history += f"{m['role']}: {m['en']}\n"
    
    system_instruction = (
        "You are a friendly English coach. Respond to the user's input naturally in English, and provide a Japanese translation. "
        "Return ONLY a JSON object: {\"en\": \"English response\", \"jp\": \"日本語の訳\"}"
    )
    full_prompt = f"{system_instruction}\n\nHistory:\n{chat_history}\nUser: {user_text}"
    
    try:
        res = model.generate_content(full_prompt)
        clean_text = res.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except:
        return {"en": res.text, "jp": ""}

# --- 7. ユーザーの入力を添削・提案する関数 ---
def get_correction_suggestions(user_text):
    # ユーザーの英語を分析し、修正が必要なら3つ提案、不要なら空リストを返す
    prompt = (
        f"Analyze this English input from a learner: '{user_text}'. "
        "If it's natural and correct, return an empty list: []. "
        "If it can be improved, suggest 3 more natural versions with Japanese translations. "
        "Return ONLY a JSON list: [{\"en\": \"...\", \"jp\": \"...\"}, ...]"
    )
    try:
        res = model.generate_content(prompt)
        clean_text = res.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_text)
    except:
        return []

# --- 8. 初期挨拶 ---
if not st.session_state.messages:
    ai_data = get_ai_chat_response("Hello! Start the conversation.")
    st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})

# 会話履歴の表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["en"])
        if show_translation and msg["role"] == "assistant" and msg["jp"]:
            st.markdown(f"<div class='translation-text'>{msg['jp']}</div>", unsafe_allow_html=True)

# --- 9. ユーザー入力処理 ---
user_input = st.chat_input("英語で返信してみましょう")

if user_input:
    # 1. まず添削（提案）が必要か確認
    with st.spinner("Checking your English..."):
        suggestions = get_correction_suggestions(user_input)
    
    if suggestions:
        # 修正案がある場合は、まだ履歴には追加せず、選択肢を表示して待機
        st.session_state.options = suggestions
        st.session_state.current_draft = user_input # 下書きとして保存
        st.rerun()
    else:
        # 修正案がない（完璧な）場合は、そのまま会話を進める
        st.session_state.messages.append({"role": "user", "en": user_input, "jp": ""})
        with st.spinner("Coach is replying..."):
            ai_data = get_ai_chat_response(user_input)
            st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
        st.session_state.options = []
        st.rerun()

# --- 10. 添削・選択肢の表示 ---
if st.session_state.options:
    st.write("---")
    st.markdown("<div class='correction-box'>💡 より自然な表現があります。どれを使いますか？</div>", unsafe_allow_html=True)
    
    # 元の文章で進むボタンも用意
    if st.button(f"そのまま送信する: {st.session_state.get('current_draft', '')}"):
        original_text = st.session_state.current_draft
        st.session_state.messages.append({"role": "user", "en": original_text, "jp": ""})
        ai_data = get_ai_chat_response(original_text)
        st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
        st.session_state.options = []
        st.rerun()

    # 提案された選択肢ボタン
    for i, opt in enumerate(st.session_state.options):
        if st.button(f"{opt['en']}\n({opt['jp']})", key=f"opt_{i}"):
            st.session_state.messages.append({"role": "user", "en": f"✅ {opt['en']}", "jp": ""})
            ai_data = get_ai_chat_response(opt['en'])
            st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
            st.session_state.options = []
            st.rerun()
