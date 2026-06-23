import os
import hmac
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
PAYSTACK_SECRET_KEY  = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_REPLACE_ME")
PAYSTACK_PUBLIC_KEY  = os.getenv("PAYSTACK_PUBLIC_KEY", "pk_test_REPLACE_ME")
SELLER_EMAIL         = os.getenv("SELLER_EMAIL", "eatfor2@gmail.com")
BASE_URL             = os.getenv("BASE_URL", "http://localhost:5000")

BREVO_SMTP_LOGIN     = os.getenv("BREVO_SMTP_LOGIN")
BREVO_SMTP_KEY       = os.getenv("BREVO_SMTP_KEY")
BREVO_SENDER_EMAIL   = os.getenv("BREVO_SENDER_EMAIL", BREVO_SMTP_LOGIN)
BREVO_SENDER_NAME    = os.getenv("BREVO_SENDER_NAME", "Eat For 2 Orders")

MENU_ITEMS = [
    {
        "id": 1,
        "name": "Jollof Rice & Chicken",
        "price": 3500,
        "description": "Smoky party-style jollof with crispy fried chicken",
        "emoji": "🍚",
        "image": "https://images.unsplash.com/photo-1604329760661-e71dc83f8f26?w=600&q=80",
        "category": "Rice"
    },
    {
        "id": 2,
        "name": "Fried Rice & Plantain",
        "price": 3000,
        "description": "Colourful fried rice served with sweet ripe plantain",
        "emoji": "🍛",
        "image": "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&q=80",
        "category": "Rice"
    },
    {
        "id": 3,
        "name": "Pepper Chicken",
        "price": 4000,
        "description": "Juicy chicken marinated in rich Nigerian pepper sauce",
        "emoji": "🍗",
        "image": "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?w=600&q=80",
        "category": "Protein"
    },
    {
        "id": 4,
        "name": "Grilled Fish",
        "price": 4500,
        "description": "Fresh fish grilled with herbs, chilli & lemon butter",
        "emoji": "🐟",
        "image": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=600&q=80",
        "category": "Protein"
    },
    {
        "id": 5,
        "name": "Baked Plantain Bowl",
        "price": 2500,
        "description": "Roasted sweet plantain loaded with stew & veggies",
        "emoji": "🌿",
        "image": "https://images.unsplash.com/photo-1574484284002-952d92456975?w=600&q=80",
        "category": "Plantain"
    },
    {
        "id": 6,
        "name": "Chef's Special Box",
        "price": 6000,
        "description": "Full combo: rice, protein, plantain & drink — feeds 2!",
        "emoji": "🎁",
        "image": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&q=80",
        "category": "Combo"
    },
]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
                           public_key=PAYSTACK_PUBLIC_KEY,
                           menu=MENU_ITEMS)


@app.route("/menu")
def menu():
    return render_template("menu.html",
                           public_key=PAYSTACK_PUBLIC_KEY,
                           menu=MENU_ITEMS)


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "GET":
        item_id = request.args.get("item_id", type=int)
        item = next((i for i in MENU_ITEMS if i["id"] == item_id), None)
        return render_template("checkout.html", item=item,
                               public_key=PAYSTACK_PUBLIC_KEY)

    data    = request.form
    item_id = int(data.get("item_id"))
    qty     = int(data.get("quantity", 1))
    item    = next((i for i in MENU_ITEMS if i["id"] == item_id), None)

    if not item:
        return redirect(url_for("menu"))

    amount_kobo = item["price"] * qty * 100

    payload = {
        "email":        data["email"],
        "amount":       amount_kobo,
        "currency":     "NGN",
        "callback_url": f"{BASE_URL}/payment/callback",
        "metadata": {
            "customer_name": data["name"],
            "phone":         data["phone"],
            "address":       data["address"],
            "item_name":     item["name"],
            "quantity":      qty,
            "item_id":       item_id,
        }
    }

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type":  "application/json"
    }

    resp   = requests.post("https://api.paystack.co/transaction/initialize",
                           json=payload, headers=headers, timeout=15)
    result = resp.json()

    if result.get("status"):
        return redirect(result["data"]["authorization_url"])

    return render_template("checkout.html", item=item,
                           public_key=PAYSTACK_PUBLIC_KEY,
                           error="Payment could not be initialised. Please try again.")


