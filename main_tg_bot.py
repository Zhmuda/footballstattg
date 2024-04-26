import telebot

# Инициализируем бота
bot = telebot.TeleBot("5119727139:AAE4doLTwEAllpkqJt0NueC9PRZDxls5GuU")

# Переменная для хранения флага, были ли сегодняшние матчи запрошены впервые
matches_requested = False


# Функция для обработки команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Как дела?')


# Запускаем бота
bot.polling()
