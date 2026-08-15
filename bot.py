import os
import re
import json
import html
import logging
import requests

from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIGURAÇÃO
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# =========================================================
# GATILHO
# =========================================================
#
# Aqui você pode trocar o gatilho quando quiser.
# O bot NÃO vai colocar "Oferta Relâmpago" automaticamente.
#

GATILHO = "🔥 OFERTA DO DIA"

# =========================================================
# IDENTIFICAR LOJA
# =========================================================

def identificar_loja(url):
    url = url.lower()

    if "shopee" in url:
        return "Shopee"

    if "mercadolivre" in url or "mercadolibre" in url:
        return "Mercado Livre"

    return None


# =========================================================
# ACESSAR LINK
# =========================================================

def acessar_link(url):
    try:
        resposta = requests.get(
            url,
            headers=HEADERS,
            timeout=25,
            allow_redirects=True,
        )

        resposta.raise_for_status()

        return resposta.url, resposta.text

    except Exception as erro:
        logging.error(f"Erro ao acessar link: {erro}")
        return None, None


# =========================================================
# PEGAR META TAG
# =========================================================

def pegar_meta(soup, propriedade):

    tag = soup.find(
        "meta",
        property=propriedade
    )

    if tag and tag.get("content"):
        return html.unescape(
            tag["content"]
        ).strip()

    tag = soup.find(
        "meta",
        attrs={"name": propriedade}
    )

    if tag and tag.get("content"):
        return html.unescape(
            tag["content"]
        ).strip()

    return None


# =========================================================
# PEGAR JSON-LD
# =========================================================

def pegar_jsonld(soup):

    resultados = []

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for script in scripts:

        try:
            texto = script.string or script.get_text()

            if not texto:
                continue

            dados = json.loads(texto)

            if isinstance(dados, list):
                resultados.extend(dados)
            else:
                resultados.append(dados)

        except Exception:
            continue

    return resultados


# =========================================================
# FORMATAR PREÇO
# =========================================================

def formatar_preco(valor):

    if valor is None:
        return None

    valor = str(valor).strip()

    valor = valor.replace(
        "R$",
        ""
    ).strip()

    try:

        numero = float(
            valor.replace(
                ".",
                ""
            ).replace(
                ",",
                "."
            )
        )

        texto = f"{numero:,.2f}"

        texto = (
            texto
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        return f"R$ {texto}"

    except Exception:

        return f"R$ {valor}"


# =========================================================
# EXTRAIR DADOS
# =========================================================

def extrair_dados(url):

    url_final, pagina = acessar_link(url)

    if not pagina:
        return None

    soup = BeautifulSoup(
        pagina,
        "html.parser"
    )

    # -----------------------------------------------------
    # NOME
    # -----------------------------------------------------

    nome = pegar_meta(
        soup,
        "og:title"
    )

    if not nome:
        nome = pegar_meta(
            soup,
            "twitter:title"
        )

    # -----------------------------------------------------
    # IMAGEM
    # -----------------------------------------------------

    imagem = pegar_meta(
        soup,
        "og:image"
    )

    if not imagem:
        imagem = pegar_meta(
            soup,
            "twitter:image"
        )

    # -----------------------------------------------------
    # PREÇOS
    # -----------------------------------------------------

    preco = None
    preco_antigo = None

    dados_json = pegar_jsonld(
        soup
    )

    for item in dados_json:

        if not isinstance(item, dict):
            continue

        objetos = [item]

        if isinstance(
            item.get("@graph"),
            list
        ):
            objetos.extend(
                item["@graph"]
            )

        for objeto in objetos:

            if not isinstance(
                objeto,
                dict
            ):
                continue

            tipo = objeto.get(
                "@type"
            )

            if tipo == "Product":

                if not nome:
                    nome = objeto.get(
                        "name"
                    )

                if not imagem:
                    imagem = objeto.get(
                        "image"
                    )

                ofertas = objeto.get(
                    "offers"
                )

                if isinstance(
                    ofertas,
                    dict
                ):

                    preco = (
                        ofertas.get(
                            "price"
                        )
                        or ofertas.get(
                            "lowPrice"
                        )
                    )

                elif isinstance(
                    ofertas,
                    list
                ):

                    for oferta in ofertas:

                        if isinstance(
                            oferta,
                            dict
                        ):

                            preco = (
                                oferta.get(
                                    "price"
                                )
                                or oferta.get(
                                    "lowPrice"
                                )
                            )

                            if preco:
                                break

    # -----------------------------------------------------
    # CORRIGIR IMAGEM EM LISTA
    # -----------------------------------------------------

    if isinstance(
        imagem,
        list
    ):

        imagem = (
            imagem[0]
            if imagem
            else None
        )

    # -----------------------------------------------------
    # LIMPAR NOME
    # -----------------------------------------------------

    if nome:

        nome = re.sub(
            r"\s+",
            " ",
            str(nome)
        ).strip()

    else:

        nome = "Produto em oferta"

    # -----------------------------------------------------
    # PREÇO
    # -----------------------------------------------------

    preco = formatar_preco(
        preco
    )

    # -----------------------------------------------------
    # CUPOM
    # -----------------------------------------------------

    cupom = None

    texto = soup.get_text(
        " ",
        strip=True
    )

    padroes = [
        r"cupom[:\s]+([A-Z0-9_-]{3,30})",
        r"código[:\s]+([A-Z0-9_-]{3,30})",
        r"codigo[:\s]+([A-Z0-9_-]{3,30})",
    ]

    for padrao in padroes:

        encontrado = re.search(
            padrao,
            texto,
            re.IGNORECASE
        )

        if encontrado:

            cupom = (
                encontrado
                .group(1)
                .strip()
            )

            break

    return {
        "url": url_final,
        "nome": nome,
        "imagem": imagem,
        "preco": preco,
        "preco_antigo": preco_antigo,
        "cupom": cupom,
    }


# =========================================================
# MONTAR MENSAGEM
# =========================================================

def montar_mensagem(dados):

    nome = dados.get("nome")
    preco_antigo = dados.get("preco_antigo")
    preco = dados.get("preco")
    cupom = dados.get("cupom")
    link = dados.get("url")

    if preco_antigo and preco:
        linha_preco = (
            f"De: <s>{html.escape(preco_antigo)}</s>\n"
            f"<b>POR: {html.escape(preco)}</b> ✅"
        )
    elif preco:
        linha_preco = (
            f"<b>POR: {html.escape(preco)}</b> ✅"
        )
    else:
        linha_preco = "💰 Confira o preço no produto"

    if cupom:
        linha_cupom = (
            f"🎟️ <b>{html.escape(cupom)}</b>"
        )
    else:
        linha_cupom = "🎟️ Consulte os cupons disponíveis"

    mensagem = (
        f"<b>OFERTA DO DIA</b>⚡️\n\n"
        f"{html.escape(nome)}\n\n"
        f"{linha_preco}\n\n"
        f"{linha_cupom}\n\n"
        f"🔗 Compre aqui: {html.escape(link)}"
    )

    return mensagem


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "💜 <b>Bem-vindo a Mavis Prime Bot!</b>\n\n"
        "Envie um link da Shopee ou Mercado Livre "
        "para gerar sua oferta. 🛍️",
        parse_mode="HTML",
    )


