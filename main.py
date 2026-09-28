import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import random
import string

# 📌 التوكن الحالي الخاص بك
API_TOKEN = '8923128265:AAGb3wUl4OVD_Jpfu3gOQjZTU6x7uqDIc7c'

# 📌 أيدي الأدمن الثابت الخاص بك
ADMIN_ID = 5209535939 

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

database = {}
pending_accounts = {}
pending_deposits = {}
unconfirmed_withdrawals = {}
pending_withdrawals = {}

def format_syp(amount):
    try:
        return f"{int(amount):,}".replace(',', '.')
    except Exception:
        return str(amount)

def format_phone(phone):
    if not phone:
        return "غير متوفر"
    clean_phone = str(phone).strip().replace("+", "")
    if clean_phone.startswith("963") and len(clean_phone) > 3:
        return f"+963 - {clean_phone[3:]}"
    return phone

class Form(StatesGroup):
    deposit_amount = State()
    deposit_operation_number = State()
    withdraw_method = State()
    withdraw_amount = State()
    withdraw_account_code = State()
    waiting_for_display_name = State()
    waiting_for_phone = State()
    waiting_for_ichancy_username = State()
    waiting_for_ichancy_password = State()
    waiting_for_support_message = State()

class AdminForm(StatesGroup):
    target_user_id = State()
    amount = State()
    message = State()

def main_menu(user_id=None):
    kb = [
        [InlineKeyboardButton(text="🔹 حساب ايشانسي", callback_data="ichancy_account")],
        [
            InlineKeyboardButton(text="📥 شحن محفظة البوت", callback_data="deposit"),
            InlineKeyboardButton(text="📤 سحب حوالة مالية", callback_data="withdraw")
        ],
        [InlineKeyboardButton(text="👥 الإحالات", callback_data="referrals")],
        [
            InlineKeyboardButton(text="📊 السجلات", callback_data="logs"),
            InlineKeyboardButton(text="🎧 دعم Opportunity Master", callback_data="support")
        ],
        [InlineKeyboardButton(text="🎮 الدخول المباشر لألعاب الموقع", url="https://www.ichancy.com")]
    ]
    if user_id == ADMIN_ID:
        kb.insert(0, [InlineKeyboardButton(text="👑 لوحة تحكم الأدمن", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    if user_id not in database:
        database[user_id] = {
            "balance": 0, 
            "display_name": "مستخدم", 
            "phone": "غير متوفر", 
            "accounts": [],
            "referrals": [],
            "real_referrals": [],
            "ref_earnings": 0,
            "referred_by": None,
            "logs": []
        }
        
        args = message.text.split()
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                referrer_id = int(args[1].replace("ref_", ""))
                if referrer_id != user_id and referrer_id in database:
                    if database[user_id]["referred_by"] is None:
                        database[user_id]["referred_by"] = referrer_id
                        if user_id not in database[referrer_id]["referrals"]:
                            database[referrer_id]["referrals"].append(user_id)
                            database[referrer_id]["logs"].append(f"👥 انضم مستخدم جديد عبر رابط إحالتك (ID: {user_id})")
                            
                            # 🔔 إشعار فوري للمُحيل بانضمام مستخدم جديد
                            try:
                                await bot.send_message(
                                    referrer_id, 
                                    f"🔔 <b>إشعار فوري:</b> انضم مستخدم جديد عبر رابط الإحالة الخاص بك! (ID: <code>{user_id}</code>)", 
                                    parse_mode="HTML"
                                )
                            except Exception:
                                pass
                    else:
                        if database[user_id]["referred_by"] != referrer_id:
                            await message.answer("❌ عذراً، أنت تابع لإحالة سابقة ولا تُحسب كإحالة جديدة.")
            except Exception:
                pass

    d_name = database[user_id].get("display_name", "مستخدم")
    balance = format_syp(database[user_id].get("balance", 0))

    if d_name and d_name != "مستخدم":
        greeting = f"⚡ <b>أهلاً بك يا {d_name} في بوت Opportunity Master</b>"
    else:
        greeting = f"⚡ <b>أهلاً بك في بوت Opportunity Master</b>"

    welcome_text = (
        f"{greeting}\n\n"
        f"🟡 رصيد محفظتك: <b>{balance} SYP</b>\n"
        f"🆔 ID: <code>{user_id}</code>"
    )
    await message.answer(welcome_text, reply_markup=main_menu(user_id), parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "back_to_home")
async def back_to_home(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    d_name = database.get(user_id, {}).get("display_name", "مستخدم")
    balance = format_syp(database.get(user_id, {}).get("balance", 0))
    
    if d_name and d_name != "مستخدم":
        greeting = f"⚡ <b>أهلاً بك يا {d_name} في بوت Opportunity Master</b>"
    else:
        greeting = f"⚡ <b>أهلاً بك في بوت Opportunity Master</b>"

    welcome_text = (
        f"{greeting}\n\n"
        f"🟡 رصيد محفظتك: <b>{balance} SYP</b>\n"
        f"🆔 ID: <code>{user_id}</code>"
    )
    await callback.message.edit_text(welcome_text, reply_markup=main_menu(user_id), parse_mode="HTML")
    await callback.answer()

async def show_single_account_view(callback_or_message, acc, is_callback=True):
    text = (
        f"📌 <b>بيانات تسجيل الدخول لحساب ايشانسي</b>\n\n"
        f"🟣 <b>الحساب الافتراضي</b>\n"
        f"👤 اسم المستخدم: <code>{acc['username']}</code>\n"
        f"🔑 كلمة السر: <code>{acc['password']}</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ الدخول المباشر للحساب", url="https://www.ichancy.com")],
        [InlineKeyboardButton(text="📥 شحن محفظة البوت", callback_data="deposit")],
        [InlineKeyboardButton(text="🏠 رجوع", callback_data="back_to_home")]
    ])
    if is_callback:
        await callback_or_message.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback_or_message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "ichancy_account")
