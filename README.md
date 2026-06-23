# 🍽️ Eat For 2 — Website

A 3D animated food ordering website for Eat For 2, a 24/7 private chef & food vendor in Lagos, Sangotedo.

## 🗂️ File Structure

```
eat-for-2/
├── app.py                  # Flask app — all routes live here
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── templates/
│   ├── index.html          # Hero landing page (Three.js 3D + Tailwind)
│   ├── menu.html           # Full menu with category filtering
│   ├── checkout.html       # Order form (name, email, phone, address)
│   └── success.html        # Payment confirmation page
└── static/
    ├── js/                 # (optional custom JS files)
    └── img/                # (optional local images)
```

## 🚀 Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your Paystack keys, Gmail, and seller email
```

### 3. Set up Paystack
- Sign up at https://dashboard.paystack.com
- Go to Settings → API Keys & Webhooks
- Copy your **Public Key** and **Secret Key** into `.env`
- Set your webhook URL to: `https://yourdomain.com/webhook/paystack`

### 4. Set up Gmail for sending order emails
- Enable 2-Step Verification on your Google account
- Go to https://myaccount.google.com/apppasswords
- Generate an App Password for "Mail"
- Put that 16-character password in `.env` as `SMTP_PASSWORD`

### 5. Run locally
```bash
python app.py
```
Visit http://localhost:5000

## 💳 Payment Flow

```
Customer selects item
    → Fills checkout form (name, email, phone, address)
    → Flask sends order to Paystack API
    → Customer redirected to Paystack hosted checkout
    → Pays via Card / Bank Transfer / USSD
    → Paystack redirects back to /payment/callback
    → Flask verifies payment with Paystack API
    → Flask emails order details to seller
    → Customer sees success page
```

## 🌐 Deploy to Production

### Option A — Render.com (free)
1. Push code to GitHub
2. Connect repo on render.com
3. Set environment variables in Render dashboard
4. Deploy!

### Option B — Railway.app
Same process — connect GitHub repo, add env vars, deploy.

## 📞 Contact
TikTok: @eat_for_2 · Phone: 08139595504 · Lagos, Sangotedo
