import os
import re
import string
import pandas as pd
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters, \
    ContextTypes
from flask import Flask

app = Flask(__name__)

# Загрузка данных из Excel с обработкой ошибок
file_path = r"\\192.168.1.5\interview\1СУП\ООИРП\КБ\spisokKnig.xlsx"
try:
    if os.path.exists(file_path):
        book_data = pd.read_excel(file_path)
        if "Жанр" not in book_data.columns:
            book_data["Жанр"] = ""
        print("✅ Файл успешно загружен.")
    else:
        print("❌ Ошибка: Файл не найден.")
        book_data = pd.DataFrame()
except Exception as e:
    print(f"❌ Ошибка при загрузке Excel-файла: {e}")
    book_data = pd.DataFrame()

# Извлечение уникальных жанров
unique_genres = sorted(
    book_data['Жанр'].dropna().unique().tolist()) if not book_data.empty and "Жанр" in book_data.columns else []


# ✅ Функция для очистки данных и возврата в главное меню (перезапуск)
async def show_main_menu(update: Update, context: CallbackContext) -> None:
    # ✅ Очищаем всю историю пользователя
    context.user_data.clear()

    # ✅ Определяем, откуда пришел запрос (кнопка или команда)
    if update.callback_query:
        message = update.callback_query.message
        await update.callback_query.answer()  # Закрываем запрос кнопки
    else:
        message = update.message

    # ✅ Удаляем предыдущее сообщение (если возможно)
    try:
        await message.delete()
    except Exception:
        pass  # Игнорируем ошибки, если сообщение уже удалено

    # ✅ Создаем новое главное меню
    keyboard = [
        [InlineKeyboardButton("📚 Узнать о наличии книг", callback_data="search_books")],
        [InlineKeyboardButton("📝 Подать заявку", callback_data="submit_request")]# Теперь это кнопка перезапуска!
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ✅ Отправляем новое "перезапущенное" меню
    await message.reply_text(
        "👋 Привет! Я - библиотекарь КМ! Я могу предоставить информацию о книгах нашей корпоративной библиотеки "
        "или принять заявку на приобретение новой книги. Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# ✅ Обработчик кнопки "🏠 Главное меню"
async def main_menu_callback(update: Update, context: CallbackContext) -> None:
    await show_main_menu(update, context)

# Меню критериев поиска с изображениями
async def show_search_criteria(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("🔍 По названию", callback_data="search_by_title")],
        [InlineKeyboardButton("📂 По жанру", callback_data="search_by_genre")],
        [InlineKeyboardButton("✍️ По автору", callback_data="search_by_author")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🔎 *Выберите критерии для поиска книги:*", reply_markup=reply_markup,
                                  parse_mode="Markdown")


# Список жанров с изображениями
async def show_genres(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    if unique_genres:
        keyboard = [[InlineKeyboardButton(f"📖 {genre}", callback_data=f"genre_{i}")] for i, genre in
                    enumerate(unique_genres)]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📚 *Выберите жанр:*", reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await query.edit_message_text("❌ Жанры не найдены.")


# Вывод списка книг по жанру
async def show_books_in_genre(update: Update, context: CallbackContext, genre_index: int) -> None:
    query = update.callback_query
    genre = unique_genres[genre_index]
    books = book_data[book_data['Жанр'] == genre]['Название'].tolist()

    if books:
        context.user_data['book_list'] = books
        books_text = "\n".join([f"{i + 1}. 📖 *{book}*" for i, book in enumerate(books)])
        await query.message.reply_text(f"📚 *Книги в жанре '{genre}':*\n\n{books_text}", parse_mode="Markdown")

        keyboard = [
            [InlineKeyboardButton("📖 Описание книги", callback_data="book_description")],
            [InlineKeyboardButton("🔙 Выбрать другой жанр", callback_data="search_by_genre")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Выберите дальнейшее действие:", reply_markup=reply_markup)
    else:
        await query.message.reply_text(f"❌ В жанре *'{genre}'* книги не найдены.", parse_mode="Markdown")


# Обработка номера книги и вывод описания
async def handle_book_description(update: Update, context: CallbackContext) -> None:
    try:
        book_number = int(update.message.text.strip())
        if 'book_list' in context.user_data and 1 <= book_number <= len(context.user_data['book_list']):
            book_name = context.user_data['book_list'][book_number - 1]
            book_row = book_data[book_data['Название'].str.lower() == book_name.lower()]
            if not book_row.empty:
                response = "📘 *Информация о книге:*\n\n"
                for column in book_row.columns:
                    if column != "Название_очищенное" and pd.notnull(book_row[column].values[0]):
                        value = str(book_row[column].values[0]).replace("_", "\\_")
                        response += f"*{column}:* {value}\n"
                await update.message.reply_text(response, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Книга не найдена.")
        else:
            await update.message.reply_text("❌ Ошибка: Неверный номер книги. Попробуйте снова.")
    except ValueError:
        await update.message.reply_text("❌ Ошибка: Введите числовое значение.")


# Обработка кнопки "По автору"
async def handle_author_search(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data['waiting_for_author_search'] = True
    await query.edit_message_text(text="Напишите фамилию автора:")
    context.user_data.clear()

# Функция обработки нажатий кнопок
async def handle_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "search_by_title":
        context.user_data['waiting_for_search_by_title'] = True
        await query.edit_message_text(
            text='Напишите название книги'
        )
    elif query.data == "search_books":
        await show_search_criteria(update, context)
    elif query.data == "submit_request":
        context.user_data['waiting_for_request'] = True
        await query.edit_message_text(
            text="Напишите название книги, автора, ваши контактные данные: фамилия, имя и номер телефона"
        )
    elif query.data == "search_by_genre":
        await show_genres(update, context)
    elif query.data == "main_menu":
        await show_main_menu(update, context)
    elif query.data == "book_description":
        context.user_data['waiting_for_book_description'] = True
        await query.edit_message_text(
            text='Напишите цифру книги'
        )
        context.user_data['waiting_for_book_description'] = True
    elif query.data == "search_by_author":  # Обработка кнопки "По автору"
        context.user_data['waiting_for_author_search'] = True
        await query.message.reply_text("✍️ Введите фамилию автора для поиска:")
    elif query.data.startswith("genre_"):
        genre_index = int(query.data.replace("genre_", ""))
        await show_books_in_genre(update, context, genre_index)


async def handle_user_input(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('waiting_for_search_by_title', False):
        await handle_search_by_title(update, context)
    elif context.user_data.get('waiting_for_request', False):
        await handle_request_message(update, context)
    elif context.user_data.get('waiting_for_book_description', False):
        await handle_book_description(update, context)
    elif context.user_data.get('waiting_for_author_search', False):
        await handle_author_search_input(update, context)
    else:
        await show_main_menu(update, context)


def clean_string(s):
    if isinstance(s, str):
        s = s.lower().strip()  # Приведение к нижнему регистру и удаление пробелов в начале и конце
        s = re.sub(r'\s+', ' ', s)  # Замена множественных пробелов на один
        s = s.translate(str.maketrans('', '', string.punctuation))  # Удаление всех знаков пунктуации
        return s
    return s


# Обработка поиска по названию
async def handle_search_by_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    book_name = update.message.text.strip().lower()
    context.user_data['waiting_for_search_by_title'] = False

    required_columns = ['Автор', 'Название', 'Описание', 'Жанр', 'Статус']
    if all(column in book_data.columns for column in required_columns):
        try:
            if 'Название_очищенное' not in book_data.columns:
                book_data['Название_очищенное'] = book_data['Название'].apply(clean_string)

            cleaned_book_name = clean_string(book_name)
            book_row = book_data[book_data['Название_очищенное'].str.contains(cleaned_book_name, na=False)]

            if not book_row.empty:
                response = "📚 *Информация о найденных книгах:*\n\n"
                for _, row in book_row.iterrows():
                    for column in required_columns:
                        value = str(row[column]).replace("-", "\\-").replace(".", "\\.").replace("(", "\\(").replace(
                            ")", "\\)").replace("!", "\\!")
                        if pd.notnull(value):
                            response += f"*{column}:* {value}\n"
                    response += "\n"

                await update.message.reply_text(response, parse_mode="MarkdownV2")

                # Кнопка "Главное меню" с изображением
                keyboard = [
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Выберите дальнейшее действие:", reply_markup=reply_markup)
            else:
                keyboard = [[InlineKeyboardButton("📝 Подать заявку", callback_data="submit_request")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    text=f"❌ Книга '{update.message.text.strip()}' не найдена. Вы можете подать заявку на приобретение этой книги.",
                    reply_markup=reply_markup
                )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при обработке данных: {str(e)}")
    else:
        missing_columns = [col for col in required_columns if col not in book_data.columns]
        await update.message.reply_text(f"❌ Ошибка: В Excel-файле отсутствуют столбцы: {', '.join(missing_columns)}.")
        # ✅ Очистка истории поиска автора
    context.user_data.pop('waiting_for_search_by_title', None)
    context.user_data.clear()


# ✅ Поиск по автору (исправленный)
async def handle_author_search_input(update: Update, context: CallbackContext) -> None:
    author_name = update.message.text.strip().lower()

    required_columns = ['Автор', 'Название', 'Описание', 'Жанр', 'Статус']
    if all(column in book_data.columns for column in required_columns):
        try:
            if 'Автор_очищенный' not in book_data.columns:
                book_data['Автор_очищенный'] = book_data['Автор'].apply(clean_string)

            cleaned_author_name = clean_string(author_name)
            books_by_author = book_data[book_data['Автор_очищенный'].str.contains(cleaned_author_name, na=False)]

            if not books_by_author.empty:
                response = "📚 *Книги этого автора:*\n\n"
                for _, row in books_by_author.iterrows():
                    book_title = row['Название'].replace("-", "\\-").replace(".", "\\.").replace("(", "\\(").replace(
                        ")", "\\)").replace("!", "\\!").replace("*", "\\*")
                    book_genre = row['Жанр'].replace("-", "\\-").replace(".", "\\.").replace("(", "\\(").replace(")",
                                                                                                                 "\\)").replace(
                        "!", "\\!").replace("*", "\\*")

                    response += f"📖 *Название:* {book_title}\n📂 *Жанр:* {book_genre}\n\n"

                await update.message.reply_text(response, parse_mode="MarkdownV2")

                # Кнопка "Главное меню"
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Выберите дальнейшее действие:", reply_markup=reply_markup)
            else:
                await update.message.reply_text(f"❌ Книги с автором '{author_name}' не найдены.",
                                                parse_mode="MarkdownV2")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при поиске автора: {str(e)}", parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("❌ Ошибка: В файле отсутствуют необходимые столбцы.", parse_mode="MarkdownV2")

    # ✅ Очистка истории поиска автора
    context.user_data.clear()


# ✅ Обработка заявки (обновленный)
async def handle_request_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    recipient_chat_id = "7769340488"  # Укажите правильный ID чата

    await context.bot.send_message(chat_id=recipient_chat_id, text=f"📬 *Новая заявка:*\n{user_message}",
                                   parse_mode="Markdown")
    await update.message.reply_text("✅ Спасибо! Ваша заявка отправлена.")

    # ✅ Очистка истории заявки
    context.user_data.pop('waiting_for_request', None)
    context.user_data.clear()



# ✅ Функция для экранирования спецсимволов в MarkdownV2
def escape_markdown_v2(text):
    """Экранирует специальные символы для MarkdownV2."""
    special_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(r'([{}])'.format(re.escape(special_chars)), r'\\\1', text)

async def handle_book_description(update: Update, context: CallbackContext) -> None:
    try:
        book_number = int(update.message.text.strip())  # Получаем номер книги от пользователя

        if 'book_list' in context.user_data and 1 <= book_number <= len(context.user_data['book_list']):
            book_name = context.user_data['book_list'][book_number - 1]
            book_row = book_data[book_data['Название'].str.lower() == book_name.lower()]

            if not book_row.empty:
                response = "📘 *Информация о книге:*\n\n"
                excluded_columns = ["Название_очищенное", "Автор_очищенный"]  # ❌ Исключаем ненужные столбцы

                for column in book_row.columns:
                    if column not in excluded_columns and pd.notnull(book_row[column].values[0]):
                        column_name = escape_markdown_v2(column)
                        value = escape_markdown_v2(str(book_row[column].values[0]))
                        response += f"*{column_name}:* {value}\n"

                await update.message.reply_text(response, parse_mode="MarkdownV2")

                # Кнопки "Главное меню" и "Выбрать другой жанр"
                keyboard = [
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
                    [InlineKeyboardButton("🔙 Выбрать другой жанр", callback_data="search_by_genre")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Выберите дальнейшее действие:", reply_markup=reply_markup)
            else:
                await update.message.reply_text(f"❌ Книга с названием '{escape_markdown_v2(book_name)}' не найдена.", parse_mode="MarkdownV2")
        else:
            await update.message.reply_text("❌ Ошибка: Неверный номер книги. Попробуйте снова.", parse_mode="MarkdownV2")
    except ValueError:
        await update.message.reply_text("❌ Ошибка: Введите числовое значение.", parse_mode="MarkdownV2")
    except Exception as e:
        await update.message.reply_text(f"❌ Произошла ошибка: {escape_markdown_v2(str(e))}", parse_mode="MarkdownV2")

    # ✅ Очистка истории поиска книги
    context.user_data.clear()

# Функция запуска бота
def main():
    telegram_token = "8062121167:AAFAXk-4dQ_w6nJWS9wTxwWgAYai-VFArYw"  # Замените на ваш токен
    app = Application.builder().token(telegram_token).build()

    app.add_handler(CommandHandler("start", show_main_menu))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input, handle_book_description))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"⚠️ Ошибка: {e}")
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")
port = int(os.environ.get("PORT", 5000))  # Railway передает порт
app.run(host="0.0.0.0", port=port)
















