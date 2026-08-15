import logging
import asyncio
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = "8666468661:AAHzXsyHorv0LDQQ7S11mLEiAcCeM2XJUbI"
LTC_WALLET = "ltc1qx3ff59204wy3pt0qygzyh3c7nw3v0d0vwcqzes"
OWNER_ID = 8936045536
OWNER_USERNAME = "enrollfo"

INVENTORY = {
    "gfx_pack": {"name": "💳 fulls", "price_usd": 5.00, "stock": 0, "items": []},
    "discord_vip": {"name": "🍔 food logs", "price_usd": 10.00, "stock": 0, "items": []}
}

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
    server.serve_forever()

def get_ltc_price():
    try:
        r = requests.get("https://binance.com", timeout=4)
        return float(r.json()["price"])
    except: return 95.00

def check_live_blockchain(wallet, target_amount):
    try:
        r = requests.get(f"https://litecoinspace.org{wallet}/mempool", timeout=10)
        for tx in r.json():
            for v in tx.get("vout", []):
                if str(v.get("scriptpubkey_address")).strip().lower() == wallet.strip().lower():
                    if round(v.get("value", 0) / 100000000, 4) == round(float(target_amount), 4): return True
        return False
    except: return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    g_lbl = f"{INVENTORY['gfx_pack']['name']} (${INVENTORY['gfx_pack']['price_usd']:.2f}) [Stock: {INVENTORY['gfx_pack']['stock']}]"
    v_lbl = f"{INVENTORY['discord_vip']['name']} (${INVENTORY['discord_vip']['price_usd']:.2f}) [Stock: {INVENTORY['discord_vip']['stock']}]"
    kbd = [[InlineKeyboardButton(g_lbl, callback_data="buy_gfx")], [InlineKeyboardButton(v_lbl, callback_data="buy_vip")]]
    await update.message.reply_text("⚡️ *LITECOIN LIVE STORE*\n\nSelect an item:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kbd))

async def handle_shop_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.startswith("verify_"):
        _, pid, amt = q.data.split("_")
        amt = float(amt)
        prod = INVENTORY[pid]
        if prod["stock"] <= 0:
            await q.edit_message_text("❌ Out of stock!")
            return
        await q.edit_message_text("🔄 *VERIFYING TRANSACTION...*")
        await asyncio.sleep(2)
        if check_live_blockchain(LTC_WALLET, amt):
            item = prod["items"].pop(0)
            prod["stock"] = len(prod["items"])
            await q.edit_message_text(f"✨ *PAID!* ✨\n\n📦 *CONTENT:*\n`{item}`")
        else:
            btn = InlineKeyboardButton("🟢 Try Confirm Again", callback_data=f"verify_{pid}_{amt}")
            await q.edit_message_text(f"❌ *NOT FOUND YET.*\n\nSupport: @{OWNER_USERNAME}", reply_markup=InlineKeyboardMarkup([[btn]]))
        return
    pid = "gfx_pack" if "gfx" in q.data else "discord_vip"
    prod = INVENTORY[pid]
    if prod["stock"] <= 0:
        await q.edit_message_text("❌ Out of stock!")
        return
    amt = round((prod["price_usd"] / get_ltc_price()) + ((q.from_user.id % 1000) / 100000), 5)
    btn = InlineKeyboardButton("🟢 Confirm Payment", callback_data=f"verify_{pid}_{amt}")
    await q.edit_message_text(f"⚙️ *INVOICE*\n\n📦 *Item:* {prod['name']}\n💰 *Send:* `{amt} LTC`\n🏦 *To Address:*\n`{LTC_WALLET}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[btn]]))

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if not context.args or len(context.args) < 1: return
    pk = context.args[0]
    if pk not in INVENTORY: return
    txt = update.message.text
    items = [l.strip() for l in txt[txt.find(f"/add_stock {pk}") + len(f"/add_stock {pk}"):].strip().split('\n') if l.strip()]
    INVENTORY[pk]["items"].extend(items)
    INVENTORY[pk]["stock"] = len(INVENTORY[pk]["items"])
    await update.message.reply_text(f"✅ Added {len(items)} items. Total: {INVENTORY[pk]['stock']}")

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_shop_buttons))
    app.add_handler(CommandHandler("add_stock", add_stock))
    print("Production Mainnet shop bot running...")
    app.run_polling()

if __name__ == '__main__':
    main()
