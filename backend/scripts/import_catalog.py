import argparse
from decimal import Decimal

from lxml import etree
from sqlalchemy.dialects.postgresql import insert

from backend.app.database import engine
from backend.app.models import metadata, categories, products

BATCH_SIZE = 500


def get_text(element, tag):
    value = element.findtext(tag)
    return value.strip() if value else None


def get_price(element, tag):
    value = get_text(element, tag)
    return Decimal(value) if value else None


def parse_category(element):
    return {
        "id": element.get("id"),
        "parent_id": element.get("parentId"),
        "name": (element.text or "").strip()
    }


def parse_product(element):
    params = {}

    for param in element.findall("param"):
        key = param.get("name")
        value = (param.text or "").strip()

        if key and value:
            params.setdefault(key, []).append(value)

    currency = get_text(element, "currencyId")

    return {
        "id": element.get("id"),
        "group_id": element.get("group_id"),
        "name": get_text(element, "name") or "",
        "vendor": get_text(element, "vendor"),
        "vendor_code": get_text(element, "vendorCode"),
        "vendor_url": get_text(element, "vendorUrl"),
        "description": get_text(element, "description"),
        "category_id": get_text(element, "categoryId"),
        "price": get_price(element, "price"),
        "old_price": get_price(element, "oldprice"),
        "currency": "RUB" if currency == "RUR" else currency,
        "available": element.get("available") == "true",
        "image_url": get_text(element, "picture"),
        "url": get_text(element, "url"),
        "sales_notes": get_text(element, "sales_notes"),
        "params": params
    }


def save_batch(table, rows):
    if not rows:
        return

    stmt = insert(table)

    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            column.name: stmt.excluded[column.name]
            for column in table.columns
            if column.name != "id"
        }
    )

    with engine.begin() as connection:
        connection.execute(stmt, rows)


def import_catalog(path, limit=None):
    metadata.create_all(engine)

    category_batch = []
    product_batch = []

    category_count = 0
    product_count = 0

    context = etree.iterparse(
        path,
        events=("end",),
        tag=("category", "offer"),
        load_dtd=False,
        no_network=True,
        resolve_entities=False
    )

    for _, element in context:
        if element.tag == "category":
            category_batch.append(parse_category(element))
            category_count += 1

            if len(category_batch) >= BATCH_SIZE:
                save_batch(categories, category_batch)
                category_batch.clear()

        elif element.tag == "offer":
            if category_batch:
                save_batch(categories, category_batch)
                category_batch.clear()

            product_batch.append(parse_product(element))
            product_count += 1

            if len(product_batch) >= BATCH_SIZE:
                save_batch(products, product_batch)
                product_batch.clear()

                print(
                    f"Products imported: {product_count}",
                    flush=True
                )

        element.clear()

        while element.getprevious() is not None:
            del element.getparent()[0]

        if limit and product_count >= limit:
            break

    save_batch(categories, category_batch)
    save_batch(products, product_batch)

    print("Import completed")
    print(f"Categories: {category_count}")
    print(f"Products: {product_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("path")
    parser.add_argument("--limit", type=int, default=None)

    args = parser.parse_args()

    import_catalog(args.path, args.limit)