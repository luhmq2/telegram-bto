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

# Prices set to $0.10 and $0.20 to stay well beneath your wallet's 0.1 tLTC fee restrictions
INVENTORY = {
    "gfx_pack": {"name": "🎨 Premium GFX Pack", "price_usd": 0.10, "stock": 10, "content": "https://example.com"},
    "discord_vip": {"name": "👑 VIP Discord Role", "price_usd": 0.20, "stock": 3, "content": "https://discord.gg"}
}

# --- 🌐 WEB SERVER FOR RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
    server.serve_forever()

def get_ltc_price():
    try:
        url = "https://binance.com"
        response = requests.get(url).json()
        return float(response["price"])
    except Exception:
        return 95.00

def check_testnet_blockchain(wallet, target_amount_ltc):
    try:
        clean_wallet = wallet.strip().lower()
        url = f"https://litecoinspace.org{clean_wallet}/mempool"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return False
            
        transactions = response.json()
        for tx in transactions:
            for vout in tx.get("vout", []):
                if str(vout.get("scriptpubkey_address")).strip().lower() == clean_wallet:
                    amount_in_ltc = vout.get("value", 0) / 100000000
                    if round(amount_in_ltc, 4) == round(target_amount_ltc, 4):
                        return True
        return False
    except Exception as e:
        logging.error(f"Blockchain Tracker Error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gfx_label = f"{INVENTORY['gfx_pack']['name']} (${INVENTORY['gfx_pack']['price_usd']}) [Stock: {INVENTORY['gfx_pack']['stock']}]"
    vip_label = f"{INVENTORY['discord_vip']['name']} (${INVENTORY['discord_vip']['price_usd']}) [Stock: {INVENTORY['discord_vip']['stock']}]"
    keyboard = [
        [InlineKeyboardButton(gfx_label, callback_data="buy_gfx")],
        [InlineKeyboardButton(vip_label, callback_data="buy_vip")]
    ]
    await update.message.reply_text(
        "⚡️ *LITECOIN TESTNET STOREFRONT*\n\nSelect a product below to purchase using your fake developer coins:", 
        parse_mode="Markdown", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_shop_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    prod_id = "gfx_pack" if "gfx" in query.data else "discord_vip"
    product = INVENTORY[prod_id]

    if product["stock"] <= 0:
        await query.edit_message_text("❌ This test item is currently completely out of stock!")
        return

    current_market_rate = get_ltc_price()
    base_ltc_needed = product["price_usd"] / current_market_rate
    unique_modifier = (query.from_user.id % 1000) / 100000
    exact_ltc_charge = round(base_ltc_needed + unique_modifier, 5)

    # 🔄 Loading Frame Cycles for Text Animations
    animation_frames = [
        "⏳ [▢▢▢▢▢▢▢▢▢▢] 0% • Scanning Mempool...",
        "📡 [■■▢▢▢▢▢▢▢▢] 20% • Syncing Network...",
        "🔍 [■■■■▢▢▢▢▢▢] 40% • Listening for Tx...",
        "💎 [■■■■■■▢▢▢▢] 60% • Checking Hashes...",
        "⚡️ [■■■■■■■■▢▢] 80% • Waiting for Broadcast...",
        "🛡️ [■■■■■■■■■■] 95% • Awaiting Input..."
    ]

    base_checkout_text = (
        f"⚙️ *ORDER CREATED (TESTNET MODE)*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Product:* {product['name']}\n"
        f"💰 *Amount Due:* `{exact_ltc_charge} tLTC`\n"
        f"🏦 *Send To Address:*\n`{LTC_WALLET}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
    )

    # Main Asynchronous Payment Loop (Runs 40 cycles total)
    for loop_count in range(40):
        current_status_frame = animation_frames[loop_count % len(animation_frames)]
        
        try:
            await query.edit_message_text(
                text=f"{base_checkout_text}\n`{current_status_frame}`\n\n_Open your Coinomi wallet and send the exact amount requested above._",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        # Check blockchain backend data directly
        if check_testnet_blockchain(LTC_WALLET, exact_ltc_charge):
            product["stock"] -= 1
            
            await query.edit_message_text(
                text=f"{base_checkout_text}\n🟢 *PAYMENT FOUND! PREPARING PARCEL...*\n`[■■■■■■■■■■] 100% COMPLETE`",
                parse_mode="Markdown"
            )
            await asyncio.sleep(2.5) 

            delivery_payload = (
                f"✨ *TRANSACTION CONFIRMED!* ✨\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎉 *Thank you for your purchase!*\n"
                f"💵 Verified Hash Amount: `{exact_ltc_charge} tLTC`\n\n"
                f"📦 *YOUR DIGITAL GOODS PACK:* \n"
                f"📥 `{product['content']}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"ℹ️ _This was a simulated Litecoin Testnet loop transaction._"
            )
            await query.edit_message_text(text=delivery_payload, parse_mode="Markdown")
            return
            
        await asyncio.sleep(15)

    # 🛑 SUPPORT TRIGGER FALLBACK: Triggers only if loop exits completely unpaid
    support_keyboard = [[InlineKeyboardButton("💬 Contact Support", url=f"tg://user?id={OWNER_ID}")]]
    
    timeout_payload = (
        f"❌ *PAYMENT NOT COMPLETE*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ The loading sequence reached `100%` but we were unable to find a verified transfer on the public testnet network.\n\n"
        f"If you already sent your coins and your wallet shows it as unconfirmed or pending, please click the button below to message our team directly.\n"
        f"━━━━━━━━━━━━━━━━━━━━━"
    )
    await query.edit_message_text(text=timeout_payload, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(support_keyboard))

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Permission Denied.")
        return
    if len(context.args) < 2: return
    product_key = context.args[0]
    try: amount_to_add = int(context.args[1])
    except ValueError: return

    if product_key in INVENTORY:
        INVENTORY[product_key]["stock"] += amount_to_add
        await update.message.reply_text(f"✅ *STOCK UPDATED:* Current total is `{INVENTORY[product_key]['stock']}`", parse_mode="Markdown")

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_shop_buttons))
    app.add_handler(CommandHandler("add_stock", add_stock))
    
    print("Testnet shop bot is successfully running online...")
    app.run_polling()

if __name__ == '__main__':
    main()
