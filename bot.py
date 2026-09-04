import logging
import random
import string
import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== ТОКЕН ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан!")

ALLOWED_USERS = [1656724625, 1962674968]

logging.basicConfig(level=logging.INFO)

# ========== ФУНКЦИИ ГЕНЕРАЦИИ ПАРОЛЯ ==========
def generate_password(length: int, use_letters: bool, use_digits: bool) -> str:
    chars = ""
    if use_letters:
        chars += string.ascii_letters
    if use_digits:
        chars += string.digits
    if not chars:
        chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_main_menu_markup(selected_type: str = None) -> InlineKeyboardMarkup:
    letters_btn = "🔤 Только буквы" + (" ✅" if selected_type == "letters" else "")
    digits_btn = "🔢 Только цифры" + (" ✅" if selected_type == "digits" else "")
    both_btn = "🔤➕🔢 Буквы и цифры" + (" ✅" if selected_type == "both" else "")
    keyboard = [
        [InlineKeyboardButton(letters_btn, callback_data="letters"), InlineKeyboardButton(digits_btn, callback_data="digits")],
        [InlineKeyboardButton(both_btn, callback_data="both")],
        [InlineKeyboardButton("⚙️ Длина 8", callback_data="len_8"), InlineKeyboardButton("⚙️ Длина 12", callback_data="len_12"), InlineKeyboardButton("⚙️ Длина 16", callback_data="len_16")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        if not edit:
            await update.message.reply_text("⛔ Доступ запрещён.")
        return
    selected = context.user_data.get('selected_type', None)
    markup = get_main_menu_markup(selected)
    text = "🔐 **Главное меню**\n\nВыбери тип и длину пароля.\nТип можно менять."
    if edit:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context, edit=False)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await query.edit_message_text("⛔ Доступ запрещён.")
        return
    data = query.data

    if data in ("letters", "digits", "both"):
        context.user_data['selected_type'] = data
        await show_main_menu(update, context, edit=True)
    elif data.startswith("len_"):
        length = int(data.split("_")[1])
        context.user_data['length'] = length
        selected_type = context.user_data.get('selected_type', 'both')
        use_letters = selected_type in ('letters', 'both')
        use_digits = selected_type in ('digits', 'both')
        password = generate_password(length, use_letters, use_digits)
        keyboard = [
            [InlineKeyboardButton("🔄 Новый пароль", callback_data="new")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        type_text = {'letters':'буквы','digits':'цифры','both':'буквы и цифры'}.get(selected_type,'буквы и цифры')
        await query.edit_message_text(
            f"🔑 **Ваш пароль** (длина {length}):\n\n`{password}`\n\nТип: {type_text}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    elif data == "new":
        length = context.user_data.get('length', 12)
        selected_type = context.user_data.get('selected_type', 'both')
        use_letters = selected_type in ('letters', 'both')
        use_digits = selected_type in ('digits', 'both')
        password = generate_password(length, use_letters, use_digits)
        keyboard = [
            [InlineKeyboardButton("🔄 Новый пароль", callback_data="new")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        type_text = {'letters':'буквы','digits':'цифры','both':'буквы и цифры'}.get(selected_type,'буквы и цифры')
        await query.edit_message_text(
            f"🔑 **Ваш пароль** (длина {length}):\n\n`{password}`\n\nТип: {type_text}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    elif data == "back":
        await show_main_menu(update, context, edit=True)

# ========== ЗАПУСК БОТА В ОТДЕЛЬНОМ ПОТОКЕ ==========
def run_bot():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Бот запущен...")
    app.run_polling()

# ========== FLASK ДЛЯ RENDER ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

@app.route('/health')
def health():
    return "OK", 200

if __name__ == "__main__":
    # Запускаем бота в фоновом потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    # Запускаем Flask-сервер, чтобы Render не ругался
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
