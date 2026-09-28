import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ChannelPostHandler,
    CallbackQueryHandler
)

# ==================== البيانات الخاصة بك ====================
BOT_TOKEN = "8923128265:AAGb3wUl4OVD_Jpfu3gOQjZTU6x7uqDIc7c"
ADMIN_CHAT_ID = 5209535939
CHANNEL_USERNAME = "@opportunity_master_channel"
CHANNEL_LINK = "https://t.me/opportunity_master_channel"
# ============================================================

USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

users_db = load_users()
pending_posts = {}

async def is_user_subscribed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"خطأ في فحص الاشتراك: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start لتسجيل المشتركين والفحص"""
    user_id = update.effective_user.id
    subscribed = await is_user_subscribed(context, user_id)

    if subscribed:
        if user_id not in users_db:
            users_db.add(user_id)
            save_users(users_db)

        await update.message.reply_text(
            "أهلاً بك! تم التحقق من اشتراكك بنجاح ✅\nيمكنك الآن استخدام البوت بحرية."
        )
    else:
        keyboard = [
            [InlineKeyboardButton("📢 اشترك بالقناة من هنا", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "عذراً! يجب عليك الاشتراك في قناة البوت الرسمية أولاً لاستخدام البوت.\n\nاشترك ثم اضغط على زر (تحقق من الاشتراك):",
            reply_markup=reply_markup
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ضغطات الأزرار"""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    if data == "check_sub":
        subscribed = await is_user_subscribed(context, user_id)
        if subscribed:
            if user_id not in users_db:
                users_db.add(user_id)
                save_users(users_db)
                
            await query.edit_message_text("تم التحقق من اشتراكك بنجاح ✅! أهلاً بك في البوت.")
        else:
            await query.answer("لم تشترك بالقناة بعد! يرجى الاشتراك أولاً ❌", show_alert=True)

    elif data.startswith("share_") or data.startswith("cancel_"):
        action, post_id_str = data.split("_")
        post_id = int(post_id_str)

        if action == "share":
            if post_id in pending_posts:
                post_data = pending_posts[post_id]
                success_count = 0
                
                for u_id in list(users_db):
                    try:
                        await context.bot.copy_message(
                            chat_id=u_id,
                            from_chat_id=post_data["chat_id"],
                            message_id=post_data["message_id"]
                        )
                        success_count += 1
                    except Exception:
                        pass
                
                await query.edit_message_text(f"تمت مشاركة المنشور بنجاح مع {success_count} مشترك ✅")
                del pending_posts[post_id]
            else:
                await query.edit_message_text("انتهت صلاحية الطلب.")

        elif action == "cancel":
            if post_id in pending_posts:
                del pending_posts[post_id]
            await query.edit_message_text("تم إلغاء مشاركة المنشور ❌")

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال منشورات القناة وتوجيه إشعار للأدمن"""
    channel_post = update.channel_post
    if not channel_post:
        return
    
    post_id = channel_post.message_id
    channel_id = channel_post.chat_id
    
    pending_posts[post_id] = {
        "chat_id": channel_id,
        "message_id": post_id
    }

    keyboard = [
        [
            InlineKeyboardButton("نعم ✅", callback_data=f"share_{post_id}"),
            InlineKeyboardButton("لا ❌", callback_data=f"cancel_{post_id}")
        ]
    ]

    post_text = channel_post.text or channel_post.caption or "[منشور يحتوي وسائط/ميديا]"

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"📌 **منشور جديد في القناة:**\n\n{post_text}\n\nهل تريد مشاركة هذا المنشور مع مشتركي البوت؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChannelPostHandler(handle_channel_post))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("البوت يعمل الآن ومربوط بالقناة والحساب بنجاح...")
    app.run_polling()
