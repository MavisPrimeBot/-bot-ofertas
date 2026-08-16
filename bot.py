import os
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Configuração de logs para acompanhamento no Heroku
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Puxa o Token das Variáveis de Ambiente do Heroku
TOKEN = os.environ.get("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_boas_vindas = "<b>Olá! Eu sou o Mavis Prime.</b>\n\nComo posso ajudar você hoje?"
    await update.message.reply_text(texto_boas_vindas, parse_mode=ParseMode.HTML)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Responde usando HTML para evitar erros com caracteres especiais
    texto_recebido = update.message.text
    resposta = f"<b>Mavis Prime recebeu:</b>\n{texto_recebido}"
    await update.message.reply_text(resposta, parse_mode=ParseMode.HTML)

def main():
    if not TOKEN:
        logging.error("TELEGRAM_TOKEN não configurado nas variáveis de ambiente!")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    # Comandos e manipuladores de mensagem
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logging.info("Iniciando Mavis Prime...")
    app.run_polling()

if __name__ == "__main__":
    main()
