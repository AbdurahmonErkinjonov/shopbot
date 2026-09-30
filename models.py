from datetime import datetime, date
from typing import List, Optional, Dict, Any
from sqlalchemy import BigInteger, String, Float, Integer, Text, Boolean, ForeignKey, DateTime, func, select, delete, and_
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload, DeclarativeBase
from config import config

# Engine & Session Setup
engine = create_async_engine(config.DATABASE_URL, echo=False, future=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cart: Mapped[Optional["Cart"]] = relationship("Cart", back_populates="user", cascade="all, delete-orphan", uselist=False)
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    products: Mapped[List["Product"]] = relationship("Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    photo_id: Mapped[str] = mapped_column(String(512), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped["Category"] = relationship("Category", back_populates="products")
    cart_items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="product", cascade="all, delete-orphan")
    order_items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="product")
    product_channels: Mapped[List["ProductChannel"]] = relationship("ProductChannel", back_populates="product", cascade="all, delete-orphan")


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="cart")
    items: Mapped[List["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="cart_items")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    product_channels: Mapped[List["ProductChannel"]] = relationship("ProductChannel", back_populates="channel", cascade="all, delete-orphan")


class ProductChannel(Base):
    __tablename__ = "product_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)

    product: Mapped["Product"] = relationship("Product", back_populates="product_channels")
    channel: Mapped["Channel"] = relationship("Channel", back_populates="product_channels")


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


# Initialize Database Tables
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ================= HIGH-PERFORMANCE ASYNC CRUD OPERATIONS =================

async def get_or_create_user(session: AsyncSession, telegram_id: int, full_name: str, username: Optional[str] = None) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user:
        user = User(telegram_id=telegram_id, full_name=full_name, username=username)
        session.add(user)
        await session.flush()
        session.add(Cart(user_id=user.id))
        await session.commit()
    elif user.full_name != full_name or user.username != username:
        user.full_name = full_name
        user.username = username
        await session.commit()
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    return (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()


async def get_categories(session: AsyncSession) -> List[Category]:
    return list((await session.execute(select(Category).order_by(Category.name.asc()))).scalars().all())


async def get_category_by_id(session: AsyncSession, category_id: int) -> Optional[Category]:
    return (await session.execute(select(Category).where(Category.id == category_id))).scalar_one_or_none()


async def add_category(session: AsyncSession, name: str) -> Category:
    cat = Category(name=name.strip())
    session.add(cat)
    await session.commit()
    return cat


async def delete_category(session: AsyncSession, category_id: int) -> bool:
    await session.execute(delete(Category).where(Category.id == category_id))
    await session.commit()
    return True


async def add_product(session: AsyncSession, category_id: int, name: str, description: str, price: float, photo_id: str, quantity: int) -> Product:
    prod = Product(category_id=category_id, name=name.strip(), description=description.strip(), price=price, photo_id=photo_id, quantity=quantity, is_active=True)
    session.add(prod)
    await session.commit()
    return prod


async def get_products_by_category(session: AsyncSession, category_id: int) -> List[Product]:
    stmt = select(Product).where(and_(Product.category_id == category_id, Product.is_active == True)).order_by(Product.name.asc())
    return list((await session.execute(stmt)).scalars().all())


async def get_product_by_id(session: AsyncSession, product_id: int) -> Optional[Product]:
    stmt = select(Product).options(selectinload(Product.category)).where(Product.id == product_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_all_products(session: AsyncSession) -> List[Product]:
    stmt = select(Product).options(selectinload(Product.category)).order_by(Product.id.desc())
    return list((await session.execute(stmt)).scalars().all())


async def update_product(session: AsyncSession, product_id: int, **kwargs) -> Optional[Product]:
    prod = await get_product_by_id(session, product_id)
    if prod:
        for k, v in kwargs.items():
            if hasattr(prod, k) and v is not None:
                setattr(prod, k, v)
        await session.commit()
    return prod


async def delete_product(session: AsyncSession, product_id: int) -> bool:
    await session.execute(delete(Product).where(Product.id == product_id))
    await session.commit()
    return True


async def get_user_cart(session: AsyncSession, telegram_id: int) -> Optional[Cart]:
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        return None
    stmt = select(Cart).options(selectinload(Cart.items).selectinload(CartItem.product)).where(Cart.user_id == user.id)
    cart = (await session.execute(stmt)).scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user.id)
        session.add(cart)
        await session.commit()
        cart = (await session.execute(stmt)).scalar_one()
    return cart


async def add_to_cart(session: AsyncSession, telegram_id: int, product_id: int, quantity: int = 1) -> bool:
    cart = await get_user_cart(session, telegram_id)
    if not cart:
        return False
    prod = await get_product_by_id(session, product_id)
    if not prod or prod.quantity < 1:
        return False
    stmt = select(CartItem).where(and_(CartItem.cart_id == cart.id, CartItem.product_id == product_id))
    item = (await session.execute(stmt)).scalar_one_or_none()
    if item:
        item.quantity += quantity
    else:
        session.add(CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity))
    await session.commit()
    return True


async def update_cart_item_quantity(session: AsyncSession, cart_item_id: int, change: int) -> Optional[CartItem]:
    stmt = select(CartItem).options(selectinload(CartItem.product)).where(CartItem.id == cart_item_id)
    item = (await session.execute(stmt)).scalar_one_or_none()
    if not item:
        return None
    new_qty = item.quantity + change
    if new_qty <= 0:
        await session.delete(item)
        await session.commit()
        return None
    if item.product and new_qty > item.product.quantity:
        return item
    item.quantity = new_qty
    await session.commit()
    return item


async def remove_from_cart(session: AsyncSession, cart_item_id: int) -> bool:
    await session.execute(delete(CartItem).where(CartItem.id == cart_item_id))
    await session.commit()
    return True


async def clear_cart(session: AsyncSession, telegram_id: int) -> bool:
    cart = await get_user_cart(session, telegram_id)
    if cart:
        await session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await session.commit()
    return True


async def create_order(session: AsyncSession, telegram_id: int, full_name: str, phone_number: str, address: str, comment: Optional[str] = None) -> Optional[Order]:
    cart = await get_user_cart(session, telegram_id)
    if not cart or not cart.items:
        return None
    total_price = sum(i.product.price * i.quantity for i in cart.items if i.product)
    order = Order(user_id=cart.user_id, full_name=full_name.strip(), phone_number=phone_number.strip(), address=address.strip(), comment=comment.strip() if comment else None, total_price=total_price, status="new")
    session.add(order)
    await session.flush()
    for item in cart.items:
        if item.product:
            session.add(OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity, price=item.product.price))
            if item.product.quantity >= item.quantity:
                item.product.quantity -= item.quantity
    await session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    await session.commit()
    stmt = select(Order).options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.user)).where(Order.id == order.id)
    return (await session.execute(stmt)).scalar_one()