async def ichancy_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in database:
        database[user_id] = {"balance": 0, "display_name": "مستخدم", "phone": "غير متوفر", "accounts": [], "referrals": [], "real_referrals": [], "ref_earnings": 0, "referred_by": None, "logs": []}

    user_data = database[user_id]
    accounts = user_data["accounts"]
    
    if len(accounts) == 1:
        await show_single_account_view(callback, accounts[0], is_callback=True)
        await callback.answer()
        return
    elif len(accounts) > 1:
        text = (
            f"📌 <b>حساباتي على ايشانسي</b>\n\n"
            f"لديك {len(accounts)} حسابات. اختر الحساب الذي تريد إدارته:\n"
            f"🟣 يشير إلى الحساب الافتراضي\n\n"
            f"للذهاب الى الموقع من المتصفح <a href='https://www.ichancy.com'>انقر هنا</a> 🔗"
        )
        kb_buttons = []
        for i, acc in enumerate(accounts):
            prefix = "🟣 " if i == 0 else ""
            kb_buttons.append([InlineKeyboardButton(text=f"{prefix}{acc['username']}", callback_data=f"select_acc_{acc['username']}")])
        
        kb_buttons.append([InlineKeyboardButton(text="إنشاء حساب جديد", callback_data="create_new_ichancy")])
        kb_buttons.append([InlineKeyboardButton(text="🏠 رجوع", callback_data="back_to_home")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    if user_data["display_name"] == "مستخدم":
        await callback.message.answer("🔹 <b>إنشاء حساب ايشانسي جديد</b>\n\nاكتب اسمك الكامل (أحرف عربية أو إإنجليزية فقط):", parse_mode="HTML")
        await state.set_state(Form.waiting_for_display_name)
    else:
        await callback.message.answer(
            f"أهلاً بك يا <b>{user_data['display_name']}</b> 👑\n\n"
            "أرسل اسم المستخدم لحساب ايشانسي الجديد:\n"
            "• 6 أحرف على الأقل.\n"
            "• يحتوي على أرقام.\n"
            "• بدون مسافات أو فراغات.",
            parse_mode="HTML"
        )
        await state.set_state(Form.waiting_for_ichancy_username)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("select_acc_"))
async def select_specific_account(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    target_username = callback.data.replace("select_acc_", "")
    accounts = database.get(user_id, {}).get("accounts", [])
    selected_acc = next((acc for acc in accounts if acc["username"] == target_username), None)
    if selected_acc:
        await show_single_account_view(callback, selected_acc, is_callback=True)
    else:
        await callback.answer("لم يتم العثور على الحساب.", show_alert=True)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "create_new_ichancy")
async def create_new_ichancy_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🔹 <b>إنشاء حساب ايشانسي إضافي جديد</b>\n\n"
        "أرسل اسم المستخدم لحساب ايشانسي الجديد:\n"
        "• 6 أحرف على الأقل.\n"
        "• يحتوي على أرقام.\n"
        "• بدون مسافات أو فراغات.",
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_for_ichancy_username)
    await callback.answer()

@dp.message(Form.waiting_for_display_name)
async def process_display_name(message: types.Message, state: FSMContext):
    display_name = message.text.strip()
    if len(display_name) < 3 or not re.match(r'^[\u0600-\u06FFa-zA-Z\s]+$', display_name):
        await message.answer("❌ الاسم يجب أن يتكون من أحرف (عربية أو إإنجليزية) فقط بدون أرقام أو رموز. أعد كتابة اسمك الكامل:")
        return

    await state.update_data(display_name=display_name)
    phone_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 مشاركة رقم الهاتف", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        f"أهلاً بك يا <b>{display_name}</b>! 👑\n\n"
        "الآن، اضغط على الزر بالأسفل (**📱 مشاركة رقم الهاتف**) لتزويد البوت برقمك تلقائياً:",
        reply_markup=phone_keyboard,
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_for_phone)

