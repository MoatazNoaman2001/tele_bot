import asyncio
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler, \
    ConversationHandler
import mysql.connector
import random
import re
import logging
import time

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
TOKEN = os.environ.get('TELEGRAM_TOKEN', "7716381751:AAFKtI0rJs2Bc3i5E-WOMWjG49IryC1bNTk")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 1388747442))

# Database Configuration from environment variables
DB_CONFIG = {
    "host": os.environ.get('DB_HOST', 'localhost'),
    "user": os.environ.get('DB_USER', 'alya'),
    "password": os.environ.get('DB_PASSWORD', 'mumdad2002'),
    "database": os.environ.get('DB_NAME', 'easymoneybot')
}


# Connect to the database with retry logic
def connect_with_retry(max_retries=10, delay=5):
    retries = 0
    while retries < max_retries:
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            print("Connected to the database successfully!")
            return conn, cursor
        except mysql.connector.Error as err:
            retries += 1
            print(f"Error connecting to the database (attempt {retries}/{max_retries}): {err}")
            if retries >= max_retries:
                print("Max retries reached. Unable to connect to the database.")
                return None, None
            time.sleep(delay)


# Initialize connection
conn, cursor = connect_with_retry()


# Ensure connection is active before executing queries
def ensure_connection():
    global conn, cursor
    if conn is None or not conn.is_connected():
        conn, cursor = connect_with_retry()


# Channel information
CHANNEL_USERNAME = "+FeWz7cHA7I42Y2Vk"  # For subscription verification (chat ID)
CHANNEL_URL = "https://t.me/+FeWz7cHA7I42Y2Vk"  # For the button and links
CHANNEL_NAME = "(Egypt) 🔝"  # Channel name for display in messages
PAYMENT_METHODS = ["اتصالات كاش", "أورانج كاش", "فودافون كاش", "باي بال", "بينانس", "ويسترن يونيون", "إنستاباي"]
user_withdraw_requests = {}

# States for ConversationHandler - fixing admin functionality
AWAITING_BROADCAST = 1
AWAITING_IMAGE_BROADCAST = 2
AWAITING_IMAGE_CAPTION = 3
AWAITING_AMOUNT = 4
AWAITING_PAYMENT_METHOD = 5
AWAITING_PAYMENT_INFO = 6


