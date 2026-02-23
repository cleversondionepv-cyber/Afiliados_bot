import json
import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from apscheduler.schedulers.background import BackgroundScheduler
from config import TOKEN

ADMIN_ID = 7089161817

# ==============================
# BANCO DE DADOS
# ==============================

def criar_tabelas():
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()

    # Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            nome TEXT,
            username TEXT,
            data_inicio TEXT
        )
    """)

    # Tabela de cliques (Mini CRM)
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
# PRODUTOS
# ==============================

def carregar_produtos():
    with open("produtos.json", "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================
# COMANDO /START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    salvar_usuario(user.id, user.first_name, user.username)

    keyboard = [
        [InlineKeyboardButton("🔥 Ver Ofertas", callback_data="ofertas")],
        [InlineKeyboardButton("📂 Categorias", callback_data="categorias")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🚀 Bem-vindo ao *Clube Ofertas exclusicas/Oficial*!\n\n"
        "Aqui você encontra os melhores produtos com desconto.\n"
        "Escolha uma opção abaixo:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


# ==============================
# BOTÕES + MINI CRM
# ==============================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Mostrar produtos
    if query.data == "ofertas":
        produtos = carregar_produtos()

        keyboard = []
        for i, p in enumerate(produtos):
            keyboard.append(
                [InlineKeyboardButton(
                    f"{p['nome']} - {p['preco']}",
                    callback_data=f"produto_{i}"
                )]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🔥 *Escolha uma oferta:*",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    # Categorias
    elif query.data == "categorias":
        await query.edit_message_text("📂 Em breve teremos categorias organizadas!")

    # Clique em produto (registrar no CRM)
    elif query.data.startswith("produto_"):
        user = query.from_user
        index = int(query.data.split("_")[1])
        produtos = carregar_produtos()

        produto = produtos[index]

        registrar_clique(user.id, produto["nome"])

        await query.message.reply_text(
            f"🚀 Você escolheu:\n\n"
            f"📦 {produto['nome']}\n\n"
            f"🔗 Acesse aqui:\n{produto['link']}"
        )


# ==============================
# ENVIO AUTOMÁTICO 30 MIN
# ==============================

produto_index = 0

def enviar_proximo_produto(bot):
    global produto_index

    print("🔥 Scheduler disparou!")
    usuarios = buscar_usuarios()
    produtos = carregar_produtos()

    if not produtos:
        return

    if produto_index >= len(produtos):
        produto_index = 0

    produto = produtos[produto_index]

    mensagem = (
        f"🔥 *OFERTA IMPERDÍVEL!*\n\n"
        f"📦 *{produto['nome']}*\n"
        f"💰 {produto['preco']}\n\n"
        f"👇 Clique no botão abaixo para aproveitar!"
    )

    keyboard = [
        [InlineKeyboardButton("🔥 Ver Oferta", callback_data=f"produto_{produto_index}")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    for user in usuarios:
        try:
            bot.send_message(
                chat_id=user[0],
                text=mensagem,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except:
            pass

    produto_index += 1

# ==============================
# PAINEL ADMIN
# ==============================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ Você não tem permissão para usar este comando.")
        return

    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()

    # Total usuários
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cursor.fetchone()[0]

    # Total cliques
    cursor.execute("SELECT COUNT(*) FROM cliques")
    total_cliques = cursor.fetchone()[0]

    # Produto mais clicado
    cursor.execute("""
        SELECT produto, COUNT(*) as total
        FROM cliques
        GROUP BY produto
        ORDER BY total DESC
        LIMIT 1
    """)
    resultado = cursor.fetchone()

    if resultado:
        produto_top = resultado[0]
        total_top = resultado[1]
    else:
        produto_top = "Nenhum ainda"
        total_top = 0

    conn.close()

    media = 0
    if total_usuarios > 0:
        media = round(total_cliques / total_usuarios, 2)

    mensagem = (
        f"📊 *PAINEL ADMIN*\n\n"
        f"👥 Total de usuários: {total_usuarios}\n"
        f"🖱 Total de cliques: {total_cliques}\n"
        f"📈 Média cliques/usuário: {media}\n\n"
        f"🏆 Produto campeão:\n"
        f"{produto_top} ({total_top} cliques)"
    )

    await update.message.reply_text(mensagem, parse_mode="Markdown")

# ==============================
# MAIN
# ==============================

def main():
    criar_tabelas()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: enviar_proximo_produto(app.bot),
        trigger="interval",
        minutes=1
    )
    scheduler.start()

    print("🤖 Bot rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()