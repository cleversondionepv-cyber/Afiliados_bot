import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = """
🔥 Bem-vindo ao Canal de Ofertas!

👉 Confira as promoções:
https://s.shopee.com.br/60MJ7Trika
"""
    await update.message.reply_text(mensagem)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

app.run_polling()