@dp.message(Form.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone_number = message.contact.phone_number if message.contact else (message.text.strip() if message.text else None)
    if not phone_number:
        await message.answer("❌ يرجى الضغط على زر **📱 مشاركة رقم الهاتف** في الأسفل حصراً:")
        return
    await state.update_data(phone_number=phone_number)
    await message.answer(
        "ممتاز! تم استلام رقم هاتفك بنجاح. 📱\n\n"
        "الآن أرسل اسم المستخدم لحساب ايشانسي:\n"
        "• 6 أحرف على الأقل.\n"
        "• يحتوي على أرقام.\n"
        "• بدون مسافات أو فراغات.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_for_ichancy_username)

@dp.message(Form.waiting_for_ichancy_username)
async def process_ichancy_username(message: types.Message, state: FSMContext):
    base_name = message.text.strip()
    if len(base_name) < 6 or not any(c.isdigit() for c in base_name) or ' ' in base_name:
        await message.answer("❌ اسم المستخدم يجب ألا يقل عن 6 أحرف، يحتوي على أرقام، **ولا يحتوي على مسافات أو فراغات**. أرسل الاسم مجدداً:")
        return

    final_acc = f"{base_name}@OM"
    for uid, data in database.items():
        for acc in data.get("accounts", []):
            if acc["username"] == final_acc:
                await message.answer("❌ هذا الاسم مستخدم مسبقاً. يرجى اختيار اسم مختلف:")
                return

    await state.update_data(ichancy_username=final_acc)
    await message.answer(
        "🔑 الآن أرسل <b>كلمة المرور</b> التي تريدها لحساب ايشانسي:",
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_for_ichancy_password)

@dp.message(Form.waiting_for_ichancy_password)
async def process_ichancy_password(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    password = message.text.strip()
    if len(password) < 4:
        await message.answer("❌ كلمة المرور قصيرة جداً. يرجى إرسال كلمة مرور مناسبة:")
        return

    data = await state.get_data()
    display_name = data.get("display_name")
    phone_number = data.get("phone_number")
    final_acc = data.get("ichancy_username")

    if user_id not in database:
        database[user_id] = {"balance": 0, "display_name": "مستخدم", "phone": "غير متوفر", "accounts": [], "referrals": [], "real_referrals": [], "ref_earnings": 0, "referred_by": None, "logs": []}

    if display_name: database[user_id]["display_name"] = display_name
    if phone_number: database[user_id]["phone"] = phone_number

    current_d_name = database[user_id]["display_name"]
    current_phone = database[user_id]["phone"]
    formatted_admin_phone = format_phone(current_phone)
    await state.clear()

    req_id = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    pending_accounts[req_id] = {"user_id": user_id, "username": final_acc, "password": password}

    user_data = database[user_id]
    if user_data.get("referred_by"):
        referrer_id = user_data["referred_by"]
        if referrer_id in database:
            referrer_name = database[referrer_id].get("display_name", "مستخدم")
            try:
                admin_notif = (
                    f"🚨 <b>تنبيه إحالة جديدة (أنشأ حساباً):</b>\n\n"
                    f"👤 المستخدم الجديد: <b>{current_d_name}</b>\n"
                    f"🔹 حساب إيشانسي: <code>{final_acc}</code>\n"
                    f"🆔 ID الجديد: <code>{user_id}</code>\n\n"
                    f"🔗 تمت إضافته عن طريق المُحيل:\n"
                    f"👑 اسم المُحيل: <b>{referrer_name}</b>\n"
                    f"🆔 ID المُحيل: <code>{referrer_id}</code>"
                )
                await bot.send_message(ADMIN_ID, admin_notif, parse_mode="HTML")
            except Exception:
                pass

    await message.answer("⏳ <b>تم إرسال طلب إنشاء الحساب بنجاح!</b>\n\nيرجى الانتظار قليلاً ريثما تتم مراجعة وتفعيل الحساب من قبل الإدارة.", parse_mode="HTML")

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة وتفعيل الحساب", callback_data=f"approve_acc_{req_id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"reject_acc_{req_id}")
        ]
    ])

    admin_text = (
        f"🚨 <b>طلب إنشاء حساب ايشانسي جديد بانتظار الموافقة!</b>\n\n"
        f"👑 اللقب: <b>{current_d_name}</b>\n"
        f"📱 الهاتف: <code>{formatted_admin_phone}</code>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🔹 الحساب المطلوب: <code>{final_acc}</code>\n"
        f"🔑 كلمة المرور المدخلة: <code>{password}</code>"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_kb, parse_mode="HTML")
    except Exception as e:
        logging.error(f"تعذر إرسال إشعار طلب الحساب للأدمن: {e}")

