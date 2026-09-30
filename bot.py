import logging
from typing import Callable, Dict, Any, Awaitable, Union, List, Set
from aiogram import Bot, Dispatcher, Router, F, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command, CommandObject, Filter
from aiogram.types import TelegramObject, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from config import config
from models import (
    async_session, Order, Product, Channel, Category,
    get_or_create_user, get_user_by_telegram_id, get_categories, get_category_by_id,
    add_category, delete_category, add_product, get_products_by_category, get_product_by_id,
    get_all_products, update_product, delete_product, get_user_cart, add_to_cart,
    update_cart_item_quantity, remove_from_cart, clear_cart, create_order, get_user_orders,
    get_all_orders, get_order_by_id, update_order_status, get_orders_stats, add_channel,
    get_channels, delete_channel, link_product_channels, get_setting, set_setting
)
from keyboards import (
    format_price, get_user_main_keyboard, get_phone_request_keyboard, get_cancel_keyboard,
    get_admin_main_keyboard, get_categories_inline_keyboard, get_products_inline_keyboard,
    get_product_detail_keyboard, get_cart_inline_keyboard, get_order_confirm_keyboard,
    get_channels_multi_select_keyboard, get_category_delete_keyboard,
    get_category_delete_confirm_keyboard, get_product_delete_keyboard,
    get_product_delete_confirm_keyboard, get_product_edit_keyboard,
    get_product_edit_fields_keyboard, get_channel_list_keyboard, get_order_status_keyboard
)

logger = logging.getLogger(__name__)

# FSM STATES
class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_comment = State()
    confirm_order = State()

class AdminAuthState(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    authenticated = State()

class CategoryState(StatesGroup):
    waiting_for_name = State()

class ProductState(StatesGroup):
    waiting_for_category = State()
    waiting_for_photo = State()
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_description = State()
    waiting_for_quantity = State()
    waiting_for_channels = State()

class EditProductState(StatesGroup):
    waiting_for_product_select = State()
    waiting_for_field_select = State()
    waiting_for_new_value = State()

class ChannelState(StatesGroup):
    waiting_for_channel_id = State()

class SettingsState(StatesGroup):
    waiting_for_about = State()
    waiting_for_contact = State()

# CUSTOM ADMIN FILTER
class IsAdminFilter(Filter):
    async def __call__(self, event: Union[Message, CallbackQuery], state: FSMContext) -> bool:
        user_id = event.from_user.id if event.from_user else 0
        if config.admin_ids and user_id in config.admin_ids:
            return True
        current_state = await state.get_state()
        if current_state == AdminAuthState.authenticated.state:
            return True
        data = await state.get_data()
        return data.get("is_admin_authenticated") is True

# DATABASE MIDDLEWARE
class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)

# FORMATTERS & UTILS
def format_order_for_admin(order: Order) -> str:
    status_map = {"new": "🆕 Yangi", "contacted": "📞 Bog'lanildi", "delivering": "🚚 Yetkazilmoqda", "completed": "✅ Yakunlandi", "cancelled": "❌ Bekor qilindi"}
    status_str = status_map.get(order.status, order.status)
    date_str = order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else ""
    text = [
        f"🔔 <b>BUYURTMA #{order.id}</b>", f"📅 <b>Sana:</b> {date_str}", f"📊 <b>Status:</b> {status_str}\n",
        f"👤 <b>Mijoz:</b> {order.full_name}", f"📞 <b>Telefon:</b> {order.phone_number}", f"📍 <b>Manzil:</b> {order.address}"
    ]
    if order.comment:
        text.append(f"📝 <b>Izoh:</b> {order.comment}")
    text.append("\n📦 <b>Mahsulotlar:</b>")
    for item in order.items:
        prod_name = item.product.name if item.product else "Mahsulot"
        text.append(f"• {prod_name} × {item.quantity} = {format_price(item.price * item.quantity)}")
    text.append(f"\n💰 <b>Jami summa:</b> {format_price(order.total_price)}")
    return "\n".join(text)

