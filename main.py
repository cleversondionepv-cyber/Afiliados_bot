import sqlite3
import asyncio
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
            first_name TEXT,
            username TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cliques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            produto TEXT
        )
    """)

    conn.commit()
    conn.close()


def salvar_usuario(user_id, first_name, username):
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO usuarios (id, first_name, username)
        VALUES (?, ?, ?)
    """, (user_id, first_name, username))

    conn.commit()
    conn.close()


def registrar_clique(user_id, produto):
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO cliques (user_id, produto)
        VALUES (?, ?)
    """, (user_id, produto))

    conn.commit()
    conn.close()


def contar_usuarios():
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total = cursor.fetchone()[0]
    conn.close()
    return total


def contar_cliques():
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cliques")
    total = cursor.fetchone()[0]
    conn.close()
    return total


# ==============================
# PRODUTOS (SIMULAÇÃO)
# ==============================

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
# ENVIO AUTOMÁTICO
# ==============================

async def envio_automatico_loop(application):
    print("🔥 Enviando ofertas automáticas...")

    produtos = carregar_produtos()

    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios")
    usuarios = cursor.fetchall()
    conn.close()

    for user in usuarios:
        for produto in produtos:
            try:
                await application.bot.send_message(
                    chat_id=user[0],
                    text=f"📦 {produto['nome']}\n💰 {produto['preco']}\n🔗 {produto['link']}"
                )
                await asyncio.sleep(1)
            except:
                pass


async def envio_automatico_job(context):
    await envio_automatico_loop(context.application)

async def menu_principal(chat_id, context, is_admin=False):
    keyboard = [
        [InlineKeyboardButton("🔥 Ver Ofertas", callback_data="ofertas")]
    ]

    if is_admin:
        keyboard.append(
            [InlineKeyboardButton("⚙️ Painel Admin", callback_data="admin")]
        )

    await context.bot.send_message(
        chat_id=chat_id,
        text="🚀 Menu Principal:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==============================
# START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    salvar_usuario(user.id, user.first_name, user.username)

    await menu_principal(
        chat_id=user.id,
        context=context,
        is_admin=(user.id == ADMIN_ID)
    )

# ==============================
# BOTÕES
# ==============================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    produtos = carregar_produtos()

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
        await menu_principal(
        chat_id=query.from_user.id,
        context=context,
        is_admin=(query.from_user.id == ADMIN_ID)
    )

    elif query.data == "admin":
        keyboard = [
            [InlineKeyboardButton("📊 Total Usuários", callback_data="admin_users")],
            [InlineKeyboardButton("📈 Total Cliques", callback_data="admin_clicks")],
            [InlineKeyboardButton("📣 Enviar Ofertas Agora", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Voltar", callback_data="voltar")]
        ]

        await query.edit_message_text(
            "⚙️ Painel Admin:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "admin_users":
        total = contar_usuarios()
        await query.edit_message_text(f"📊 Total de usuários: {total}")

    elif query.data == "admin_clicks":
        total = contar_cliques()
        await query.edit_message_text(f"📈 Total de cliques: {total}")

    elif query.data == "admin_broadcast":
        await envio_automatico_loop(context.application)
        await query.edit_message_text("📣 Ofertas enviadas manualmente!")

    elif query.data == "voltar":
        keyboard = [
            [InlineKeyboardButton("🔥 Ver Ofertas", callback_data="ofertas")]
        ]

        if query.from_user.id == ADMIN_ID:
            keyboard.append(
                [InlineKeyboardButton("⚙️ Painel Admin", callback_data="admin")]
            )

        await query.edit_message_text(
            "🚀 Menu Principal:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ==============================
# MAIN
# ==============================

async def post_init(application):
    print("Limpando conexões antigas...")
    await application.bot.delete_webhook(drop_pending_updates=True)

    application.job_queue.run_repeating(
        envio_automatico_job,
        interval=1800,
        first=10
    )


def main():
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot rodando...")

    app.run_polling()


if __name__ == "__main__":
    criar_tabelas()
    main()