import os
import re
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ==========================================
# CONFIGURAÇÃO
# ==========================================

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# ==========================================
# COMANDO /START
# ==========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "💜Bem-vindo a Mavis Prime Bot!\n\n"
        "Envie um link da Shopee ou Mercado Livre "
        "para gerar sua oferta. 🛍️"
    )


# ==========================================
# COMANDO /HELP
# ==========================================

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "📌 Como usar o Mavis Prime:\n\n"
        "1️⃣ Copie o link do produto.\n"
        "2️⃣ Envie o link aqui.\n"
        "3️⃣ O bot prepara a oferta com a imagem.\n\n"
        "🛒 Lojas aceitas:\n"
        "• Shopee\n"
        "• Mercado Livre"
    )


# ==========================================
# IDENTIFICAR A LOJA
# ==========================================

def identificar_loja(link):

    link = link.lower()

    if "shopee" in link:
        return "Shopee"

    if "mercadolivre" in link or "mercadolibre" in link:
        return "Mercado Livre"

    return None


# ==========================================
# GERAR TEXTO DA OFERTA
# ==========================================

def gerar_oferta(
    nome,
    preco_antigo,
    preco_atual,
    cupom,
    link,
    loja
):

    mensagem = (
        "🔥 *OFERTA RELÂMPAGO*\n\n"
        f"*{nome}*\n\n"
        f"De: ~{preco_antigo}~\n"
        f"*POR: {preco_atual}* ✅\n\n"
        f"🎟️ Use o cupom: *{cupom}*\n\n"
        f"🔗 *Compre aqui:*\n"
        f"{link}\n\n"
    
    )

    return mensagem


# ==========================================
# RECEBER LINK
# ==========================================

async def receber_mensagem(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    texto = update.message.text

    if not texto:
        return

    # Procurar link dentro da mensagem
    links = re.findall(
        r"https?://\S+",
        texto
    )

    if not links:

        await update.message.reply_text(
            "❌ Não encontrei nenhum link.\n\n"
            "Envie um link da Shopee ou Mercado Livre."
        )

        return

    link = links[0]

    # Identificar loja
    loja = identificar_loja(link)

    if not loja:

        await update.message.reply_text(
            "⚠️ Esse link não parece ser da "
            "Shopee ou do Mercado Livre."
        )

        return

    await update.message.reply_text(
        "⏳ Preparando sua oferta..."
    )

    # ======================================
    # DADOS TEMPORÁRIOS
    # ======================================
    #
    # Essa parte será substituída depois
    # pela captura automática dos dados.
    #



    # ======================================
    # MONTAR OFERTA
    # ======================================

    oferta = gerar_oferta(
        nome=nome,
        preco_antigo=preco_antigo,
        preco_atual=preco_atual,
        cupom=cupom,
        link=link,
        loja=loja
    )


    # ======================================
    # ENVIAR OFERTA
    # ======================================

    await update.message.reply_text(
        oferta,
        parse_mode="Markdown",
        disable_web_page_preview=False
    )


# ==========================================
# INICIAR BOT
# ==========================================

def main():

    if not TOKEN:

        raise RuntimeError(
            "BOT_TOKEN não foi configurado no Railway."
        )

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # Comandos
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    # Mensagens
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receber_mensagem
        )
    )

    print("🔥 Mavis Prime iniciado!")

    app.run_polling()


# ==========================================
# EXECUTAR
# ==========================================

if __name__ == "__main__":
    main()