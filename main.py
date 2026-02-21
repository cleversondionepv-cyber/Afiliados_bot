import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from config import TOKEN

# Lista de usuários (substituir depois por DB)
usuarios = []

# Carregar produtos
def carregar_produtos():
    with open("produtos.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Função start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id not in usuarios:
        usuarios.append(user_id)

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

# Função de botões
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

# Envio automático
def enviar_ofertas_automaticas(bot):
    produtos = carregar_produtos()
    mensagem = "🔥 *OFERTAS DO DIA:*\n\n"
    for p in produtos:
        mensagem += f"📦 *{p['nome']}*\n💰 {p['preco']}\n🔗 {p['link']}\n\n"

    for user_id in usuarios:
        bot.send_message(chat_id=user_id, text=mensagem, parse_mode="Markdown")

# Função principal
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Scheduler para envio automático diário
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: enviar_ofertas_automaticas(app.bot),trigger='cron', hour=10, minute=2)  # envia a cada 24h
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    main()