@dp.callback_query(lambda c: c.data.startswith("approve_acc_") or c.data.startswith("reject_acc_"))
async def admin_account_review(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    action = parts[0]
    req_id = parts[2]

    if req_id not in pending_accounts:
        await callback.answer("❌ انتهت صلاحية الطلب أو تم معالجته مسبقاً.", show_alert=True)
        return

    req_data = pending_accounts[req_id]
    target_id = req_data["user_id"]
    final_acc = req_data["username"]
    password = req_data["password"]

    if target_id not in database:
        database[target_id] = {"balance": 0, "display_name": "مستخدم", "phone": "غير متوفر", "accounts": [], "referrals": [], "real_referrals": [], "ref_earnings": 0, "referred_by": None, "logs": []}

    if action == "approve":
        new_account_obj = {"username": final_acc, "password": password}
        database[target_id]["accounts"].append(new_account_obj)
        database[target_id]["logs"].append(f"✅ تم تفعيل حساب ايشانسي جديد: {final_acc}")

        # 🔔 إشعار فوري للمستخدم بقبول الحساب
        await bot.send_message(target_id, "🔔 <b>إشعار فوري:</b> 🎉 تم إنشاء وتفعيل الحساب بنجاح! إليك تفاصيل حسابك:", parse_mode="HTML")
        
        class DummyMessage:
            def __init__(self, bot_instance, chat_id):
                self.bot = bot_instance
                self.chat_id = chat_id
            async def answer(self, text, reply_markup=None, parse_mode=None):
                await self.bot.send_message(self.chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

        dummy_msg = DummyMessage(bot, target_id)
        await show_single_account_view(dummy_msg, new_account_obj, is_callback=False)
        await callback.message.edit_text(callback.message.text + "\n\n✅ [تمت الموافقة وتفعيل الحساب بنجاح]", parse_mode="HTML")
    elif action == "reject":
        # 🔔 إشعار فوري للمستخدم برفض الحساب
        await bot.send_message(target_id, "🔔 <b>إشعار فوري:</b> ❌ عذراً، تم رفض طلب إنشاء حساب ايشانسي من قبل الإدارة.", parse_mode="HTML")
        await callback.message.edit_text(callback.message.text + "\n\n❌ [تم رفض الطلب]", parse_mode="HTML")

    del pending_accounts[req_id]
    await callback.answer()

# ==================== لوحة تحكم الأدمن ====================

@dp.callback_query(lambda c: c.data == "admin_panel" and c.from_user.id == ADMIN_ID)
async def admin_panel_handler(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 عرض جميع المستخدمين", callback_data="admin_list_users")],
        [InlineKeyboardButton(text="💸 تحويل رصيد لمستخدم", callback_data="admin_start_transfer")],
        [InlineKeyboardButton(text="🏠 رجوع للقائمة الرئيسية", callback_data="back_to_home")]
    ])
    await callback.message.edit_text("👑 <b>مرحباً بك في لوحة تحكم الأدمن</b>\n\nاختر الإجراء المطلوب:", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_list_users" and c.from_user.id == ADMIN_ID)
async def admin_list_users(callback: types.CallbackQuery):
    if not database:
        await callback.answer("لا توجد بيانات مستخدمين مسجلة حتى الآن.", show_alert=True)
        return
    
    text = "👥 <b>قائمة المستخدمين في البوت:</b>\n\n"
    for uid, data in database.items():
        name = data.get("display_name", "مستخدم")
        bal = format_syp(data.get("balance", 0))
        real_refs = len(data.get("real_referrals", []))
        text += f"• <b>{name}</b> (ID: <code>{uid}</code>)\n  الرصيد: {bal} SYP | إحالات حقيقية: {real_refs}\n\n"
        
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع للوحة التحكم", callback_data="admin_panel")]
    ])
    if len(text) > 4096:
        text = text[:4000] + "\n\n...(تم الاختصار لطول القائمة)"
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "admin_start_transfer" and c.from_user.id == ADMIN_ID)
async def admin_start_transfer(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel")]
    ])
    await callback.message.edit_text("💸 <b>تحويل رصيد لمستخدم</b>\n\nأرسل الآن **ID المستخدم** المراد التحويل إليه:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(AdminForm.target_user_id)
    await callback.answer()

@dp.message(AdminForm.target_user_id)
async def admin_process_target_id(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.strip())
        await state.update_data(target_user_id=target_id)
        await message.answer("💵 أرسل المبلغ المراد تحويله (بالليرة السورية):")
        await state.set_state(AdminForm.amount)
    except ValueError:
        await message.answer("❌ الـ ID يجب أن يتكون من أرقام فقط. أرسل ID صحيح:")

@dp.message(AdminForm.amount)
async def admin_process_amount(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        amount = int(message.text.strip().replace('.', '').replace(',', ''))
        if amount <= 0:
            await message.answer("❌ المبلغ يجب أن يكون أكبر من الصفر:")
            return
        await state.update_data(amount=amount)
        await message.answer("✉️ أرسل رسالة أو سبب التحويل (مثال: 'مكافأة إحالة وشحن' أو 'أرباح حرق'):")
        await state.set_state(AdminForm.message)
    except ValueError:
        await message.answer("❌ يرجى إرسال رقم صحيح للمبلغ:")

@dp.message(AdminForm.message)
async def admin_process_message(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    transfer_msg = message.text.strip()
    data = await state.get_data()
    target_id = data.get("target_user_id")
    amount = data.get("amount")

    if target_id not in database:
        database[target_id] = {"balance": 0, "display_name": "مستخدم", "phone": "غير متوفر", "accounts": [], "referrals": [], "real_referrals": [], "ref_earnings": 0, "referred_by": None, "logs": []}

    database[target_id]["balance"] += amount

    if "إحالة" in transfer_msg or "احالة" in transfer_msg or "حرق" in transfer_msg:
        database[target_id]["ref_earnings"] += amount

    database[target_id]["logs"].append(f"👑 تحويل من الإدارة بقيمة {format_syp(amount)} SYP - السبب: {transfer_msg}")

    # 🔔 إشعار فوري للمستخدم بتحويل رصيد من الإدارة
    try:
        await bot.send_message(
            target_id,
            f"🔔 <b>إشعار فوري:</b> 🎉 وصلك تحويل رصيد من الإدارة!\n\n"
            f"💵 المبلغ: <b>{format_syp(amount)} SYP</b>\n"
            f"✉️ الرسالة: <i>{transfer_msg}</i>",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await message.answer(f"✅ تم تحويل مبلغ **{format_syp(amount)} SYP** إلى المستخدم `({target_id})` بنجاح وتحديث أرباحه ورصيده!", parse_mode="HTML")
    await state.clear()

# ==================== نظام الشحن اليدوي لمحفظة البوت ====================

@dp.callback_query(lambda c: c.data == "deposit")
async def start_deposit_methods(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 شام كاش (Sham Cash)", callback_data="pay_sham")],
        [InlineKeyboardButton(text="📱 سيريتل كاش (Syriatel Cash)", callback_data="pay_syriatel")],
        [InlineKeyboardButton(text="🏠 رجوع", callback_data="back_to_home")]
    ])
    await callback.message.edit_text("📥 <b>اختر طريقة التحويل اليدوي للشحن (ليرة سورية SYP):</b>", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["pay_sham", "pay_syriatel"])
async def select_payment_method(callback: types.CallbackQuery, state: FSMContext):
    method = "شام كاش (Sham Cash)" if callback.data == "pay_sham" else "سيريتل كاش (Syriatel Cash)"
    await state.update_data(payment_method=method)
    
    text = (
        f"💳 <b>طريقة التحويل المختارة: {method}</b>\n\n"
        f"⚠️ <i>ملاحظة: أقل مبلغ للشحن هو {format_syp(20000)} ليرة سورية.</i>\n\n"
        f"👇 <b>يرجى إرسال المبلغ المراد شحنه (بالليرة السورية) الآن:</b>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 إلغاء ورجوع", callback_data="back_to_home")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(Form.deposit_amount)
    await callback.answer()

@dp.message(Form.deposit_amount)
async def process_deposit_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip().replace('.', '').replace(',', ''))
        if amount < 20000:
            await message.answer(f"❌ عذراً، أقل مبلغ للشحن هو {format_syp(20000)} ليرة سورية. يرجى إرسال مبلغ صحيح:")
            return
    except ValueError:
        await message.answer("❌ يرجى إرسال رقم صحيح للمبلغ:")
        return

    await state.update_data(deposit_amount=amount)
    data = await state.get_data()
    method = data.get("payment_method")

    if "شام" in method:
        account_info = "رمز الحساب (التحويل اليدوي):\n<code>21fd15f571f265371ec771ee0a564e1464e14</code>"
    else:
        account_info = "رقم محفظة سيريتل كاش (التحويل اليدوي):\n<code>0930699813</code>"

    text = (
        f"💵 المبلغ المطلوب شحنه: <b>{format_syp(amount)} SYP</b>\n\n"
        f"📌 <b>معلومات الحساب المراد التحويل إليه:</b>\n{account_info}\n\n"
        f"👇 <b>الخطوة الأخيرة:</b>\n"
        f"يرجى تحويل المبلغ يدوياً، ثم أرسل **رقم العملية** فقط الآن:"
    )
    
    await message.answer(text, parse_mode="HTML")
    await state.set_state(Form.deposit_operation_number)

@dp.message(Form.deposit_operation_number)
async def process_deposit_operation_number(message: types.Message, state: FSMContext):
    op_number = message.text.strip()
    user_id = message.from_user.id
    d_name = database.get(user_id, {}).get("display_name", "مستخدم")
    phone = database.get(user_id, {}).get("phone", "غير متوفر")
    formatted_admin_phone = format_phone(phone)
    data = await state.get_data()
    method = data.get("payment_method", "طريقة غير معروفة")
    base_amount = data.get("deposit_amount", 0)
    
    req_id = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    pending_deposits[req_id] = {"user_id": user_id, "amount": base_amount}

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة وشحن حساب ايشانسي", callback_data=f"app_dep_{req_id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"rej_dep_{req_id}")
        ]
    ])

    admin_text = (
        f"🚨 <b>طلب شحن جديد (سيتم شحن ايشانسي فور الموافقة)!</b>\n\n"
        f"👑 اللقب: <b>{d_name}</b>\n"
        f"📱 الهاتف: <code>{formatted_admin_phone}</code>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💳 الطريقة: <b>{method}</b>\n"
        f"💵 المبلغ المدخل: <b>{format_syp(base_amount)} SYP</b>\n"
        f"🔢 رقم العملية: <code>{op_number}</code>"
    )

    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_kb, parse_mode="HTML")
    except Exception as e:
        logging.error(f"خطأ في إرسال طلب الشحن للأدمن: {e}")

    await message.answer("⏳ <b>جاري المعالجة...</b>\nتم إرسال رقم العملية إلى الإدارة للتحقق، وسيتم شحن رصيدك على حسابك فور اعتمادها.", parse_mode="HTML")
    await state.clear()

