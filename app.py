import streamlit as st
import os, base64, uuid, json, requests

# --- 1. DATA PERSISTENCE ---
DB_FILE = "soot_vault.json"

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {"user": {"name": "Guest", "pfp": "", "api_key": ""}, "library": {}, "chats": {}}

if "db" not in st.session_state:
    st.session_state.db = load_db()

# --- 2. UI SETUP ---
st.set_page_config(page_title="The Silent Engine", layout="wide")

def get_base64(file):
    if file:
        return base64.b64encode(file.getvalue()).decode()
    return ""

st.markdown("""
    <style>
    .stApp { background-color: #F0F2F6 !important; color: black !important; }
    [data-testid="stSidebar"] { background-color: #E2E6EC !important; min-width: 380px !important; }
    .chat-wrapper { height: 65vh; overflow-y: auto; padding: 10px; margin-bottom: 120px; display: flex; flex-direction: column; }
    .chat-row { display: flex; align-items: flex-start; margin-bottom: 15px; width: 100%; gap: 10px; }
    .bot-row { justify-content: flex-start; flex-direction: row; }
    .user-row { justify-content: flex-end; }
    .chat-avatar { border-radius: 50%; width: 45px; height: 45px; flex-shrink: 0; object-fit: cover; }
    .thin-hr { border: 0; border-top: 1px solid #DDD; margin: 15px 0; }
    div.stButton > button {
        border-radius: 15px !important; padding: 10px 18px !important; 
        border: 1px solid #CCC !important; text-align: left !important;
        white-space: normal !important; height: auto !important; line-height: 1.4 !important;
    }
    .bot-row div.stButton > button { background-color: white !important; color: black !important; border-bottom-left-radius: 2px !important; max-width: 75%; }
    .user-row div.stButton > button { background-color: #D1D5DB !important; color: black !important; border-bottom-right-radius: 2px !important; max-width: 75%; }
    .bottom-dock { position: fixed; bottom: 0; left: 380px; right: 0; height: 100px; background: white; border-top: 1px solid #EEE; z-index: 99; }
    .stChatInput { position: fixed !important; bottom: 20px !important; width: 50% !important; left: 42% !important; z-index: 1000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SAFETY ---
BANNED_WORDS = ["suicide", "self harm", "overdose", "kill myself", "end my life", "cutting"]
def is_safe(text):
    low = text.lower()
    return not any(word in low for word in BANNED_WORDS)

# --- 4. GROQ ENGINE ---
def generate_response(history, char_name):
    char = st.session_state.db["library"][char_name]
    user_key = st.session_state.db["user"].get("api_key", "").strip()
    
    if not user_key:
        return "System: No API Key found. Please add your Groq Key in the User Profile section."

    my_persona = char.get('my_rp_persona', 'A mysterious traveler')
    safety = f"CORE CONDUCT: RP Bot. Romance tension/heat allowed. NO explicit sexual acts/self-harm. Talking to: {my_persona}."
    
    api_messages = [{"role": "system", "content": f"RP as {char_name}. {char['desc']}. {safety}. Length: {char.get('min_words', 100)}-{char.get('max_words', 500)} words."}]
    # ENHANCED MEMORY: Now keeps 30 messages instead of 15
    for m in history[-30:]:
        api_messages.append({"role": m["role"], "content": m["content"]})
    
    try:
        r = requests.post(
            url="https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {user_key}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": api_messages, "temperature": 0.8},
            timeout=20
        )
        return r.json()['choices'][0]['message']['content'].strip()
    except:
        return "System: API Error. Check your key or wait a few minutes."

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("Vault")

    with st.expander("👤 User Profile & Login", expanded=True):
        st.write("### Profile Info")
        u_name = st.text_input("Display Name", st.session_state.db["user"].get("name", "Guest"))
        u_key = st.text_input("Groq API Key", value=st.session_state.db["user"].get("api_key", ""), type="password")
        u_pfp = st.file_uploader("Upload Profile Pic", key="upfp")
        if st.button("Update & Save Profile"):
            st.session_state.db["user"]["name"] = u_name
            st.session_state.db["user"]["api_key"] = u_key
            if u_pfp: st.session_state.db["user"]["pfp"] = f"data:image/png;base64,{get_base64(u_pfp)}"
            save_db(st.session_state.db); st.rerun()

    with st.expander("✨ Create New Character", expanded=False):
        bn = st.text_input("Bot Name")
        bd = st.text_area("Bot Persona")
        bg = st.text_area("Initial Greeting")
        bi = st.file_uploader("Bot Avatar", key="b_up")
        if st.button("Initialize Character"):
            if bn and bd:
                img = f"data:image/png;base64,{get_base64(bi)}" if bi else ""
                st.session_state.db["library"][bn] = {"desc": bd, "greet": bg, "img": img, "min_words": 100, "max_words": 500, "my_rp_persona": ""}
                st.session_state.db["chats"][bn] = [{"id": str(uuid.uuid4()), "role": "assistant", "content": bg}]
                save_db(st.session_state.db); st.rerun()

    st.markdown('<div class="thin-hr"></div>', unsafe_allow_html=True)

    if st.session_state.db["library"]:
        sel_char = st.selectbox("Select Character", list(st.session_state.db["library"].keys()))
        if st.button("Open Selection"): st.session_state.active_char = sel_char; st.rerun()

        if "active_char" in st.session_state:
            act = st.session_state.active_char
            with st.expander(f"💬 Chatting with: {act}", expanded=True):
                st.session_state.db["library"][act]["my_rp_persona"] = st.text_area("My RP Identity", value=st.session_state.db["library"][act].get("my_rp_persona", ""))
                c1, c2 = st.columns(2)
                st.session_state.db["library"][act]["min_words"] = c1.number_input("Min", 1, 1000, st.session_state.db["library"][act].get("min_words", 100))
                st.session_state.db["library"][act]["max_words"] = c2.number_input("Max", 1, 2000, st.session_state.db["library"][act].get("max_words", 500))
                
                if st.button("Save Settings"): save_db(st.session_state.db); st.toast("Saved!")
                
                st.markdown("---")
                # NEW RESET CHAT BUTTON
                if st.button("🔄 Reset Whole Chat"):
                    greet = st.session_state.db["library"][act].get("greet", "Hello!")
                    st.session_state.db["chats"][act] = [{"id": str(uuid.uuid4()), "role": "assistant", "content": greet}]
                    save_db(st.session_state.db); st.toast("Chat Wiped!"); st.rerun()
                
                if st.button("🗑️ Delete Bot"):
                    del st.session_state.db["library"][act]; del st.session_state.db["chats"][act]
                    del st.session_state.active_char; save_db(st.session_state.db); st.rerun()

# --- 6. MAIN AREA ---
has_key = st.session_state.db["user"].get("api_key")
has_char = "active_char" in st.session_state

if has_key and has_char:
    char_data = st.session_state.db["library"][st.session_state.active_char]
    messages = st.session_state.db["chats"][st.session_state.active_char]
    
    st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)
    for i, msg in enumerate(messages):
        is_bot = msg["role"] == "assistant"
        st.markdown(f'<div class="chat-row {"bot-row" if is_bot else "user-row"}">', unsafe_allow_html=True)
        if is_bot: st.markdown(f'<img src="{char_data["img"]}" class="chat-avatar">', unsafe_allow_html=True)
        
        # MESSAGE CLICK TO SHOW TOOLS
        if st.button(msg["content"], key=f"b_{msg['id']}"): 
            st.session_state.sel_id = msg['id']
        st.markdown('</div>', unsafe_allow_html=True)

        # RESTORED TOOLS: Delete, Edit, Reroll
        if st.session_state.get("sel_id") == msg["id"]:
            m1, m2, m3 = st.columns([0.1, 0.1, 0.8])
            if m1.button("🗑️", key=f"d_{msg['id']}"): 
                messages.pop(i); save_db(st.session_state.db); st.rerun()
            if m2.button("✏️", key=f"e_{msg['id']}"): 
                st.session_state.edit_id = msg['id']
            if is_bot and m3.button("🔄 Reroll", key=f"r_{msg['id']}"):
                messages[i]["content"] = generate_response(messages[:i], st.session_state.active_char)
                save_db(st.session_state.db); st.rerun()
            
            if st.session_state.get("edit_id") == msg["id"]:
                edited = st.text_area("Edit message:", value=msg["content"], key=f"edit_{msg['id']}")
                if st.button("Apply", key=f"sv_{msg['id']}"):
                    messages[i]["content"] = edited; st.session_state.edit_id = None
                    save_db(st.session_state.db); st.rerun()

    st.markdown('</div><div class="bottom-dock"></div>', unsafe_allow_html=True)

    if prompt := st.chat_input(f"Speak to {st.session_state.active_char}..."):
        if is_safe(prompt):
            messages.append({"id": str(uuid.uuid4()), "role": "user", "content": prompt})
            save_db(st.session_state.db); st.session_state.waiting = True; st.rerun()

    if st.session_state.get("waiting"):
        st.session_state.waiting = False
        reply = generate_response(messages, st.session_state.active_char)
        messages.append({"id": str(uuid.uuid4()), "role": "assistant", "content": reply})
        save_db(st.session_state.db); st.rerun()

else:
    # --- ANONYMOUS TUTORIAL ---
    st.title(f"Welcome to the Vault, {st.session_state.db['user']['name']}")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔑 Step 1: Connect your Brain")
        st.write("1. Visit **console.groq.com**.")
        st.write("2. Create an API Key '(can be named anything) .")
        st.write("3. Paste it in the sidebar and click **Save**.")
    with col2:
        st.subheader("✨ Step 2: Bring them to Life")
        st.write("1. Create a character in the sidebar.")
        st.write("2. Select them and click **Open Selection**.")