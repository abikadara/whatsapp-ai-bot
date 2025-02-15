from flask import Flask, request

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])  # Указываем, что 
принимаем только POST-запросы
def webhook():
    try:
        # Пытаемся получить JSON-данные от Twilio
        data = request.get_json()
        print("📩 Полученные данные:", data)  # Выводим в терминал 
для проверки

        # Проверяем, что данные получены
        if not data:
            return "❌ Ошибка: пустой JSON", 400

        # Извлекаем текст сообщения и номер отправителя
        message_body = data.get("Body", "Нет текста")  # Извлекаем 
текст сообщения
        sender_number = data.get("From", "Неизвестный отправитель")  
# Извлекаем номер

        print(f"📨 Сообщение от {sender_number}: {message_body}")  
# Лог в терминал

        return "✅ OK", 200  # Отправляем Twilio успешный ответ
    except Exception as e:
        print("❌ Ошибка:", e)
        return "❌ Ошибка обработки запроса", 400

if __name__ == "__main__":
    app.run(port=5000, debug=True)