# ==================== نظام سحب الأرباح ====================

@dp.callback_query(lambda c: c.data == "withdraw")
async def start_withdraw_methods(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 شام كاش (Sham Cash)", callback_data="withdraw_sham")],
        [InlineKeyboardButton(text="📱 سيريتل كاش (Syriatel Cash)", callback_data="withdraw_syriatel")],
        [InlineKeyboardButton(text="🏠 رجوع", callback_data="back_to_home")]
    ])
    await callback.message.edit_text("📤 <b>اختر طريقة السحب المناسبة:</b>", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["withdraw_sham", "withdraw_syriatel"])
async def select_withdraw_method(callback: types.CallbackQuery, state: FSMContext):
    method = "شام كاش (Sham Cash)" if callback.data == "withdraw_sham" else "سيريتل كاش (Syriatel Cash)"
    
    await state.update_data(withdraw_method=method)
    
    text = (
        f"📌 <b>{method} (SYP)</b>\n\n"
        f"💱 العملة: <b>SYP</b>\n"
        f"📥 الحد الأدنى للسحب: <b>SYP {format_syp(50000)}</b>\n"
        f"📤 الحد الأقصى للسحب: <b>SYP {format_syp(220000000)}</b>\n"
        f"🏷️ رسوم السحب: <b>10%</b>\n\n"
        f"👇 <b>ادخل المبلغ الذي تريد سحبه بالليرة السورية:</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 رجوع", callback_data="back_to_home")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(Form.withdraw_amount)
    await callback.answer()

@dp.message(Form.withdraw_amount)
async def process_withdraw_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip().replace('.', '').replace(',', ''))
    except ValueError:
        await message.answer("❌ يرجى إرسال رقم صحيح للمبلغ:")
        return
    
    if amount < 50000:
        await message.answer(f"❌ الحد الأدنى للسحب هو {format_syp(50000)} SYP. يرجى إرسال مبلغ صحيح:")
        return
        
    await state.update_data(withdraw_amount=amount)
    data = await state.get_data()
    method = data.get("withdraw_method")
    
    await message.answer(
        f"💳 المبلغ المحدد: <b>{format_syp(amount)} SYP</b>\n\n"
        f"👇 <b>يرجى إدخال حساب {method} المراد سحب الأموال عليه (رقم الحساب / الرمز):</b>",
        parse_mode="HTML"
    )
    await state.set_state(Form.withdraw_account_code)