# =========================================================
# /HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "📌 <b>Como usar:</b>\n\n"
        "Envie o link de um produto da "
        "Shopee ou Mercado Livre.\n\n"
        "O Mavis Prime vai preparar a oferta "
        "automaticamente.",
        parse_mode="HTML",
    )


# =========================================================
# RECEBER LINK
# =========================================================

async def receber_mensagem(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    texto = update.message.text

    if not texto:
        return

    links = re.findall(
        r"https?://\S+",
        texto
    )

    if not links:

        await update.message.reply_text(
            "❌ Envie um link da Shopee "
            "ou Mercado Livre."
        )

        return

    link = links[0].rstrip(
        ".,!?)]}>"
    )

    loja = identificar_loja(
        link
    )

    if not loja:

        await update.message.reply_text(
            "⚠️ Esse link não parece ser "
            "da Shopee ou Mercado Livre."
        )

        return

    carregando = await update.message.reply_text(
        "⏳ Buscando as informações da oferta..."
    )

    dados = extrair_dados(
        link
    )

    if not dados:

        await carregando.edit_text(
            "❌ Não consegui acessar esse produto.\n\n"
            "Tente enviar o link novamente."
        )

        return

    mensagem = montar_mensagem(
        dados
    )

    try:
        await carregando.delete()
    except Exception:
        pass

    # =====================================================
    # ENVIAR IMAGEM
    # =====================================================

    imagem = dados.get(
        "imagem"
    )

    if imagem:

        try:

            await update.message.reply_photo(
                photo=imagem,
                caption=mensagem,
                parse_mode="HTML"
            )

            return

        except Exception as erro:

            logging.error(
                f"Não foi possível enviar imagem: {erro}"
            )

    # =====================================================
    # SE A IMAGEM NÃO ESTIVER DISPONÍVEL
    # =====================================================

    await update.message.reply_text(
        mensagem,
        parse_mode="HTML",
        disable_web_page_preview=False
    )


# =========================================================
# INICIAR
# =========================================================

def main():

    if not TOKEN:

        raise RuntimeError(
            "BOT_TOKEN não foi configurado no Railway."
        )

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

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

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receber_mensagem
        )
    )

    print(
        "🔥 Mavis Prime iniciado!"
    )

    app.run_polling()


# =========================================================
# EXECUTAR
# =========================================================

if __name__ == "__main__":
    main()