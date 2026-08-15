import os
import re
import time
import hashlib
import hmac
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Variáveis de Ambiente configuradas no Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
SHOPEE_APP_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_SECRET = os.getenv("SHOPEE_SECRET")

# Configuração da API GraphQL da Shopee
SHOPEE_GRAPHQL_URL = "https://open-api.affiliate.shopee.com.br/graphql"

def generate_shopee_signature(payload_str, timestamp):
    """Gera a assinatura HMAC-SHA256 para autenticação na Shopee."""
    base_string = f"{SHOPEE_APP_ID}{timestamp}{payload_str}{SHOPEE_SECRET}"
    signature = hmac.new(
        SHOPEE_SECRET.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def get_shopee_product_data(link_url):
    """Consulta a API GraphQL da Shopee para obter título, preço e imagem."""
    if not SHOPEE_APP_ID or not SHOPEE_SECRET:
        return None

    timestamp = int(time.time())
    
    # Query GraphQL para buscar informações do produto/link
    query = """
    query GetLinkInfo($url: String!) {
      productOfferV2(link: $url) {
        nodes {
          productName
          price
          imageUrl
          offerLink
        }
      }
    }
    """
    
    payload = {
        "query": query,
        "variables": {"url": link_url}
    }
    
    import json
    payload_str = json.dumps(payload)
    signature = generate_shopee_signature(payload_str, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Timestamp={timestamp}, Signature={signature}"
    }
    
    try:
        response = requests.post(SHOPEE_GRAPHQL_URL, data=payload_str, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            nodes = data.get("data", {}).get("productOfferV2", {}).get("nodes", [])
            if nodes:
                prod = nodes[0]
                return {
                    "title": prod.get("productName"),
                    "price": f"R$ {float(prod.get('price')):.2f}".replace('.', ','),
                    "image": prod.get("imageUrl"),
                    "link": prod.get("offerLink", link_url)
                }
    except Exception as e:
        print(f"Erro na API Shopee: {e}")
    
    return None

def fallback_web_scrape(url):
    """Raspagem secundária de emergência caso a API não responda."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        title = soup.find("meta", property="og:title")
        image = soup.find("meta", property="og:image")
        
        return {
            "title": title["content"] if title else "Shopee Brasil | Oferta Especial",
            "price": "Confira no site",
            "image": image["content"] if image else "https://cf.shopee.com.br/file/cbd5e022f4116049a4635ed9f303253a",
            "link": url
        }
    except Exception:
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    url_match = re.search(r'https?://[^\s]+', text)
    
    if not url_match:
        return
        
    url = url_match.group(0)
    await update.message.reply_text("🔎 Processando o link e gerando a oferta...")

    # Tenta obter via API Oficial
    data = get_shopee_product_data(url)
    
    # Se falhar, tenta o fallback
    if not data:
        data = fallback_web_scrape(url)

    if not data:
        await update.message.reply_text("❌ Não foi possível carregar as informações desse link.")
        return

    # Mensagem formatada exatamente no seu padrão
    caption = (
        f"🚨 *OFERTA IMPERDÍVEL*\n\n"
        f"🛍️ _{data['title']}_\n\n"
        f"De: ~R$ --~\n"
        f"*POR: {data['price']}* 🔥🔥\n\n"
        f"🎟️ *Resgate cupons na página do produto*\n\n"
        f"🔗 Compre aqui: {data['link']}\n\n"
        f"‼️ _Essa oferta pode acabar a qualquer momento_"
    )

    # Envia a foto com o texto formatado
    try:
        await update.message.reply_photo(photo=data['image'], caption=caption, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(caption, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Bot Mavis Prime Ativo! Mande um link da Shopee para gerar a oferta.")

def main():
    if not BOT_TOKEN:
        print("ERRO: BOT_TOKEN não encontrado nas variáveis de ambiente.")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🔥 Mavis Prime iniciado!")
    app.run_polling()

if __name__ == "__main__":
    main()
