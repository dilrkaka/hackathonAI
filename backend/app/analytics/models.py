from sqlalchemy import (
    Table, Column, MetaData, Text,
    Integer, Float, DateTime, Index, func
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

search_logs = Table(
    "search_logs",
    metadata,

    Column("id", Text, primary_key=True),
    Column("query", Text, nullable=False),
    Column("normalized_query", Text),
    Column("mode", Text, nullable=False),
    Column("total", Integer, nullable=False),
    Column("returned_count", Integer, nullable=False),
    Column("match_count", Integer),
    Column("processing_time_ms", Float),
    Column("result_ids", JSONB),
    Column("fixes", JSONB),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now()
    )
)

user_events = Table(
    "user_events",
    metadata,

    Column("id", Text, primary_key=True),
    Column("type", Text, nullable=False),
    Column("query", Text),
    Column("mode", Text),
    Column("product_id", Text),
    Column("position", Integer),
    Column("payload", JSONB),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now()
    )
)

Index("ix_search_logs_query", search_logs.c.query)
Index("ix_search_logs_mode", search_logs.c.mode)
Index("ix_search_logs_created", search_logs.c.created_at)

Index("ix_user_events_type", user_events.c.type)
Index("ix_user_events_product", user_events.c.product_id)
Index("ix_user_events_created", user_events.c.created_at)