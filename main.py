import json
import sqlite3
import asyncio
import requests
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import TOKEN

ADMIN_ID = 7089161817

# ==============================
# BANCO DE DADOS
# ==============================

def criar_tabelas():
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            nome TEXT,
            username TEXT,
            data_inicio TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cliques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            produto TEXT,
            data TEXT
        )
    """)

    conn.commit()
    conn.close()


def salvar_usuario(user_id, nome, username):
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO usuarios (id, nome, username, data_inicio) VALUES (?, ?, ?, ?)",
            (user_id, nome, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )

    conn.commit()
    conn.close()


def registrar_clique(user_id, produto_nome):
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO cliques (user_id, produto, data) VALUES (?, ?, ?)",
        (user_id, produto_nome, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    conn.commit()
    conn.close()


def buscar_usuarios():
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios")
    usuarios = cursor.fetchall()
    conn.close()
    return usuarios


# ==============================
# GOOGLE SHEETS
# ==============================

def carregar_produtos():
    try:
        url = "https://docs.google.com/spreadsheets/d/1speaE2hamb2j6yrKLMMOmo-k98FJZP7FG-_nBefVTDI/gviz/tq?tqx=out:json"
        response = requests.get(url)
        text = response.text

        json_data = json.loads(text.split("(", 1)[1].rstrip(");"))
        rows = json_data["table"]["rows"]

        produtos = []

        for r in rows:
            cells = r.get("c", [])

            nome = cells[0]["v"] if len(cells) > 0 and cells[0] else ""
            preco = cells[1]["v"] if len(cells) > 1 and cells[1] else ""
            link = cells[2]["v"] if len(cells) > 2 and cells[2] else ""
            plataforma = cells[3]["v"] if len(cells) > 3 and cells[3] else ""
            categoria = cells[4]["v"] if len(cells) > 4 and cells[4] else ""

            if nome and link:
                produtos.append({
                    "nome": nome,
                    "preco": preco,
                    "link": link,
                    "plataforma": plataforma,
                    "categoria": categoria
                })

        print(f"{len(produtos)} produtos carregados da planilha")
        return produtos

    except Exception as e:
        print("Erro ao carregar planilha:", e)
        return []


# ==============================
# /START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    salvar_usuario(user.id, user.first_name, user.username)

    keyboard = [
        [InlineKeyboardButton("🔥 Ver Ofertas", callback_data="ofertas")]
    ]

    # Se for admin, adiciona botão admin
    if user.id == ADMIN_ID:
        keyboard.append(
            [InlineKeyboardButton("⚙️ Painel Admin", callback_data="admin")]
        )

    await update.message.reply_text(
        "🚀 Bem-vindo ao Clube de Ofertas Tech!\n\nEscolha uma opção:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==============================
# BOTÕES
# ==============================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    produtos = carregar_produtos()

    if query.data == "admin":
        await query.edit_message_text(
            "⚙️ Painel Admin\n\n"
            "📊 1 - Ver total de usuários\n"
            "📈 2 - Ver total de cliques\n",
        )
        return

    if query.data == "ofertas":
        keyboard = []
        for i, p in enumerate(produtos):
            keyboard.append(
                [InlineKeyboardButton(
                    f"{p['nome']} - {p['preco']}",
                    callback_data=f"produto_{i}"
                )]
            )

        await query.edit_message_text(
            "🔥 Escolha uma oferta:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("produto_"):
        index = int(query.data.split("_")[1])
        produto = produtos[index]

        registrar_clique(query.from_user.id, produto["nome"])

        await query.message.reply_text(
            f"📦 {produto['nome']}\n\n💰 {produto['preco']}\n\n🔗 {produto['link']}"
        )


# ==============================
# ENVIO AUTOMÁTICO
# ==============================

produto_index = 0

async def envio_automatico_loop(app):
    global produto_index

    while True:
        try:
            print("🔥 Loop automático rodando...")

            usuarios = buscar_usuarios()
            produtos = carregar_produtos()

            if produtos and usuarios:

                if produto_index >= len(produtos):
                    produto_index = 0

                produto = produtos[produto_index]

                mensagem = (
                    f"🔥 OFERTA IMPERDÍVEL!\n\n"
                    f"📦 {produto['nome']}\n"
                    f"💰 {produto['preco']}\n\n"
                    f"🔗 {produto['link']}"
                )

                for u in usuarios:
                    await app.bot.send_message(
                        chat_id=u[0],
                        text=mensagem
                    )

                produto_index += 1

        except Exception as e:
            print("Erro no loop automático:", e)

        await asyncio.sleep(1800)# 30 minutos
       

# ==============================
# MAIN
# ==============================

async def post_init(application):
    print("Limpando conexões antigas...")
    await application.bot.delete_webhook(drop_pending_updates=True)

    print("Iniciando envio automático...")
    application.create_task(envio_automatico_loop(application))

def main():
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot rodando...")

    app.run_polling()


if __name__ == "__main__":
    criar_tabelas()
    main()