@dp.message(Form.withdraw_account_code)
async def process_withdraw_account_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if len(code) < 3:
        await message.answer("❌ حساب التلقي غير صحيح. يرجى إدخال حساب صحيح:")
        return
        
    user_id = message.from_user.id
    data = await state.get_data()
    amount = data.get("withdraw_amount")
    method = data.get("withdraw_method")
    
    fee = int(amount * 0.10)
    net_amount = amount - fee
    
    d_name = database.get(user_id, {}).get("display_name", "مستخدم")
    phone = database.get(user_id, {}).get("phone", "غير متوفر")
    
    req_id = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    unconfirmed_withdrawals[req_id] = {
        "user_id": user_id,
        "amount": amount,
        "method": method,
        "code": code,
        "fee": fee,
        "net_amount": net_amount,
        "phone": phone,
        "d_name": d_name
    }
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تأكيد العملية", callback_data=f"confirm_wit_{req_id}"),
            InlineKeyboardButton(text="❌ إلغاء العملية", callback_data=f"cancel_wit_{req_id}")
        ]
    ])
    
    text = (
        f"⏳ <b>مراجعة تفاصيل طلب السحب:</b>\n\n"
        f"• المبلغ المطلوب سحبه: <b>{format_syp(amount)} SYP</b>\n"
        f"• رسوم التحويل (10%): <b>{format_syp(fee)} SYP</b>\n"
        f"• الصافي المستلم: <b>{format_syp(net_amount)} SYP</b>\n"
        f"• حساب التلقي: <code>{code}</code>\n\n"
        f"👇 <b>يرجى التأكيد أو إلغاء العملية:</b>"
    )
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("confirm_wit_") or c.data.startswith("cancel_wit_"))
async def user_withdraw_confirmation(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    action = parts[0]
    req_id = parts[2]
    
    if req_id not in unconfirmed_withdrawals:
        await callback.answer("❌ انتهت صلاحية الطلب أو تم معالجته مسبقاً.", show_alert=True)
        return
        
    data = unconfirmed_withdrawals[req_id]
    user_id = data["user_id"]
    
    if callback.from_user.id != user_id:
        await callback.answer("❌ هذا الطلب ليس لك.", show_alert=True)
        return
        
    if action == "cancel":
        del unconfirmed_withdrawals[req_id]
        await callback.message.edit_text("❌ <b>تم إلغاء العملية بنجاح.</b>", parse_mode="HTML")
        await callback.answer()
        return
        
    amount = data["amount"]
    method = data["method"]
    code = data["code"]
    fee = data["fee"]
    net_amount = data["net_amount"]
    d_name = data["d_name"]
    formatted_admin_phone = format_phone(data["phone"])
    
    user_accounts = database.get(user_id, {}).get("accounts", [])
    if user_accounts:
        ichancy_accounts_str = "\n".join([f"• <code>{acc['username']}</code>" for acc in user_accounts])
    else:
        ichancy_accounts_str = "⚠️ لا توجد حسابات ايشانسي مسجلة في البوت"
        
    pending_withdrawals[req_id] = {"user_id": user_id, "amount": amount}
    del unconfirmed_withdrawals[req_id]
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ موافقة وتأكيد السحب", callback_data=f"app_wit_{req_id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"rej_wit_{req_id}")
        ]
    ])
    
    admin_text = (
        f"🚨 <b>طلب سحب جديد!</b>\n\n"
        f"👑 اللقب: <b>{d_name}</b>\n"
        f"📱 الهاتف: <code>{formatted_admin_phone}</code>\n"
        f"🆔 ID: <code>{user_id}</code>\n\n"
        f"🔹 <b>حسابات ايشانسي المرتبطة:</b>\n{ichancy_accounts_str}\n\n"
        f"💳 الطريقة: <b>{method}</b>\n"
        f"📌 حساب التلقي: <code>{code}</code>\n"
        f"💵 المبلغ المطلوب: <b>{format_syp(amount)} SYP</b>\n"
        f"🏷️ الرسوم (10%): <b>{format_syp(fee)} SYP</b>\n"
        f"💰 الصافي للتحويل: <b>{format_syp(net_amount)} SYP</b>"
    )
    
    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_kb, parse_mode="HTML")
    except Exception as e:
        logging.error(f"خطأ في إرسال طلب السحب للأدمن: {e}")
        
    await callback.message.edit_text(
        f"⏳ <b>جاري المعالجة...</b>\n\n"
        f"• المبلغ المطلوب سحبه: <b>{format_syp(amount)} SYP</b>\n"
        f"• رسوم التحويل (10%): <b>{format_syp(fee)} SYP</b>\n"
        f"• الصافي المستلم: <b>{format_syp(net_amount)} SYP</b>\n"
        f"• حساب التلقي: <code>{code}</code>\n\n"
        f"تم تأكيد وإرسال طلبك إلى الإدارة للتحقق من حساب إيشانسي الخاص بك ومراجعته.",
        parse_mode="HTML"
    )
    await callback.answer()

# ==================== معالجة موافقة الأدمن ====================

