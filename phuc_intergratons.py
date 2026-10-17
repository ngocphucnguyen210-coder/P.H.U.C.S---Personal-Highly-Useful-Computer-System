"""Optional service adapters for P.H.U.C.S AI.
All credentials are read from Streamlit secrets or environment variables.
"""
import os, base64, time, requests
from pathlib import Path


def setting(name, default=""):
    try:
        import streamlit as st
        value = st.secrets.get(name, None)
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass
    return os.getenv(name, default).strip()


def tavily_search(query, max_results=5):
    key = setting("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("Thiếu TAVILY_API_KEY. Tạo khóa tại https://tavily.com/ rồi thêm vào Secrets.")
    r = requests.post("https://api.tavily.com/search", headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"},
                      json={"query": query, "max_results": max_results, "search_depth":"advanced", "include_answer":True}, timeout=45)
    r.raise_for_status()
    return r.json()


def ai_client(vision=False):
    from openai import OpenAI
    groq_key = setting("GROQ_API_KEY")
    openai_key = setting("OPENAI_API_KEY")
    if groq_key:
        return OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1"), setting("GROQ_VISION_MODEL" if vision else "GROQ_MODEL", "llama-3.3-70b-versatile")
    if openai_key:
        return OpenAI(api_key=openai_key), setting("OPENAI_VISION_MODEL" if vision else "OPENAI_MODEL", "gpt-4.1-mini")
    raise RuntimeError("Thiếu GROQ_API_KEY hoặc OPENAI_API_KEY trong Streamlit Secrets.")


def analyze_image(image_bytes, mime_type, question):
    client, model = ai_client(vision=True)
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":"Bạn là P.H.U.C.S, phân tích ảnh cẩn thận. Với bài tập, giải từng bước. Nếu ảnh mờ hoặc thiếu dữ kiện, hãy nói rõ; không đoán nội dung không nhìn thấy."},
                  {"role":"user","content":[{"type":"text","text":question or "Hãy mô tả và phân tích ảnh này."},
                                               {"type":"image_url","image_url":{"url":f"data:{mime_type};base64,{encoded}"}}]}],
        temperature=0.2)
    return response.choices[0].message.content


def transcribe_audio(audio_bytes, filename="recording.wav"):
    key = setting("GROQ_API_KEY")
    if key:
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        model = setting("GROQ_TRANSCRIPTION_MODEL", "whisper-large-v3-turbo")
    elif setting("OPENAI_API_KEY"):
        from openai import OpenAI
        client = OpenAI(api_key=setting("OPENAI_API_KEY"))
        model = setting("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
    else:
        raise RuntimeError("Cần GROQ_API_KEY hoặc OPENAI_API_KEY để chuyển giọng nói thành văn bản.")
    import io
    return client.audio.transcriptions.create(model=model, file=(filename, io.BytesIO(audio_bytes))).text


def generate_image(prompt):
    key = setting("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Tạo ảnh hiện dùng OpenAI Images API. Hãy thêm OPENAI_API_KEY; Groq chỉ dùng cho chat/một số tác vụ khác.")
    from openai import OpenAI
    client = OpenAI(api_key=key)
    model = setting("OPENAI_IMAGE_MODEL", "gpt-image-1")
    result = client.images.generate(model=model, prompt=prompt, size="1024x1024")
    item = result.data[0]
    if getattr(item, "b64_json", None):
        return base64.b64decode(item.b64_json)
    if getattr(item, "url", None):
        img = requests.get(item.url, timeout=90); img.raise_for_status(); return img.content
    raise RuntimeError("Nhà cung cấp không trả về dữ liệu ảnh.")


def replicate_create(model, prompt, extra_input=None):
    token = setting("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("Thiếu REPLICATE_API_TOKEN. Tạo token tại https://replicate.com/account/api-tokens.")
    if not model or ":" not in model:
        raise RuntimeError("Hãy cấu hình model Replicate dạng owner/model:version hoặc dùng model slug được API hỗ trợ.")
    payload = {"version": model.split(":", 1)[1], "input": {"prompt": prompt}}
    # For version IDs, the owner/model portion is not needed by the predictions endpoint.
    r = requests.post("https://api.replicate.com/v1/predictions", headers={"Authorization":f"Bearer {token}", "Content-Type":"application/json", "Prefer":"wait=10"}, json=payload, timeout=60)
    if r.status_code == 404:
        # The model identifier may be an owner/model slug; use the model endpoint.
        owner_model = model.split(":", 1)[0]
        r = requests.post(f"https://api.replicate.com/v1/models/{owner_model}/predictions", headers={"Authorization":f"Bearer {token}", "Content-Type":"application/json", "Prefer":"wait=10"}, json={"input":{"prompt":prompt}}, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data


def supabase_client():
    url = setting("SUPABASE_URL")
    # Service role is only used server-side in this Streamlit app; never expose it in browser code.
    key = setting("SUPABASE_SERVICE_ROLE_KEY") or setting("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Cần SUPABASE_URL và SUPABASE_ANON_KEY; các tác vụ quản trị server cần SUPABASE_SERVICE_ROLE_KEY.")
    from supabase import create_client
    return create_client(url, key)


def create_checkout_url(user_id, email=""):
    import stripe
    stripe.api_key = setting("STRIPE_SECRET_KEY")
    price_id = setting("STRIPE_PLUS_PRICE_ID")
    if not stripe.api_key or not price_id:
        raise RuntimeError("Cần STRIPE_SECRET_KEY và STRIPE_PLUS_PRICE_ID; tạo sản phẩm/giá trong Stripe Dashboard trước.")
    app_url = setting("APP_BASE_URL", "http://localhost:8501").rstrip("/")
    session = stripe.checkout.Session.create(
        mode="subscription", line_items=[{"price":price_id,"quantity":1}],
        success_url=app_url + "?payment=success", cancel_url=app_url + "?payment=cancelled",
        client_reference_id=str(user_id), customer_email=email or None,
        metadata={"phucs_user_id":str(user_id), "plan":"plus"},
        subscription_data={"metadata":{"phucs_user_id":str(user_id), "plan":"plus"}})
    return session.url


def upload_supabase_file(user_id, uploaded_file, bucket=None):
    client = supabase_client()
    bucket = bucket or setting("SUPABASE_STORAGE_BUCKET", "phucs-files")
    safe_name = Path(uploaded_file.name).name.replace(" ", "_")
    path = f"{user_id}/{int(time.time())}_{safe_name}"
    data = uploaded_file.getvalue()
    client.storage.from_(bucket).upload(path, data, {"content-type": uploaded_file.type or "application/octet-stream", "upsert":"false"})
    return {"bucket":bucket,"path":path,"size":len(data)}


def group_messages(group_id, limit=50):
    client = supabase_client()
    return client.table("group_messages").select("id,group_id,user_id,display_name,content,created_at").eq("group_id", group_id).order("created_at", desc=False).limit(limit).execute().data


def send_group_message(group_id, user_id, display_name, content):
    client = supabase_client()
    return client.table("group_messages").insert({"group_id":group_id,"user_id":str(user_id),"display_name":display_name,"content":content}).execute().data
