import os
import telebot

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "🤖 Olá! Sou seu Bot de Ofertas!\n\n"
        "Envie o nome de um produto e eu preparo uma oferta para você. 🛍️🔥"
    )

@bot.message_handler(func=lambda message: True)
def oferta(message):
    produto = message.text

    texto = (
        "🔥 ACHADINHO DO DIA 🔥\n\n"
        f"🛍️ {produto}\n\n"
        "💰 Aproveite essa oferta antes que o preço mude! 👀\n\n"
        "👉 Confira a oferta e garanta o seu!"
    )

    bot.reply_to(message, texto)

print("Bot iniciado!")

bot.infinity_polling()
