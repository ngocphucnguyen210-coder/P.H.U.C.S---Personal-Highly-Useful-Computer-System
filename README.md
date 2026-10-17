# P.H.U.C.S AI — Alpha 2 (Groq + integrations)

P.H.U.C.S is a Vietnamese pastel-pink learning assistant built with Streamlit. This repository includes the core app plus optional integrations for web search, vision, speech transcription, AI image/video/music generation, social login, group chat, storage, and Stripe subscriptions.

> **Important:** The code is a configurable starter, not a fully audited commercial platform. External services require real credentials, provider-side setup, correct model IDs, database policies, and testing. Do not advertise 500 GB storage or paid Plus entitlements until quotas and verified subscription state are enforced.

## 1. Files

- `app.py` — Streamlit application and UI.
- `phucs_integrations.py` — service adapters for APIs.
- `api_server.py` — Stripe webhook receiver; deploy separately from Streamlit.
- `supabase_schema.sql` — starter tables for group messages and subscriptions.
- `requirements.txt` — Python dependencies.
- `.env.example` — names of configuration variables; replace placeholders in Streamlit Secrets, not in GitHub.

## 2. Run locally

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Fill `.env` with real values. Never commit `.env` or `.streamlit/secrets.toml`.

## 3. Deploy on Streamlit Community Cloud

1. Upload the repository to GitHub.
2. Go to <https://share.streamlit.io/> and create an app from the repository, entrypoint `app.py`.
3. Open **App settings → Secrets** and paste only the variables you have actually configured.
4. Redeploy after saving secrets.

Official guide: <https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app>

## 4. Core AI (Groq)

Create a key at <https://console.groq.com/keys> and add:

```toml
GROQ_API_KEY = "gsk-..."
GROQ_MODEL = "llama-3.3-70b-versatile"
```

Model IDs and feature availability can change. Check <https://console.groq.com/docs/models>. Image analysis requires a model that supports image input, configured as `GROQ_VISION_MODEL`; Groq does not provide the image generation endpoint used here.

## 5. Web search with citations

Get a Tavily API key at <https://tavily.com/> and add:

```toml
TAVILY_API_KEY = "tvly-..."
```

The app displays source titles, URLs, snippets, and a search summary. Search results can still be incomplete or incorrect; open the sources to verify claims.

## 6. Image generation, audio and media

- Image generation uses OpenAI Images API: configure `OPENAI_API_KEY` and optionally `OPENAI_IMAGE_MODEL`.
- Speech-to-text uses Groq transcription when `GROQ_API_KEY` is present, otherwise OpenAI transcription. Confirm current model IDs in the provider docs.
- Browser text-to-speech uses the device's built-in speech synthesis; available voices depend on the browser/device.
- Video/music generation calls Replicate: configure `REPLICATE_API_TOKEN`, `REPLICATE_VIDEO_MODEL`, and `REPLICATE_MUSIC_MODEL` with model identifiers supported by Replicate. Models have different input schemas and costs; the generic `prompt` input may need adjustment for the specific model.

Replicate token page: <https://replicate.com/account/api-tokens>

## 7. Google / Facebook / Apple sign-in, group chat and cloud storage

1. Create a project at <https://supabase.com/>.
2. Add `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and the **server-only** `SUPABASE_SERVICE_ROLE_KEY` to Streamlit Secrets.
3. In Supabase Authentication → Providers, configure Google, Facebook, and Apple, and set each provider's callback URL to the exact callback shown by Supabase (usually `https://PROJECT_REF.supabase.co/auth/v1/callback`).
4. Add the Streamlit app URL to Supabase's allowed redirect URLs and set `APP_BASE_URL` to the app's public URL.
5. Run `supabase_schema.sql` in Supabase SQL Editor.
6. Create a Storage bucket named `phucs-files`, or set `SUPABASE_STORAGE_BUCKET` to your bucket name. Review and configure Storage policies before public launch.

Supabase Auth supports social providers; each provider also requires its own developer-console configuration. See <https://supabase.com/docs/guides/auth/social-login>.

**Security:** `SUPABASE_SERVICE_ROLE_KEY` bypasses Row Level Security. It must remain server-side, never be used in browser JavaScript, never be committed to GitHub, and should be rotated if exposed. Before a public launch, enforce user ownership, group membership, quotas, rate limits, and private bucket policies. The current Streamlit starter is not a substitute for a dedicated authorization backend.

The group-chat view loads and posts messages to the `group_messages` table. The video-call button opens an external Jitsi room; it is not a self-hosted video service and public rooms should not be used for sensitive meetings.

## 8. Plus subscription and Stripe

1. In Stripe Dashboard, create a product named `P.H.U.C.S Plus` and a recurring yearly price of **35,000 VND/year** (if that is the intended commercial price).
2. Add `STRIPE_SECRET_KEY`, `STRIPE_PLUS_PRICE_ID`, and `APP_BASE_URL` to Streamlit Secrets.
3. Deploy `api_server.py` separately on a Python host that supports an HTTP service, for example Render or Fly.io. Start it with `uvicorn api_server:app --host 0.0.0.0 --port 8000`.
4. Set server environment variables `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` on that host.
5. In Stripe Webhooks, register `https://YOUR-WEBHOOK-HOST/stripe/webhook` for checkout completion and subscription update/deletion events.
6. Test using Stripe test mode before accepting real payments.

The webhook writes verified subscription status into the `subscriptions` table. The current UI does not yet enforce Plus entitlements or storage quotas against this table; that enforcement must be added before selling the plan. Do not grant Plus solely based on the browser's success redirect.

Stripe docs: <https://docs.stripe.com/billing/subscriptions/checkout>

## 9. Storage sizing

A 400–500 GB quota is a product/business setting, not a feature automatically provided by this code. Confirm provider plan limits and pricing, create per-user quotas, handle upload size limits, and use private signed URLs. Never promise the quota until it is actually purchased and enforced.

## 10. Production checklist

- Use a persistent managed database rather than SQLite for multi-user production.
- Configure OAuth redirect URLs and verify callbacks.
- Keep all secret keys out of GitHub; rotate exposed keys.
- Configure Supabase RLS and private storage policies; restrict group membership.
- Add subscription entitlement checks, quota enforcement, rate limits, abuse prevention, logging and backups.
- Validate webhook signatures and test subscription cancellation/renewal.
- Confirm each AI provider's current model IDs, input schema, rate limits, terms, and cost.
- Add privacy policy, terms of service, support contact, and applicable legal/tax requirements before launch.
