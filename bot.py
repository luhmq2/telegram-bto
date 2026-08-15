import logging
import asyncio
import requests
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8666468661:AAHzXsyHorv0LDQQ7S11mLEiAcCeM2XJUbI"
LTC_WALLET = "ltc1qx3ff59204wy3pt0qygzyh3c7nw3v0d0vwcqzes"
OWNER_ID = 8936045536
OWNER_USERNAME = "enrollfo"

INVENTORY = {
    "gfx_pack": {"name": "💳 fulls", "price_usd": 5.00, "stock": 0, "items": []},
    "discord_vip": {"name": "🍔 food logs", "price_usd": 10.00, "stock": 0, "items": []}
}

# Explicitly disable local polling flags to enforce strict Web-Hook integration
tg_app = Application.builder().token(TOKEN).updater(None).build()
fastapi_app = FastAPI()

def get_ltc_price():
    try:
        url = "https://binance.com"
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            return float(response.json()["price"])
    except Exception:
        pass
    return 95.00

def check_live_blockchain(wallet, target_amount):
    clean_wallet = wallet.strip()
    target_rounded = round(float(target_amount), 4)
    endpoints = [
        f"https://litecoinspace.org{clean_wallet}/mempool",
        f"https://litecoinspace.org{clean_wallet}/txs"
    ]
    for url in endpoints:
        try:
            response = requests.get(url, timeout=8)
            if response.status_code != 200:
                continue
            transactions = response.json()
            if not isinstance(transactions, list):
                continue
            for tx in transactions:
                for vout in tx.get("vout", []):
                    if str(vout.get("scriptpubkey_address")).strip() == clean_wallet:
                        amount_ltc = vout.get("value", 0) / 100000000
                        if round(amount_ltc, 4) == target_rounded:
                            return True
        except Exception:
            pass
    return False

async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gfx_label = f"{INVENTORY['gfx_pack']['name']} (${INVENTORY['gfx_pack']['price_usd']:.2f}) [Stock: {INVENTORY['gfx_pack']['stock']}]"
    vip_label = f"{INVENTORY['discord_vip']['name']} (${INVENTORY['discord_vip']['price_usd']:.2f}) [Stock: {INVENTORY['discord_vip']['stock']}]"
    keyboard = [[InlineKeyboardButton(gfx_label, callback_data="buy_gfx")], [InlineKeyboardButton(vip_label, callback_data="buy_vip")]]
    await update.message.reply_text("⚡️ *LITECOIN LIVE STORE*\n\nSelect an item:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_shop_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("verify_"):
        _, pid, amt = query.data.split("_")
        amt = float(amt)
        product = INVENTORY[pid]
        
        if product["stock"] <= 0 or len(product["items"]) == 0:
            await query.edit_message_text(text="❌ This item just sold out! Payment verification canceled.", parse_mode="Markdown")
            return
            
        animation_frames = [
            "⏳ [▢▢▢▢▢▢▢▢▢▢] 10% • Querying Network Node...",
            "📡 [■■■▢▢▢▢▢▢▢] 35% • Searching Mempool Hashes...",
            "🔍 [■■■■■■▢▢▢▢] 65% • Inspecting Address UTXOs...",
            "🛡️ [■■■■■■■■■▢] 90% • Checking Broadcast Signatures..."
        ]
        for frame in animation_frames:
            try:
                await query.edit_message_text(text=f"🔄 *BLOCKCHAIN VERIFICATION IN PROGRESS*\n\n`{frame}`", parse_mode="Markdown")
                await asyncio.sleep(0.5)
            except Exception:
                pass
                
        if check_live_blockchain(LTC_WALLET, amt):
            delivered_item = product["items"].pop(0)
            product["stock"] = len(product["items"])
            
            delivery_payload = (
                f"✨ *TRANSACTION CONFIRMED!* ✨\n\n"
                f"🎉 *Thank you for your purchase!*\n"
                f"💵 Verified Hash Volume: `{amt} LTC`\n\n"
                f"📦 *YOUR DELIVERED PRODUCT CONTENT:* \n"
                f"`{delivered_item}`\n\n"
                f"📊 *Current Stock Remaining:* `{product['stock']}` items left"
            )
            await query.edit_message_text(text=delivery_payload, parse_mode="Markdown")
            asyncio.create_task(delete_message_after_delay(context, query.message.chat_id, query.message.message_id, 180))
            return
        else:
            retry_btn = InlineKeyboardButton("🟢 Confirm Payment Again", callback_data=f"verify_{pid}_{amt}")
            failed_screen = (
                f"❌ *PAYMENT NOT COMPLETE*\n\n"
                f"⚠️ The loading verification reached `100%` but no matching transaction of `{amt} LTC` was detected on the live ledger.\n\n"
                f"If you already sent the transfer from your wallet, allow up to 60 seconds for network propagation before attempting manual verification again.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ *Not working?* [Contact Support](https://t.me{OWNER_USERNAME})"
            )
            await query.edit_message_text(text=failed_screen, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[retry_btn]]))
            asyncio.create_task(delete_message_after_delay(context, query.message.chat_id, query.message.message_id, 180))
        return
        
    pid = "gfx_pack" if "gfx" in query.data else "discord_vip"
    prod = INVENTORY[pid]
    if prod["stock"] <= 0:
        await query.edit_message_text("❌ This product asset is currently completely out of stock!")
        return
        
    current_market_rate = get_ltc_price()
    base_ltc_needed = prod["price_usd"] / current_market_rate
    unique_modifier = (query.from_user.id % 1000) / 100000
    exact_ltc_charge = round(base_ltc_needed + unique_modifier, 5)
    
    checkout_btn = InlineKeyboardButton("🟢 Confirm Payment", callback_data=f"verify_{pid}_{exact_ltc_charge}")
    checkout_screen = (
        f"⚙️ *REAL LITECOIN INVOICE GENERATED*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Product:* {prod['name']}\n"
        f"📊 *Current Stock:* {prod['stock']} available\n"
        f"💰 *Amount Due:* `{exact_ltc_charge} LTC`\n"
        f"🏦 *Send To Address:* (Tap address text box below to copy)\n`{LTC_WALLET}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 _Instructions: Transfer the exact amount shown above using any mobile or desktop hardware crypto wallet. Once sent, click the green verification button below to claim your digital goods instantly._"
    )
    await query.edit_message_text(text=checkout_screen, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[checkout_btn]]))

