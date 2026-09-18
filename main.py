import os
import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Загружаем ключи из .env
load_dotenv()
TG_TOKEN = os.getenv("TG_TOKEN")
# Токен провайдера оплат (получается в BotFather -> Bot Settings -> Payments)
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN") 

bot = telebot.TeleBot(TG_TOKEN)

# Каталог товаров (в реальном проекте тянется из БД)
PRODUCTS = {
    "vip_access": {
        "title": "👑 VIP Доступ в закрытый клуб",
        "description": "Доступ к премиум-статьям, приватному чату и прямым эфирам.",
        "price": 150000, # Цена указывается в копейках! 150000 = 1500.00 RUB
        "currency": "RUB",
        "photo_url": "https://images.unsplash.com/photo-1550565118-3a14e8d0386f?w=600",
        "payload": "invoice_vip_access" # Уникальный ID транзакции для проверки
    },
    "pdf_guide": {
        "title": "📚 Гайд: 'Как стать Fullstack за год'",
        "description": "Пошаговый PDF-мануал с полезными ссылками и roadmap.",
        "price": 30000, # 300.00 RUB
        "currency": "RUB",
        "photo_url": "https://images.unsplash.com/photo-1544716196-8eb52df6e580?w=600",
        "payload": "invoice_pdf_guide"
    }
}

@bot.message_handler(commands=['start', 'shop'])
def show_storefront(message):
    """Отображает витрину магазина с кнопками"""
    markup = InlineKeyboardMarkup(row_width=1)
    
    # Генерируем кнопки на основе нашего каталога
    for item_id, item_data in PRODUCTS.items():
        btn_text = f"Купить {item_data['title']} - {item_data['price'] // 100} ₽"
        btn = InlineKeyboardButton(text=btn_text, callback_data=f"buy_{item_id}")
        markup.add(btn)
        
    bot.send_message(
        message.chat.id, 
        "👋 Добро пожаловать в цифровой магазин!\nВыберите товар для покупки:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_buy_callback(call):
    """Обработка нажатия на кнопку 'Купить' и формирование счета (Invoice)"""
    item_id = call.data.split('_', 1)[1]
    product = PRODUCTS.get(item_id)
    
    if not product:
        bot.answer_callback_query(call.id, "Товар не найден :(")
        return

    # Убираем "часики" загрузки на кнопке
    bot.answer_callback_query(call.id)
    
    # Формируем ценник (можно добавить скидки, доставку и т.д. отдельными LabeledPrice)
    prices = [LabeledPrice(label=product["title"], amount=product["price"])]

    # Отправляем красивый счет (Invoice) в чат
    bot.send_invoice(
        call.message.chat.id,
        title=product["title"],
        description=product["description"],
        invoice_payload=product["payload"], # Это вернется нам при подтверждении оплаты
        provider_token=PAYMENT_TOKEN,
        currency=product["currency"],
        prices=prices,
        photo_url=product["photo_url"],
        photo_height=512,
        photo_width=512,
        photo_size=512,
        is_flexible=False, # True, если нужна доставка (запросит адрес юзера)
        start_parameter=f"pay_{item_id}"
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout_process(pre_checkout_query):
    """
    КРИТИЧЕСКИЙ ЭТАП: Телеграм спрашивает нас 'Товар еще в наличии? Можно списывать деньги?'
    Здесь нужно проверять остатки на складе (в БД). Если всё ок - даем добро.
    """
    # Проверяем, что payload оплаты нам знаком
    valid_payloads = [p["payload"] for p in PRODUCTS.values()]
    
    if pre_checkout_query.invoice_payload not in valid_payloads:
        bot.answer_pre_checkout_query(
            pre_checkout_query.id, 
            ok=False, 
            error_message="Ошибка в корзине. Попробуйте снова или напишите в поддержку."
        )
    else:
        # Даем добро на списание средств
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment(message):
    """
    ДЕНЬГИ СПИСАНЫ! Выдаем товар пользователю.
    Здесь обычно пишут в базу данных 'user_id = VIP' или отправляют файл.
    """
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    user_id = message.from_user.id
    
    # Имитируем бизнес-логику выдачи товара
    bot.send_message(
        message.chat.id, 
        f"✅ Оплата на сумму {payment_info.total_amount // 100} {payment_info.currency} успешно прошла!"
    )
    
    if payload == "invoice_vip_access":
        bot.send_message(user_id, "🎉 Поздравляем! Ваш статус обновлен до VIP.\nВот ссылка на закрытый чат: https://t.me/+fake_link")
        # TODO: db.update_user_status(user_id, 'vip')
        
    elif payload == "invoice_pdf_guide":
        # Имитация отправки файла
        bot.send_message(user_id, "📚 Держите ваш гайд! (В реале тут был бы bot.send_document)")
        # bot.send_document(user_id, open('guide.pdf', 'rb'))

if __name__ == '__main__':
    print("💳 Платежный бот запущен и готов принимать кэш...")
    bot.infinity_polling(timeout=60)