@dp.callback_query(lambda c: c.data.startswith("app_") or c.data.startswith("rej_"))
async def admin_actions(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    action = parts[0]
    t_type = parts[1]
    req_id = parts[2]

    if t_type == "dep":
        if req_id not in pending_deposits:
            await callback.answer("❌ انتهت صلاحية الطلب أو تم معالجته مسبقاً.", show_alert=True)
            return
        req_data = pending_deposits[req_id]
        target_id = req_data["user_id"]
        amount = req_data["amount"]

        if target_id not in database:
            database[target_id] = {"balance": 0, "display_name": "مستخدم", "phone": "غير متوفر", "accounts": [], "referrals": [], "real_referrals": [], "ref_earnings": 0, "referred_by": None, "logs": []}

        if action == "app":
            database[target_id]["balance"] += amount
            database[target_id]["logs"].append(f"📥 تم شحن الرصيد بقيمة {format_syp(amount)} SYP")
            
            user_data = database[target_id]
            if amount >= 50000 and user_data.get("referred_by") and not user_data.get("ref_bonus_given", False):
                user_data["ref_bonus_given"] = True
                referrer_id = user_data["referred_by"]
                if referrer_id in database:
                    database[referrer_id]["balance"] += 5000
                    database[referrer_id]["ref_earnings"] += 5000
                    if target_id not in database[referrer_id]["real_referrals"]:
                        database[referrer_id]["real_referrals"].append(target_id)
                    database[referrer_id]["logs"].append(f"🎁 مكافأة إحالة (شحن أول) بقيمة {format_syp(5000)} SYP من المستخدم {target_id}")
                    try:
                        # 🔔 إشعار فوري للمُحيل بحصوله على مكافأة الإحالة
                        await bot.send_message(
                            referrer_id, 
                            f"🔔 <b>إشعار فوري:</b> 🎉 مبروك! تمت إضافة مكافأة إحالة بقيمة **{format_syp(5000)} SYP** لرصيدك بسبب شحن إحالتك لأول مرة.", 
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass

            dep_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚡ الدخول المباشر للحساب", url="https://www.ichancy.com")],
                [InlineKeyboardButton(text="🏠 رجوع إلى القائمة الرئيسية", callback_data="back_to_home")]
            ])
            # 🔔 إشعار فوري للمستخدم بنجاح شحن الرصيد
            await bot.send_message(target_id, f"🔔 <b>إشعار فوري:</b> ✅ تم شحن الرصيد بنجاح بقيمة {format_syp(amount)} SYP.", reply_markup=dep_kb, parse_mode="HTML")
            await callback.message.edit_text(callback.message.text + "\n\n✅ [تمت الموافقة وشحن الرصيد بنجاح]", parse_mode="HTML")
        else:
            # 🔔 إشعار فوري للمستخدم برفض الشحن
            await bot.send_message(target_id, "🔔 <b>إشعار فوري:</b> ❌ تم رفض طلب الشحن من الإدارة.")
            await callback.message.edit_text(callback.message.text + "\n\n❌ [تم الرفض]", parse_mode="HTML")

        del pending_deposits[req_id]

    elif t_type == "wit":
        if req_id not in pending_withdrawals:
            await callback.answer("❌ انتهت صلاحية الطلب أو تم معالجته مسبقاً.", show_alert=True)
            return
        req_data = pending_withdrawals[req_id]
        target_id = req_data["user_id"]
        amount = req_data["amount"]

        if target_id not in database:
            database[target_id] = {"balance": 0, "display_name": "مستخدم", "phone": "غير متوفر", "accounts": [], "referrals": [], "real_referrals": [], "ref_earnings": 0, "referred_by": None, "logs": []}

        if action == "app":
            net_amount = amount - int(amount * 0.10)
            database[target_id]["logs"].append(f"📤 تم تنفيذ سحب أرباح بقيمة {format_syp(amount)} SYP من حساب ايشانسي")
            
            # 🔔 إشعار فوري للمستخدم بنجاح السحب
            await bot.send_message(target_id, f"🔔 <b>إشعار فوري:</b> ✅ تمت عملية السحب بنجاح!\nتم سحب مبلغ <b>{format_syp(amount)} SYP</b> (الصافي بعد خصم الرسوم 10%: <b>{format_syp(net_amount)} SYP</b>) وتحويله إلى حسابك.", parse_mode="HTML")
            await callback.message.edit_text(callback.message.text + "\n\n✅ [تم تأكيد وإتمام السحب]", parse_mode="HTML")
        else:
            # 🔔 إشعار فوري للمستخدم برفض السحب
            await bot.send_message(target_id, "🔔 <b>إشعار فوري:</b> ❌ تم رفض طلب السحب من الإدارة لعدم كفاية الرصيد أو لسبب آخر.")
            await callback.message.edit_text(callback.message.text + "\n\n❌ [تم رفض السحب]", parse_mode="HTML")

        del pending_withdrawals[req_id]

    await callback.answer()

# ==================== نظام الإحالات والأزرار الخاصة بها ====================

