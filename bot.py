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
# TEXTO DA OFERTA (GATILHO DEFAULT)
# =========================================================

GATILHO = "OFERTA IMPERDÍVEL"

# =========================================================
# IDENTIFICAR LOJA
# =========================================================

def identificar_loja(url):
    url = url.lower()
    if "shopee" in url or "shope.ee" in url:
        return "Shopee"
    if "mercadolivre" in url or "mercadolibre" in url or "mercadolivre.com" in url:
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
    tag = soup.find("meta", property=propriedade)
    if tag and tag.get("content"):
        return html.unescape(tag["content"]).strip()

    tag = soup.find("meta", attrs={"name": propriedade})
    if tag and tag.get("content"):
        return html.unescape(tag["content"]).strip()

    return None

# =========================================================
# PEGAR JSON-LD
# =========================================================

def pegar_jsonld(soup):
    resultados = []
    scripts = soup.find_all("script", type="application/ld+json")

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

    valor = str(valor).strip().replace("R$", "").strip()

    try:
        if "." in valor and "," not in valor:
            numero = float(valor)
        else:
            numero = float(valor.replace(".", "").replace(",", "."))

        texto = f"{numero:,.2f}"
        texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
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

    soup = BeautifulSoup(pagina, "html.parser")

    # Nome
    nome = pegar_meta(soup, "og:title") or pegar_meta(soup, "twitter:title")

    # Imagem
    imagem = pegar_meta(soup, "og:image") or pegar_meta(soup, "twitter:image")

    # Preço
    preco = None
    preco_antigo = None

    dados_json = pegar_jsonld(soup)

    for item in dados_json:
        if not isinstance(item, dict):
            continue

        objetos = [item]
        if isinstance(item.get("@graph"), list):
            objetos.extend(item["@graph"])

        for objeto in objetos:
            if not isinstance(objeto, dict):
                continue

            tipo = objeto.get("@type")
            eh_produto = ("Product" in tipo) if isinstance(tipo, list) else (tipo == "Product")

            if not eh_produto:
                continue

            if not nome:
                nome = objeto.get("name")

            if not imagem:
                imagem = objeto.get("image")

            ofertas = objeto.get("offers")
            if isinstance(ofertas, dict):
                preco = ofertas.get("price") or ofertas.get("lowPrice")
            elif isinstance(ofertas, list):
                for oferta in ofertas:
                    if isinstance(oferta, dict):
                        preco = oferta.get("price") or oferta.get("lowPrice")
                        if preco:
                            break

    if isinstance(imagem, list):
        imagem = imagem[0] if imagem else None

    if nome:
        nome = re.sub(r"\s+", " ", str(nome)).strip()
        nome = re.sub(r"\s*\|\s*(Shopee|Mercado Livre).*$", "", nome, flags=re.IGNORECASE)
    else:
        nome = "Produto em oferta"

    texto = soup.get_text(" ", strip=True)

    if not preco:
        padroes_preco = [
            r"R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}",
            r"R\$\s?\d+(?:,\d{2})?",
        ]
        for padrao in padroes_preco:
            encontrados = re.findall(padrao, texto, re.IGNORECASE)
            if encontrados:
                preco = encontrados[0]
                break

    preco = formatar_preco(preco)

    # Cupom
    cupom = None
    padroes_cupom = [
        r"cupom[:\s]+([A-Z0-9_-]{3,30})",
        r"código[:\s]+([A-Z0-9_-]{3,30})",
        r"codigo[:\s]+([A-Z0-9_-]{3,30})",
    ]
    for padrao in padroes_cupom:
        encontrado = re.search(padrao, texto, re.IGNORECASE)
        if encontrado:
            cupom = encontrado.group(1).strip()
            break

    return {
        "url": url_final or url,
        "nome": nome,
        "imagem": imagem,
        "preco": preco or "Confira no site",
        "preco_antigo": preco_antigo or "—",
        "cupom": cupom or "Resgate na página do produto",
    }

# =========================================================
# MONTAR MENSAGEM PADRÃO
# =========================================================

def montar_mensagem(dados):
    gatilho = GATILHO
    nome = dados.get("nome", "Produto em oferta")
    pa = dados.get("preco_antigo", "—")
    preco = dados.get("preco", "Confira no site")
    cp = dados.get("cupom", "Resgate na página")
    link = dados.get("url")

    # Usando formatação HTML compatível com o Telegram
    mensagem = (
        f"📌 <b>{html.escape(gatilho)}</b>\n\n"
        f"🛍️ <i>{html.escape(nome)}</i>\n\n"
        f"De: <s>{html.escape(str(pa))}</s>\n"
        f"<b>POR: {html.escape(str(preco))}</b> 🔥🔥\n\n"
        f"🎟️ <b>{html.escape(str(cp))}</b>\n\n"
        f"🔗 Compre aqui: {html.escape(link)}\n\n"
        f"‼️ <i>Essa oferta pode acabar a qualquer momento</i>"
    )

    return mensagem

# =========================================================
# COMMANDS
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜 <b>Bem-vindo ao Mavis Prime Bot!</b>\n\n"
        "Envie um link da Shopee ou Mercado Livre para gerar sua oferta.",
        parse_mode="HTML"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 <b>Como usar:</b>\n\n"
        "Envie um link da Shopee ou Mercado Livre e o bot vai preparar a oferta automaticamente.",
        parse_mode="HTML"
    )

# =========================================================
# RECEBER LINK
# =========================================================

async def receber_mensagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    texto = update.message.text
    links = re.findall(r"https?://\S+", texto)

    if not links:
        await update.message.reply_text("❌ Envie um link da Shopee ou Mercado Livre.")
        return

    link = links[0].rstrip(".,!?)]}>")
    loja = identificar_loja(link)

    if not loja:
        await update.message.reply_text("⚠️ Esse link não parece ser da Shopee ou Mercado Livre.")
        return

    carregando = await update.message.reply_text("⏳ Preparando sua oferta...")
    dados = extrair_dados(link)

    if not dados:
        await carregando.edit_text("❌ Não consegui acessar esse produto.\nTente enviar o link novamente.")
        return

    mensagem = montar_mensagem(dados)

    try:
        await carregando.delete()
    except Exception:
        pass

    imagem = dados.get("imagem")

    # Tenta enviar como Foto com a Legenda
    if imagem:
        try:
            await update.message.reply_photo(
                photo=imagem,
                caption=mensagem,
                parse_mode="HTML"
            )
            return
        except Exception as erro:
            logging.error(f"Erro ao enviar imagem: {erro}")

    # Caso a foto falhe, envia apenas a mensagem formatada
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
        raise RuntimeError("BOT_TOKEN não foi configurado no Railway.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_mensagem))

    print("🔥 Mavis Prime iniciado!")
    app.run_polling()

if __name__ == "__main__":
    main()
