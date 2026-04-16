#!/usr/bin/env python3
"""
Seed sample data into BigQuery so you can test the agent immediately.
Creates two tables: `sales_data` and `customer_data`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import bigquery

from config.settings import get_settings


def main():
    settings = get_settings()
    client = bigquery.Client(project=settings.gcp_project_id)

    dataset_ref = f"{settings.gcp_project_id}.{settings.bq_dataset}"
    print(f"📦 Seeding data into {dataset_ref}...\n")

    # ─── Table 1: sales_data ─────────────────────────────
    sales_schema = [
        bigquery.SchemaField("order_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("order_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("customer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("category", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("region", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("quantity", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("unit_price", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("total_amount", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("discount", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
    ]

    sales_rows = [
        {"order_id": "ORD-001", "order_date": "2024-01-15", "customer_id": "CUST-101", "product": "Laptop Pro 15", "category": "Electronics", "region": "North", "quantity": 2, "unit_price": 1299.99, "total_amount": 2599.98, "discount": 0.0, "status": "completed"},
        {"order_id": "ORD-002", "order_date": "2024-01-18", "customer_id": "CUST-102", "product": "Wireless Mouse", "category": "Electronics", "region": "South", "quantity": 5, "unit_price": 29.99, "total_amount": 149.95, "discount": 0.1, "status": "completed"},
        {"order_id": "ORD-003", "order_date": "2024-02-01", "customer_id": "CUST-103", "product": "Standing Desk", "category": "Furniture", "region": "East", "quantity": 1, "unit_price": 549.00, "total_amount": 549.00, "discount": None, "status": "completed"},
        {"order_id": "ORD-004", "order_date": "2024-02-10", "customer_id": "CUST-101", "product": "Monitor 27in", "category": "Electronics", "region": "North", "quantity": 2, "unit_price": 399.99, "total_amount": 799.98, "discount": 0.05, "status": "completed"},
        {"order_id": "ORD-005", "order_date": "2024-02-14", "customer_id": "CUST-104", "product": "Keyboard Mech", "category": "Electronics", "region": "West", "quantity": 3, "unit_price": 89.99, "total_amount": 269.97, "discount": 0.0, "status": "completed"},
        {"order_id": "ORD-006", "order_date": "2024-03-01", "customer_id": "CUST-105", "product": "Office Chair", "category": "Furniture", "region": "South", "quantity": 1, "unit_price": 699.00, "total_amount": 699.00, "discount": 0.15, "status": "completed"},
        {"order_id": "ORD-007", "order_date": "2024-03-05", "customer_id": "CUST-102", "product": "Laptop Pro 15", "category": "Electronics", "region": "South", "quantity": 1, "unit_price": 1299.99, "total_amount": 1299.99, "discount": 0.0, "status": "pending"},
        {"order_id": "ORD-008", "order_date": "2024-03-12", "customer_id": "CUST-106", "product": "Webcam HD", "category": "Electronics", "region": "East", "quantity": 10, "unit_price": 59.99, "total_amount": 599.90, "discount": 0.2, "status": "completed"},
        {"order_id": "ORD-009", "order_date": "2024-03-20", "customer_id": "CUST-103", "product": "Desk Lamp", "category": "Furniture", "region": "East", "quantity": 2, "unit_price": 45.00, "total_amount": 90.00, "discount": None, "status": "cancelled"},
        {"order_id": "ORD-010", "order_date": "2024-04-01", "customer_id": "CUST-107", "product": "Laptop Pro 15", "category": "Electronics", "region": "West", "quantity": 1, "unit_price": 1299.99, "total_amount": 1299.99, "discount": 0.1, "status": "completed"},
        {"order_id": "ORD-011", "order_date": "2024-04-05", "customer_id": "CUST-108", "product": "Wireless Mouse", "category": "Electronics", "region": "North", "quantity": 20, "unit_price": 29.99, "total_amount": 599.80, "discount": 0.25, "status": "completed"},
        {"order_id": "ORD-012", "order_date": "2024-04-10", "customer_id": "CUST-104", "product": "Standing Desk", "category": "Furniture", "region": "West", "quantity": 2, "unit_price": 549.00, "total_amount": 1098.00, "discount": 0.0, "status": "completed"},
        {"order_id": "ORD-013", "order_date": "2024-05-01", "customer_id": "CUST-109", "product": "Monitor 27in", "category": "Electronics", "region": "South", "quantity": 3, "unit_price": 399.99, "total_amount": 1199.97, "discount": 0.1, "status": "pending"},
        {"order_id": "ORD-014", "order_date": "2024-05-15", "customer_id": "CUST-110", "product": "Office Chair", "category": "Furniture", "region": "North", "quantity": 4, "unit_price": 699.00, "total_amount": 2796.00, "discount": 0.2, "status": "completed"},
        {"order_id": "ORD-015", "order_date": "2024-06-01", "customer_id": "CUST-101", "product": "Keyboard Mech", "category": "Electronics", "region": "North", "quantity": 1, "unit_price": 89.99, "total_amount": 89.99, "discount": 0.0, "status": "completed"},
        # Intentional data quality issues for cleaning demos
        {"order_id": "ORD-016", "order_date": "2024-06-10", "customer_id": "CUST-111", "product": "  Laptop Pro 15  ", "category": "electronics", "region": "NORTH", "quantity": 1, "unit_price": 1299.99, "total_amount": 1299.99, "discount": None, "status": "completed"},
        {"order_id": "ORD-016", "order_date": "2024-06-10", "customer_id": "CUST-111", "product": "  Laptop Pro 15  ", "category": "electronics", "region": "NORTH", "quantity": 1, "unit_price": 1299.99, "total_amount": 1299.99, "discount": None, "status": "completed"},
        {"order_id": "ORD-017", "order_date": "2024-06-15", "customer_id": "CUST-112", "product": "Webcam HD", "category": "Electronics", "region": "south", "quantity": -1, "unit_price": 59.99, "total_amount": -59.99, "discount": 0.0, "status": "completed"},
        {"order_id": "ORD-018", "order_date": "2024-07-01", "customer_id": "CUST-113", "product": "", "category": "", "region": "East", "quantity": 0, "unit_price": 0.0, "total_amount": 0.0, "discount": None, "status": ""},
    ]

    table_ref = f"{dataset_ref}.sales_data"
    print(f"  📊 Creating {table_ref} ({len(sales_rows)} rows)...")
    table = bigquery.Table(table_ref, schema=sales_schema)
    table.description = "Sample sales orders with intentional data quality issues for demo"
    table = client.create_table(table, exists_ok=True)
    errors = client.insert_rows_json(table_ref, sales_rows)
    if errors:
        print(f"    ⚠️  Insert errors: {errors}")
    else:
        print(f"    ✅ {len(sales_rows)} rows inserted.")

    # ─── Table 2: customer_data ──────────────────────────
    customer_schema = [
        bigquery.SchemaField("customer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("email", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("signup_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("region", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("tier", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("lifetime_value", "FLOAT", mode="NULLABLE"),
    ]

    customer_rows = [
        {"customer_id": "CUST-101", "name": "Alice Johnson", "email": "alice@example.com", "signup_date": "2023-06-15", "region": "North", "tier": "Gold", "lifetime_value": 4989.96},
        {"customer_id": "CUST-102", "name": "Bob Smith", "email": "bob@example.com", "signup_date": "2023-08-20", "region": "South", "tier": "Silver", "lifetime_value": 1449.94},
        {"customer_id": "CUST-103", "name": "Carol Davis", "email": "carol@example.com", "signup_date": "2023-09-01", "region": "East", "tier": "Bronze", "lifetime_value": 639.00},
        {"customer_id": "CUST-104", "name": "Dan Wilson", "email": "dan@example.com", "signup_date": "2023-11-10", "region": "West", "tier": "Gold", "lifetime_value": 1367.97},
        {"customer_id": "CUST-105", "name": "Eve Martinez", "email": None, "signup_date": "2024-01-05", "region": "South", "tier": "Silver", "lifetime_value": 699.00},
        {"customer_id": "CUST-106", "name": "Frank Lee", "email": "frank@example.com", "signup_date": "2024-01-20", "region": "East", "tier": "Bronze", "lifetime_value": 599.90},
        {"customer_id": "CUST-107", "name": "Grace Kim", "email": "grace@example.com", "signup_date": "2024-02-14", "region": "West", "tier": "Silver", "lifetime_value": 1299.99},
        {"customer_id": "CUST-108", "name": "Hank Brown", "email": "", "signup_date": "2024-03-01", "region": "North", "tier": "Bronze", "lifetime_value": 599.80},
        {"customer_id": "CUST-109", "name": "Iris Chen", "email": "iris@example.com", "signup_date": "2024-03-15", "region": "South", "tier": "Gold", "lifetime_value": 1199.97},
        {"customer_id": "CUST-110", "name": "Jack Taylor", "email": "jack@example.com", "signup_date": "2024-04-01", "region": "North", "tier": "Gold", "lifetime_value": 2796.00},
    ]

    table_ref = f"{dataset_ref}.customer_data"
    print(f"  👥 Creating {table_ref} ({len(customer_rows)} rows)...")
    table = bigquery.Table(table_ref, schema=customer_schema)
    table.description = "Sample customer data"
    table = client.create_table(table, exists_ok=True)
    errors = client.insert_rows_json(table_ref, customer_rows)
    if errors:
        print(f"    ⚠️  Insert errors: {errors}")
    else:
        print(f"    ✅ {len(customer_rows)} rows inserted.")

    print(f"\n🎉 Done! Sample data loaded into {dataset_ref}")
    print("   Tables: sales_data, customer_data")
    print(f"\n   Try: make run → then ask: 'Show me total sales by region'")


if __name__ == "__main__":
    main()