@dp.callback_query(lambda c: c.data == "referrals")
async def referrals_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in database:
        database[user_id] = {"balance": 0, "display_name": "مستخدم", "phone": "غير متوفر", "accounts": [], "referrals": [], "real_referrals": [], "ref_earnings": 0, "referred_by": None, "logs": []}
        
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    user_data = database[user_id]
    ref_count = len(user_data.get("referrals", []))
    real_ref_count = len(user_data.get("real_referrals", []))
    ref_earnings = format_syp(user_data.get("ref_earnings", 0))

    text = (
        f"📊 <b>إحصائياتك:</b>\n\n"
        f"• إحالاتك: <b>{ref_count}</b>\n"
        f"• إحالاتك الحقيقية: <b>{real_ref_count} ✅</b>\n"
        f"• الارباح منذ الانضمام: <b>SYP {ref_earnings}</b>\n\n"
        f"⚠️ <i>ملاحظة: يشترط وجود 3 إحالات حقيقية على الأقل لتفعيل أرباح الحرق.</i>\n\n"
        f"🔗 رابط الإحالة الخاص بك:\n<code>{ref_link}</code>\n\n"
    )
    if ref_count == 0:
        text += "لم تبدأ بعد في الإحالة. شارك رابط الإحالة مع أصدقائك لبدء كسب المكافآت."

    tg_share_url = f"https://t.me/share/url?url={ref_link}&text=⚡ أنضم الآن إلى بوت Opportunity Master وابدأ ربح الأموال معنا!"
    wa_share_url = f"https://api.whatsapp.com/send?text=⚡ أنضم الآن إلى بوت Opportunity Master عبر رابط الإحالة الخاص بي:\n{ref_link}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 على ماذا أحصل؟", callback_data="show_ref_alert")],
        [
            InlineKeyboardButton(text="✈️ مشاركة عبر تلغرام", url=tg_share_url),
            InlineKeyboardButton(text="💬 مشاركة عبر واتساب", url=wa_share_url)
        ],
        [InlineKeyboardButton(text="🏠 رجوع", callback_data="back_to_home")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "show_ref_alert")
async def show_ref_alert_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"

    alert_text = (
        "👥 <b>على ماذا تحصل؟</b>\n\n"
        "• تربح من حرق اللاعبين الذين انضمو عن طريقك كل 10 أيام (يشترط وجود 3 إحالات حقيقية على الأقل لتفعيل الأرباح)\n"
        "• رصيد بقيمة SYP 5.000 لكل احالة تشحن SYP 50.000 وما فوق لمرة واحدة على كل احالة\n\n"
        f"🔗 رابط الإحالة الخاص بك:\n<code>{ref_link}</code>"
    )

    tg_share_url = f"https://t.me/share/url?url={ref_link}&text=⚡ أنضم الآن إلى بوت Opportunity Master وابدأ ربح الأموال معنا!"
    wa_share_url = f"https://api.whatsapp.com/send?text=⚡ أنضم الآن إلى بوت Opportunity Master عبر رابط الإحالة الخاص بي:\n{ref_link}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✈️ مشاركة عبر تلغرام", url=tg_share_url),
            InlineKeyboardButton(text="💬 مشاركة عبر واتساب", url=wa_share_url)
        ],
        [InlineKeyboardButton(text="🔙 رجوع إلى الإحالات", callback_data="referrals")]
    ])
    
    await callback.message.edit_text(alert_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ==================== نظام الدعم والسجلات والانتقال المباشر للشات ====================

@dp.callback_query(lambda c: c.data == "support")
async def support_handler(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "💬 <b>ارسل رسالة لدعم البوت</b>\n\n"
        "يرجى تزويدنا بالمشكلة التي تواجهها أو كتابة رسالة بشكل تفصيلي تشرح سبب التواصل مع الدعم لكي يقوم فريق الدعم بالمساعدة الفورية.\n\n"
        "<b>ينتظر البوت رسالة منك ...</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 رجوع", callback_data="back_to_home")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(Form.waiting_for_support_message)
    await callback.answer()

@dp.message(Form.waiting_for_support_message)
async def process_support_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    support_text = message.text.strip()
    
    if user_id not in database:
        database[user_id] = {"balance": 0, "display_name": "مستخدم", "phone": "غير متوفر", "accounts": [], "referrals": [], "real_referrals": [], "ref_earnings": 0, "referred_by": None, "logs": []}
    
    user_data = database[user_id]
    d_name = user_data.get("display_name", "مستخدم")
    phone = format_phone(user_data.get("phone", "غير متوفر"))
    accounts = user_data.get("accounts", [])
    
    acc_str = "\n".join([f"• <code>{acc['username']}</code>" for acc in accounts]) if accounts else "لا توجد حسابات ايشانسي مسجلة"
    
    admin_msg = (
        f"🎧 <b>رسالة دعم جديدة من مستخدم!</b>\n\n"
        f"👑 اللقب: <b>{d_name}</b>\n"
        f"📱 الهاتف: <code>{phone}</code>\n"
        f"🆔 ID: <code>{user_id}</code>\n\n"
        f"🔹 <b>حسابات ايشانسي:</b>\n{acc_str}\n\n"
        f"✉️ <b>الرسالة / المشكلة:</b>\n<i>{support_text}</i>"
    )
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 مراسلة المستخدم (فتح الشات)", url=f"tg://openmessage?user_id={user_id}")]
    ])
    
    try:
        await bot.send_message(ADMIN_ID, admin_msg, reply_markup=admin_kb, parse_mode="HTML")
    except Exception as e:
        logging.error(f"خطأ في إرسال رسالة الدعم للأدمن: {e}")
        
    await message.answer("✅ <b>تم ارسال الرسالة، سيتم التواصل من قبل الإدارة بوقت قصير لحل المشكلة.</b>", parse_mode="HTML")
    await state.clear()

@dp.callback_query(lambda c: c.data == "logs")
async def logs_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_logs = database[user_id].get("logs", [])
    logs_text = "📭 لا توجد سجلات أو عمليات سابقة مسجلة حتى الآن." if not user_logs else "📊 <b>سجل آخر عملياتك في البوت:</b>\n\n" + "\n".join([f"• {log}" for log in user_logs[-10:]])
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 رجوع", callback_data="back_to_home")]])
    await callback.message.edit_text(logs_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

