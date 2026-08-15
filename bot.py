import os
import logging
import re

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIGURAÇÃO
# =========================

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# =========================
# MENSAGEM DA OFERTA
# =========================

def criar_oferta(link):
    gatilho = "OFERTA DO DIA⚡️"
    nome = "Shopee Brasil | Ofertas incríveis. Melhores preços do mercado"
    pa = "Confira o preço no produto"
    preco = "Confira o preço no produto"
    cp = "Consulte os cupons disponíveis"

    return f"""*{gatilho}*

🛍️ _{nome}_

De: ~{pa}~
*POOR: {preco}* 🔥🔥

🎟️ *{cp}*

🔗 Compre aqui: {link}

‼️ _Essa oferta pode acabar a qualquer momento_"""


# =========================
# RECEBER LINK
# =========================

async def receber_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    texto = update.message.text.strip()

    # Procura o primeiro link enviado
    match = re.search(r"https?://\S+", texto)

    if not match:
        await update.message.reply_text(
            "⚠️ Envie um link da Shopee."
        )
        return

    link = match.group(0).rstrip(".,)")

    mensagem = criar_oferta(link)

    await update.message.reply_text(
        mensagem,
        parse_mode="Markdown"
    )


# =========================
# INICIAR BOT
# =========================

def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN não encontrado nas variáveis de ambiente."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receber_link
        )
    )

    print("✅ Bot online!")

    app.run_polling()


if __name__ == "__main__":
    main()