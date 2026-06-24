"""
app/prompts/semantic_layer.py
--------------------------------
This is the "Semantic Layer Needed" diamond from the architecture diagram:
business users say things like "revenue" or "top client" that don't match
your actual BigQuery table/column names. This file is what bridges that
gap before any SQL gets written.
"""

# Short, plain-English description of each table that matters for this
# assistant. This helps the model pick the right table(s) to inspect/join
# without guessing from table names alone.
DATASET_NOTES = """
`sales`: One row per sales transaction.

Columns:
- order_id: Unique order identifier.
- order_date: Date the order was placed.
- customer_name: Name of the customer.
- region: Geographic region of the customer.
- category: Product category.
- product: Product name.
- quantity: Number of units sold.
- unit_price: Price per unit.
- revenue: Total revenue for the transaction.
"""

# Map business language -> the real table/column it actually refers to.
# Add every term your business users are likely to use that doesn't match
# a column name exactly.
BUSINESS_GLOSSARY = {
    "sales": "sales table",
    "order": "sales.order_id",
    "order id": "sales.order_id",
    "order date": "sales.order_date",

    "customer": "sales.customer_name",
    "customer name": "sales.customer_name",

    "region": "sales.region",

    "category": "sales.category",
    "product category": "sales.category",

    "product": "sales.product",

    "quantity": "sales.quantity",

    "unit price": "sales.unit_price",
    "price": "sales.unit_price",

    "revenue": "sales.revenue",

    # Common business phrases
    "total revenue": "SUM(sales.revenue)",
    "total sales": "SUM(sales.revenue)",
    "top customer": "customer with the highest SUM(sales.revenue)",
    "top region": "region with the highest SUM(sales.revenue)",
    "top product": "product with the highest SUM(sales.revenue)",
    "top category": "category with the highest SUM(sales.revenue)",
    "average order value": "AVG(sales.revenue)",
    "number of orders": "COUNT(sales.order_id)",
}


def build_semantic_layer_text() -> str:
    glossary_lines = "\n".join(f'- {term} : {ref}' for term, ref in BUSINESS_GLOSSARY.items())
    
    return (
        f"DATASET NOTES:\n{DATASET_NOTES.strip()}\n\n"
        f"BUSINESS GLOSSARY (translate business language to real schema BEFORE writing SQL):\n{glossary_lines}"
    )
