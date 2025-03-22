import uuid
import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.db.base_mixins import TimestampSoftDeleteMixin

Base = declarative_base()

class UserRoles(enum.Enum):
    admin = "admin"
    user = "user"


class User(TimestampSoftDeleteMixin, Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    name = Column(String(100))
    last_name = Column(String(150))
    password = Column(String(64))
    salt = Column(String(32))
    roles = Column(ARRAY(Enum(UserRoles)), nullable=False, default=[UserRoles.user])
    email = Column(String, unique=True, index=True)
    
    reviews = relationship("Review", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user")

class Category(TimestampSoftDeleteMixin, Base):
    __tablename__ = "categories"
    
    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True)
    
    products = relationship("Product", back_populates="category")

class Product(TimestampSoftDeleteMixin, Base):
    __tablename__ = "products"
    
    product_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"))
    price = Column(Float)
    rating = Column(Float, default=0.0)
    
    category = relationship("Category", back_populates="products")
    reviews = relationship("Review", back_populates="product")
    cart_items = relationship("CartItem", back_populates="product")

class Review(TimestampSoftDeleteMixin, Base):
    __tablename__ = "reviews"
    
    review_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.product_id"))
    text = Column(Text)
    rating = Column(Integer)
    
    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")

class CartItem(Base):
    __tablename__ = "cart_items"
    
    cart_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.product_id"))
    quantity = Column(Integer, default=1)
    
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")
