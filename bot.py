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
# TEXTO DA OFERTA
# =========================================================

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

        logging.error(
            f"Erro ao acessar link: {erro}"
        )

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

            texto = (
                script.string
                or script.get_text()
            )

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

        if "." in valor and "," not in valor:

            numero = float(valor)

        else:

            numero = float(
                valor
                .replace(".", "")
                .replace(",", ".")
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
# PEGAR DADOS DO PRODUTO
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
    # PREÇO
    # -----------------------------------------------------

    preco = None
    preco_antigo = None

    dados_json = pegar_jsonld(
        soup
    )

    for item in dados_json:

        if not isinstance(
            item,
            dict
        ):
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

            if isinstance(tipo, list):

                eh_produto = (
                    "Product" in tipo
                )

            else:

                eh_produto = (
                    tipo == "Product"
                )

            if not eh_produto:
                continue

            # -------------------------------------------------
            # NOME
            # -------------------------------------------------

            if not nome:

                nome = objeto.get(
                    "name"
                )

            # -------------------------------------------------
            # IMAGEM
            # -------------------------------------------------

            if not imagem:

                imagem = objeto.get(
                    "image"
                )

            # -------------------------------------------------
            # OFERTAS
            # -------------------------------------------------

            ofertas = objeto.get(
                "offers"
            )

            if isinstance(
                ofertas,
                dict
            ):

                valor = (
                    ofertas.get("price")
                    or ofertas.get("lowPrice")
                )

                if valor:

                    preco = valor

            elif isinstance(
                ofertas,
                list
            ):

                for oferta in ofertas:

                    if not isinstance(
                        oferta,
                        dict
                    ):
                        continue

                    valor = (
                        oferta.get("price")
                        or oferta.get("lowPrice")
                    )

                    if valor:

                        preco = valor

                        break

    # -----------------------------------------------------
    # IMAGEM EM LISTA
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

        nome = re.sub(
            r"\s*\|\s*(Shopee|Mercado Livre).*$",
            "",
            nome,
            flags=re.IGNORECASE
        )

    else:

        nome = "Produto em oferta"

    # -----------------------------------------------------
    # TEXTO DA PÁGINA
    # -----------------------------------------------------

    texto = soup.get_text(
        " ",
        strip=True
    )

    # -----------------------------------------------------
    # PREÇO PELO TEXTO
    # -----------------------------------------------------

    if not preco:

        padroes_preco = [

            r"R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}",

            r"R\$\s?\d+(?:,\d{2})?",

        ]

        for padrao in padroes_preco:

            encontrados = re.findall(
                padrao,
                texto,
                re.IGNORECASE
            )

            if encontrados:

                preco = encontrados[0]

                break

    # -----------------------------------------------------
    # FORMATAR PREÇO
    # -----------------------------------------------------

    preco = formatar_preco(
        preco
    )

    # -----------------------------------------------------
    # CUPOM
    # -----------------------------------------------------

    cupom = None

    padroes_cupom = [

        r"cupom[:\s]+([A-Z0-9_-]{3,30})",

        r"código[:\s]+([A-Z0-9_-]{3,30})",

        r"codigo[:\s]+([A-Z0-9_-]{3,30})",

    ]

    for padrao in padroes_cupom:

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

    # -----------------------------------------------------
    # RETORNAR
    # -----------------------------------------------------

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

    gatilho = dados.get(
        "gatilho",
        GATILHO
    )

    nome = dados.get(
        "nome",
        "Produto em oferta"
    )

    preco_antigo = dados.get(
        "preco_antigo"
    )

    preco = dados.get(
        "preco"
    )

    cupom = dados.get(
        "cupom"
    )

    link = dados.get(
        "url"
    )

    # =====================================================
    # PREÇO
    # =====================================================

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

        linha_preco = (
            "POR: Confira o preço no produto"
        )

    # =====================================================
    # CUPOM
    # =====================================================

    if cupom:

        linha_cupom = (
            f"🎟️ Use o cupom: "
            f"{html.escape(cupom)}"
        )

    else:

        linha_cupom = (
            "🎟️ Use o cupom: —"
        )

    # =====================================================
    # MENSAGEM FINAL
    # =====================================================

    mensagem = (

        f"<b>{html.escape(gatilho)}</b>\n\n"

        f"{html.escape(nome)}\n\n"

        f"{linha_preco}\n\n"

        f"{linha_cupom}\n\n"

        f"🔗 Compre aqui: "
        f"{html.escape(link)}"

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

        "💜 <b>Bem-vindo ao Mavis Prime Bot!</b>\n\n"
        "Envie um link da Shopee ou Mercado Livre "
        "para gerar sua oferta.",

        parse_mode="HTML"

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
        "Envie um link da Shopee ou Mercado Livre "
        "e o bot vai preparar a oferta automaticamente.",

        parse_mode="HTML"

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
            "❌ Envie um link da Shopee ou Mercado Livre."
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
            "⚠️ Esse link não parece ser da Shopee "
            "ou Mercado Livre."
        )

        return

    carregando = (
        await update.message.reply_text(
            "⏳ Preparando sua oferta..."
        )
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
    # ENVIAR IMAGEM + TEXTO
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
                f"Erro ao enviar imagem: {erro}"
            )

    # =====================================================
    # SE NÃO TIVER IMAGEM
    # =====================================================

    await update.message.reply_text(
        mensagem,
        parse_mode="HTML",
        disable_web_page_preview=False
    )


# =========================================================
# INICIAR BOT
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

    # /start
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # /help
    app.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    # Links enviados
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