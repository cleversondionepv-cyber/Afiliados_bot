import sqlite3
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import TOKEN

# 🔐 SEU ID DE ADMIN
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
    cursor.execute("INSERT OR IGNORE INTO usuarios (id, first_name, username) VALUES (?, ?, ?)",
                   (user_id, first_name, username))
    conn.commit()
    conn.close()


def registrar_clique(user_id, produto):
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO cliques (user_id, produto) VALUES (?, ?)", (user_id, produto))
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
# PRODUTOS (PLANILHA GOOGLE SHEETS)
# ==============================

def carregar_produtos():
    # Configurações da API do Google Sheets
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_url("SUA_URL_AQUI")  # substitua com o link da sua planilha
    worksheet = sheet.sheet1  # primeira aba

    data = worksheet.get_all_records()
    produtos = []

    for row in data:
        produtos.append({
            "nome": row.get("nome", ""),
            "preco": row.get("preco", ""),
            "link": row.get("link", "")
        })

    return produtos

# ==============================
# MENU PRINCIPAL
# ==============================

async def menu_principal(chat_id, context, is_admin=False):
    keyboard = [[InlineKeyboardButton("🔥 Ver Ofertas", callback_data="ofertas")]]
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ Painel Admin", callback_data="admin")])

    await context.bot.send_message(
        chat_id=chat_id,
        text="🚀 Menu Principal:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==============================
# /START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    salvar_usuario(user.id, user.first_name, user.username)
    await menu_principal(user.id, context, is_admin=(user.id == ADMIN_ID))

# ==============================
# BOTÕES
# ==============================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    produtos = carregar_produtos()

    # 🔹 Menu Admin
    if query.data == "admin":
        keyboard = [
            [InlineKeyboardButton("📊 Total Usuários", callback_data="admin_users")],
            [InlineKeyboardButton("📈 Total Cliques", callback_data="admin_clicks")],
            [InlineKeyboardButton("📣 Enviar Ofertas Agora", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Voltar", callback_data="voltar")]
        ]
        await query.edit_message_text("⚙️ Painel Admin:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # 🔹 Admin: usuários
    elif query.data == "admin_users":
        await query.edit_message_text(f"📊 Total de usuários: {contar_usuarios()}")

    # 🔹 Admin: cliques
    elif query.data == "admin_clicks":
        await query.edit_message_text(f"📈 Total de cliques: {contar_cliques()}")

    # 🔹 Admin: envio manual
    elif query.data == "admin_broadcast":
        for user in range(contar_usuarios()):
            await envio_automatico_loop(context.application)
        await query.edit_message_text("📣 Ofertas enviadas manualmente!")

    # 🔹 Voltar ao menu
    elif query.data == "voltar":
        await menu_principal(query.from_user.id, context, is_admin=(query.from_user.id == ADMIN_ID))

    # 🔹 Ver ofertas
    elif query.data == "ofertas":
        keyboard = []
        for i, p in enumerate(produtos):
            keyboard.append([InlineKeyboardButton(f"{p['nome']} - {p['preco']}", callback_data=f"produto_{i}")])
        await query.edit_message_text("🔥 Escolha uma oferta:", reply_markup=InlineKeyboardMarkup(keyboard))

    # 🔹 Produto selecionado
    elif query.data.startswith("produto_"):
        index = int(query.data.split("_")[1])
        produto = produtos[index]
        registrar_clique(query.from_user.id, produto["nome"])
        await query.message.reply_text(f"📦 {produto['nome']}\n💰 {produto['preco']}\n🔗 {produto['link']}")
        await menu_principal(query.from_user.id, context, is_admin=(query.from_user.id == ADMIN_ID))

# ==============================
# ENVIO AUTOMÁTICO
# ==============================

async def envio_automatico_loop(application):
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
                await asyncio.sleep(1)  # para não floodar
            except:
                pass

# ==============================
# MAIN
# ==============================

async def post_init(application):
    await application.bot.delete_webhook(drop_pending_updates=True)
    print("Bot iniciado e webhook limpo.")

def main():
    criar_tabelas()
    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Bot rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()