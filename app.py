import streamlit as st
import google.generativeai as genai
import json

# --- 1. ページ設定 ---
st.set_page_config(page_title="Gemini English Coach", page_icon="🎧")

# --- 2. デザイン (CSS) ---
st.markdown("""
    <style>
    .stButton > button { width: 100%; border-radius: 12px; padding: 12px; text-align: left; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Gemini APIの設定 ---
# transport='grpc' を追加して通信を安定させます
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"], transport='grpc')
else:
    st.error("Secretsに 'GEMINI_API_KEY' を設定してください。")

# モデル名を最も確実に認識される形式に変更
model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# --- 4. セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "options" not in st.session_state:
    st.session_state.options = []

# --- 5. AIの初期挨拶 ---
if not st.session_state.messages:
    try:
        # 指示をシンプルにしてエラーを回避
        initial_prompt = "Hello! I am your friendly English coach. Let's start our conversation with a short greeting!"
        response = model.generate_content(initial_prompt)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
    except Exception as e:
        st.error(f"接続エラーが発生しました。APIキーを確認してください: {e}")

# 会話履歴の表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- 6. ユーザー入力エリア ---
user_input = st.chat_input("英語で返信してみましょう")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # 3つの提案を求めるプロンプト
    analysis_prompt = f"The user said '{user_input}'. Suggest 3 natural English sentences they might have meant with Japanese translations. Return ONLY a JSON list: [{{'en': '...', 'jp': '...'}}, ...]"
    
    try:
        res = model.generate_content(analysis_prompt)
        text = res.text
        # JSON部分を抽出する処理
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != 0:
            st.session_state.options = json.loads(text[start:end])
    except:
        st.session_state.options = []
    st.rerun()

# --- 7. 選択肢の表示 ---
if st.session_state.options:
    st.write("---")
    st.caption("💡 Suggestion (クリックして返信):")
    for i, opt in enumerate(st.session_state.options):
        if st.button(f"{opt['en']}\n({opt['jp']})", key=f"opt_{i}"):
            st.session_state.messages.append({"role": "user", "content": f"✅ {opt['en']}"})
            try:
                next_res = model.generate_content(f"The user chose: '{opt['en']}'. Continue the conversation in English.")
                st.session_state.messages.append({"role": "assistant", "content": next_res.text})
            except:
                st.error("AIからの返信に失敗しました。")
            st.session_state.options = []
            st.rerun()
