import logging
import json
from google.oauth2.service_account import Credentials
import os
import asyncio
import gspread
from google.oauth2.service_account import Credentials
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
SPREADSHEET_ID = "1speaE2hamb2j6yrKLMMOmo-k98FJZP7FG-_nBefVTDI"
SHEET_NAME = "Afiliados"

ADMIN_ID = 7089161817  # coloque seu ID aqui

# ==============================
# LOG
# ==============================

logging.basicConfig(level=logging.INFO)

# ==============================
# GOOGLE SHEETS
# ==============================

import os
import json
import gspread
from google.oauth2.service_account import Credentials

def conectar_planilha():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    info = json.loads(creds_json)

    creds = Credentials.from_service_account_info(info, scopes=scope)
    client = gspread.authorize(creds)

    planilha = client.open("Afiliados")
    aba = planilha.sheet1  # ou .worksheet("Nome da Aba")

    return aba

def buscar_produtos():
  aba = conectar_planilha() 
  dados = aba.get_all_records() 
  return dados

def salvar_usuario(user_id):
    aba = conectar_planilha()

    try:
        usuarios_sheet = aba.spreadsheet.worksheet("Usuarios")
    except:
        usuarios_sheet = aba.spreadsheet.add_worksheet(title="Usuarios", rows="1000", cols="1")
        usuarios_sheet.append_row(["user_id"])

    lista = usuarios_sheet.col_values(1)

    if str(user_id) not in lista:
        usuarios_sheet.append_row([str(user_id)])


def buscar_usuarios():
    aba = conectar_planilha()

    try:
        usuarios_sheet = aba.spreadsheet.worksheet("Usuarios")
        return usuarios_sheet.col_values(1)[1:]  # remove cabeçalho
    except:
        return []

# ==============================
# START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    salvar_usuario(user_id)

    await update.message.reply_text(
        "🚀 Bem-vindo! Você agora receberá ofertas exclusivas!"
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
              produto = {k.strip(): v for k, v in produto.items()}

        mensagem = f"""
        🔥 {produto.get('Nome', 'Produto')}
        💰 {produto.get('Preço', '')}
        🛒 {produto.get('Link', '')}
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

from datetime import datetime

async def envio_automatico(context: ContextTypes.DEFAULT_TYPE):

    agora = datetime.now()
    hora = agora.hour

    # horário permitido: 08h até 20h
    if hora < 8 or hora >= 20:
        print("Fora do horário comercial")
        return

    produtos = buscar_produtos()

    if not produtos:
        return

    # controle de índice
    if "indice_produto" not in context.bot_data:
        context.bot_data["indice_produto"] = 0

    indice = context.bot_data["indice_produto"]

    produto = produtos[indice]
    produto = {k.strip(): v for k, v in produto.items()}

    nome = produto.get("Nome", "Produto")
    preco = produto.get("Preço", "")
    link = produto.get("Link", "")

    mensagem = f"""
🔥 {nome}
💰 {preco}
🛒 {link}
    """

    usuarios = buscar_usuarios()

    for user_id in usuarios:
        try:
            await context.bot.send_message(chat_id=int(user_id), text=mensagem)
        except:
            pass

    context.bot_data["indice_produto"] = (indice + 1) % len(produtos)
# ==============================
# MAIN
# ==============================

async def limpar_conexoes_antigas(app):
    await app.bot.delete_webhook(drop_pending_updates=True)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_respostas))

    app.job_queue.run_repeating(envio_automatico, interval=600, first=5)

    print("BOT RODANDO...")

    # força matar conexões antigas
    app.post_init = limpar_conexoes_antigas

    app.run_polling(drop_pending_updates=True)
    # 🔥 força limpar webhook e conexões antigas
   

if __name__ == "__main__":
    main()