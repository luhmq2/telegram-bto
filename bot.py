import logging
import asyncio
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Logging setup to track payment attempts from your phone console
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8666468661:AAHzXsyHorv0LDQQ7S11mLEiAcCeM2XJUbI"
LTC_WALLET = "tltc1qhykunxr89ryvesvqgh7u5tp7decvfrz3e335uh"
OWNER_ID = 8936045536

INVENTORY = {
    "gfx_pack": {"name": "🎨 Premium GFX Pack", "price_usd": 5, "stock": 10, "content": "https://example.com"},
    "discord_vip": {"name": "👑 VIP Discord Role", "price_usd": 10, "stock": 3, "content": "https://discord.gg"}
}

# --- 🌐 TINY WEB SERVER FOR RENDER FREE TIER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
    server.serve_forever()
# ------------------------------------------------

def get_ltc_price():
    try:
        url = "https://binance.com"
        response = requests.get(url).json()
        return float(response["price"])
    except Exception as e:
        logging.error(f"Price Feed Error: {e}")
        return 95.00

def check_testnet_blockchain(wallet, target_amount_ltc):
    try:
        url = f"https://litecoinspace.org{wallet}/mempool"
        response = requests.get(url).json()
        for tx in response:
            for vout in tx.get("vout", []):
                if vout.get("scriptpubkey_address") == wallet:
                    amount_in_ltc = vout["value"] / 100000000
                    if round(amount_in_ltc, 4) == round(target_amount_ltc, 4):
                        return True
        return False
    except Exception as e:
        logging.error(f"Testnet Blockchain Tracker Error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gfx_label = f"{INVENTORY['gfx_pack']['name']} (${INVENTORY['gfx_pack']['price_usd']}) [Stock: {INVENTORY['gfx_pack']['stock']}]"
    vip_label = f"{INVENTORY['discord_vip']['name']} (${INVENTORY['discord_vip']['price_usd']}) [Stock: {INVENTORY['discord_vip']['stock']}]"
    keyboard = [
        [InlineKeyboardButton(gfx_label, callback_data="buy_gfx")],
        [InlineKeyboardButton(vip_label, callback_data="buy_vip")]
    ]
    await update.message.reply_text(
        "⚡️ *LITECOIN TESTNET STOREFRONT*\n\nSelect a product:", 
        parse_mode="Markdown", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_shop_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = "gfx_pack" if "gfx" in query.data else "discord_vip"
    product = INVENTORY[prod_id]

    if product["stock"] <= 0:
        await query.edit_message_text("❌ Out of stock!")
        return

    current_market_rate = get_ltc_price()
    base_ltc_needed = product["price_usd"] / current_market_rate
    unique_modifier = (query.from_user.id % 1000) / 100000
    exact_ltc_charge = round(base_ltc_needed + unique_modifier, 5)

    checkout_screen = f"⚙️ *ORDER CREATED*\n\nSend: `{exact_ltc_charge} tLTC`\nTo: `{LTC_WALLET}`"
    await query.edit_message_text(text=checkout_screen, parse_mode="Markdown")

    for _ in range(40):
        await asyncio.sleep(15)
        if check_testnet_blockchain(LTC_WALLET, exact_ltc_charge):
            product["stock"] -= 1
            await query.edit_message_text(text=f"🎉 Paid!\n📦 `{product['content']}`", parse_mode="Markdown")
            return
    await query.edit_message_text("❌ Timed out.")

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID: return
    if len(context.args) < 2: return
    product_key = context.args[0]
    try: amount_to_add = int(context.args[1])
    except ValueError: return
    if product_key in INVENTORY:
        INVENTORY[product_key]["stock"] += amount_to_add
        await update.message.reply_text(f"✅ Stock updated: {INVENTORY[product_key]['stock']}")

def main():
    # Start the tiny web portal in a background thread for Render
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_shop_buttons))
    app.add_handler(CommandHandler("add_stock", add_stock))
    
    print("Testnet shop bot is successfully running online...")
    app.run_polling()

if __name__ == '__main__':
    main()
