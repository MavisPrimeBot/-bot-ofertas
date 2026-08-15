import os
import re
import logging
import requests

from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIGURAÇÕES
# =========================

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# =========================
# EXTRAIR INFORMAÇÕES
# =========================

def extrair_produto(link):
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            )
        }

        resposta = requests.get(
            link,
            headers=headers,
            timeout=15,
            allow_redirects=True
        )

        soup = BeautifulSoup(resposta.text, "html.parser")

        # Nome
        nome = ""

        og_title = soup.find("meta", property="og:title")

        if og_title and og_title.get("content"):
            nome = og_title["content"].strip()

        if not nome:
            titulo = soup.find("title")
            if titulo:
                nome = titulo.text.strip()

        if not nome:
            nome = "Oferta especial"

        # Preço
        preco = ""

        meta_preco = soup.find(
            "meta",
            property="product:price:amount"
        )

        if meta_preco and meta_preco.get("content"):
            preco = meta_preco["content"]

        if not preco:
            texto = soup.get_text(" ", strip=True)

            encontrados = re.findall(
                r"R\$\s?\d+(?:[.,]\d{2})?",
                texto
            )

            if encontrados:
                preco = encontrados[0]

        if not preco:
            preco = "Confira no produto"

        return nome, preco

    except Exception as erro:
        logging.error("Erro ao extrair produto: %s", erro)

        return "Oferta especial", "Confira no produto"


# =========================
# MENSAGEM DA OFERTA
# =========================

def criar_mensagem(nome, preco, link):
    gatilho = "OFERTA DO DIA⚡️"

    pa = "preço anterior"

    cp = "Consulte os cupons disponíveis"

    mensagem = f"""*{gatilho}*

🛍️ _{nome}_

De: ~{pa}~
*POOR: {preco}* 🔥🔥

🎟️ *{cp}*

🔗 Compre aqui: {link}

‼️ _Essa oferta pode acabar a qualquer momento_"""

    return mensagem


# =========================
# RECEBER LINK
# =========================

async def receber_link(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    texto = update.message.text.strip()

    # Procura qualquer link enviado
    resultado = re.search(
        r"https?://\S+",
        texto
    )

    if not resultado:
        await update.message.reply_text(
            "⚠️ Envie um link da oferta."
        )
        return

    link = resultado.group(0).rstrip(".,)")

    await update.message.chat.send_action("typing")

    nome, preco = extrair_produto(link)

    mensagem = criar_mensagem(
        nome,
        preco,
        link
    )

    await update.message.reply_text(
        mensagem,
        parse_mode="Markdown",
        disable_web_page_preview=False
    )


# =========================
# INICIAR BOT
# =========================

def main():

    if not TOKEN:
        raise ValueError(
            "A variável BOT_TOKEN não foi configurada."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receber_link
        )
    )

    print("Bot iniciado com sucesso!")

    app.run_polling()


if __name__ == "__main__":
    main()