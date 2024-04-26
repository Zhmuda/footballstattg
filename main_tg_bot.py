import telebot
import psycopg2
import worker

# Инициализируем бота
bot = telebot.TeleBot("5119727139:AAE4doLTwEAllpkqJt0NueC9PRZDxls5GuU")

# Переменная для хранения флага, были ли сегодняшние матчи запрошены впервые
matches_requested = False


# Функция для обработки команды /start
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1)
    button = telebot.types.KeyboardButton("Сегодняшние матчи")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=keyboard)


# Функция для обработки нажатия на кнопку "Сегодняшние матчи"
@bot.message_handler(func=lambda message: message.text == "Сегодняшние матчи")
def process_matches(message):
    global matches_requested

    # Если сегодняшние матчи еще не были запрошены, отправляем запрос на сайт
    if not matches_requested:
        matches_finder = worker.find_matches()
        if matches_finder == 1:
            matches_requested = True

    matches = worker.get_matches()

    # Если матчей нет, отправляем сообщение об этом
    if matches is None:
        bot.send_message(message.chat.id, "На сегодняшний день нет матчей.")
    else:
        # Формируем список кнопок для каждого матча
        buttons = []
        for match_info in matches:
            home_team, away_team, fixture_id = match_info
            buttons.append(telebot.types.InlineKeyboardButton(text=f"{home_team} - {away_team}",
                                                      callback_data=f"match:{home_team}:{away_team}:{fixture_id}"))

        keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(*buttons)

        # Отправляем сообщение с кнопками
        bot.send_message(message.chat.id, "Выберите матч:", reply_markup=keyboard)


# Обработка нажатия на кнопку с матчем
@bot.callback_query_handler(func=lambda call: True)
def process_match(callback_query):
    if callback_query.data.startswith('match'):
        home_team, away_team, fixture_id = callback_query.data.split(':')[1:]

        # вызовем функцию для вывода информации о матче
        match_data = worker.get_match_data(home_team, away_team, fixture_id)

        keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        # Добавляем кнопку "Коэффициенты"
        keyboard.add(telebot.types.InlineKeyboardButton(text="Коэффициенты", callback_data=f"coefficients:{fixture_id}"))

        # Отправляем сообщение с информацией о матче
        bot.send_message(callback_query.message.chat.id, match_data, reply_markup=keyboard)

    elif callback_query.data.startswith('coefficients'):
        fixture_id = callback_query.data.split(':')[1:]
        match_odds = worker.get_odds(fixture_id)

        # отправка сообщения с коэффициентами
        bot.send_message(callback_query.message.chat.id, match_odds)


# Запускаем бота
bot.polling()
