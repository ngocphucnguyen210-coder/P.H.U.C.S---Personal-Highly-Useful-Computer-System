import os
import time
import uuid
import sqlite3
from datetime import datetime, date, timedelta
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "phucs.db"

st.set_page_config(
    page_title="P.H.U.C.S AI — Đồng hành cùng bạn",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Visual identity ----------
PINK = "#D94F83"
PALE = "#FFF4F8"
DARK_PINK = "#A82F62"

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=Nunito:wght@400;600;700;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Be Vietnam Pro', sans-serif; }
    .stApp { background: linear-gradient(135deg,#fff8fb 0%,#fff1f7 48%,#fff9fc 100%); }
    [data-testid="stSidebar"] { background: linear-gradient(180deg,#ffe7f0 0%,#fff4f8 100%); border-right:1px solid #f5c8da; }
    h1,h2,h3 { color:#8f2854; font-family:'Nunito','Be Vietnam Pro',sans-serif; }
    .hero { padding:1.3rem 1.5rem; border:1px solid #f4c5d8; border-radius:24px;
            background:linear-gradient(120deg,rgba(255,255,255,.95),rgba(255,228,239,.92));
            box-shadow:0 12px 34px rgba(177,56,106,.09); }
    .brand { font-family:'Nunito',sans-serif; font-weight:900; letter-spacing:.04em;
             font-size:clamp(2rem,5vw,3.8rem); color:#d94f83; line-height:1.05; }
    .slogan { color:#8f2854; font-weight:600; font-size:1.03rem; }
    .small-muted { color:#8e6a7a; font-size:.9rem; }
    div.stButton > button { border-radius:14px; border:1px solid #efb5cc; font-weight:700; }
    div.stButton > button[kind="primary"] { background:#d94f83; color:white; border:0; }
    [data-testid="stMetric"] { background:#fff; padding:1rem; border:1px solid #f4d0df; border-radius:18px; }
    .stTabs [data-baseweb="tab-list"] { gap:8px; }
    .stTabs [data-baseweb="tab"] { background:#ffe8f1; border-radius:12px 12px 0 0; padding:10px 16px; }
    .stTabs [aria-selected="true"] { background:#d94f83 !important; color:white !important; }
    </style>
    """, unsafe_allow_html=True)

inject_css()

# ---------- Database ----------
def db():
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          user_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, provider TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chats (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
          title TEXT NOT NULL, messages TEXT NOT NULL DEFAULT '[]',
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS todos (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
          task TEXT NOT NULL, due_date TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
          title TEXT NOT NULL, category TEXT NOT NULL, event_date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notes (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
          title TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS study_sessions (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
          subject TEXT NOT NULL, seconds INTEGER NOT NULL, saved_at TEXT NOT NULL
        );
        """)
init_db()

def current_user():
    return st.session_state.get("user")

def create_user(name, provider="guest"):
    uid = str(uuid.uuid4())[:8].upper()
    user = {"user_id": uid, "display_name": name.strip() or "Học viên", "provider": provider}
    with db() as con:
        con.execute("INSERT INTO users VALUES (?,?,?,?)",
                    (uid, user["display_name"], provider, datetime.now().isoformat(timespec="seconds")))
    st.session_state.user = user
    st.session_state.active_chat = None
    st.session_state.messages = []
    st.rerun()

# ---------- Login ----------
def login_screen():
    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.1, 1], gap="large", vertical_alignment="center")
    with left:
        st.markdown("""
        <div class="hero" style="text-align:center;padding:2.1rem 1.2rem">
          <div style="font-size:5rem">🎓🌸</div>
          <div class="brand">P.H.U.C.S</div>
          <div style="font-size:1.1rem;font-weight:800;color:#a82f62;margin:.35rem 0">
            Personal Highly Useful Computer System
          </div>
          <p class="slogan">Đồng hành cùng P.H.U.C.S, vững bước thành công</p>
          <p class="small-muted">Không gian học tập thông minh — sáng tạo — truyền cảm hứng.</p>
        </div>
        """, unsafe_allow_html=True)
        logo = st.file_uploader("Tải logo riêng (PNG/JPG, tùy chọn)", type=["png", "jpg", "jpeg"], key="login_logo")
        if logo:
            st.image(logo, width=220)
    with right:
        st.markdown("### Chào mừng bạn đến với P.H.U.C.S")
        st.write("Đăng nhập để bắt đầu hành trình chinh phục tri thức.")
        name = st.text_input("Tên hiển thị", placeholder="Ví dụ: Minh Anh")
        if st.button("✨ Tiếp tục với tài khoản khách", type="primary", use_container_width=True):
            create_user(name or "Học viên", "guest")
        st.divider()
        st.markdown("**Đăng nhập bằng tài khoản bên ngoài**")
        st.caption("Cần cấu hình OAuth và callback URL trong môi trường triển khai để xác minh tài khoản thật.")
        # Real social OAuth is delegated to Supabase Auth. Provider credentials and redirect URLs
        # must first be configured in the Supabase dashboard.
        try:
            from phucs_integrations import setting, supabase_client
            supabase_ready = bool(setting("SUPABASE_URL") and setting("SUPABASE_ANON_KEY"))
        except Exception:
            supabase_ready = False
        cols = st.columns(3)
        for col, label, provider in zip(cols, ["Google", "Facebook", "Apple / iCloud"], ["google", "facebook", "apple"]):
            with col:
                if supabase_ready:
                    if st.button(label, use_container_width=True, key=f"oauth_{provider}"):
                        try:
                            from urllib.parse import urlparse
                            client = supabase_client()
                            st.session_state["supabase_oauth_client"] = client
                            redirect_to = setting("APP_BASE_URL", "http://localhost:8501")
                            result = client.auth.sign_in_with_oauth({"provider": provider, "options": {"redirect_to": redirect_to}})
                            oauth_url = getattr(result, "url", None) or (result.get("url") if isinstance(result, dict) else None)
                            if oauth_url:
                                st.session_state["oauth_link"] = oauth_url
                            else:
                                st.error("Không nhận được URL OAuth từ Supabase.")
                        except Exception as exc:
                            st.error(f"Không tạo được liên kết đăng nhập: {exc}")
                else:
                    st.button(label, disabled=True, use_container_width=True,
                              help="Cấu hình SUPABASE_URL và SUPABASE_ANON_KEY trước.")
        if st.session_state.get("oauth_link"):
            st.link_button("Tiếp tục đăng nhập an toàn ↗", st.session_state["oauth_link"], use_container_width=True)
        st.info("Đăng nhập xã hội dùng Supabase Auth. Bạn phải bật Google/Facebook/Apple và cấu hình callback trong Supabase trước khi dùng thật.")

# Handle Supabase OAuth PKCE callback after the provider redirects back to APP_BASE_URL.
try:
    from phucs_integrations import setting, supabase_client
    oauth_code = st.query_params.get("code")
    if oauth_code and not current_user() and setting("SUPABASE_URL") and setting("SUPABASE_ANON_KEY"):
        try:
            auth_client = st.session_state.get("supabase_oauth_client") or supabase_client()
            auth_result = auth_client.auth.exchange_code_for_session(oauth_code)
            auth_user = getattr(auth_result, "user", None)
            if auth_user is None and isinstance(auth_result, dict):
                auth_user = auth_result.get("user")
            if auth_user:
                if isinstance(auth_user, dict):
                    au = auth_user
                else:
                    au = {"id": getattr(auth_user, "id", ""), "email": getattr(auth_user, "email", ""),
                          "user_metadata": getattr(auth_user, "user_metadata", {}) or {},
                          "app_metadata": getattr(auth_user, "app_metadata", {}) or {}}
                metadata = au.get("user_metadata") or {}
                provider = (au.get("app_metadata") or {}).get("provider", "supabase")
                name = metadata.get("full_name") or metadata.get("name") or au.get("email") or "Học viên"
                user_id = str(au.get("id") or uuid.uuid4())
                st.session_state.user = {"user_id": user_id, "display_name": name, "provider": provider}
                st.session_state.active_chat = None
                st.session_state.messages = []
                st.query_params.clear()
                st.rerun()
        except Exception as oauth_exc:
            st.error(f"Đăng nhập OAuth chưa hoàn tất: {oauth_exc}. Kiểm tra callback URL trong Supabase.")
except Exception:
    pass

if not current_user():
    login_screen()
    st.stop()

user = current_user()
uid = user["user_id"]

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown(f"<div style='text-align:center;font-size:3rem'>🎓🌸</div><div style='text-align:center' class='brand'>P.H.U.C.S</div>", unsafe_allow_html=True)
    st.caption("Đồng hành cùng P.H.U.C.S, vững bước thành công")
    st.divider()
    st.markdown(f"### 👤 {user['display_name']}")
    st.caption(f"ID cá nhân: `{uid}`")
    st.caption(f"Tài khoản: {user['provider'].title()}")
    if st.button("↪ Đăng xuất", use_container_width=True):
        for key in ["user", "messages", "active_chat"]:
            st.session_state.pop(key, None)
        st.rerun()

    st.divider()
    language = st.selectbox("🌐 Ngôn ngữ", [
        "Tiếng Việt", "English", "한국어", "Français", "Deutsch", "日本語",
        "Español", "Русский", "中文", "ไทย", "Português", "Italiano"
    ])
    theme = st.selectbox("🎨 Giao diện", ["Hồng mộng mơ", "Dải ngân hà hồng", "Sóng biển hồng", "Dark mode hồng đêm"])
    st.session_state.theme = theme
    if theme == "Dark mode hồng đêm":
        st.markdown("""<style>.stApp{background:linear-gradient(135deg,#211725,#342033)!important;color:#fff}
        h1,h2,h3,p,label{color:#ffe5f0!important} [data-testid="stSidebar"]{background:#281b2b!important}</style>""",
                    unsafe_allow_html=True)
    bg = st.file_uploader("Tải hình nền riêng", type=["png", "jpg", "jpeg", "webp"], key="bg_upload")
    if bg:
        st.image(bg, caption="Xem trước hình nền")
        st.caption("Ảnh tải lên hiện là bản xem trước; chưa được lưu làm nền vĩnh viễn.")
    st.divider()
    with st.expander("⚙️ Cài đặt"):
        st.markdown("**P.H.U.C.S AI Plus**")
        st.write("35.000 VNĐ/năm — mức giá đề xuất, chưa tích hợp thanh toán.")
        st.write("• Hạn mức sử dụng rộng hơn")
        st.write("• Dung lượng mục tiêu 500 GB²")
        st.button("Xem gói Plus", use_container_width=True, disabled=True)
        st.divider()
        st.markdown("**🔔 Thông báo**")
        notif = st.toggle("Bật thông báo", value=True)
        if not notif:
            st.caption("Thông báo đang tắt trong phiên hiện tại.")
        else:
            st.selectbox("Tắt thông báo trong", ["Không", "1 giờ", "2 giờ", "3 giờ", "4 giờ", "6 giờ", "12 giờ"])
        st.divider()
        st.markdown("**🗣️ Giọng đọc**")
        st.selectbox("Giọng P.H.U.C.S", [
            "Nữ trung — miền Bắc", "Nữ cao — miền Bắc", "Nữ trầm — miền Nam",
            "Nam trung — miền Bắc", "Nam trầm — miền Nam", "Nam cao — miền Trung"
        ])
        st.caption("Tùy chọn giọng đọc cần tích hợp dịch vụ Text-to-Speech.")
        st.divider()
        st.markdown("**ⓘ Giới thiệu**")
        st.write("P.H.U.C.S Alpha 1")
        st.caption("Bản khởi đầu. Các bản sau sẽ bổ sung đăng nhập, đồng bộ và công cụ nâng cao.")

    st.divider()
    st.markdown("**🔎 Tìm lịch sử chat**")
    search_text = st.text_input("Từ khóa", label_visibility="collapsed", placeholder="Tìm cuộc trò chuyện...")
    if st.button("Tìm", use_container_width=True):
        st.session_state.history_search = search_text

    if st.button("＋ Cuộc trò chuyện mới", type="primary", use_container_width=True):
        st.session_state.active_chat = None
        st.session_state.messages = []
        st.rerun()

    with db() as con:
        chats = con.execute("SELECT id,title,updated_at FROM chats WHERE user_id=? ORDER BY updated_at DESC", (uid,)).fetchall()
    st.markdown("**Lịch sử trò chuyện**")
    for chat in chats:
        if st.session_state.get("history_search") and st.session_state.history_search.lower() not in chat["title"].lower():
            continue
        c1, c2 = st.columns([4, 1])
        with c1:
            if st.button("💬 " + chat["title"][:27], key=f"open_chat_{chat['id']}", use_container_width=True):
                import json
                st.session_state.active_chat = chat["id"]
                with db() as con:
                    row = con.execute("SELECT messages FROM chats WHERE id=? AND user_id=?", (chat["id"], uid)).fetchone()
                st.session_state.messages = json.loads(row["messages"]) if row else []
                st.rerun()
        with c2:
            if st.button("🗑️", key=f"delete_chat_{chat['id']}"):
                with db() as con:
                    con.execute("DELETE FROM chats WHERE id=? AND user_id=?", (chat["id"], uid))
                if st.session_state.get("active_chat") == chat["id"]:
                    st.session_state.active_chat = None
                    st.session_state.messages = []
                st.rerun()

# ---------- Header ----------
st.markdown("""
<div class="hero">
  <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
    <div style="font-size:3rem">🎓</div>
    <div><div class="brand" style="font-size:2.3rem">P.H.U.C.S AI</div>
    <div class="slogan">Đồng hành cùng P.H.U.C.S, vững bước thành công</div>
    <div class="small-muted">Personal Highly Useful Computer System · Alpha 1</div></div>
  </div>
</div>
""", unsafe_allow_html=True)
st.write("")

pages = st.tabs(["💬 Cơ bản", "⏱️ Đồng hồ học", "📅 Lịch & Sự kiện", "✅ To-do List",
                 "📝 Note & Studio", "📊 Biểu đồ", "🎮 Giải trí", "🧪 Phòng thí nghiệm",
                 "🌐 Web & Media AI", "👥 Nhóm & Gọi", "☁️ Plus & Cloud"])

# ---------- Chat ----------
with pages[0]:
    st.subheader("Trợ lý học tập của bạn")
    st.caption("Hỏi về Toán, Văn, Anh, Lý, Hóa, Sinh, Sử, Địa, ngoại ngữ, kỹ năng và kiến thức đời sống.")
    # Streamlit Cloud Secrets first, then environment/.env for local development.
    def setting(name, default=""):
        try:
            value = st.secrets.get(name, None)
            if value is not None and str(value).strip():
                return str(value).strip()
        except Exception:
            pass
        return os.getenv(name, default).strip()

    api_key = setting("GROQ_API_KEY") or setting("OPENAI_API_KEY")
    provider = "Groq" if setting("GROQ_API_KEY") else ("OpenAI" if setting("OPENAI_API_KEY") else "")
    model = setting("GROQ_MODEL", "llama-3.3-70b-versatile") if provider == "Groq" else setting("OPENAI_MODEL", "gpt-4.1-mini")
    if not api_key:
        st.warning("Chưa cấu hình API. Tạo GROQ_API_KEY tại console.groq.com/keys rồi thêm vào Streamlit Secrets để bật AI.")
    else:
        st.caption(f"Đang dùng AI qua {provider} · model: {model}")
    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"], avatar="🎓" if message["role"] == "assistant" else "🙂"):
            st.markdown(message["content"])
    uploaded = st.file_uploader("Đính kèm ảnh bài tập (tùy chọn)", type=["png", "jpg", "jpeg"], key="chat_image")
    if uploaded:
        st.image(uploaded, caption="Ảnh đính kèm", width=300)
        st.caption("Bản starter hiển thị ảnh; xử lý ảnh bằng AI cần bật tích hợp vision.")
    prompt = st.chat_input("Nhập câu hỏi hoặc bài tập bạn muốn giải...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="🙂"):
            st.markdown(prompt)
        answer = None
        if api_key:
            try:
                from openai import OpenAI
                if provider == "Groq":
                    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
                else:
                    client = OpenAI(api_key=api_key)
                system_prompt = (
                    "Bạn là P.H.U.C.S, trợ lý học tập thân thiện, lịch sự và chính xác. "
                    "Trả lời bằng ngôn ngữ người dùng đang dùng. Giải thích từng bước, nêu giả định, "
                    "phân biệt dữ kiện đã xác minh với điều chưa chắc chắn. Với y tế/pháp luật/tài chính, "
                    "cung cấp thông tin giáo dục thận trọng và khuyến nghị chuyên gia khi phù hợp. "
                    "Không bịa nguồn hoặc trích dẫn."
                )
                msgs = [{"role": "system", "content": system_prompt}]
                msgs += [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[-20:]]
                with st.chat_message("assistant", avatar="🎓"):
                    with st.spinner("P.H.U.C.S đang suy nghĩ..."):
                        response = client.chat.completions.create(model=model, messages=msgs, temperature=0.25)
                        answer = response.choices[0].message.content
                        st.markdown(answer)
            except Exception as e:
                answer = f"Chưa thể kết nối AI: {e}. Hãy kiểm tra API key, hạn mức và tên model."
                with st.chat_message("assistant", avatar="🎓"):
                    st.error(answer)
        else:
            answer = ("Mình đã nhận được câu hỏi! Để bật AI, hãy tạo khóa Groq tại "
                      "https://console.groq.com/keys rồi thêm `GROQ_API_KEY` vào Streamlit Secrets. "
                      "Sau khi cấu hình, mình sẽ giải thích từng bước và ưu tiên độ chính xác.")
            with st.chat_message("assistant", avatar="🎓"):
                st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        if not st.session_state.get("active_chat"):
            title = prompt[:48] + ("…" if len(prompt) > 48 else "")
            import json
            with db() as con:
                cur = con.execute("INSERT INTO chats(user_id,title,messages,updated_at) VALUES(?,?,?,?)",
                                  (uid, title, json.dumps(st.session_state.messages, ensure_ascii=False),
                                   datetime.now().isoformat(timespec="seconds")))
                st.session_state.active_chat = cur.lastrowid
        else:
            import json
            with db() as con:
                con.execute("UPDATE chats SET messages=?,updated_at=? WHERE id=? AND user_id=?",
                            (json.dumps(st.session_state.messages, ensure_ascii=False),
                             datetime.now().isoformat(timespec="seconds"), st.session_state.active_chat, uid))
        st.rerun()
    with st.expander("＋ Công cụ bổ sung"):
        st.write("📷 Ảnh bài tập: có giao diện đính kèm; cần tích hợp vision để AI đọc ảnh.")
        st.write("🎙️ Voice chat: cần dịch vụ speech-to-text và text-to-speech.")
        st.write("🎨 Tạo ảnh / 🎬 tạo video / 🎵 tạo nhạc: cần kết nối API tương ứng.")
        st.write("🌐 Tìm kiếm Internet: cần tích hợp công cụ search có trích dẫn và kiểm tra nguồn.")

# ---------- Timer ----------
with pages[1]:
    st.subheader("⏱️ Đồng hồ tập trung")
    subjects = ["Ngữ Văn", "Toán học", "Vật lí", "Hóa học", "Sinh học", "Tiếng Anh", "Lịch sử", "Địa lí", "Tự đặt tên"]
    subject = st.selectbox("Môn học", subjects)
    custom_subject = st.text_input("Tên môn học tùy chỉnh") if subject == "Tự đặt tên" else ""
    subject_name = custom_subject.strip() or subject
    if "timer_started_at" not in st.session_state:
        st.session_state.timer_started_at = None
        st.session_state.timer_elapsed = 0
        st.session_state.timer_running = False
    if st.session_state.timer_running and st.session_state.timer_started_at:
        elapsed = st.session_state.timer_elapsed + int(time.time() - st.session_state.timer_started_at)
    else:
        elapsed = st.session_state.timer_elapsed
    hh, rem = divmod(elapsed, 3600); mm, ss = divmod(rem, 60)
    st.markdown(f"<div class='hero' style='text-align:center'><div style='font-size:3.5rem;font-weight:900;color:#d94f83;font-variant-numeric:tabular-nums'>{hh:02}:{mm:02}:{ss:02}</div><div class='small-muted'>Thời gian học tập trung</div></div>", unsafe_allow_html=True)
    b1,b2,b3,b4 = st.columns(4)
    with b1:
        if st.button("▶ Bắt đầu", type="primary", use_container_width=True) and not st.session_state.timer_running:
            st.session_state.timer_started_at = time.time()
            st.session_state.timer_running = True
            st.rerun()
    with b2:
        if st.button("Ⅱ Tạm dừng", use_container_width=True) and st.session_state.timer_running:
            st.session_state.timer_elapsed = elapsed
            st.session_state.timer_started_at = None
            st.session_state.timer_running = False
            st.rerun()
    with b3:
        if st.button("↺ Đặt lại", use_container_width=True):
            st.session_state.timer_elapsed = 0
            st.session_state.timer_started_at = time.time() if st.session_state.timer_running else None
            st.rerun()
    with b4:
        if st.button("💾 Lưu phiên", use_container_width=True):
            with db() as con:
                con.execute("INSERT INTO study_sessions(user_id,subject,seconds,saved_at) VALUES(?,?,?,?)",
                            (uid, subject_name, elapsed, datetime.now().isoformat(timespec="seconds")))
            st.success("Đã lưu phiên học.")
    if st.session_state.timer_running:
        st.caption("Đồng hồ đang chạy. Streamlit có thể cần tương tác/làm mới để cập nhật số hiển thị.")
        if st.button("↻ Cập nhật đồng hồ"):
            st.rerun()
    with db() as con:
        sessions = con.execute("SELECT subject,seconds,saved_at FROM study_sessions WHERE user_id=? ORDER BY id DESC LIMIT 20", (uid,)).fetchall()
    st.markdown("#### Lịch sử học gần đây")
    if sessions:
        for s in sessions:
            st.write(f"• {s['saved_at'][:10]} · **{s['subject']}** · {s['seconds']//3600:02}:{(s['seconds']%3600)//60:02}:{s['seconds']%60:02}")
    else:
        st.info("Chưa có phiên học được lưu.")

# ---------- Calendar ----------
with pages[2]:
    st.subheader("📅 Lịch & Sự kiện")
    chosen_date = st.date_input("Chọn ngày", value=date.today(), format="DD/MM/YYYY")
    with st.form("event_form", clear_on_submit=True):
        ev_title = st.text_input("Tên sự kiện")
        ev_cat = st.selectbox("Phân loại", ["Sinh nhật", "Kỷ niệm", "Thi cử", "Quan trọng", "Khác"])
        ev_date = st.date_input("Ngày diễn ra", value=chosen_date, format="DD/MM/YYYY")
        ev_submit = st.form_submit_button("＋ Thêm sự kiện", type="primary")
    if ev_submit:
        if ev_title.strip():
            with db() as con:
                con.execute("INSERT INTO events(user_id,title,category,event_date) VALUES(?,?,?,?)",
                            (uid, ev_title.strip(), ev_cat, ev_date.isoformat()))
            st.success("Đã thêm sự kiện.")
            st.rerun()
        else:
            st.error("Hãy nhập tên sự kiện.")
    with db() as con:
        events = con.execute("SELECT id,title,category FROM events WHERE user_id=? AND event_date=? ORDER BY id",
                             (uid, chosen_date.isoformat())).fetchall()
    st.markdown(f"#### Sự kiện ngày {chosen_date.strftime('%d/%m/%Y')}")
    if not events:
        st.info("Không có sự kiện trong ngày này.")
    for ev in events:
        c1,c2 = st.columns([5,1])
        c1.write(f"**{ev['title']}** · {ev['category']}")
        if c2.button("Xóa", key=f"del_ev_{ev['id']}"):
            with db() as con: con.execute("DELETE FROM events WHERE id=? AND user_id=?", (ev["id"],uid))
            st.rerun()

# ---------- Todo ----------
with pages[3]:
    st.subheader("✅ To-do List")
    todo_date = st.date_input("Ngày thực hiện", value=date.today(), format="DD/MM/YYYY", key="todo_date")
    with st.form("todo_form", clear_on_submit=True):
        task = st.text_input("Nhiệm vụ mới", placeholder="Ví dụ: Ôn 20 từ vựng IELTS")
        add_task = st.form_submit_button("＋ Thêm nhiệm vụ", type="primary")
    if add_task and task.strip():
        with db() as con:
            con.execute("INSERT INTO todos(user_id,task,due_date,done) VALUES(?,?,?,0)",
                        (uid,task.strip(),todo_date.isoformat()))
        st.rerun()
    with db() as con:
        todos = con.execute("SELECT id,task,done FROM todos WHERE user_id=? AND due_date=? ORDER BY done,id",
                            (uid,todo_date.isoformat())).fetchall()
    st.markdown("#### Chưa hoàn thành")
    for t in [x for x in todos if not x["done"]]:
        c1,c2 = st.columns([6,1])
        c1.write("✕ " + t["task"])
        if c2.button("✓", key=f"done_{t['id']}"):
            with db() as con: con.execute("UPDATE todos SET done=1 WHERE id=? AND user_id=?", (t["id"],uid))
            st.rerun()
    st.markdown("#### Đã hoàn thành")
    for t in [x for x in todos if x["done"]]:
        c1,c2 = st.columns([6,1])
        c1.markdown(f"~~{t['task']}~~")
        if c2.button("↩", key=f"undo_{t['id']}"):
            with db() as con: con.execute("UPDATE todos SET done=0 WHERE id=? AND user_id=?", (t["id"],uid))
            st.rerun()
    if not todos:
        st.info("Chưa có nhiệm vụ nào trong ngày này.")

# ---------- Notes and drawing ----------
with pages[4]:
    st.subheader("📝 Note & Studio")
    mode = st.radio("Chế độ", ["Trình soạn thảo văn bản", "Bảng vẽ Studio Pro"], horizontal=True)
    if mode == "Trình soạn thảo văn bản":
        with st.form("note_form", clear_on_submit=True):
            note_title = st.text_input("Tiêu đề ghi chú")
            note_body = st.text_area("Nội dung", height=240, placeholder="Bắt đầu ghi lại ý tưởng, công thức hoặc kiến thức...")
            note_submit = st.form_submit_button("💾 Lưu ghi chú", type="primary")
        if note_submit:
            if note_title.strip() and note_body.strip():
                with db() as con:
                    con.execute("INSERT INTO notes(user_id,title,body,created_at) VALUES(?,?,?,?)",
                                (uid,note_title.strip(),note_body,datetime.now().isoformat(timespec="seconds")))
                st.success("Đã lưu ghi chú.")
                st.rerun()
            else:
                st.error("Vui lòng nhập tiêu đề và nội dung.")
    else:
        st.caption("Bản vẽ canvas tối giản: vẽ bằng chuột/touch, chọn màu và tải ảnh xuống bằng trình duyệt.")
        st.components.v1.html("""
        <div style="font-family:sans-serif;background:#fff7fb;border:1px solid #efb5cc;border-radius:16px;padding:12px">
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px">
            <label>Màu <input id="color" type="color" value="#d94f83"></label>
            <label>Nét <input id="width" type="range" min="1" max="24" value="4"></label>
            <button id="clear">Xóa bảng</button><button id="download">Tải PNG</button>
          </div>
          <canvas id="pad" width="900" height="430" style="width:100%;height:auto;background:white;border:1px solid #e9c4d4;border-radius:10px;touch-action:none"></canvas>
        </div>
        <script>
        const c=document.getElementById('pad'),x=c.getContext('2d'); x.lineCap='round'; let down=false,last=null;
        c.addEventListener('pointerdown',e=>{down=true;last=pos(e);c.setPointerCapture(e.pointerId)});
        c.addEventListener('pointerup',()=>{down=false;last=null});
        c.addEventListener('pointermove',e=>{if(!down)return;let p=pos(e);x.strokeStyle=document.getElementById('color').value;x.lineWidth=document.getElementById('width').value;x.beginPath();x.moveTo(last.x,last.y);x.lineTo(p.x,p.y);x.stroke();last=p});
        function pos(e){let r=c.getBoundingClientRect();return{x:(e.clientX-r.left)*c.width/r.width,y:(e.clientY-r.top)*c.height/r.height}}
        document.getElementById('clear').onclick=()=>x.clearRect(0,0,c.width,c.height);
        document.getElementById('download').onclick=()=>{let a=document.createElement('a');a.download='phucs-drawing.png';a.href=c.toDataURL();a.click()};
        </script>""", height=540)
    st.markdown("#### Kho lưu trữ ghi chú")
    with db() as con:
        notes = con.execute("SELECT id,title,body,created_at FROM notes WHERE user_id=? ORDER BY id DESC", (uid,)).fetchall()
    if not notes:
        st.caption("Chưa có ghi chú được lưu.")
    for n in notes:
        with st.expander(f"🗒️ {n['title']} · {n['created_at'][:10]}"):
            st.write(n["body"])
            if st.button("Xóa ghi chú", key=f"delete_note_{n['id']}"):
                with db() as con: con.execute("DELETE FROM notes WHERE id=? AND user_id=?", (n["id"],uid))
                st.rerun()

# ---------- Charts ----------
with pages[5]:
    st.subheader("📊 Tạo biểu đồ")
    st.caption("Nhập dữ liệu theo từng dòng, mỗi dòng gồm nhãn và giá trị, phân cách bằng dấu phẩy.")
    chart_type = st.selectbox("Loại biểu đồ", ["Biểu đồ cột", "Biểu đồ đường", "Biểu đồ tròn", "Biểu đồ miền"])
    data_text = st.text_area("Dữ liệu", value="Toán,8\nVăn,7\nTiếng Anh,9", height=120)
    if st.button("Vẽ biểu đồ", type="primary"):
        import pandas as pd
        rows = []
        for line in data_text.splitlines():
            try:
                label, value = line.rsplit(",",1)
                rows.append({"Mục":label.strip(),"Giá trị":float(value.strip())})
            except ValueError:
                pass
        if rows:
            frame = pd.DataFrame(rows).set_index("Mục")
            if chart_type == "Biểu đồ cột": st.bar_chart(frame)
            elif chart_type == "Biểu đồ đường": st.line_chart(frame)
            elif chart_type == "Biểu đồ miền": st.area_chart(frame)
            else: st.vega_lite_chart(
                pd.DataFrame(rows),
                {"mark":{"type":"arc","innerRadius":35},
                 "encoding":{"theta":{"field":"Giá trị","type":"quantitative"},
                             "color":{"field":"Mục","type":"nominal"},
                             "tooltip":[{"field":"Mục"},{"field":"Giá trị"}]}}
            )
        else:
            st.error("Không đọc được dữ liệu. Hãy dùng định dạng Nhãn,Giá trị.")

# ---------- Games ----------
with pages[6]:
    st.subheader("🎮 Góc giải trí lành mạnh")
    st.write("Chọn một trò chơi ngắn để thư giãn giữa các phiên học.")
    games = {
        "Đố vui kiến thức": "Trả lời câu hỏi kiến thức tổng hợp.",
        "Đoán số": "Đoán một số từ 1 đến 20.",
        "Thử thách bảng cửu chương": "Luyện tính nhẩm.",
        "Từ vựng nhanh": "Ôn từ vựng ngoại ngữ.",
        "Ghi nhớ dãy số": "Rèn trí nhớ ngắn hạn.",
        "Câu đố logic": "Thử sức với suy luận."
    }
    game = st.selectbox("Trò chơi", list(games.keys()) + [
        "Sudoku mini", "Tìm từ khác biệt", "Đố cờ", "Quiz lịch sử", "Quiz địa lý",
        "Đố khoa học", "Nối từ", "Anagram", "Đoán thành ngữ", "Tính nhẩm 60 giây",
        "Flashcard", "Wordle mini", "Tìm cặp giống nhau", "Đố mẹo", "Quiz tiếng Anh",
        "Quiz IELTS", "Quiz HSK", "Đuổi hình bắt chữ", "Cờ caro", "Kéo búa bao",
        "Trắc nghiệm âm nhạc", "Đố thiên văn", "Thử thách chính tả", "Tìm đường mê cung",
        "Phản xạ màu sắc", "Ô chữ mini", "Đố toán", "Quiz sinh học"
    ])
    st.info(games.get(game, "Trò chơi được liệt kê trong lộ trình mở rộng; phiên bản hiện tại mới có một số trò chơi mẫu.") )
    if game == "Đoán số":
        import random
        if "secret_number" not in st.session_state: st.session_state.secret_number = random.randint(1,20)
        guess = st.number_input("Số bạn đoán", min_value=1, max_value=20, step=1)
        if st.button("Kiểm tra"):
            if guess == st.session_state.secret_number:
                st.success("Chính xác! Bạn giỏi lắm 🌸")
                st.session_state.secret_number = random.randint(1,20)
            elif guess < st.session_state.secret_number: st.warning("Thử số lớn hơn nhé.")
            else: st.warning("Thử số nhỏ hơn nhé.")
    elif game == "Thử thách bảng cửu chương":
        import random
        if "math_question" not in st.session_state:
            a,b=random.randint(2,12),random.randint(2,12); st.session_state.math_question=(a,b)
        a,b=st.session_state.math_question
        st.write(f"**{a} × {b} = ?**")
        ans=st.number_input("Đáp án", step=1, key="math_answer")
        if st.button("Chấm đáp án"):
            if ans==a*b: st.success("Đúng rồi!"); st.session_state.math_question=(random.randint(2,12),random.randint(2,12))
            else: st.error("Chưa đúng, thử lại nhé.")

# ---------- Lab ----------
with pages[7]:
    st.subheader("🧪 Phòng thí nghiệm ảo")
    lab = st.selectbox("Chọn mô phỏng", ["Quỹ đạo hành tinh (mô hình khái niệm)", "Đồ thị hàm số bậc hai", "Chuyển động thẳng đều", "Mô hình tam giác"])
    if lab == "Quỹ đạo hành tinh (mô hình khái niệm)":
        st.write("Mô hình minh họa quỹ đạo tròn đơn giản, không dùng để dự đoán thiên văn chính xác.")
        import numpy as np
        import pandas as pd
        angle = np.linspace(0, 2*np.pi, 180)
        st.line_chart(pd.DataFrame({"x":np.cos(angle),"y":np.sin(angle)}))
        st.caption("Đây là đồ thị tham số minh họa, chưa phải mô phỏng hấp dẫn N-body.")
    elif lab == "Đồ thị hàm số bậc hai":
        import numpy as np
        import pandas as pd
        a = st.slider("Hệ số a", -5.0, 5.0, 1.0, 0.5)
        b = st.slider("Hệ số b", -10.0, 10.0, 0.0, 0.5)
        c = st.slider("Hệ số c", -10.0, 10.0, 0.0, 0.5)
        x = np.linspace(-10,10,201)
        st.line_chart(pd.DataFrame({"y=ax²+bx+c":a*x*x+b*x+c}, index=x))
    elif lab == "Chuyển động thẳng đều":
        v = st.slider("Vận tốc (m/s)", 0.0, 30.0, 5.0)
        import pandas as pd
        t = list(range(0,11))
        st.line_chart(pd.DataFrame({"Quãng đường (m)":[v*i for i in t]}, index=t))
        st.caption("Công thức: s = v × t, giả sử vận tốc không đổi.")
    else:
        st.write("Nhập cạnh để tính diện tích tam giác vuông.")
        x = st.number_input("Cạnh góc vuông thứ nhất", min_value=0.0, value=3.0)
        y = st.number_input("Cạnh góc vuông thứ hai", min_value=0.0, value=4.0)
        st.metric("Diện tích", f"{x*y/2:.2f} đơn vị²")
        st.metric("Cạnh huyền", f"{(x*x+y*y)**0.5:.2f} đơn vị")

# ---------- Web search, vision, voice and generation ----------
with pages[8]:
    st.subheader("🌐 Tìm kiếm Internet có nguồn & Media AI")
    from phucs_integrations import setting, tavily_search, analyze_image, transcribe_audio, generate_image, replicate_create
    mode = st.radio("Công cụ", ["Tìm kiếm Internet", "Phân tích ảnh bằng AI", "Giọng nói", "Tạo ảnh AI", "Tạo video AI", "Tạo nhạc AI"], horizontal=True)
    if mode == "Tìm kiếm Internet":
        query = st.text_input("Bạn muốn tìm thông tin gì?", placeholder="Ví dụ: định luật Newton nguồn giáo dục đáng tin cậy")
        count = st.slider("Số nguồn", 3, 10, 5)
        if st.button("🔎 Tìm kiếm và trích dẫn", type="primary", key="tavily_search_btn"):
            if not query.strip():
                st.warning("Hãy nhập nội dung cần tìm.")
            else:
                try:
                    with st.spinner("Đang tìm trên Internet..."):
                        result = tavily_search(query.strip(), count)
                    if result.get("answer"):
                        st.markdown("#### Tóm tắt tìm kiếm")
                        st.write(result["answer"])
                    st.markdown("#### Nguồn tham khảo")
                    for i, item in enumerate(result.get("results", []), 1):
                        st.markdown(f"**[{i}] [{item.get('title') or 'Nguồn tham khảo'}]({item.get('url')})**")
                        st.write(item.get("content", "")[:900])
                        st.caption(f"Điểm liên quan: {item.get('score', '—')} · Hãy mở nguồn để xác minh nội dung.")
                except Exception as exc:
                    st.error(str(exc))
        st.caption("Cần TAVILY_API_KEY. Kết quả tìm kiếm có thể thiếu hoặc sai; hãy mở và kiểm chứng nguồn gốc.")
    elif mode == "Phân tích ảnh bằng AI":
        image_file = st.file_uploader("Tải ảnh bài tập, sơ đồ hoặc tài liệu", type=["png","jpg","jpeg","webp"], key="vision_image")
        question = st.text_area("Bạn muốn AI làm gì với ảnh?", value="Đọc nội dung ảnh và giải thích từng bước.")
        if image_file: st.image(image_file, width=420)
        if st.button("🧠 Phân tích ảnh", type="primary", key="analyze_img_btn"):
            if not image_file: st.warning("Hãy tải ảnh lên trước.")
            else:
                try:
                    with st.spinner("Đang phân tích ảnh..."):
                        st.markdown(analyze_image(image_file.getvalue(), image_file.type or "image/png", question))
                except Exception as exc: st.error(str(exc))
        st.caption("Cần model hỗ trợ vision; nếu dùng Groq, hãy đặt GROQ_VISION_MODEL theo danh sách model vision hiện hành.")
    elif mode == "Giọng nói":
        st.markdown("**Nói để nhập câu hỏi**")
        audio_file = st.audio_input("Ghi âm câu hỏi")
        if audio_file and st.button("🎙️ Chuyển giọng nói thành chữ", type="primary"):
            try:
                text = transcribe_audio(audio_file.getvalue(), "recording.wav")
                st.session_state["transcribed_text"] = text
                st.success("Đã chuyển thành văn bản:")
                st.text_area("Văn bản nhận diện", value=text, key="transcribed_result")
            except Exception as exc: st.error(str(exc))
        speech_text = st.text_area("Đọc câu trả lời thành tiếng", key="speech_text")
        if st.button("🔊 Đọc văn bản", key="speak_btn"):
            import json as _json
            safe_text = _json.dumps(speech_text, ensure_ascii=False)
            st.components.v1.html(f"""<button id="phucs-speak">▶ Phát giọng đọc</button><script>const phucsText={safe_text};document.getElementById("phucs-speak").onclick=()=>{{const u=new SpeechSynthesisUtterance(phucsText);u.lang="vi-VN";speechSynthesis.cancel();speechSynthesis.speak(u);}};</script>""", height=60)
        st.caption("Nhận diện giọng nói cần API transcription. Đọc văn bản dùng giọng hệ thống của trình duyệt, chất lượng tùy thiết bị.")
    elif mode == "Tạo ảnh AI":
        prompt = st.text_area("Mô tả ảnh muốn tạo", placeholder="Một mascot học tập màu hồng pastel, sách và mũ tốt nghiệp...")
        if st.button("🎨 Tạo ảnh", type="primary", key="generate_img_btn"):
            try:
                with st.spinner("Đang tạo ảnh..."):
                    image_bytes = generate_image(prompt)
                st.image(image_bytes, caption="Ảnh do AI tạo", use_container_width=True)
                st.download_button("Tải ảnh PNG", data=image_bytes, file_name="phucs-ai-image.png", mime="image/png")
            except Exception as exc: st.error(str(exc))
    elif mode in ("Tạo video AI", "Tạo nhạc AI"):
        is_video = mode == "Tạo video AI"
        secret_name = "REPLICATE_VIDEO_MODEL" if is_video else "REPLICATE_MUSIC_MODEL"
        prompt = st.text_area("Mô tả nội dung", placeholder="Mô tả cảnh video..." if is_video else "Mô tả phong cách nhạc, nhịp điệu và cảm xúc...")
        configured_model = setting(secret_name)
        st.caption(f"Model đang cấu hình: {configured_model or 'chưa cấu hình'}")
        if st.button("🎬 Tạo video" if is_video else "🎵 Tạo nhạc", type="primary", key="replicate_media_btn"):
            try:
                with st.spinner("Đang gửi yêu cầu đến dịch vụ tạo nội dung..."):
                    result = replicate_create(configured_model, prompt)
                st.json(result)
                output = result.get("output")
                if isinstance(output, str) and output.startswith("http"):
                    st.markdown(f"[Mở kết quả được tạo]({output})")
                elif isinstance(output, list):
                    for item in output:
                        if isinstance(item, str) and item.startswith("http"): st.markdown(f"[Mở kết quả]({item})")
                st.caption("Một số model trả về trạng thái processing; cần đợi hoặc mở URL prediction để lấy kết quả sau.")
            except Exception as exc: st.error(str(exc))
        st.caption("Cần REPLICATE_API_TOKEN và REPLICATE_VIDEO_MODEL / REPLICATE_MUSIC_MODEL tương thích với API Replicate.")

# ---------- Group chat and video calls ----------
with pages[9]:
    st.subheader("👥 Nhóm học tập & phòng gọi video")
    from phucs_integrations import setting, group_messages, send_group_message
    group_id = st.text_input("Mã nhóm", value="lop-hoc-1", help="Mọi người dùng cùng mã nhóm để xem cùng phòng chat.")
    st.markdown("#### 💬 Tin nhắn nhóm")
    if setting("SUPABASE_URL") and setting("SUPABASE_ANON_KEY"):
        if st.button("↻ Tải tin nhắn", key="load_group_msgs"):
            try: st.session_state["group_msgs"] = group_messages(group_id)
            except Exception as exc: st.error(f"Không tải được tin nhắn: {exc}")
        for msg in st.session_state.get("group_msgs", []):
            st.markdown(f"**{msg.get('display_name','Học viên')}** · <small>{msg.get('created_at','')}</small>  \n{msg.get('content','')}", unsafe_allow_html=True)
        with st.form("group_message_form", clear_on_submit=True):
            content = st.text_input("Tin nhắn mới", max_chars=2000)
            send = st.form_submit_button("Gửi tin nhắn", type="primary")
        if send and content.strip():
            try:
                send_group_message(group_id, uid, user["display_name"], content.strip())
                st.session_state["group_msgs"] = group_messages(group_id)
                st.rerun()
            except Exception as exc: st.error(f"Không gửi được tin nhắn. Kiểm tra Supabase Auth/RLS: {exc}")
    else:
        st.info("Cần cấu hình Supabase và chạy supabase_schema.sql. Tin nhắn nhóm chưa được bật cho đến khi có database.")
    st.divider()
    st.markdown("#### 📹 Gọi video")
    room = st.text_input("Tên phòng gọi", value=f"phucs-{group_id}")
    room_url = "https://meet.jit.si/" + "".join(ch for ch in room if ch.isalnum() or ch in "-_ ").replace(" ", "-")
    st.markdown(f"[Mở phòng gọi Jitsi ↗]({room_url})")
    st.caption("Đây là phòng họp Jitsi bên ngoài; không phải hệ thống gọi video tự lưu trữ. Không dùng phòng công khai để trao đổi dữ liệu nhạy cảm.")

# ---------- Plus, cloud storage and payment ----------
with pages[10]:
    st.subheader("☁️ P.H.U.C.S Plus & Lưu trữ đám mây")
    st.markdown("### P.H.U.C.S Plus")
    st.write("Giá dự kiến: **35.000 VNĐ/năm**. Bạn cần tạo sản phẩm và giá định kỳ trong Stripe Dashboard trước khi bật thanh toán.")
    st.caption("Không đánh dấu tài khoản là Plus chỉ vì người dùng quay về trang thành công; trạng thái trả phí phải được xác minh bằng webhook Stripe và lưu trong database đáng tin cậy.")
    email = st.text_input("Email nhận hóa đơn (tùy chọn)", key="billing_email")
    if st.button("💳 Thanh toán Plus", type="primary"):
        try:
            from phucs_integrations import create_checkout_url
            checkout_url = create_checkout_url(uid, email.strip())
            st.link_button("Mở trang thanh toán bảo mật ↗", checkout_url, use_container_width=True)
        except Exception as exc: st.error(str(exc))
    st.divider()
    st.markdown("### Tải tệp lên lưu trữ đám mây")
    st.write("Mục tiêu dung lượng 400–500 GB là dung lượng dự kiến của gói, không phải dung lượng tự có. Cần mua/chọn gói lưu trữ phù hợp và đặt giới hạn theo người dùng.")
    cloud_file = st.file_uploader("Chọn tệp để tải lên Supabase Storage", key="cloud_upload")
    if st.button("☁️ Tải lên", key="cloud_upload_btn"):
        if not cloud_file: st.warning("Hãy chọn một tệp.")
        else:
            try:
                from phucs_integrations import upload_supabase_file
                with st.spinner("Đang tải tệp lên..."):
                    meta = upload_supabase_file(uid, cloud_file)
                st.success(f"Đã tải lên: {meta['path']} ({meta['size']:,} byte)")
                st.json(meta)
            except Exception as exc: st.error(str(exc))
    st.caption("Cần SUPABASE_URL, SUPABASE_ANON_KEY và bucket phucs-files. Cấu hình Storage policies trước khi triển khai công khai.")

st.divider()
st.caption("P.H.U.C.S Alpha 2 · Một số tích hợp cần khóa API, cấu hình nhà cung cấp, chính sách bảo mật và kiểm thử trước khi mở cho công chúng.")