@app.route("/payment/callback")
def payment_callback():
    reference = request.args.get("reference")
    if not reference:
        return redirect(url_for("index"))

    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    resp    = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=headers, timeout=15
    )
    result = resp.json()

    if result.get("status") and result["data"]["status"] == "success":
        meta = result["data"]["metadata"]
        _send_order_email(result["data"], meta)
        return render_template("success.html",
                               reference=reference,
                               meta=meta,
                               amount=result["data"]["amount"] // 100)

    return render_template("success.html",
                           reference=reference,
                           meta={},
                           amount=0,
                           failed=True)


@app.route("/webhook/paystack", methods=["POST"])
def paystack_webhook():
    signature = request.headers.get("x-paystack-signature", "")
    raw_body  = request.get_data()
    expected  = hmac.new(
        PAYSTACK_SECRET_KEY.encode(), raw_body, hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        return jsonify({"status": "invalid signature"}), 400

    event = request.get_json()
    if event and event.get("event") == "charge.success":
        data = event["data"]
        _send_order_email(data, data.get("metadata", {}))

    return jsonify({"status": "ok"}), 200


# ── Email helper ──────────────────────────────────────────────────────────────

def _send_order_email(transaction_data, meta):
    if not BREVO_SMTP_LOGIN or not BREVO_SMTP_KEY:
        print("WARNING: Brevo SMTP not configured – skipping email.")
        return

    subject = (
        f"New Order: {meta.get('item_name', 'Unknown')} "
        f"— NGN {transaction_data['amount'] // 100:,}"
    )

    html = f"""
    <html><body style="font-family:sans-serif;background:#f9f5f0;padding:20px;">
    <div style="max-width:520px;margin:auto;background:#fff;border-radius:12px;
                padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.1)">
      <div style="text-align:center;margin-bottom:20px">
        <h2 style="color:#e84c1e;margin:8px 0 0">New Order Received!</h2>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:15px;">
        <tr style="background:#fdf6ec">
          <td style="padding:10px 12px;color:#888;width:40%">Customer</td>
          <td style="padding:10px 12px"><b>{meta.get('customer_name','—')}</b></td>
        </tr>
        <tr>
          <td style="padding:10px 12px;color:#888">Email</td>
          <td style="padding:10px 12px">{transaction_data.get('customer',{}).get('email','—')}</td>
        </tr>
        <tr style="background:#fdf6ec">
          <td style="padding:10px 12px;color:#888">Phone</td>
          <td style="padding:10px 12px">{meta.get('phone','—')}</td>
        </tr>
        <tr>
          <td style="padding:10px 12px;color:#888">Address</td>
          <td style="padding:10px 12px">{meta.get('address','—')}</td>
        </tr>
        <tr style="background:#fdf6ec">
          <td style="padding:10px 12px;color:#888">Item</td>
          <td style="padding:10px 12px"><b>{meta.get('item_name','—')}</b></td>
        </tr>
        <tr>
          <td style="padding:10px 12px;color:#888">Quantity</td>
          <td style="padding:10px 12px">{meta.get('quantity','1')}</td>
        </tr>
        <tr style="background:#fdf6ec">
          <td style="padding:10px 12px;color:#888">Amount Paid</td>
          <td style="padding:10px 12px">
            <b style="color:#27ae60">NGN {transaction_data['amount']//100:,}</b>
          </td>
        </tr>
        <tr>
          <td style="padding:10px 12px;color:#888">Reference</td>
          <td style="padding:10px 12px;font-size:12px;color:#aaa">
            {transaction_data.get('reference','—')}
          </td>
        </tr>
      </table>
      <p style="margin-top:20px;color:#555;font-size:13px;text-align:center">
        Check your
        <a href="https://dashboard.paystack.com" style="color:#e84c1e">
          Paystack dashboard
        </a>
        to confirm payment.
      </p>
    </div></body></html>
    """

    msg            = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{BREVO_SENDER_NAME} <{BREVO_SENDER_EMAIL}>"
    msg["To"]      = SELLER_EMAIL
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP("smtp-relay.brevo.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(BREVO_SMTP_LOGIN, BREVO_SMTP_KEY)
            server.sendmail(BREVO_SENDER_EMAIL, SELLER_EMAIL, msg.as_string())
        print(f"Order email sent to {SELLER_EMAIL} via Brevo")
    except Exception as e:
        print(f"Brevo email error: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    port       = int(os.getenv("PORT", 5000))
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
