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

def carregar_produtos():
    return [
        {
            "nome": "Mouse Gamer RGB",
            "preco": "R$ 89,90",
            "link": "https://exemplo.com/mouse"
        },
        {
            "nome": "Teclado Mecânico",
            "preco": "R$ 199,90",
            "link": "https://exemplo.com/teclado"
        }
    ]


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


# ==============================
# START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    salvar_usuario(user.id, user.first_name, user.username)

    keyboard = [
        [InlineKeyboardButton("🔥 Ver Ofertas", callback_data="ofertas")]
    ]

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