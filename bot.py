import logging
import asyncio
import requests
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = "8666468661:AAHzXsyHorv0LDQQ7S11mLEiAcCeM2XJUbI"
LTC_WALLET = "ltc1qx3ff59204wy3pt0qygzyh3c7nw3v0d0vwcqzes"
OWNER_ID = 8936045536
OWNER_USERNAME = "https://t.me/enrollfo"
INVENTORY = {
"gfx_pack": {"name": "💳 fulls", "price_usd": 5.00, "stock": 0, "items": []},
"discord_vip": {"name": "🍔 food logs", "price_usd": 10.00, "stock": 0, "items": []}
}
class HealthCheckHandler(BaseHTTPRequestHandler):
def do_GET(self):
self.send_response(200)
self.send_header("Content-type", "text/html")
self.end_headers()
self.wfile.write(b"Live Service Operational")
def run_health_server():
server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
server.serve_forever()
def get_ltc_price():
try:
url = "binance.com"
response = requests.get(url, timeout=4)
if response.status_code == 200:
data = response.json()
if "price" in data:
return float(data["price"])
except Exception:
pass
try:
backup_url = "coingecko.com"
response = requests.get(backup_url, timeout=4)
if response.status_code == 200:
data = response.json()
if "litecoin" in data and "usd" in data["litecoin"]:
return float(data["litecoin"]["usd"])
except Exception:
pass
return 95.00
def check_live_blockchain(wallet, target_amount_ltc):
try:
clean_wallet = wallet.strip().lower()
url = f"litecoinspace.org{clean_wallet}/mempool"
response = requests.get(url, timeout=10)
if response.status_code != 200:
return False
transactions = response.json()
if not isinstance(transactions, list):
return False
for tx in transactions:
for vout in tx.get("vout", []):
if str(vout.get("scriptpubkey_address")).strip().lower() == clean_wallet:
amount_in_satoshis = vout.get("value", 0)
amount_in_ltc = amount_in_satoshis / 100000000
logging.info(f"Detected incoming live mainnet tx: {amount_in_ltc} LTC")
if round(amount_in_ltc, 4) == round(target_amount_ltc, 4):
return True
return False
except Exception as e:
logging.error(f"Live Blockchain Tracking Fault: {e}")
return False
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
await asyncio.sleep(delay)
try:
await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
logging.info(f"Successfully auto-deleted message {message_id} in chat {chat_id}")
except Exception as e:
logging.error(f"Failed to auto-delete message: {e}")
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
gfx_label = f"{INVENTORY['gfx_pack']['name']} (${INVENTORY['gfx_pack']['price_usd']:.2f}) [Stock: {INVENTORY['gfx_pack']['stock']}]"
vip_label = f"{INVENTORY['discord_vip']['name']} (${INVENTORY['discord_vip']['price_usd']:.2f}) [Stock: {INVENTORY['discord_vip']['stock']}]"
keyboard = [[InlineKeyboardButton(gfx_label, callback_data="buy_gfx")], [InlineKeyboardButton(vip_label, callback_data="buy_vip")]]
await update.message.reply_text("⚡️ LITECOIN LIVE PRODUCTION STOREFRONT\n\nSelect a digital product asset below to purchase:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
async def handle_shop_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
if query.data.startswith("verify_"):
, prod_id, exact_ltc_charge = query.data.split("")
exact_ltc_charge = float(exact_ltc_charge)
product = INVENTORY[prod_id]
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
await query.edit_message_text(text=f"🔄 BLOCKCHAIN VERIFICATION IN PROGRESS\n\n{frame}", parse_mode="Markdown")
await asyncio.sleep(0.6)
if check_live_blockchain(LTC_WALLET, exact_ltc_charge):
delivered_item = product["items"].pop(0)
product["stock"] = len(product["items"])
success_animation = [
"📭 [■■■■■■■■■■] 100% • Processing Order...",
"🟢 Verified! Dispensing structured keys...",
"✨ 🔘 [Allocating secure asset link]...",
"✨ 🟢 [Allocating secure asset link]..."
]
for frame in success_animation:
await query.edit_message_text(text=f"⚙️ TRANSACTION DETECTED\n\n{frame}", parse_mode="Markdown")
await asyncio.sleep(0.5)
delivery_payload = (
f"✨ TRANSACTION CONFIRMED! ✨\n\n"
f"🎉 Thank you for your purchase!\n"
f"💵 Verified Hash Volume: {exact_ltc_charge} LTC\n\n"
f"📦 YOUR DELIVERED PRODUCT CONTENT: \n"
f"{delivered_item}\n\n"
f"📊 Current Stock Remaining: {product['stock']} items left"
)
await query.edit_message_text(text=delivery_payload, parse_mode="Markdown")
asyncio.create_task(delete_message_after_delay(context, query.message.chat_id, query.message.message_id, 180))
return
else:
retry_btn = InlineKeyboardButton("🟢 Confirm Payment Again", callback_data=f"verify_{prod_id}{exact_ltc_charge}")
failed_screen = (
f"❌ PAYMENT NOT COMPLETE\n\n"
f"⚠️ The loading verification reached 100% but no matching transaction of {exact_ltc_charge} LTC was detected on the live ledger.\n\n"
f"If you already sent the transfer from your wallet, allow up to 60 seconds for network propagation before attempting manual verification again.\n\n"
f"⚠️ Not working? Contact Support"
)
await query.edit_message_text(text=failed_screen, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[retry_btn]]))
asyncio.create_task(delete_message_after_delay(context, query.message.chat_id, query.message.message_id, 180))
return
prod_id = "gfx_pack" if "gfx" in query.data else "discord_vip"
product = INVENTORY[prod_id]
if product["stock"] <= 0:
await query.edit_message_text("❌ This product asset is currently completely out of stock!")
return
current_market_rate = get_ltc_price()
base_ltc_needed = product["price_usd"] / current_market_rate
unique_modifier = (query.from_user.id % 1000) / 100000
exact_ltc_charge = round(base_ltc_needed + unique_modifier, 5)
checkout_btn = InlineKeyboardButton("🟢 Confirm Payment", callback_data=f"verify{prod_id}_{exact_ltc_charge}")
checkout_screen = (
f"⚙️ REAL LITECOIN INVOICE GENERATED\n\n"
f"📦 Product: {product['name']}\n"
f"📊 Current Stock: {product['stock']} available\n"
f"💰 Amount Due: {exact_ltc_charge} LTC\n"
f"🏦 Send To Address: (Tap address text box below to copy)\n{LTC_WALLET}\n\n"
f"💡 Instructions: Transfer the exact amount shown above using any mobile or desktop hardware crypto wallet. Once sent, click the green verification button below to claim your digital goods instantly.


"
)
await query.edit_message_text(text=checkout_screen, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[checkout_btn]]))
async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.effective_user.id
if user_id != OWNER_ID:
await update.message.reply_text("❌ Permission Denied. Restocking commands are private to the bot owner.")
return
if len(context.args) < 1:
await update.message.reply_text("⚠️ Usage: /add_stock [gfx_pack OR discord_vip] [paste item lines]", parse_mode="Markdown")
return
product_key = context.args[0]
if product_key not in INVENTORY:
await update.message.reply_text("❌ Error: Invalid key pattern specified. Use gfx_pack or discord_vip.")
return
raw_message = update.message.text
header_to_remove = f"/add_stock {product_key}"
pasted_content = raw_message[raw_message.find(header_to_remove) + len(header_to_remove):].strip()
if not pasted_content:
await update.message.reply_text("⚠️ Error: You didn't paste any item data inputs!")
return
raw_lines = pasted_content.split('\n')
clean_lines = [line.strip() for line in raw_lines if line.strip()]
added_count = len(clean_lines)
if added_count == 0:
await update.message.reply_text("⚠️ Error: No valid item configurations found inside your message input block.")
return
INVENTORY[product_key]["items"].extend(clean_lines)
INVENTORY[product_key]["stock"] = len(INVENTORY[product_key]["items"])
await update.message.reply_text(f"✅ STRUCTURED STOCK DEPOSITED!\n\n📦 Product Target:{INVENTORY[product_key]['name']}\n📥 Unique Lines Added: {added_count} items\n📊 New Live Stock Level: {INVENTORY[product_key]['stock']} available", parse_mode="Markdown")
def main():
threading.Thread(target=run_health_server, daemon=True).start()
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_shop_buttons))
app.add_handler(CommandHandler("add_stock", add_stock))
print("Production Mainnet shop bot is successfully running online...")
app.run_polling()
if name == 'main':
main()
