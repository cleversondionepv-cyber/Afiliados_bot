import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TOKEN

# Carregar produtos
def carregar_produtos():
    with open("produtos.json", "r", encoding="utf-8") as f:
        return json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔥 Ver Ofertas", callback_data="ofertas")],
        [InlineKeyboardButton("📂 Categorias", callback_data="categorias")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🚀 Bem-vindo ao *Clube de Ofertas Tech*!\n\n"
        "Aqui você encontra os melhores produtos com desconto.\n"
        "Escolha uma opção abaixo:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "ofertas":
        produtos = carregar_produtos()
        mensagem = "🔥 *OFERTAS DISPONÍVEIS:*\n\n"

        for p in produtos:
            mensagem += f"📦 *{p['nome']}*\n💰 {p['preco']}\n🔗 {p['link']}\n\n"

        await query.edit_message_text(mensagem, parse_mode="Markdown")

    elif query.data == "categorias":
        await query.edit_message_text("📂 Em breve teremos categorias organizadas!")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()