import io
import logging

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

from PIL import Image
import pytesseract

# Укажите путь к tesseract.exe на Windows, если нужно:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для диагностики
SYMPTOMS, DIET, FAMILY_HISTORY, BLOOD_TEST, TEST_RESULTS = range(5)

# Ключевые глютеновые ингредиенты (в нижнем регистре)
GLUTEN_INGREDIENTS = {
    'wheat', 'barley', 'rye', 'malt', "brewer's yeast", 'farro', 'spelt',
    'kamut', 'triticale', 'bulgur', 'durum', 'semolina', 'einkorn', 'emmer',
    'wheat starch', 'wheat flour', 'barley malt', 'rye flour'
}

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(
        f"👋 Hi, {user.first_name}!\n"
        "I'm your Celiac Bot.\n"
        "Commands:\n"
        "/scan - send photo of ingredients to check gluten\n"
        "/diagnose - celiac disease risk assessment\n"
        "/help - info"
    )

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Available commands:\n"
        "/start - welcome message\n"
        "/scan - send a photo of product ingredients\n"
        "/diagnose - risk assessment questions\n"
        "/help - this message"
    )

def scan_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📷 Please send a clear photo of the ingredients label."
    )

def analyze_image(update: Update, context: CallbackContext):
    try:
        photo_file = update.message.photo[-1].get_file()
        photo_bytes = photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))

        # OCR — распознаём текст с фото
        text = pytesseract.image_to_string(image, lang='eng').lower()

        logger.info(f"OCR Text: {text}")

        found = [ing for ing in GLUTEN_INGREDIENTS if ing in text]

        if found:
            msg = "🚫 Gluten detected:\n" + "\n".join(f"- {ing}" for ing in found) + \
                  "\n\nThis product is NOT safe for celiac disease."
        else:
            msg = "✅ No gluten ingredients found.\nBut always double-check packaging."

        update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        update.message.reply_text("❌ Couldn't process image. Please try a clearer photo.")

def diagnose(update: Update, context: CallbackContext):
    reply_kb = [['Yes', 'No', 'Sometimes']]
    update.message.reply_text(
        "Do you have symptoms such as diarrhea, bloating, fatigue, anemia?",
        reply_markup=ReplyKeyboardMarkup(reply_kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return SYMPTOMS

def symptoms(update: Update, context: CallbackContext):
    context.user_data['symptoms'] = update.message.text
    reply_kb = [['Yes', 'No', 'Sometimes']]
    update.message.reply_text(
        "Do symptoms improve on gluten-free diet?",
        reply_markup=ReplyKeyboardMarkup(reply_kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return DIET

def diet(update: Update, context: CallbackContext):
    context.user_data['diet'] = update.message.text
    reply_kb = [['Yes', 'No', 'Unknown']]
    update.message.reply_text(
        "Any relatives with celiac disease?",
        reply_markup=ReplyKeyboardMarkup(reply_kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return FAMILY_HISTORY

def family_history(update: Update, context: CallbackContext):
    context.user_data['family_history'] = update.message.text
    reply_kb = [['Yes', 'No', 'Not tested']]
    update.message.reply_text(
        "Have you had celiac blood tests (tTG-IgA, EMA)?",
        reply_markup=ReplyKeyboardMarkup(reply_kb, one_time_keyboard=True, resize_keyboard=True)
    )
    return BLOOD_TEST

def blood_test(update: Update, context: CallbackContext):
    context.user_data['blood_test'] = update.message.text
    if update.message.text == 'Yes':
        reply_kb = [['Positive', 'Negative', 'Borderline']]
        update.message.reply_text(
            "What were the results?",
            reply_markup=ReplyKeyboardMarkup(reply_kb, one_time_keyboard=True, resize_keyboard=True)
        )
        return TEST_RESULTS
    else:
        context.user_data['test_results'] = 'Not tested'
        return conclusion(update, context)

def test_results(update: Update, context: CallbackContext):
    context.user_data['test_results'] = update.message.text
    return conclusion(update, context)

def conclusion(update: Update, context: CallbackContext):
    data = context.user_data
    score = 0
    if data['symptoms'] in ['Yes', 'Sometimes']:
        score += 1
    if data['diet'] in ['Yes', 'Sometimes']:
        score += 1
    if data['family_history'] == 'Yes':
        score += 1
    if data.get('blood_test') == 'Yes':
        if data['test_results'] == 'Positive':
            score += 2
        elif data['test_results'] == 'Borderline':
            score += 1

    if score >= 3:
        text = "🔴 High likelihood of celiac disease.\nPlease consult a doctor."
    elif score >= 1:
        text = "🟡 Possible risk. Consider medical advice."
    else:
        text = "🟢 Low likelihood. Monitor symptoms."

    update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Assessment cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def handle_text(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    found = [ing for ing in GLUTEN_INGREDIENTS if ing in text]
    if found:
        update.message.reply_text(
            "⚠ Gluten ingredients found:\n" + "\n".join(f"- {ing}" for ing in found)
        )
    else:
        update.message.reply_text("No gluten ingredients found. Please check carefully.")

def error_handler(update: Update, context: CallbackContext):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main():
    TOKEN = "8144787318:AAHBNOt-FDfHS7bUaysb76Wxb_BsSj8CqdI"  # <-- Замените на ваш токен

    updater = Updater(TOKEN)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('diagnose', diagnose)],
        states={
            SYMPTOMS: [MessageHandler(Filters.regex('^(Yes|No|Sometimes)$'), symptoms)],
            DIET: [MessageHandler(Filters.regex('^(Yes|No|Sometimes)$'), diet)],
            FAMILY_HISTORY: [MessageHandler(Filters.regex('^(Yes|No|Unknown)$'), family_history)],
            BLOOD_TEST: [MessageHandler(Filters.regex('^(Yes|No|Not tested)$'), blood_test)],
            TEST_RESULTS: [MessageHandler(Filters.regex('^(Positive|Negative|Borderline)$'), test_results)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("scan", scan_command))
    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.photo, analyze_image))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_error_handler(error_handler)

    print("Bot started")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
