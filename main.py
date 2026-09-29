import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = "8923128265:AAEu6b8YRv9faBeON83N6Nr8L54Z9GL-Q-k"
ADMIN_ID = 123456789  # ضع آيدي حسابك الأدمن هنا (رقم)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# 1️⃣ تعريف حالة انتظار الوسائط (FSM)
class Form(StatesGroup):
    waiting_for_proof = State()

# 📌 لوحة القائمة الرئيسية (مثال)
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="مشاركة إصابة 🖼️"), KeyboardButton(text="الدعم 🎧")],
        [KeyboardButton(text="المحفظة 💳"), KeyboardButton(text="الإحالات 👥")]
    ],
    resize_keyboard=True
)

# 📌 لوحة الإلغاء أثناء الإرسال
cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="إلغاء 🚫")],
        [KeyboardButton(text="القائمة الرئيسية 🔗")]
    ],
    resize_keyboard=True
)


# 2️⃣ عند الضغط على زر "مشاركة إصابة"
@dp.message(F.text.contains("مشاركة إصابة"))
async def start_proof_submission(message: types.Message, state: FSMContext):
    # تفعيل حالة الانتظار
    await state.set_state(Form.waiting_for_proof)
    
    text = (
        "🖼️ <b>مشاركة إصابة</b>\n\n"
        "💬 أرسل صورة أرباحك، ويمكنك إضافة تعليق اختياري.\n\n"
        "أرسل الصورة أو الفيديو الآن:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=cancel_keyboard)


# 3️⃣ إلغاء العملية والعودة للقائمة الرئيسية
@dp.message(Form.waiting_for_proof, F.text.in_(["إلغاء 🚫", "القائمة الرئيسية 🔗"]))
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ تم إلغاء العملية والعودة للقائمة الرئيسية.", reply_markup=main_keyboard)


# 4️⃣ استقبال الصورة أو الفيديو وإرسالها للأدمن
@dp.message(Form.waiting_for_proof, F.photo | F.video)
async def process_proof(message: types.Message, state: FSMContext):
    user = message.from_user
    caption_text = message.caption if message.caption else "بدون تعليق"
    
    # تجهيز رسالة التنبيه للأدمن مع معلومات المستخدم
    admin_info = (
        "📥 <b>مشاركة إصابة جديدة!</b>\n\n"
        f"👤 <b>المستخدم:</b> {user.full_name}\n"
        f"🆔 <b>الآيدي:</b> <code>{user.id}</code>\n"
        f"🔗 <b>اليوزر:</b> @{user.username if user.username else 'لا يوجد'}\n\n"
        f"💬 <b>التعليق/الوصف:</b>\n{caption_text}"
    )

    # إرسال الملف للأدمن (سواء كان صورة أو فيديو)
    if message.photo:
        await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=admin_info, parse_mode="HTML")
    elif message.video:
        await bot.send_video(chat_id=ADMIN_ID, video=message.video.file_id, caption=admin_info, parse_mode="HTML")

    # إنهاء الحالة وإعادة القائمة الرئيسية للمستخدم
    await state.clear()
    await message.answer("✅ تم إرسال مشاركتك للآدمن بنجاح، شكراً لك!", reply_markup=main_keyboard)


# 5️⃣ التعامل مع النصوص العشوائية أثناء انتظار الصورة
@dp.message(Form.waiting_for_proof)
async def invalid_input(message: types.Message):
    await message.answer("⚠️ يرجى إرسال <b>صورة</b> أو <b>فيديو</b> (مع تعليق اختياري)، أو اضغط على إلغاء.", parse_mode="HTML")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