def format_order_for_user(order: Order) -> str:
    status_map = {"new": "🆕 Yangi", "contacted": "📞 Bog'lanildi", "delivering": "🚚 Yetkazilmoqda", "completed": "✅ Yakunlandi", "cancelled": "❌ Bekor qilindi"}
    status_str = status_map.get(order.status, order.status)
    date_str = order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else ""
    text = [
        f"📦 <b>Buyurtma #{order.id}</b>", f"📅 <b>Sana:</b> {date_str}", f"📊 <b>Holati:</b> {status_str}\n",
        f"👤 <b>Ism:</b> {order.full_name}", f"📞 <b>Tel:</b> {order.phone_number}", f"📍 <b>Manzil:</b> {order.address}\n<b>Mahsulotlar:</b>"
    ]
    for item in order.items:
        prod_name = item.product.name if item.product else "Mahsulot"
        text.append(f"• {prod_name} × {item.quantity} ({format_price(item.price)})")
    text.append(f"\n💰 <b>Jami:</b> {format_price(order.total_price)}")
    return "\n".join(text)

def format_stats(stats: Dict[str, Any]) -> str:
    return (
        "📊 <b>BOT STATISTIKASI</b>\n\n"
        f"👥 <b>Foydalanuvchilar:</b> {stats['total_users']} ta\n"
        f"📂 <b>Kataloglar:</b> {stats['total_categories']} ta\n"
        f"📦 <b>Mahsulotlar:</b> {stats['total_products']} ta\n\n"
        f"🛒 <b>Jami buyurtmalar:</b> {stats['total_orders']} ta\n"
        f"💰 <b>Umumiy tushum:</b> {format_price(stats['total_revenue'])}\n\n"
        f"📅 <b>BUGUNGI KO'RSATKICHLAR:</b>\n"
        f"📦 <b>Bugungi buyurtmalar:</b> {stats['today_orders']} ta\n"
        f"💵 <b>Bugungi savdo:</b> {format_price(stats['today_revenue'])}"
    )

async def publish_product_to_channels(bot: Bot, product: Product, channels: List[Channel]) -> List[int]:
    if not channels:
        return []
    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start=product_{product.id}"
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Buyurtma berish", url=deep_link)]])
    caption = (
        f"📦 <b>YANGI MAHSULOT</b>\n\n🔥 <b>{product.name}</b>\n\n"
        f"💰 <b>Narxi:</b> {format_price(product.price)}\n\n📝 <b>Tavsif:</b> {product.description}\n\n"
        f"📦 <b>Mavjud:</b> {product.quantity} dona\n\n🛒 Buyurtma berish uchun botga o'ting:"
    )
    success = []
    for ch in channels:
        try:
            await bot.send_photo(chat_id=ch.channel_id, photo=product.photo_id, caption=caption, reply_markup=inline_kb, parse_mode="HTML")
            success.append(ch.channel_id)
        except Exception as e:
            logger.error(f"Channel send error for {ch.title}: {e}")
    return success

