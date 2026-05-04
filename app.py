import streamlit as st
import google.generativeai as genai
import json

# --- 1. ページ設定（スマホ最適化） ---
st.set_page_config(
    page_title="Gemini English Coach",
    page_icon="🎧",
    layout="centered"
)

# --- 2. デザインのカスタマイズ (CSS) ---
st.markdown("""
    <style>
    /* 選択肢ボタンのスタイル */
    .stButton > button {
        width: 100%;
        border-radius: 12px;
        padding: 12px;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: left;
        margin-bottom: 10px;
    }
    .option-en {
        font-size: 1.05rem;
        font-weight: 600;
        display: block;
        color: #1A73E8;
    }
    .option-jp {
        font-size: 0.8rem;
        color: #5f6368;
        display: block;
        margin-top: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Gemini APIの設定 ---
# Streamlit CloudのSecretsからAPIキーを読み込む設定
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("APIキーが設定されていません。StreamlitのSecretsに 'GEMINI_API_KEY' を追加してください。")

model = genai.GenerativeModel('gemini-1.5-flash')

# --- 4. セッション状態の初期化 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "options" not in st.session_state:
    st.session_state.options = []

# --- 5. AIの初期挨拶 ---
if not st.session_state.messages:
    initial_prompt = "You are a friendly English teacher. Start a conversation with a short greeting and a simple question about a daily topic (e.g., weather, food, hobbies)."
    response = model.generate_content(initial_prompt)
    st.session_state.messages.append({"role": "assistant", "content": response.text})

# 会話履歴の表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- 6. ユーザー入力エリア ---
user_input = st.chat_input("英語で返信してみましょう（音声入力も可）")

if user_input:
    # ユーザーの発言を記録
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Geminiに「推測される正しい英文3パターン」をJSON形式で要求
    analysis_prompt = f"""
    Based on the user's input: "{user_input}"
    1. Act as an English coach.
    2. Suggest 3 natural English sentences the user likely wanted to say.
    3. Provide a brief Japanese translation for each.
    Return ONLY a JSON list in this format: 
    [{"en": "Sentence 1", "jp": "和訳1"}, {"en": "Sentence 2", "jp": "和訳2"}, {"en": "Sentence 3", "jp": "和訳3"}]
    """
    
    with st.spinner("分析中..."):
        try:
            res = model.generate_content(analysis_prompt)
            # JSON部分を抽出してパース
            json_str = res.text.replace("```json", "").replace("```", "").strip()
            st.session_state.options = json.loads(json_str)
        except:
            st.session_state.options = []
    st.rerun()

# --- 7. 選択肢の表示（GUIの肝） ---
if st.session_state.options:
    st.write("---")
    st.caption("💡 もしかしてこう言いたかったですか？（タップして確定）")
    
    for i, opt in enumerate(st.session_state.options):
        # 英文（大）＋和文（小）のラベルを作成
        button_label = f'{opt["en"]}\n({opt["jp"]})'
        
        # 実際にはHTMLタグをボタン内に直接入れるのが難しいため、
        # StreamlitのボタンとMarkdownを組み合わせて見た目を調整
        if st.button(f"{opt['en']}\n{opt['jp']}", key=f"opt_{i}"):
            # 選択した英文を「修正済み回答」として履歴に追加
            st.session_state.messages.append({"role": "user", "content": f"✅ {opt['en']}"})
            
            # 次のAIのターンを生成
            next_prompt = f"The user just said: '{opt['en']}'. Continue the conversation naturally in English."
            next_res = model.generate_content(next_prompt)
            st.session_state.messages.append({"role": "assistant", "content": next_res.text})
            
            # 選択肢をクリアしてリロード
            st.session_state.options = []
            st.rerun()