# Function to add a new user
def add_user(user_id, username, referred_by=None):
    ensure_connection()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        referral_code = f"ref{random.randint(1000, 9999)}"
        if not username:
            username = f"User_{user_id}"
        cursor.execute("""
            INSERT INTO users (user_id, username, balance, referral_code, referred_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, username, 0, referral_code, referred_by))
        conn.commit()


# Function to check if the user is subscribed to the channel
async def is_user_subscribed(user_id, context):
    try:
        chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False


# Start command handler
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    referred_by = None

    if context.args:
        referred_by = context.args[0]

    user_keyboard = ReplyKeyboardMarkup(
        [["💰 التحقق من الرصيد", "🎁 دعوة صديق"], ["💵 سحب الرصيد"]],
        resize_keyboard=True
    )

    ensure_connection()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user.id,))
    existing_user = cursor.fetchone()

    referral_link = f"https://t.me/Easy_Money_win_bot?start={user.id}"
    message = (
        "من كل شخص تقوم بدعوته سوف تكسب 1 جنيه مصري 🔥\n\n"
        f"شارك هذا الرابط مع أصدقائك:\n\n{referral_link}"
    )

    await update.message.reply_text(message, reply_markup=user_keyboard)

    if not existing_user:
        add_user(user.id, user.username, referred_by)

        if referred_by:
            referred_by = int(referred_by)
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (referred_by,))
            referrer = cursor.fetchone()

            if referrer:
                cursor.execute("UPDATE users SET balance = balance + 1 WHERE user_id = %s", (referred_by,))
                conn.commit()

                cursor.execute("UPDATE users SET referred_by = %s WHERE user_id = %s", (referred_by, user.id))
                conn.commit()

                await context.bot.send_message(
                    chat_id=referred_by,
                    text=f"🎉 انضم صديق باستخدام رابط الدعوة الخاص بك! لقد ربحت 1 جنيه مصري!",
                    reply_markup=user_keyboard
                )

    return ConversationHandler.END


# Command handler for user commands
async def handle_user_commands(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    # Skip processing if this is admin
    if user_id == ADMIN_ID:
        return ConversationHandler.END

    if text == "💰 التحقق من الرصيد":
        ensure_connection()
        cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        if result:
            balance = result[0]
            await update.message.reply_text(f"رصيدك: {balance} جنيه مصري")
        else:
            await update.message.reply_text("❌ حدث خطأ: لم يتم العثور على حسابك.")
        return ConversationHandler.END

    elif text == "🎁 دعوة صديق":
        referral_link = f"https://t.me/Easy_Money_win_bot?start={user_id}"
        await update.message.reply_text(
            "من كل شخص تقوم بدعوته سوف تكسب 1 جنيه مصري 🔥\n\n"
            f"شارك هذا الرابط مع أصدقائك:\n\n{referral_link}"
        )
        return ConversationHandler.END

    elif text == "💵 سحب الرصيد":
        if await is_user_subscribed(user_id, context):
            print(f"[DEBUG] User {user_id} selected Withdraw Balance")
            await update.message.reply_text("أدخل المبلغ الذي تريد سحبه:")
            return AWAITING_AMOUNT
        else:
            await update.message.reply_text(
                f"لسحب الرصيد، يجب عليك الانضمام إلى [قناتنا]({CHANNEL_URL}) أولاً.\n"
                "بمجرد الانضمام، اضغط على 'سحب الرصيد' مرة أخرى.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END

    await update.message.reply_text("❌ خيار غير صالح. يرجى اختيار خيار من القائمة.")
    return ConversationHandler.END


# Handler for withdraw amount input
async def handle_withdraw_amount(update: Update, context: CallbackContext):
    user_keyboard = ReplyKeyboardMarkup(
        [["💰 التحقق من الرصيد", "🎁 دعوة صديق"], ["💵 سحب الرصيد"]],
        resize_keyboard=True
    )
    user_id = update.message.from_user.id
    text = update.message.text

    print(f"[DEBUG] Received withdraw amount input: {text} from user {user_id}")

    try:
        amount = int(text)

        ensure_connection()
        cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if result is None:
            await update.message.reply_text("❌ حدث خطأ: لم يتم العثور على حسابك في قاعدة البيانات.")
            return ConversationHandler.END

        balance = result[0]

        # تعديل الحد الأدنى للسحب إلى 15 جنيهًا
        if balance < 15:
            await update.message.reply_text(
                "❌ رصيدك الحالي أقل من الحد الأدنى المسموح به للسحب (15 جنيه مصري). "
                "قم بدعوة المزيد من الأصدقاء لزيادة رصيدك! 💰",
                reply_markup=user_keyboard
            )
            return ConversationHandler.END

        if amount > balance:
            await update.message.reply_text(f"❌ رصيد غير كافٍ! لديك فقط {balance} جنيه مصري. يرجى إدخال مبلغ صالح.",
                                            reply_markup=user_keyboard)
            return ConversationHandler.END
        elif amount <= 0:
            await update.message.reply_text("❌ يرجى إدخال مبلغ أكبر من 0.", reply_markup=user_keyboard)
            return ConversationHandler.END

        print(f"[DEBUG] Saving withdraw request: {amount} for user {user_id}")

        user_withdraw_requests[user_id] = amount

        payment_keyboard = ReplyKeyboardMarkup([[method] for method in PAYMENT_METHODS], resize_keyboard=True)
        await update.message.reply_text("✅ اختر طريقة السحب:", reply_markup=payment_keyboard)

        return AWAITING_PAYMENT_METHOD

    except ValueError:
        await update.message.reply_text("❌ يرجى إدخال رقم صحيح.")
        return AWAITING_AMOUNT


# Handler for payment method selection
async def handle_payment_method(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    print(f"[DEBUG] User {user_id} selected payment method: {text}")

    if text in PAYMENT_METHODS:
        amount = user_withdraw_requests.get(user_id)

        if amount is None:
            await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")
            return ConversationHandler.END

        user_withdraw_requests[user_id] = {"amount": amount, "method": text}

        if text in ["باي بال", "بينانس", "ويسترن يونيون"]:
            await update.message.reply_text(f"أدخل بريدك الإلكتروني الخاص بـ {text}:")
        else:
            await update.message.reply_text("أدخل رقم هاتفك المرتبط بطريقة الدفع:")

        return AWAITING_PAYMENT_INFO
    else:
        await update.message.reply_text("❌ يرجى اختيار طريقة دفع صالحة من القائمة.")
        return AWAITING_PAYMENT_METHOD


# Function to validate phone number
def is_valid_phone_number(number, method):
    if not number.isdigit() or len(number) != 11:
        return False

    if method == "فودافون كاش" and not number.startswith("010"):
        return False
    elif method == "اتصالات كاش" and not number.startswith("011"):
        return False
    elif method == "أورانج كاش" and not number.startswith("012"):
        return False

    return True


# Function to validate email
def is_valid_email(email):
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_regex, email)


# Handler for payment info input
async def handle_payment_info(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    withdraw_data = user_withdraw_requests.get(user_id)
    if not withdraw_data:
        await update.message.reply_text("❌ حدث خطأ ما. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

    amount = withdraw_data["amount"]
    method = withdraw_data["method"]

    if method in ["باي بال", "بينانس", "ويسترن يونيون"]:
        if not is_valid_email(text):
            await update.message.reply_text("❌ تنسيق البريد الإلكتروني غير صالح! يرجى إدخال بريد إلكتروني صالح.")
            return AWAITING_PAYMENT_INFO
    else:
        if not is_valid_phone_number(text, method):
            await update.message.reply_text(f"❌ رقم الهاتف غير صالح! يرجى إدخال رقم {method} صالح.")
            return AWAITING_PAYMENT_INFO

    user_withdraw_requests[user_id]["info"] = text

    ensure_connection()
    cursor.execute("""
        INSERT INTO withdrawals (user_id, amount, method, payment_info, status)
        VALUES (%s, %s, %s, %s, 'pending')
    """, (user_id, amount, method, text))
    conn.commit()

    user_keyboard = ReplyKeyboardMarkup(
        [["💰 التحقق من الرصيد", "🎁 دعوة صديق"], ["💵 سحب الرصيد"]],
        resize_keyboard=True
    )

    await update.message.reply_text(
        f"✅ تم تسجيل طلب السحب الخاص بك بمبلغ {amount} جنيه مصري عبر {method}. سيتم مراجعته قريبًا.",
        reply_markup=user_keyboard
    )
    return ConversationHandler.END


# Admin command handler - FIXED
async def admin(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    logger.info(f"Admin command received from user {user_id}")

    if user_id != ADMIN_ID:
        logger.warning(f"Unauthorized admin access attempt by user {user_id}")
        await update.message.reply_text("❌ الوصول مرفوض.")
        return ConversationHandler.END

    admin_keyboard = ReplyKeyboardMarkup(
        [["📢 رسالة جماعية", "👥 عرض عدد المستخدمين"], ["📷 إرسال صورة جماعية", "📋 عرض طلبات السحب"]],
        resize_keyboard=True
    )

    logger.info("Sending admin panel to admin")
    await update.message.reply_text("🔹 لوحة تحكم الأدمن\nاختر خيارًا:", reply_markup=admin_keyboard)
    return ConversationHandler.END


# Handler for admin text commands
async def handle_admin_text(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    # Verify this is the admin
    if user_id != ADMIN_ID:
        return ConversationHandler.END

    logger.info(f"Admin text command received: {text}")

    admin_keyboard = ReplyKeyboardMarkup(
        [["📢 رسالة جماعية", "👥 عرض عدد المستخدمين"], ["📷 إرسال صورة جماعية", "📋 عرض طلبات السحب"]],
        resize_keyboard=True
    )

    if text == "📢 رسالة جماعية":
        await update.message.reply_text("✏️ أدخل الرسالة التي تريد إرسالها:")
        return AWAITING_BROADCAST

    elif text == "👥 عرض عدد المستخدمين":
        ensure_connection()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        await update.message.reply_text(f"👥 إجمالي المستخدمين: {count}")
        return ConversationHandler.END

    elif text == "📷 إرسال صورة جماعية":
        await update.message.reply_text("📷 أرسل الصورة التي تريد إرسالها لجميع المستخدمين:")
        return AWAITING_IMAGE_BROADCAST

    elif text == "📋 عرض طلبات السحب":
        ensure_connection()
        cursor.execute(
            "SELECT id, user_id, amount, method, payment_info, status FROM withdrawals WHERE status = 'pending'")
        withdrawals = cursor.fetchall()

        if not withdrawals:
            await update.message.reply_text("لا توجد طلبات سحب معلقة.")
            return ConversationHandler.END

        for withdrawal in withdrawals:
            withdrawal_id, user_id, amount, method, payment_info, status = withdrawal
            message = (
                f"🆔 طلب رقم: {withdrawal_id}\n"
                f"👤 المستخدم: {user_id}\n"
                f"💵 المبلغ: {amount} جنيه مصري\n"
                f"💳 الطريقة: {method}\n"
                f"📧 معلومات الدفع: {payment_info}\n"
                f"📅 الحالة: {status}"
            )

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ قبول", callback_data=f"approve_{withdrawal_id}"),
                 InlineKeyboardButton("❌ رفض", callback_data=f"reject_{withdrawal_id}")]
            ])

            await update.message.reply_text(message, reply_markup=keyboard)
        return ConversationHandler.END

    # Default - return to admin panel
    await update.message.reply_text("🔹 لوحة تحكم الأدمن\nاختر خيارًا:", reply_markup=admin_keyboard)
    return ConversationHandler.END


# Handler for broadcast message
async def handle_broadcast_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    # Verify this is the admin
    if user_id != ADMIN_ID:
        return ConversationHandler.END

    message_to_send = text
    admin_keyboard = ReplyKeyboardMarkup(
        [["📢 رسالة جماعية", "👥 عرض عدد المستخدمين"], ["📷 إرسال صورة جماعية", "📋 عرض طلبات السحب"]],
        resize_keyboard=True
    )

    logger.info("Preparing to broadcast message to all users")

    ensure_connection()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent_count = 0

    for user in users:
        try:
            await context.bot.send_message(chat_id=user[0], text=message_to_send)
            sent_count += 1
        except Exception as e:
            logger.error(f"Could not send message to {user[0]}: {e}")

    await update.message.reply_text(f"✅ تم إرسال الرسالة إلى {sent_count} مستخدم.", reply_markup=admin_keyboard)
    return ConversationHandler.END


# Handler for image broadcast (receive photo)
async def handle_image_broadcast(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # Verify this is the admin
    if user_id != ADMIN_ID:
        return ConversationHandler.END

    if update.message.photo:
        photo = update.message.photo[-1].file_id
        context.user_data["photo_file_id"] = photo

        cancel_keyboard = ReplyKeyboardMarkup([["❌ إلغاء"]], resize_keyboard=True)
        await update.message.reply_text(
            "📝 أدخل النص الذي تريد إرساله مع الصورة (أو اضغط 'إلغاء' للتخطي عن الكابشن):",
            reply_markup=cancel_keyboard
        )
        return AWAITING_IMAGE_CAPTION
    else:
        await update.message.reply_text("❌ يرجى إرسال صورة صالحة.")
        return AWAITING_IMAGE_BROADCAST


# Handler for image caption
async def handle_image_caption(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    # Verify this is the admin
    if user_id != ADMIN_ID:
        return ConversationHandler.END

    photo = context.user_data.get("photo_file_id")
    admin_keyboard = ReplyKeyboardMarkup(
        [["📢 رسالة جماعية", "👥 عرض عدد المستخدمين"], ["📷 إرسال صورة جماعية", "📋 عرض طلبات السحب"]],
        resize_keyboard=True
    )

    if text == "❌ إلغاء":
        await update.message.reply_text(
            "✅ تم إلغاء إرسال الصورة الجماعية.",
            reply_markup=admin_keyboard
        )
        return ConversationHandler.END

    logger.info(f"Caption entered by admin: {text}")

    join_button = InlineKeyboardButton(
        text="انضم إلينا 🚀",
        url=CHANNEL_URL
    )
    keyboard = InlineKeyboardMarkup([[join_button]])

    ensure_connection()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    sent_count = 0

    for user in users:
        try:
            await context.bot.send_photo(
                chat_id=user[0],
                photo=photo,
                caption=text if text else "",
                reply_markup=keyboard
            )
            sent_count += 1
            logger.info(f"Photo sent to user {user[0]} with caption: {text}")
        except Exception as e:
            logger.error(f"Could not send photo to {user[0]}: {e}")

    await update.message.reply_text(
        f"✅ تم إرسال الصورة إلى {sent_count} مستخدم.",
        reply_markup=admin_keyboard
    )
    return ConversationHandler.END


# Handler for withdrawal actions
async def handle_withdrawal_action(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    action, withdrawal_id = query.data.split("_")
    withdrawal_id = int(withdrawal_id)

    ensure_connection()
    cursor.execute("SELECT user_id, amount, method FROM withdrawals WHERE id = %s", (withdrawal_id,))
    withdrawal = cursor.fetchone()

    if not withdrawal:
        await query.edit_message_text("❌ الطلب غير موجود.")
        return

    user_id, amount, method = withdrawal

    if action == "approve":
        cursor.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
        user_balance = cursor.fetchone()[0]

        if user_balance < amount:
            await query.edit_message_text("❌ لا يمكن قبول الطلب. الرصيد غير كافٍ.")
            return

        cursor.execute("UPDATE users SET balance = balance - %s WHERE user_id = %s", (amount, user_id))
        conn.commit()

        cursor.execute("UPDATE withdrawals SET status = 'approved', processed_at = NOW() WHERE id = %s",
                       (withdrawal_id,))
        conn.commit()

        await context.bot.send_message(chat_id=user_id,
                                       text=f"✅ تم قبول طلب السحب الخاص بك بمبلغ {amount} جنيه مصري عبر {method}.")
        await query.edit_message_text("✅ تم قبول الطلب.")

    elif action == "reject":
        cursor.execute("UPDATE withdrawals SET status = 'rejected', processed_at = NOW() WHERE id = %s",
                       (withdrawal_id,))
        conn.commit()

        await context.bot.send_message(chat_id=user_id, text=f"❌ تم رفض طلب السحب الخاص بك بمبلغ {amount} جنيه مصري.")
        await query.edit_message_text("❌ تم رفض الطلب.")


# Error handler
async def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Update {update} caused error {context.error}")
    if str(context.error).startswith("Conflict: terminated by other getUpdates request"):
        logger.warning("Another instance of the bot is running. Stopping this instance.")
        raise SystemExit("Stopping bot due to conflict with another instance.")


def main():
    logger.info("Starting the bot...")
    app = Application.builder().token(TOKEN).build()

    # Basic handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    # Admin conversation handler with all states
    admin_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & filters.User(user_id=ADMIN_ID), handle_admin_text),
        ],
        states={
            AWAITING_BROADCAST: [
                MessageHandler(filters.TEXT & filters.User(user_id=ADMIN_ID), handle_broadcast_message)],
            AWAITING_IMAGE_BROADCAST: [
                MessageHandler(filters.PHOTO & filters.User(user_id=ADMIN_ID), handle_image_broadcast)],
            AWAITING_IMAGE_CAPTION: [
                MessageHandler(filters.TEXT & filters.User(user_id=ADMIN_ID), handle_image_caption)],
        },
        fallbacks=[MessageHandler(filters.TEXT & filters.User(user_id=ADMIN_ID), handle_admin_text)],
        name="admin_conversation",
        persistent=False
    )
    app.add_handler(admin_conv_handler)

    # User conversation handler with all states
    user_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.User(user_id=ADMIN_ID), handle_user_commands),
        ],
        states={
            AWAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_amount)],
            AWAITING_PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_method)],
            AWAITING_PAYMENT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_info)],
        },
        fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_commands)],
        name="user_conversation",
        persistent=False
    )
    app.add_handler(user_conv_handler)

    # Callback handler for inline buttons
    app.add_handler(CallbackQueryHandler(handle_withdrawal_action))

    # Error handler
    app.add_error_handler(error_handler)

    logger.info("Bot is running with polling...")
    app.run_polling()


if __name__ == "__main__":
    main()