async def notify_admins_new_order(bot: Bot, order: Order):
    text = format_order_for_admin(order)
    keyboard = get_order_status_keyboard(order.id)
    for admin_id in config.admin_ids:
        if admin_id > 0:
            try:
                await bot.send_message(chat_id=admin_id, text=f"🔔 <b>YANGI BUYURTMA KELDI!</b>\n\n{text}", reply_markup=keyboard, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Admin notify error: {e}")

async def notify_user_order_status(bot: Bot, user_telegram_id: int, order: Order):
    try:
        await bot.send_message(chat_id=user_telegram_id, text=f"🔔 <b>BUYURTMA HOLATI O'ZGARTIRILDI</b>\n\n{format_order_for_user(order)}", parse_mode="HTML")
    except Exception as e:
        logger.error(f"User notify error: {e}")

# ROUTERS SETUP
user_router = Router()
admin_router = Router()
admin_router.message.filter(IsAdminFilter())
admin_router.callback_query.filter(IsAdminFilter())

# USER HANDLERS
@user_router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, session: AsyncSession, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(session, message.from_user.id, message.from_user.full_name or message.from_user.first_name, message.from_user.username)
    args = command.args
    if args and args.startswith("product_"):
        try:
            prod_id = int(args.split("_")[1])
            product = await get_product_by_id(session, prod_id)
            if product and product.is_active:
                stock = f"📦 <b>Mavjud:</b> {product.quantity} dona" if product.quantity > 0 else "❌ <b>Mavjud emas</b>"
                caption = f"📦 <b>{product.name}</b>\n\n💰 <b>Narxi:</b> {format_price(product.price)}\n\n📝 <b>Tavsif:</b>\n{product.description}\n\n{stock}"
                await message.answer_photo(photo=product.photo_id, caption=caption, reply_markup=get_product_detail_keyboard(product.id, product.category_id), parse_mode="HTML")
                return
        except Exception:
            pass
    await message.answer(f"Assalomu alaykum, <b>{user.full_name}</b>!\n\n🤖 <b>GoodCenter Store</b> sotuv botiga xush kelibsiz.", reply_markup=get_user_main_keyboard(), parse_mode="HTML")

@user_router.message(F.text == "🛍 Katalog")
async def user_catalog(message: Message, session: AsyncSession):
    cats = await get_categories(session)
    if not cats:
        await message.answer("⚠️ Hozircha kataloglar mavjud emas.")
        return
    await message.answer("🛍 <b>Kerakli katalogni tanlang:</b>", reply_markup=get_categories_inline_keyboard(cats), parse_mode="HTML")

@user_router.callback_query(F.data == "cats_list")
async def user_cats_list(callback: CallbackQuery, session: AsyncSession):
    cats = await get_categories(session)
    text = "🛍 <b>Kerakli katalogni tanlang:</b>"
    kb = get_categories_inline_keyboard(cats)
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text=text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@user_router.callback_query(F.data.startswith("cat:"))
async def user_cat_products(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.split(":")[1])
    cat = await get_category_by_id(session, cat_id)
    prods = await get_products_by_category(session, cat_id)
    text = f"📂 <b>{cat.name if cat else ''}</b> katalogidagi mahsulotlar:"
    kb = get_products_inline_keyboard(prods, cat_id)
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text=text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@user_router.callback_query(F.data.startswith("prod:"))
async def user_prod_detail(callback: CallbackQuery, session: AsyncSession):
    prod_id = int(callback.data.split(":")[1])
    product = await get_product_by_id(session, prod_id)
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    stock = f"📦 <b>Mavjud:</b> {product.quantity} dona" if product.quantity > 0 else "❌ <b>Mavjud emas</b>"
    caption = f"📦 <b>{product.name}</b>\n\n💰 <b>Narxi:</b> {format_price(product.price)}\n\n📝 <b>Tavsif:</b>\n{product.description}\n\n{stock}"
    await callback.message.delete()
    await callback.message.answer_photo(photo=product.photo_id, caption=caption, reply_markup=get_product_detail_keyboard(product.id, product.category_id), parse_mode="HTML")
    await callback.answer()

@user_router.callback_query(F.data.startswith("add_cart:"))
async def user_add_cart(callback: CallbackQuery, session: AsyncSession):
    prod_id = int(callback.data.split(":")[1])
    success = await add_to_cart(session, callback.from_user.id, prod_id, 1)
    await callback.answer("✅ Mahsulot savatga qo'shildi!" if success else "⚠️ Omborimizda qolmagan!", show_alert=True)

# CART HANDLERS
async def render_cart(user_id: int, session: AsyncSession):
    cart = await get_user_cart(session, user_id)
    if not cart or not cart.items:
        return "🛒 <b>Sizning savatingiz bo'sh.</b>", None
    total = sum(i.product.price * i.quantity for i in cart.items if i.product)
    lines = ["🛒 <b>SAVATINGIZ:</b>\n"]
    for idx, item in enumerate(cart.items, 1):
        if item.product:
            lines.append(f"<b>{idx}. {item.product.name}</b>\n   └ {format_price(item.product.price)} × {item.quantity} = <b>{format_price(item.product.price * item.quantity)}</b>")
    lines.append(f"\n💰 <b>Jami summa:</b> {format_price(total)}")
    return "\n".join(lines), get_cart_inline_keyboard(cart.items)

@user_router.message(F.text == "🛒 Savat")
async def user_view_cart(message: Message, session: AsyncSession):
    text, kb = await render_cart(message.from_user.id, session)
    await message.answer(text=text, reply_markup=kb, parse_mode="HTML")

@user_router.callback_query(F.data.startswith("cart_inc:"))
async def cart_inc(callback: CallbackQuery, session: AsyncSession):
    await update_cart_item_quantity(session, int(callback.data.split(":")[1]), 1)
    text, kb = await render_cart(callback.from_user.id, session)
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML") if kb else await callback.message.edit_text(text=text, parse_mode="HTML")
    await callback.answer()

@user_router.callback_query(F.data.startswith("cart_dec:"))
async def cart_dec(callback: CallbackQuery, session: AsyncSession):
    await update_cart_item_quantity(session, int(callback.data.split(":")[1]), -1)
    text, kb = await render_cart(callback.from_user.id, session)
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML") if kb else await callback.message.edit_text(text=text, parse_mode="HTML")
    await callback.answer()

@user_router.callback_query(F.data.startswith("cart_del:"))
async def cart_del(callback: CallbackQuery, session: AsyncSession):
    await remove_from_cart(session, int(callback.data.split(":")[1]))
    text, kb = await render_cart(callback.from_user.id, session)
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML") if kb else await callback.message.edit_text(text=text, parse_mode="HTML")
    await callback.answer("O'chirildi")

@user_router.callback_query(F.data == "cart_clear")
async def cart_clear_all(callback: CallbackQuery, session: AsyncSession):
    await clear_cart(session, callback.from_user.id)
    await callback.message.edit_text("🛒 <b>Sizning savatingiz tozalandi.</b>", parse_mode="HTML")
    await callback.answer()

# ORDER CHECKOUT FSM HANDLERS
@user_router.callback_query(F.data == "cart_checkout")
async def order_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    cart = await get_user_cart(session, callback.from_user.id)
    if not cart or not cart.items:
        await callback.answer("Savat bo'sh!", show_alert=True)
        return
    await state.set_state(OrderState.waiting_for_name)
    await callback.message.delete()
    await callback.message.answer("👤 <b>Ismingizni kiriting:</b>", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@user_router.message(F.text == "❌ Bekor qilish", OrderState())
async def order_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=get_user_main_keyboard())

@user_router.message(OrderState.waiting_for_name)
async def order_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await state.set_state(OrderState.waiting_for_phone)
    await message.answer("📞 <b>Telefon raqamingizni yuboring yoki yozing:</b>", reply_markup=get_phone_request_keyboard(), parse_mode="HTML")

@user_router.message(OrderState.waiting_for_phone, F.contact | F.text)
async def order_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text.strip()
    if not phone.startswith("+"):
        phone = f"+{phone}"
    await state.update_data(phone_number=phone)
    await state.set_state(OrderState.waiting_for_address)
    await message.answer("📍 <b>Yetkazib berish manzilini kiriting:</b>", reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@user_router.message(OrderState.waiting_for_address)
async def order_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await state.set_state(OrderState.waiting_for_comment)
    await message.answer("📝 <b>Buyurtma uchun izohingiz bormi?</b> (Bo'lmasa 'Yo'q' deb yozing):", reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@user_router.message(OrderState.waiting_for_comment)
async def order_comment(message: Message, session: AsyncSession, state: FSMContext):
    comment = message.text.strip() if message.text and message.text.lower() not in ["yo'q", "yoq", "no"] else ""
    await state.update_data(comment=comment)
    data = await state.get_data()
    cart = await get_user_cart(session, message.from_user.id)
    total = sum(i.product.price * i.quantity for i in cart.items if i.product)
    summary = [f"📦 <b>BUYURTMANI TASDIQLANG:</b>\n", f"👤 <b>Ism:</b> {data['full_name']}", f"📞 <b>Tel:</b> {data['phone_number']}", f"📍 <b>Manzil:</b> {data['address']}"]
    if comment: summary.append(f"📝 <b>Izoh:</b> {comment}")
    summary.append("\n<b>Mahsulotlar:</b>")
    for i in cart.items:
        if i.product: summary.append(f"• {i.product.name} × {i.quantity} = {format_price(i.product.price * i.quantity)}")
    summary.append(f"\n💰 <b>Jami summa:</b> {format_price(total)}")
    await state.set_state(OrderState.confirm_order)
    await message.answer("\n".join(summary), reply_markup=get_order_confirm_keyboard(), parse_mode="HTML")

@user_router.callback_query(F.data == "confirm_order_yes", OrderState.confirm_order)
async def order_confirm_yes(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    order = await create_order(session, callback.from_user.id, data['full_name'], data['phone_number'], data['address'], data['comment'])
    await state.clear()
    if order:
        await notify_admins_new_order(callback.bot, order)
        await callback.message.delete()
        await callback.message.answer(f"🎉 <b>Rahmat! Buyurtma qabul qilindi (# {order.id}).</b>", reply_markup=get_user_main_keyboard(), parse_mode="HTML")
    await callback.answer()

@user_router.callback_query(F.data == "confirm_order_no", OrderState.confirm_order)
async def order_confirm_no(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Buyurtma bekor qilindi.", reply_markup=get_user_main_keyboard())
    await callback.answer()

@user_router.message(F.text == "📦 Buyurtmalarim")
async def user_my_orders(message: Message, session: AsyncSession):
    orders = await get_user_orders(session, message.from_user.id)
    if not orders:
        await message.answer("📦 Sizda hali buyurtmalar mavjud emas.")
        return
    text_blocks = ["<b>📦 SIZNING BUYURTMALARINGIZ:</b>\n"]
    for o in orders[:10]:
        text_blocks.append(format_order_for_user(o))
        text_blocks.append("────────────────────")
    await message.answer("\n\n".join(text_blocks), parse_mode="HTML")

@user_router.message(F.text == "ℹ️ Biz haqimizda")
async def user_about(message: Message, session: AsyncSession):
    default_about = "ℹ️ <b>GoodCenter Store</b>\n\nSifatli mahsulotlar va tezkor yetkazib berish xizmati!"
    await message.answer(await get_setting(session, "about_us", default_about), parse_mode="HTML")

@user_router.message(F.text == "📞 Aloqa")
async def user_contact(message: Message, session: AsyncSession):
    default_contact = "📞 <b>Mijozlar xizmati:</b> @goodcenter_admin\n📱 <b>Tel:</b> +998 90 123 45 67"
    await message.answer(await get_setting(session, "contact_info", default_contact), parse_mode="HTML")

# ADMIN SECRET AUTHENTICATION HANDLERS
@user_router.message(Command("admingoodcentermanage"))
async def admin_auth_cmd(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AdminAuthState.waiting_for_login)
    await message.answer("🔐 <b>ADMIN PANELGA KIRISH</b>\n\n<b>Login:</b> kiriting:", reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@user_router.message(AdminAuthState.waiting_for_login)
async def admin_login(message: Message, state: FSMContext):
    if message.text == config.ADMIN_LOGIN:
        await state.set_state(AdminAuthState.waiting_for_password)
        await message.answer("🔑 <b>Parol:</b> kiriting:", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    else:
        await state.clear()
        await message.answer("❌ <b>Login noto'g'ri!</b>", reply_markup=get_user_main_keyboard(), parse_mode="HTML")

@user_router.message(AdminAuthState.waiting_for_password)
async def admin_pass(message: Message, session: AsyncSession, state: FSMContext):
    if message.text == config.ADMIN_PASSWORD:
        await state.set_state(AdminAuthState.authenticated)
        await state.update_data(is_admin_authenticated=True)
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user:
            user.is_admin = True
            await session.commit()
        await message.answer("✅ <b>Xush kelibsiz!</b> Admin panelga kirdingiz.", reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    else:
        await state.clear()
        await message.answer("❌ <b>Parol noto'g'ri!</b>", reply_markup=get_user_main_keyboard(), parse_mode="HTML")

# ADMIN PANEL ACTIONS
@admin_router.message(F.text == "🚪 Chiqish")
async def admin_logout(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚪 Admin paneldan chiqdingiz.", reply_markup=get_user_main_keyboard())

@admin_router.message(F.text == "📂 Kataloglar")
async def admin_cats(message: Message, session: AsyncSession):
    cats = await get_categories(session)
    if not cats:
        await message.answer("📂 Kataloglar yo'q.")
        return
    await message.answer("<b>📂 MAVJUD KATALOGLAR:</b>\n\n" + "\n".join(f"{idx}. {c.name}" for idx, c in enumerate(cats, 1)), parse_mode="HTML")

@admin_router.message(F.text == "➕ Katalog qo'shish")
async def admin_add_cat_start(message: Message, state: FSMContext):
    await state.set_state(CategoryState.waiting_for_name)
    await message.answer("➕ <b>Yangi katalog nomini kiriting:</b>", reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@admin_router.message(CategoryState.waiting_for_name)
async def admin_add_cat_save(message: Message, session: AsyncSession, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return
    cat = await add_category(session, message.text)
    await state.clear()
    await message.answer(f"✅ Katalog qo'shildi: <b>{cat.name}</b>", reply_markup=get_admin_main_keyboard(), parse_mode="HTML")

@admin_router.message(F.text == "🗑 Katalog o'chirish")
async def admin_del_cat_start(message: Message, session: AsyncSession):
    cats = await get_categories(session)
    await message.answer("🗑 <b>O'chirmoqchi bo'lgan katalogni tanlang:</b>", reply_markup=get_category_delete_keyboard(cats), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("del_cat_ask:"))
async def admin_del_cat_ask(callback: CallbackQuery, session: AsyncSession):
    cat = await get_category_by_id(session, int(callback.data.split(":")[1]))
    await callback.message.edit_text(f"⚠️ <b>{cat.name}</b> katalogni o'chirishni tasdiqlaysizmi?", reply_markup=get_category_delete_confirm_keyboard(cat.id), parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("del_cat_yes:"))
async def admin_del_cat_yes(callback: CallbackQuery, session: AsyncSession):
    await delete_category(session, int(callback.data.split(":")[1]))
    await callback.message.edit_text("✅ Katalog o'chirildi.", parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "del_cat_no")
async def admin_del_cat_no(callback: CallbackQuery):
    await callback.message.edit_text("Bekor qilindi.")
    await callback.answer()

# ADMIN PRODUCT MANAGEMENT
@admin_router.message(F.text == "📦 Mahsulotlar")
async def admin_list_prods(message: Message, session: AsyncSession):
    prods = await get_all_products(session)
    if not prods:
        await message.answer("📦 Mahsulotlar yo'q.")
        return
    text = ["<b>📦 MAVJUD MAHSULOTLAR:</b>\n"]
    for idx, p in enumerate(prods, 1):
        text.append(f"<b>{idx}. {p.name}</b> - {format_price(p.price)} ({p.quantity} dona)")
    await message.answer("\n".join(text), parse_mode="HTML")

@admin_router.message(F.text == "➕ Mahsulot qo'shish")
async def admin_add_prod_start(message: Message, session: AsyncSession, state: FSMContext):
    cats = await get_categories(session)
    if not cats:
        await message.answer("Avval katalog yarating!")
        return
    await state.set_state(ProductState.waiting_for_category)
    await message.answer("➕ <b>Katalogni tanlang:</b>", reply_markup=get_categories_inline_keyboard(cats), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("cat:"), ProductState.waiting_for_category)
async def admin_add_prod_cat(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category_id=int(callback.data.split(":")[1]), selected_channel_ids=set())
    await state.set_state(ProductState.waiting_for_photo)
    await callback.message.delete()
    await callback.message.answer("📸 <b>Mahsulot rasmini yuboring:</b>", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@admin_router.message(ProductState.waiting_for_photo, F.photo)
async def admin_add_prod_photo(message: Message, state: FSMContext):
    await state.update_data(photo_id=message.photo[-1].file_id)
    await state.set_state(ProductState.waiting_for_name)
    await message.answer("📦 <b>Mahsulot nomini kiriting:</b>", reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@admin_router.message(ProductState.waiting_for_name)
async def admin_add_prod_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(ProductState.waiting_for_price)
    await message.answer("💰 <b>Narxini so'mda kiriting:</b>", reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@admin_router.message(ProductState.waiting_for_price)
async def admin_add_prod_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(" ", "").replace(",", ".").strip())
        await state.update_data(price=price)
        await state.set_state(ProductState.waiting_for_description)
        await message.answer("📝 <b>Tavsifini kiriting:</b>", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    except ValueError:
        await message.answer("To'g'ri narx raqamini kiriting:")

@admin_router.message(ProductState.waiting_for_description)
async def admin_add_prod_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(ProductState.waiting_for_quantity)
    await message.answer("📦 <b>Mavjud miqdorini kiriting:</b>", reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@admin_router.message(ProductState.waiting_for_quantity)
async def admin_add_prod_qty(message: Message, session: AsyncSession, state: FSMContext):
    try:
        qty = int(message.text.strip())
        await state.update_data(quantity=qty)
        channels = await get_channels(session)
        if not channels:
            await save_product_and_publish(message, session, state, [])
        else:
            await state.set_state(ProductState.waiting_for_channels)
            data = await state.get_data()
            await message.answer("📢 <b>Post qaysi kanallarga yuborilsin?</b>", reply_markup=get_channels_multi_select_keyboard(channels, data.get("selected_channel_ids", set())), parse_mode="HTML")
    except ValueError:
        await message.answer("Miqdorni raqamda kiriting:")

@admin_router.callback_query(F.data.startswith("toggle_chan:"), ProductState.waiting_for_channels)
async def admin_toggle_chan(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    cid = int(callback.data.split(":")[1])
    data = await state.get_data()
    sel: Set[int] = data.get("selected_channel_ids", set())
    sel.remove(cid) if cid in sel else sel.add(cid)
    await state.update_data(selected_channel_ids=sel)
    channels = await get_channels(session)
    await callback.message.edit_reply_markup(reply_markup=get_channels_multi_select_keyboard(channels, sel))
    await callback.answer()

@admin_router.callback_query(F.data == "finish_chan_select", ProductState.waiting_for_channels)
async def admin_finish_chan(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    await callback.message.delete()
    await save_product_and_publish(callback.message, session, state, list(data.get("selected_channel_ids", set())))
    await callback.answer()

@admin_router.callback_query(F.data == "skip_chan_select", ProductState.waiting_for_channels)
async def admin_skip_chan(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.message.delete()
    await save_product_and_publish(callback.message, session, state, [])
    await callback.answer()

async def save_product_and_publish(message: Message, session: AsyncSession, state: FSMContext, channel_db_ids: list):
    data = await state.get_data()
    prod = await add_product(session, data["category_id"], data["name"], data["description"], data["price"], data["photo_id"], data["quantity"])
    all_chans = await get_channels(session)
    targets = [c for c in all_chans if c.id in channel_db_ids]
    if targets:
        await link_product_channels(session, prod.id, [c.id for c in targets])
        pub = await publish_product_to_channels(message.bot, prod, targets)
        msg = f"\n📢 Telegram kanallarga joylandi: <b>{len(pub)}/{len(targets)}</b>"
    else:
        msg = ""
    await state.clear()
    await message.answer(f"✅ <b>Mahsulot saqlandi!</b>\n\n📦 <b>{prod.name}</b> - {format_price(prod.price)}{msg}", reply_markup=get_admin_main_keyboard(), parse_mode="HTML")

@admin_router.message(F.text == "🗑 Mahsulot o'chirish")
async def admin_del_prod_start(message: Message, session: AsyncSession):
    prods = await get_all_products(session)
    await message.answer("🗑 <b>O'chirmoqchi bo'lgan mahsulotni tanlang:</b>", reply_markup=get_product_delete_keyboard(prods), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("del_prod_ask:"))
async def admin_del_prod_ask(callback: CallbackQuery, session: AsyncSession):
    p = await get_product_by_id(session, int(callback.data.split(":")[1]))
    await callback.message.edit_text(f"⚠️ <b>{p.name}</b> o'chirilishini tasdiqlaysizmi?", reply_markup=get_product_delete_confirm_keyboard(p.id), parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("del_prod_yes:"))
async def admin_del_prod_yes(callback: CallbackQuery, session: AsyncSession):
    await delete_product(session, int(callback.data.split(":")[1]))
    await callback.message.edit_text("✅ Mahsulot o'chirildi.", parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "del_prod_no")
async def admin_del_prod_no(callback: CallbackQuery):
    await callback.message.edit_text("Bekor qilindi.")
    await callback.answer()

@admin_router.message(F.text == "✏️ Mahsulotni tahrirlash")
async def admin_edit_prod_start(message: Message, session: AsyncSession):
    prods = await get_all_products(session)
    await message.answer("✏️ <b>Tahrirlanadigan mahsulotni tanlang:</b>", reply_markup=get_product_edit_keyboard(prods), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("edit_prod_select:"))
async def admin_edit_prod_select(callback: CallbackQuery, session: AsyncSession):
    pid = int(callback.data.split(":")[1])
    p = await get_product_by_id(session, pid)
    await callback.message.edit_text(f"✏️ <b>{p.name}</b> uchun qaysi maydonni o'zgartirasiz?", reply_markup=get_product_edit_fields_keyboard(pid), parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("edit_field:"))
async def admin_edit_field_select(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    await state.set_state(EditProductState.waiting_for_new_value)
    await state.update_data(edit_product_id=int(parts[1]), edit_field=parts[2])
    await callback.message.delete()
    await callback.message.answer(f"✏️ <b>Yangi {parts[2]} qiymatini kiriting:</b>", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@admin_router.message(EditProductState.waiting_for_new_value)
async def admin_edit_field_save(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    val = message.photo[-1].file_id if data['edit_field'] == "photo_id" and message.photo else (float(message.text.replace(" ", "")) if data['edit_field'] == "price" else (int(message.text) if data['edit_field'] == "quantity" else message.text.strip()))
    await update_product(session, data['edit_product_id'], **{data['edit_field']: val})
    await state.clear()
    await message.answer("✅ <b>Mahsulot muvaffaqiyatli tahrirlandi!</b>", reply_markup=get_admin_main_keyboard(), parse_mode="HTML")

# ADMIN CHANNELS MANAGEMENT
@admin_router.message(F.text == "📢 Kanallar")
async def admin_channels_list(message: Message, session: AsyncSession):
    chans = await get_channels(session)
    if not chans:
        await message.answer("📢 Kanallar yo'q.")
        return
    await message.answer("📢 <b>ULANGAN TELEGRAM KANALLAR:</b>", reply_markup=get_channel_list_keyboard(chans), parse_mode="HTML")

@admin_router.message(F.text == "➕ Kanal qo'shish")
async def admin_add_chan_start(message: Message, state: FSMContext):
    await state.set_state(ChannelState.waiting_for_channel_id)
    await message.answer("➕ <b>Kanal username yoki ID'sini yuboring:</b>\n(Masalan: @goodcenter_products)", reply_markup=get_cancel_keyboard(), parse_mode="HTML")

@admin_router.message(ChannelState.waiting_for_channel_id)
async def admin_add_chan_save(message: Message, session: AsyncSession, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_main_keyboard())
        return
    try:
        chat = await message.bot.get_chat(message.text.strip())
        mem = await message.bot.get_chat_member(chat.id, message.bot.id)
        if mem.status not in ["administrator", "creator"]:
            await message.answer("❌ Bot kanalda Admin emas!")
            return
        ch = await add_channel(session, chat.id, chat.title or "Kanal", f"@{chat.username}" if chat.username else None)
        await state.clear()
        await message.answer(f"✅ Kanal ulandi: <b>{ch.title}</b>", reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")

@admin_router.callback_query(F.data.startswith("del_chan:"))
async def admin_del_chan(callback: CallbackQuery, session: AsyncSession):
    await delete_channel(session, int(callback.data.split(":")[1]))
    await callback.message.edit_text("✅ Kanal o'chirildi.", parse_mode="HTML")
    await callback.answer()

# ADMIN ORDERS & STATS & SETTINGS
@admin_router.message(F.text == "📋 Buyurtmalar")
async def admin_orders_list(message: Message, session: AsyncSession):
    orders = await get_all_orders(session, limit=20)
    if not orders:
        await message.answer("📋 Buyurtmalar hali yo'q.")
        return
    for o in orders:
        await message.answer(format_order_for_admin(o), reply_markup=get_order_status_keyboard(o.id), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("adm_status:"))
async def admin_order_status(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    order = await update_order_status(session, int(parts[1]), parts[2])
    if order and order.user:
        await notify_user_order_status(callback.bot, order.user.telegram_id, order)
    await callback.message.edit_text(format_order_for_admin(order), reply_markup=get_order_status_keyboard(order.id), parse_mode="HTML")
    await callback.answer("Status o'zgartirildi")

@admin_router.message(F.text == "📊 Statistika")
async def admin_stats(message: Message, session: AsyncSession):
    s = await get_orders_stats(session)
    await message.answer(format_stats(s), parse_mode="HTML")

@admin_router.message(F.text == "⚙️ Sozlamalar")
async def admin_settings(message: Message, session: AsyncSession):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ 'Biz haqimizda' matni", callback_data="edit_setting:about_us")],
        [InlineKeyboardButton(text="✏️ 'Aloqa' matni", callback_data="edit_setting:contact_info")]
    ])
    await message.answer("⚙️ <b>BOT SOZLAMALARI:</b>", reply_markup=kb, parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("edit_setting:"))
async def admin_edit_setting_start(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":")[1]
    await state.set_state(SettingsState.waiting_for_about if key == "about_us" else SettingsState.waiting_for_contact)
    await callback.message.delete()
    await callback.message.answer("✏️ <b>Yangi matnni kiriting:</b>", reply_markup=get_cancel_keyboard(), parse_mode="HTML")
    await callback.answer()

@admin_router.message(SettingsState.waiting_for_about)
async def admin_edit_about(message: Message, session: AsyncSession, state: FSMContext):
    await set_setting(session, "about_us", message.text.strip())
    await state.clear()
    await message.answer("✅ Saqlandi!", reply_markup=get_admin_main_keyboard())

@admin_router.message(SettingsState.waiting_for_contact)
async def admin_edit_contact(message: Message, session: AsyncSession, state: FSMContext):
    await set_setting(session, "contact_info", message.text.strip())
    await state.clear()
    await message.answer("✅ Saqlandi!", reply_markup=get_admin_main_keyboard())

@user_router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()

# BUILD DISPATCHER
def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(admin_router)
    dp.include_router(user_router)
    return dp
