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
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Gemini APIの設定 ---
if "GEMINI_API_KEY" in st.secrets:
    # 通信を安定させるため transport='grpc' を指定
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"], transport='grpc')
else:
    st.error("Secretsに 'GEMINI_API_KEY' を設定してください。")

# ご自身で見つけられた最新モデルを指定
model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')

# --- 4. サイドバー / 設定スイッチ ---
with st.sidebar:
    st.title("Coach Settings")
    show_translation = st.checkbox("和訳を表示 (Show Translation)", value=True)
    st.write("---")
    if st.button("会話をリセット (Reset Conversation)"):
        st.session_state.messages = []
        st.session_state.options = []
        st.rerun()

# --- 5. セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "options" not in st.session_state:
    st.session_state.options = []

# --- 6. AIの返信生成関数 ---
def get_ai_response(prompt_text):
    # 返信と和訳をJSONで受け取るためのシステム指示
    system_instruction = (
        "Respond in English as a friendly coach, but also provide a natural Japanese translation. "
        "Return ONLY a JSON object: {\"en\": \"English response\", \"jp\": \"日本語の訳\"}"
    )
    full_prompt = f"{system_instruction}\n\nUser input: {prompt_text}"
    
    try:
        res = model.generate_content(full_prompt)
        # 不要な装飾（```jsonなど）を削除して解析
        clean_text = res.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_text)
        return data
    except:
        # エラー時のフォールバック
        return {"en": res.text, "jp": "(翻訳を取得できませんでした)"}

# --- 7. 初期挨拶の発動 ---
if not st.session_state.messages:
    with st.spinner("Coach is preparing..."):
        initial_data = get_ai_response("Hello! Please start a conversation with a short greeting.")
        st.session_state.messages.append({"role": "assistant", "en": initial_data["en"], "jp": initial_data["jp"]})

# 会話履歴の描画
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["en"])
        # スイッチがオン、かつAI（assistant）の発言のみ和訳を表示
        if show_translation and msg["role"] == "assistant":
            st.markdown(f"<div class='translation-text'>{msg['jp']}</div>", unsafe_allow_html=True)

# --- 8. ユーザー入力エリア ---
user_input = st.chat_input("英語でメッセージを送る...")

if user_input:
    # ユーザーの発言を履歴に追加
    st.session_state.messages.append({"role": "user", "en": user_input, "jp": ""})
    
    # ユーザー発言に対する「3つの返信候補」を作成
    analysis_prompt = (
        f"The user said: '{user_input}'. Suggest 3 natural English sentences they could use next with Japanese translations. "
        "Return ONLY a JSON list: [{\"en\": \"...\", \"jp\": \"...\"}, {\"en\": \"...\", \"jp\": \"...\"}, {\"en\": \"...\", \"jp\": \"...\"}]"
    )
    
    try:
        res_opt = model.generate_content(analysis_prompt)
        clean_opt = res_opt.text.replace('```json', '').replace('```', '').strip()
        st.session_state.options = json.loads(clean_opt)
    except:
        st.session_state.options = []

    # AI先生としての返信を作成
    with st.spinner("Thinking..."):
        ai_data = get_ai_response(user_input)
        st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
    
    st.rerun()

# --- 9. 提案（Suggestion）ボタンの表示 ---
if st.session_state.options:
    st.write("---")
    st.caption("💡 あなたへの提案 (クリックで返信):")
    for i, opt in enumerate(st.session_state.options):
        # 英語と日本語をセットにしたボタン
        button_label = f"{opt['en']}\n({opt['jp']})"
        if st.button(button_label, key=f"opt_{i}"):
            # ボタンを押したら、それをユーザーの発言として扱う
            st.session_state.messages.append({"role": "user", "en": f"✅ {opt['en']}", "jp": ""})
            with st.spinner("Coach is replying..."):
                ai_data = get_ai_response(f"The user selected this option: {opt['en']}")
                st.session_state.messages.append({"role": "assistant", "en": ai_data["en"], "jp": ai_data["jp"]})
            # 次のターンのために提案をクリア
            st.session_state.options = []
            st.rerun()
