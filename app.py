import os
import openai
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Загружаем переменные окружения
load_dotenv()

# Подключение к базе данных
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ Ошибка: DATABASE_URL не найден!")

engine = create_engine(DATABASE_URL, echo=True)  # Лог SQL-запросов для отладки

# Инициализируем Flask
app = Flask(__name__)

# Устанавливаем API-ключ OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise ValueError("❌ Ошибка: API-ключ OpenAI отсутствует!")

def get_latest_pricing():
    """Получает актуальные цены и даты пробных занятий из БД"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT price, trial_days, trial_time, subscription_details FROM pricing LIMIT 1"))
        data = result.fetchone()

        if data:
            price, trial_days, trial_time, subscription_details = data
            print(f"Цена: {price}, Дни пробных занятий: {trial_days}, Время: {trial_time}, Детали: {subscription_details}")
            return {
                "price": price,
                "trial_days": trial_days,
                "trial_time": trial_time,
                "subscription_details": subscription_details
            }
        else:
            print("Нет данных в таблице pricing")
            return None

@app.route("/webhook", methods=["POST"])
def webhook():
    """Обрабатывает входящие сообщения WhatsApp через Twilio"""
    try:
        if not request.form:
            return jsonify({"error": "Пустой запрос"}), 400
        
        user_message = request.form.get("Body", "").strip().lower()
        sender_id = request.form.get("From", "Неизвестный пользователь")
        print(f"📩 Новое сообщение от {sender_id}: {user_message}")
        
        # Получаем актуальные данные о пробных занятиях и ценах
        pricing_data = get_latest_pricing()
        price = pricing_data["price"] if pricing_data else "не указана"
        trial_date = pricing_data["trial_days"] if pricing_data else "не определена"
                
        # Формируем промпт для ChatGPT
        system_prompt = (
            "Ты — менеджер по продажам в танцевальной школе, знаешь все техники и стратегии из книги Гениальные скрипты продаж, Михаил Гребенюка. "
            "Твоя цель — закрывать клиентов на покупку абонемента через WhatsApp. "
            "Ты продаёшь не просто уроки, а эмоции, уверенность, новые знакомства. "
            "Ты уверен в продукте и ведёшь клиента к решению без лишних сомнений, отвечай коротко, без лишних слов, без воды.\n\n"

            "📌 **Как ты работаешь:**\n"
            "1. **Первый контакт**: выясняешь, что хочет клиент, вовлекаешь в диалог.\n"
            "2. **Презентация**: показываешь выгоды, создаёшь желание прийти на пробное занятие.\n"
            "3. **Запись на пробный урок**: говоришь уверенно, без «если хотите». Например: "
            f"\"Записываю вас на занятие, выберите день: {trial_date}.\"\n"
            "4. **Дожим после пробного урока**: помогаешь принять решение, отвечаешь на возражения.\n\n"
            "5. **Когда отвечаешь про дату пробного занятия, сразу укажи время. После записи на пробный урок, напомни про удобную одежду и сменную обувь.** \n"

            f"💰 **Стоимость абонемента**: {price} KZT.\n"
            f"📅 **Дата ближайшего пробного занятия**: {trial_date}.\n\n"

            "🔥 **Правила ответов:**\n"
            "- Отвечай **уверенно и чётко**, как опытный продавец.\n"
            "- Не используй фразы типа \"если хотите\", \"если вам удобно\".\n"
            "- Создавай **срочность** и показывай **ограниченность мест**.\n"
            "- Никогда не оставляй клиента «подумать», лучше задавай уточняющие вопросы.\n"
            "- Используй техники работы с возражениями, направляй клиента к оплате.\n\n"

            "💬 **Примеры ответов:**\n"
            "**Клиент:** \"Сколько стоит?\"\n"
            f"**Ты:** \"Абонемент стоит {price} KZT. Но сначала попробуйте бесплатное занятие – выберите день: {trial_date}.\"\n\n"

            "**Клиент:** \"Я подумаю.\"\n"
            "**Ты:** \"Конечно, важно принять правильное решение. Но места быстро заканчиваются. Записать вас?\"\n\n"

            "**Клиент:** \"Я не умею танцевать.\"\n"
            "**Ты:** \"Отлично! 90% наших учеников начинали с нуля. Пробное занятие как раз для этого – выберите день: {trial_date}.\""
        )
        
        # ОТПРАВКА В OPENAI API
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        ai_reply = response.choices[0].message.content.strip()
        print(f"🤖 Ответ OpenAI: {ai_reply.encode('utf-8', errors='replace').decode('utf-8')}")        

        # ОТПРАВКА В TWILIO
        twilio_response = MessagingResponse()
        twilio_response.message(ai_reply)
        
        print(f"📨 Отправлено в Twilio: {ai_reply}")
        return str(twilio_response), 200
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e).encode('utf-8', errors='replace').decode('utf-8')}")
        return jsonify({"error": f"Ошибка обработки запроса: {str(e)}"}), 500

# Запуск сервера
if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=10000)