async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID: return
    if not context.args or len(context.args) < 1: return
    product_key = context.args[0]
    if product_key not in INVENTORY: return
    raw_message = update.message.text
    header_to_remove = f"/add_stock {product_key}"
    pasted_content = raw_message[raw_message.find(header_to_remove) + len(header_to_remove):].strip()
    if not pasted_content: return
    raw_lines = pasted_content.split('\n')
    clean_lines = [line.strip() for line in raw_lines if line.strip()]
    if len(clean_lines) == 0: return
    INVENTORY[product_key]["items"].extend(clean_lines)
    INVENTORY[product_key]["stock"] = len(INVENTORY[product_key]["items"])
    await update.message.reply_text(f"✅ Added {len(clean_lines)} items. Total: {INVENTORY[product_key]['stock']}")

# --- 🌐 WEBHOOK ENDPOINT FOR TELEGRAM ENTRY ROUTING ---
@fastapi_app.post(f"/webhook-{TOKEN}")
async def telegram_webhook(request: Request):
    """Intercepts live JSON entries from Telegram and forces single-thread parsing."""
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, tg_app.bot)
        await tg_app.initialize()
        await tg_app.process_update(update)
    except Exception as e:
        logging.error(f"Webhook tracking execution failure: {e}")
    return {"status": "processed"}

@fastapi_app.get("/")
async def home_route():
    return {"status": "Web Hook Router Online"}

# Automated hook configuration trigger run at launch parameters
async def setup_webhook_on_boot():
    await asyncio.sleep(5)
    try:
        # Pulls down your public web URL parameters dynamically from Render's config mappings
        import os
        render_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}"
        webhook_target = f"{render_url}/webhook-{TOKEN}"
        await tg_app.bot.set_webhook(url=webhook_target)
        logging.info(f"Successfully locked single-instance Web-Hook route: {webhook_target}")
    except Exception as e:
        logging.error(f"Webhook structural setup failure: {e}")

# Launch hook setup task outside main blocker threads
asyncio.ensure_future(setup_webhook_on_boot())
