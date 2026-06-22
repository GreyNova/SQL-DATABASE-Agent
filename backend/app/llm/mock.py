"""Mock chat model for local/offline development.

Returns canned SQL + explanations keyed on the question, all written against
the *actual* amazon_test.db schema:
    amazon_products(id, product_name, category, price, rating, stock_quantity)
    amazon_sales(id, product_id, customer_id, sale_date, quantity, total_price)

Use MOCK_LLM=true in .env to avoid spending Gemini quota while iterating on
the UI / graph / security layer.
"""
from __future__ import annotations

import json
import re
from typing import Any, List, Optional

from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import SimpleChatModel
from langchain_core.messages import BaseMessage


def _extract_question(messages: List[BaseMessage], full_text: str) -> str:
    if "## QUESTION" in full_text:
        parts = full_text.split("## QUESTION", 1)
        if len(parts) > 1:
            return parts[1].strip().split("\n")[0].strip()
    for m in reversed(messages):
        if getattr(m, "type", "") == "human":
            return str(m.content).strip()
    return ""


class MockChatModel(SimpleChatModel):
    """A deterministic, offline stand-in for the real LLM."""

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"

    def _call(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        full_text = "\n".join(str(m.content) for m in messages)
        question = _extract_question(messages, full_text)
        q = question.lower()

        is_sql_gen = "DATABASE SCHEMA" in full_text or "## FAILED SQL" in full_text
        is_explanation = "SQL THAT RAN" in full_text or "## RESULTS" in full_text

        if is_sql_gen:
            return json.dumps(_build_sql(q, question))
        if is_explanation:
            return _build_explanation(q, question)
        return (
            "Hello! I am the SQL Database Agent for the Amazon sample data. "
            "Ask me about products, ratings, sales, revenue, or stock."
        )


# ---------------------------------------------------------------------------
# SQL generation (returns dict that the generator node parses)
# ---------------------------------------------------------------------------
def _build_sql(q: str, question: str) -> dict[str, Any]:
    sql: str
    rationale: str
    assumptions: list[str] = []

    if "revenue by category" in q or "sales by category" in q or "category revenue" in q:
        sql = (
            "SELECT p.category, ROUND(SUM(s.total_price), 2) AS revenue "
            "FROM amazon_sales s JOIN amazon_products p ON s.product_id = p.id "
            "GROUP BY p.category ORDER BY revenue DESC"
        )
        rationale = "Sum line revenue per category via the sales→products join."
    elif "total sales" in q or "total revenue" in q or "overall revenue" in q or "how much revenue" in q:
        sql = "SELECT ROUND(SUM(total_price), 2) AS total_revenue FROM amazon_sales"
        rationale = "Single aggregate over amazon_sales.total_price."
    elif "revenue by month" in q or "sales by month" in q or "monthly revenue" in q:
        sql = (
            "SELECT strftime('%Y-%m', sale_date) AS month, "
            "ROUND(SUM(total_price), 2) AS revenue "
            "FROM amazon_sales GROUP BY month ORDER BY month"
        )
        rationale = "Bucket sale_date by month and sum revenue."
        assumptions.append("Uses SQLite strftime; in Postgres use date_trunc.")
    elif "top selling" in q or "best selling" in q or "top products" in q or "top 10" in q:
        sql = (
            "SELECT p.product_name, p.category, SUM(s.quantity) AS units_sold, "
            "ROUND(SUM(s.total_price), 2) AS revenue "
            "FROM amazon_sales s JOIN amazon_products p ON s.product_id = p.id "
            "GROUP BY p.id ORDER BY units_sold DESC LIMIT 10"
        )
        rationale = "Rank products by total units sold."
    elif "top rated" in q or "highest rated" in q or "best rated" in q or "rating" in q:
        sql = (
            "SELECT product_name, category, price, rating, stock_quantity "
            "FROM amazon_products ORDER BY rating DESC, product_name LIMIT 10"
        )
        rationale = "Highest customer rating first."
    elif "low stock" in q or "out of stock" in q or "stock" in q:
        threshold = _extract_number(q, default=20)
        sql = (
            f"SELECT product_name, category, stock_quantity, price "
            f"FROM amazon_products WHERE stock_quantity <= {threshold} "
            f"ORDER BY stock_quantity ASC"
        )
        rationale = f"Products at or below {threshold} units of stock."
        assumptions.append(f"Threshold inferred as {threshold}.")
    elif "spent the most" in q or "top customer" in q or "top buyer" in q or "customer" in q:
        sql = (
            "SELECT customer_id, ROUND(SUM(total_price), 2) AS total_spent, "
            "COUNT(*) AS orders "
            "FROM amazon_sales GROUP BY customer_id ORDER BY total_spent DESC LIMIT 5"
        )
        rationale = "Rank anonymized customers by total spend."
    elif "category" in q and ("count" in q or "how many" in q or "products" in q):
        sql = (
            "SELECT category, COUNT(*) AS product_count, "
            "ROUND(AVG(rating), 2) AS avg_rating "
            "FROM amazon_products GROUP BY category ORDER BY product_count DESC"
        )
        rationale = "Product count and average rating per category."
    else:
        # Safe generic fallback
        sql = (
            "SELECT product_name, category, price, rating, stock_quantity "
            "FROM amazon_products ORDER BY rating DESC LIMIT 10"
        )
        rationale = "Default: show top-rated products."

    return {"sql": sql, "rationale": rationale, "assumptions": assumptions}


def _extract_number(text: str, default: int) -> int:
    m = re.search(r"\d+", text)
    return int(m.group(0)) if m else default


# ---------------------------------------------------------------------------
# Explanation
# ---------------------------------------------------------------------------
def _build_explanation(q: str, question: str) -> str:
    if "revenue by category" in q or "sales by category" in q:
        answer = (
            "Electronics is the top-revenue category, followed by Home & Kitchen "
            "and Clothing. The bar chart shows the full breakdown — Electronics "
            "alone accounts for the largest share of total sales."
        )
        follow = "Top selling products in Electronics | Revenue by month | Lowest revenue category"
    elif "total sales" in q or "total revenue" in q or "overall revenue" in q or "how much revenue" in q:
        answer = (
            "Total revenue across all recorded sales is shown as a single KPI. "
            "This is the sum of every line item in amazon_sales."
        )
        follow = "Revenue by category | Revenue by month | Top selling products"
    elif "revenue by month" in q or "sales by month" in q or "monthly revenue" in q:
        answer = (
            "Revenue trends upward across the recorded months, with a clear peak "
            "in the most recent period. The line chart makes the month-over-month "
            "growth visible at a glance."
        )
        follow = "Which month had the highest revenue? | Revenue by category | Top selling products"
    elif "top selling" in q or "best selling" in q or "top products" in q or "top 10" in q:
        answer = (
            "The best-selling products by units are led by a handful of Electronics "
            "and Books items. The table ranks all ten, with units sold and revenue."
        )
        follow = "Revenue by category | Show low stock products | Top rated products"
    elif "top rated" in q or "highest rated" in q or "best rated" in q or "rating" in q:
        answer = (
            "The highest-rated products sit at the top of the rating scale (near 5.0). "
            "The table lists the top ten with their category, price, and stock."
        )
        follow = "Top rated products under ₹1000 | Top selling products | Low stock products"
    elif "low stock" in q or "out of stock" in q or "stock" in q:
        answer = (
            "Several products are running low on inventory. The table lists them "
            "from the most depleted upward — these are good candidates for restocking."
        )
        follow = "Top selling products | Revenue by category | Products that are both low stock and top selling"
    elif "spent the most" in q or "top customer" in q or "top buyer" in q or "customer" in q:
        answer = (
            "The top-spending customer (by anonymized id) is shown first, with their "
            "total spend and order count. The next four customers round out the top five."
        )
        follow = "Average spend per customer | Revenue by category | Top selling products"
    elif "category" in q:
        answer = (
            "The catalog is spread across several categories. The table shows how many "
            "products each category holds plus its average rating."
        )
        follow = "Revenue by category | Top rated products | Low stock products"
    else:
        answer = (
            "Here are the top-rated products from the catalog. The table shows name, "
            "category, price, rating, and stock for each."
        )
        follow = "Top selling products | Revenue by category | Low stock products"

    return f"{answer}\n\nFOLLOWUPS: {follow}"
