from sqlalchemy import (
    MetaData, Table, Column, Text,
    Boolean, Numeric, Index
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

categories = Table(
    "categories",
    metadata,
    Column("id", Text, primary_key=True),
    Column("parent_id", Text),
    Column("name", Text, nullable=False)
)

products = Table(
    "products",
    metadata,
    Column("id", Text, primary_key=True),
    Column("group_id", Text),
    Column("name", Text, nullable=False),
    Column("vendor", Text),
    Column("vendor_code", Text),
    Column("vendor_url", Text),
    Column("description", Text),
    Column("category_id", Text),
    Column("price", Numeric(18, 2)),
    Column("old_price", Numeric(18, 2)),
    Column("currency", Text),
    Column("available", Boolean),
    Column("image_url", Text),
    Column("url", Text),
    Column("sales_notes", Text),
    Column("params", JSONB)
)

Index("ix_products_category", products.c.category_id)
Index("ix_products_group", products.c.group_id)
Index("ix_products_vendor", products.c.vendor)
Index("ix_products_vendor_code", products.c.vendor_code)