from typing import List, Set
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from models import Category, Product, CartItem, Channel


def format_price(amount: float) -> str:
    return f"{int(amount):,}".replace(",", " ") + " so'm"


# Reply Keyboards
def get_user_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Katalog"), KeyboardButton(text="🛒 Savat")],
            [KeyboardButton(text="📦 Buyurtmalarim"), KeyboardButton(text="ℹ️ Biz haqimizda")],
            [KeyboardButton(text="📞 Aloqa")]
        ],
        resize_keyboard=True
    )


def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )


def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📂 Kataloglar"), KeyboardButton(text="➕ Katalog qo'shish"), KeyboardButton(text="🗑 Katalog o'chirish")],
            [KeyboardButton(text="📦 Mahsulotlar"), KeyboardButton(text="➕ Mahsulot qo'shish"), KeyboardButton(text="🗑 Mahsulot o'chirish")],
            [KeyboardButton(text="✏️ Mahsulotni tahrirlash"), KeyboardButton(text="📋 Buyurtmalar")],
            [KeyboardButton(text="📢 Kanallar"), KeyboardButton(text="➕ Kanal qo'shish"), KeyboardButton(text="🗑 Kanal o'chirish")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="🚪 Chiqish")]
        ],
        resize_keyboard=True
    )


# Inline Keyboards
def get_categories_inline_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"📂 {c.name}", callback_data=f"cat:{c.id}")] for c in categories])


def get_products_inline_keyboard(products: List[Product], category_id: int) -> InlineKeyboardMarkup:
    builder = []
    for p in products:
        stock = f"({p.quantity} dona)" if p.quantity > 0 else "(Tugagan)"
        builder.append([InlineKeyboardButton(text=f"📦 {p.name} - {format_price(p.price)} {stock}", callback_data=f"prod:{p.id}")])
    builder.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="cats_list")])
    return InlineKeyboardMarkup(inline_keyboard=builder)


def get_product_detail_keyboard(product_id: int, category_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add_cart:{product_id}")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"cat:{category_id}")]
        ]
    )


def get_cart_inline_keyboard(cart_items: List[CartItem]) -> InlineKeyboardMarkup:
    builder = []
    for item in cart_items:
        prod_name = item.product.name if item.product else "Mahsulot"
        item_total = format_price(item.product.price * item.quantity) if item.product else ""
        builder.append([InlineKeyboardButton(text=f"📦 {prod_name} - {item_total}", callback_data=f"prod:{item.product_id}")])
        builder.append([
            InlineKeyboardButton(text="➖", callback_data=f"cart_dec:{item.id}"),
            InlineKeyboardButton(text=f"{item.quantity} dona", callback_data="ignore"),
            InlineKeyboardButton(text="➕", callback_data=f"cart_inc:{item.id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"cart_del:{item.id}")
        ])
    builder.append([
        InlineKeyboardButton(text="🧹 Savatni tozalash", callback_data="cart_clear"),
        InlineKeyboardButton(text="✅ Buyurtma berish", callback_data="cart_checkout")
    ])
    builder.append([InlineKeyboardButton(text="🛍 Katalogga qaytish", callback_data="cats_list")])
    return InlineKeyboardMarkup(inline_keyboard=builder)


def get_order_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order_yes"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="confirm_order_no")
        ]]
    )


def get_channels_multi_select_keyboard(channels: List[Channel], selected_ids: Set[int]) -> InlineKeyboardMarkup:
    builder = []
    for ch in channels:
        checked = "☑️" if ch.id in selected_ids else "☐"
        builder.append([InlineKeyboardButton(text=f"{checked} {ch.title} ({ch.username or ch.channel_id})", callback_data=f"toggle_chan:{ch.id}")])
    builder.append([InlineKeyboardButton(text="🚀 Nashr qilish", callback_data="finish_chan_select")])
    builder.append([InlineKeyboardButton(text="⏭️ O'tkazib yuborish", callback_data="skip_chan_select")])
    return InlineKeyboardMarkup(inline_keyboard=builder)


def get_category_delete_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🗑 {c.name}", callback_data=f"del_cat_ask:{c.id}")] for c in categories])


def get_category_delete_confirm_keyboard(category_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"del_cat_yes:{category_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="del_cat_no")
        ]]
    )


def get_product_delete_keyboard(products: List[Product]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🗑 {p.name} ({format_price(p.price)})", callback_data=f"del_prod_ask:{p.id}")] for p in products])


def get_product_delete_confirm_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"del_prod_yes:{product_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="del_prod_no")
        ]]
    )


def get_product_edit_keyboard(products: List[Product]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"✏️ {p.name}", callback_data=f"edit_prod_select:{p.id}")] for p in products])


def get_product_edit_fields_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Rasm", callback_data=f"edit_field:{product_id}:photo_id"), InlineKeyboardButton(text="📦 Nom", callback_data=f"edit_field:{product_id}:name")],
            [InlineKeyboardButton(text="💰 Narx", callback_data=f"edit_field:{product_id}:price"), InlineKeyboardButton(text="📝 Tavsif", callback_data=f"edit_field:{product_id}:description")],
            [InlineKeyboardButton(text="🔢 Miqdor", callback_data=f"edit_field:{product_id}:quantity"), InlineKeyboardButton(text="📂 Katalog", callback_data=f"edit_field:{product_id}:category_id")],
            [InlineKeyboardButton(text="⬅️ Ortga", callback_data="edit_prod_back")]
        ]
    )


def get_channel_list_keyboard(channels: List[Channel]) -> InlineKeyboardMarkup:
    builder = []
    for ch in channels:
        uname = ch.username or str(ch.channel_id)
        builder.append([
            InlineKeyboardButton(text=f"📢 {ch.title} ({uname})", callback_data="ignore"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_chan_ask:{ch.id}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=builder)


def get_channel_delete_confirm_keyboard(channel_db_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"del_chan_yes:{channel_db_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="del_chan_no")
        ]]
    )


def get_channel_delete_keyboard(channels: List[Channel]) -> InlineKeyboardMarkup:
    builder = []
    for ch in channels:
        uname = ch.username or str(ch.channel_id)
        builder.append([InlineKeyboardButton(text=f"🗑 {ch.title} ({uname})", callback_data=f"del_chan_ask:{ch.id}")])
    return InlineKeyboardMarkup(inline_keyboard=builder)


def get_order_status_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Bog'lanildi", callback_data=f"adm_status:{order_id}:contacted"), InlineKeyboardButton(text="🚚 Yetkazilmoqda", callback_data=f"adm_status:{order_id}:delivering")],
            [InlineKeyboardButton(text="✅ Yakunlandi", callback_data=f"adm_status:{order_id}:completed"), InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"adm_status:{order_id}:cancelled")]
        ]
    )