async def get_user_orders(session: AsyncSession, telegram_id: int) -> List[Order]:
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        return []
    stmt = select(Order).options(selectinload(Order.items).selectinload(OrderItem.product)).where(Order.user_id == user.id).order_by(Order.id.desc())
    return list((await session.execute(stmt)).scalars().all())


async def get_all_orders(session: AsyncSession, limit: int = 50) -> List[Order]:
    stmt = select(Order).options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.user)).order_by(Order.id.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    stmt = select(Order).options(selectinload(Order.items).selectinload(OrderItem.product), selectinload(Order.user)).where(Order.id == order_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def update_order_status(session: AsyncSession, order_id: int, status: str) -> Optional[Order]:
    order = await get_order_by_id(session, order_id)
    if order:
        order.status = status
        await session.commit()
    return order


async def get_orders_stats(session: AsyncSession) -> Dict[str, Any]:
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0
    total_products = (await session.execute(select(func.count(Product.id)))).scalar() or 0
    total_categories = (await session.execute(select(func.count(Category.id)))).scalar() or 0
    total_orders = (await session.execute(select(func.count(Order.id)))).scalar() or 0
    total_revenue = (await session.execute(select(func.sum(Order.total_price)).where(Order.status != "cancelled"))).scalar() or 0.0
    today = date.today()
    today_orders = (await session.execute(select(func.count(Order.id)).where(func.date(Order.created_at) == today))).scalar() or 0
    today_revenue = (await session.execute(select(func.sum(Order.total_price)).where(and_(func.date(Order.created_at) == today, Order.status != "cancelled")))).scalar() or 0.0
    return {
        "total_users": total_users, "total_products": total_products, "total_categories": total_categories,
        "total_orders": total_orders, "total_revenue": total_revenue, "today_orders": today_orders, "today_revenue": today_revenue
    }


async def add_channel(session: AsyncSession, channel_id: int, title: str, username: Optional[str] = None) -> Channel:
    stmt = select(Channel).where(Channel.channel_id == channel_id)
    ch = (await session.execute(stmt)).scalar_one_or_none()
    if not ch:
        ch = Channel(channel_id=channel_id, title=title, username=username)
        session.add(ch)
    else:
        ch.title = title
        ch.username = username
    await session.commit()
    return ch


async def get_channels(session: AsyncSession) -> List[Channel]:
    return list((await session.execute(select(Channel).order_by(Channel.id.asc()))).scalars().all())


async def delete_channel(session: AsyncSession, channel_db_id: int) -> bool:
    await session.execute(delete(Channel).where(Channel.id == channel_db_id))
    await session.commit()
    return True


async def link_product_channels(session: AsyncSession, product_id: int, channel_ids: List[int]) -> None:
    await session.execute(delete(ProductChannel).where(ProductChannel.product_id == product_id))
    for cid in channel_ids:
        session.add(ProductChannel(product_id=product_id, channel_id=cid))
    await session.commit()


async def get_setting(session: AsyncSession, key: str, default: str = "") -> str:
    res = (await session.execute(select(Settings).where(Settings.key == key))).scalar_one_or_none()
    return res.value if res else default


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    res = (await session.execute(select(Settings).where(Settings.key == key))).scalar_one_or_none()
    if res:
        res.value = value
    else:
        session.add(Settings(key=key, value=value))
    await session.commit()
