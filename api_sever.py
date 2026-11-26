"""Stripe webhook receiver for P.H.U.C.S Plus. Deploy separately from Streamlit.
Example: uvicorn api_server:app --host 0.0.0.0 --port 8000
"""
import os
import re, hmac, hashlib, time
from datetime import datetime, timezone
import requests
from fastapi import FastAPI, Request, HTTPException
import stripe

app = FastAPI(title="P.H.U.C.S billing webhook")

@app.get('/health')
def health():
    return {"status": "ok"}

@app.post('/stripe/webhook')
async def stripe_webhook(request: Request):
    secret = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    api_key = os.getenv('STRIPE_SECRET_KEY', '')
    if not secret or not api_key:
        raise HTTPException(status_code=503, detail='Stripe webhook is not configured')
    stripe.api_key = api_key
    payload = await request.body()
    signature = request.headers.get('stripe-signature', '')
    try:
        event = stripe.Webhook.construct_event(payload, signature, secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f'Invalid webhook: {exc}')

    supabase_url = os.getenv('SUPABASE_URL', '').rstrip('/')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    if not supabase_url or not service_key:
        raise HTTPException(status_code=503, detail='Supabase server credentials are not configured')

    event_type = event['type']
    obj = event['data']['object']
    relevant = event_type in ('checkout.session.completed', 'customer.subscription.updated', 'customer.subscription.deleted')
    if relevant:
        metadata = obj.get('metadata') or {}
        user_id = metadata.get('phucs_user_id') or obj.get('client_reference_id')
        subscription_id = obj.get('subscription') if event_type == 'checkout.session.completed' else obj.get('id')
        customer_id = obj.get('customer')
        status = 'active' if event_type == 'checkout.session.completed' else obj.get('status', 'inactive')
        period_end = obj.get('current_period_end')
        # For checkout completion, retrieve subscription so its actual status/period are verified.
        if event_type == 'checkout.session.completed' and subscription_id:
            try:
                sub = stripe.Subscription.retrieve(subscription_id)
                status = sub.get('status', status)
                period_end = sub.get('current_period_end', period_end)
                metadata = sub.get('metadata') or metadata
                user_id = metadata.get('phucs_user_id') or user_id
            except Exception:
                pass
        if not user_id:
            # Ignore unrelated Stripe events that do not belong to a P.H.U.C.S user.
            return {'received': True, 'ignored': True}
        row = {
            'user_id': str(user_id), 'stripe_customer_id': str(customer_id or ''),
            'stripe_subscription_id': str(subscription_id or ''), 'status': str(status),
            'current_period_end': datetime.fromtimestamp(period_end, timezone.utc).isoformat() if period_end else None,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        response = requests.post(
            f'{supabase_url}/rest/v1/subscriptions?on_conflict=user_id',
            headers={'apikey': service_key, 'Authorization': f'Bearer {service_key}',
                     'Content-Type': 'application/json', 'Prefer': 'resolution=merge-duplicates,return=minimal'},
            json=row, timeout=20)
        if not response.ok:
            raise HTTPException(status_code=502, detail='Could not update subscription status in Supabase')
    return {'received': True}


@app.post('/sepay/webhook')
async def sepay_webhook(request: Request):
    """Verify SePay transfer events and grant one year of Plus for exactly 35,000 VND."""
    raw = await request.body()
    api_key = os.getenv('SEPAY_WEBHOOK_API_KEY', '').strip()
    hmac_secret = os.getenv('SEPAY_WEBHOOK_HMAC_SECRET', '').strip()
    auth = request.headers.get('authorization', '')
    authenticated = bool(api_key and hmac.compare_digest(auth, f'Apikey {api_key}'))
    if hmac_secret:
        signature = request.headers.get('x-sepay-signature', '')
        timestamp = request.headers.get('x-sepay-timestamp', '')
        try:
            ts = int(timestamp)
            expected = 'sha256=' + hmac.new(hmac_secret.encode(), timestamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
            authenticated = authenticated or (abs(int(time.time()) - ts) <= 300 and hmac.compare_digest(signature, expected))
        except Exception:
            pass
    if not authenticated:
        raise HTTPException(status_code=401, detail='Invalid SePay webhook authentication')

    try:
        data = await request.json()
        transaction_id = int(data.get('id'))
        amount = int(data.get('transferAmount') or 0)
        transfer_type = str(data.get('transferType') or '').lower()
        content = str(data.get('content') or data.get('description') or '')
        match = re.search(r'PHUCS-([A-Za-z0-9_-]{4,100})', content, re.IGNORECASE)
        if transfer_type != 'in':
            return {'success': True, 'ignored': 'not_incoming'}
        if amount != 35000:
            return {'success': True, 'ignored': 'amount_mismatch'}
        if not match:
            return {'success': True, 'ignored': 'missing_payment_code'}
        user_id = match.group(1)
        paid_at_raw = data.get('transactionDate')
        paid_at = None
        if paid_at_raw:
            try:
                paid_at = datetime.strptime(paid_at_raw, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                paid_at = None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f'Invalid SePay payload: {exc}')

    supabase_url = os.getenv('SUPABASE_URL', '').rstrip('/')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    if not supabase_url or not service_key:
        raise HTTPException(status_code=503, detail='Supabase server credentials are not configured')
    payload = {
        'p_transaction_id': transaction_id,
        'p_user_id': user_id,
        'p_amount_vnd': amount,
        'p_transfer_content': content,
        'p_reference_code': str(data.get('referenceCode') or ''),
        'p_paid_at': paid_at,
    }
    response = requests.post(
        f'{supabase_url}/rest/v1/rpc/process_phucs_bank_payment',
        headers={'apikey': service_key, 'Authorization': f'Bearer {service_key}', 'Content-Type': 'application/json'},
        json=payload, timeout=15)
    if not response.ok:
        raise HTTPException(status_code=502, detail='Could not record bank payment')
    return {'success': True, 'activated': response.json() if response.content else None}
