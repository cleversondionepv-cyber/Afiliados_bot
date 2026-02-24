import logging
import os
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==============================
# CONFIGURAÇÕES
# ==============================

TOKEN = os.getenv("TOKEN")
SPREADSHEET_ID = "1speaE2hamb2j6yrKLMMOmo-k98FJZP7FG-_nBefVTDI/edit?usp=sharing"
SHEET_NAME = "Afiliados"

ADMIN_ID = 7089161817  # coloque seu ID aqui

# ==============================
# LOG
# ==============================

logging.basicConfig(level=logging.INFO)

# ==============================
# GOOGLE SHEETS
# ==============================

def conectar_planilha():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = eval(os.getenv("GOOGLE_CREDENTIALS"))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    planilha = client.open_by_key(SPREADSHEET_ID)
    aba = planilha.worksheet(SHEET_NAME)
    return aba


def buscar_produtos():
    aba = conectar_planilha()
    dados = aba.get_all_records()
    return dados


# ==============================
# START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 Bem-vindo! Em breve você receberá ofertas exclusivas!"
    )


# ==============================
# MENU ADMIN
# ==============================

def menu_admin():
    teclado = [
        ["📤 Enviar Produto Agora"],
        ["📊 Total Produtos"],
        ["🔙 Sair"],
    ]
    return ReplyKeyboardMarkup(teclado, resize_keyboard=True)


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "🔧 Painel Admin",
        reply_markup=menu_admin(),
    )


# ==============================
# RESPOSTAS ADMIN
# ==============================

async def admin_respostas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    texto = update.message.text

    if texto == "📤 Enviar Produto Agora":
        produtos = buscar_produtos()

        if not produtos:
            await update.message.reply_text("Nenhum produto encontrado.")
        else:
            produto = produtos[0]

            mensagem = f"""
🔥 {produto['Nome']}
💰 {produto['Preco']}
🛒 {produto['Link']}
            """

            await update.message.reply_text(mensagem)

        # 🔁 RETORNA PARA MENU
        await update.message.reply_text(
            "Escolha uma opção:",
            reply_markup=menu_admin(),
        )

    elif texto == "📊 Total Produtos":
        produtos = buscar_produtos()
        await update.message.reply_text(
            f"📦 Total de produtos na planilha: {len(produtos)}",
            reply_markup=menu_admin(),
        )

    elif texto == "🔙 Sair":
        await update.message.reply_text("Saindo do painel admin.")


# ==============================
# ENVIO AUTOMÁTICO
# ==============================

async def envio_automatico(context: ContextTypes.DEFAULT_TYPE):
    produtos = buscar_produtos()

    if not produtos:
        return

    produto = produtos[0]

    mensagem = f"""
🔥 {produto['Nome']}
💰 {produto['Preco']}
🛒 {produto['Link']}
    """

    # Aqui você pode colocar ID de grupo ou canal
    await context.bot.send_message(chat_id=ADMIN_ID, text=mensagem)


# ==============================
# MAIN
# ==============================

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_respostas))

    # ⏱️ Agendador (a cada 1 hora)
    app.job_queue.run_repeating(envio_automatico, interval=60, first=10)

    print("BOT RODANDO...")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())