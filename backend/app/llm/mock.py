from typing import Any, List, Optional
from langchain_core.language_models.chat_models import SimpleChatModel
from langchain_core.messages import BaseMessage
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
import json

class MockChatModel(SimpleChatModel):
    """A mock chat model that mimics LLM responses locally for testing and fallback."""

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
        # Combine messages into a single text block
        full_text = "\n".join([str(m.content) for m in messages])
        
        # Determine the user's question
        question = ""
        if "## QUESTION" in full_text:
            parts = full_text.split("## QUESTION")
            if len(parts) > 1:
                question = parts[1].strip().split("\n")[0].strip()
        
        if not question:
            # Fallback: look for the last human message
            for m in reversed(messages):
                if getattr(m, "type", "") == "human":
                    question = str(m.content)
                    break
        
        is_sql_gen = "DATABASE SCHEMA" in full_text or "## FAILED SQL" in full_text
        is_explanation = "SQL THAT RAN" in full_text or "RESULTS" in full_text

        if is_sql_gen:
            q_lower = question.lower()
            
            # 0. Amazon mock
            if "amazon" in q_lower:
                sql = (
                    "SELECT product_name, category, price, rating, stock_quantity "
                    "FROM amazon_products "
                    "ORDER BY rating DESC "
                    "LIMIT 10"
                )
                rationale = "Query amazon_products table for top rated products."
                assumptions = []

            # 1. Category total sales / revenue
            elif "total sales" in q_lower or "revenue by category" in q_lower or "highest total sales" in q_lower or "sales revenue" in q_lower:
                sql = (
                    "SELECT c.name AS category_name, SUM(oi.quantity * oi.price) AS total_sales "
                    "FROM order_items oi "
                    "JOIN products p ON oi.product_id = p.id "
                    "JOIN categories c ON p.category_id = c.id "
                    "GROUP BY c.name "
                    "ORDER BY total_sales DESC"
                )
                rationale = "Sum the total price * quantity of order items grouped by category, ordered descending."
                assumptions = ["Sales is defined as the sum of order_items price * quantity."]

            # 2. Top-rated products in a category
            elif "top rated" in q_lower or "highest rated" in q_lower or "best rated" in q_lower:
                if "electronics" in q_lower:
                    sql = (
                        "SELECT p.name, p.price, p.average_rating, p.review_count "
                        "FROM products p "
                        "JOIN categories c ON p.category_id = c.id "
                        "WHERE c.name LIKE '%Electronics%' "
                        "ORDER BY p.average_rating DESC, p.review_count DESC "
                        "LIMIT 5"
                    )
                    rationale = "Select products from Electronics category sorted by average rating and review count."
                    assumptions = ["Filter is case-insensitive for Electronics category."]
                else:
                    sql = (
                        "SELECT p.name, c.name AS category, p.price, p.average_rating, p.review_count "
                        "FROM products p "
                        "JOIN categories c ON p.category_id = c.id "
                        "ORDER BY p.average_rating DESC, p.review_count DESC "
                        "LIMIT 5"
                    )
                    rationale = "Select products sorted by average rating and review count descending across all categories."
                    assumptions = []

            # 3. Rating and price filters (e.g. rated above 4.5 and price less than 1500)
            elif "rating above" in q_lower or "rated above" in q_lower or "rating higher than" in q_lower:
                # Extracts potential price limit or uses 1500 as default
                price_limit = 1500
                if "less than 1000" in q_lower or "under 1000" in q_lower:
                    price_limit = 1000
                elif "less than 500" in q_lower or "under 500" in q_lower:
                    price_limit = 500
                
                sql = (
                    f"SELECT name, price, average_rating, review_count "
                    f"FROM products "
                    f"WHERE average_rating > 4.5 AND price < {price_limit} "
                    f"ORDER BY price ASC"
                )
                rationale = f"Filter products by average_rating > 4.5 and price < {price_limit}, sorted by price ascending."
                assumptions = []

            # 4. Category breakdown of rating / reviews
            elif "rating and reviews by category" in q_lower or "reviews by category" in q_lower:
                sql = (
                    "SELECT c.name AS category_name, AVG(p.average_rating) AS avg_rating, SUM(p.review_count) AS total_reviews "
                    "FROM products p "
                    "JOIN categories c ON p.category_id = c.id "
                    "GROUP BY c.name "
                    "ORDER BY avg_rating DESC"
                )
                rationale = "Group products by category and calculate average rating and sum of review counts."
                assumptions = []

            # 5. Top customers
            elif "spent the most" in q_lower or "top customers" in q_lower or "top users" in q_lower or "top spending" in q_lower:
                sql = (
                    "SELECT u.name, u.email, u.city, SUM(o.total_amount) AS total_spent "
                    "FROM orders o "
                    "JOIN users u ON o.user_id = u.id "
                    "GROUP BY u.id "
                    "ORDER BY total_spent DESC "
                    "LIMIT 5"
                )
                rationale = "Group orders by user, sum total_amount, order descending, and return top 5."
                assumptions = ["Includes all order statuses, including pending and shipped."]

            # 6. Count products per category
            elif "how many products" in q_lower or "product count" in q_lower or "products in each category" in q_lower:
                sql = (
                    "SELECT c.name AS category_name, COUNT(p.id) AS product_count "
                    "FROM products p "
                    "JOIN categories c ON p.category_id = c.id "
                    "GROUP BY c.name "
                    "ORDER BY product_count DESC"
                )
            # Default fallback
            else:
                sql = "SELECT * FROM products ORDER BY average_rating DESC LIMIT 5"
                rationale = "Default query showing top 5 products by rating."
                assumptions = []

            response_json = {
                "sql": sql,
                "rationale": rationale,
                "assumptions": assumptions
            }
            return json.dumps(response_json)

        elif is_explanation:
            q_lower = question.lower()
            
            if "amazon" in q_lower:
                answer = "Here are the top rated Amazon products from your test database."
                followups = (
                    "Show Amazon sales for electronics. | "
                    "List highest stock Amazon products."
                )
            elif "total sales" in q_lower or "revenue by category" in q_lower or "highest total sales" in q_lower or "sales revenue" in q_lower:
                answer = (
                    "Based on our sales data, the category with the highest total sales revenue is **Electronics**, "
                    "which generated the most sales, followed closely by Home & Kitchen and Clothing & Accessories."
                )
                followups = (
                    "Show the top selling products in Electronics | "
                    "What is the total sales for Books? | "
                    "List recent orders in Electronics"
                )
            elif "top rated" in q_lower or "highest rated" in q_lower or "best rated" in q_lower:
                if "electronics" in q_lower:
                    answer = (
                        "The highest-rated products in the Electronics category are led by the **Premium Keyboard** "
                        "and **Smart Watch**, which maintain an average rating of 4.6+ based on verified reviews."
                    )
                    followups = (
                        "Show reviews for Premium Keyboard | "
                        "What is the price of the Smart Watch? | "
                        "List all Electronics sorted by price"
                    )
                else:
                    answer = (
                        "Our top-rated products across all categories are led by the **Premium Keyboard** and **Wireless Speaker**, "
                        "both maintaining a perfect 5.0 rating based on multiple verified reviews."
                    )
                    followups = (
                        "Show reviews for Wireless Speaker | "
                        "Which category has the highest average rating? | "
                        "List the top 5 cheapest products"
                    )
            elif "rating above" in q_lower or "rated above" in q_lower or "rating higher than" in q_lower:
                answer = (
                    "There are several highly-rated products (above 4.5 stars) priced under the selected price limit. "
                    "This includes budget-friendly items like the **Premium Water Bottle** (4.8 stars) and **Smart Mouse Pad** (4.7 stars)."
                )
                followups = (
                    "List all products under 1000 | "
                    "Show reviews for Premium Water Bottle | "
                    "What is the highest rated product under 500?"
                )
            elif "rating and reviews by category" in q_lower or "reviews by category" in q_lower:
                answer = (
                    "The category with the highest average rating is **Books** (average rating of 4.45), "
                    "while the category with the most customer reviews is **Electronics**."
                )
                followups = (
                    "Show the top products in Books | "
                    "Which category has the lowest average rating? | "
                    "List all categories with product counts"
                )
            elif "spent the most" in q_lower or "top customers" in q_lower or "top users" in q_lower or "top spending" in q_lower:
                answer = (
                    "Our top spending customer is **Aarav Sharma** from Mumbai, who spent the highest aggregate total "
                    "across multiple orders. The other top spenders are Diya Patel and Rohan Verma."
                )
                followups = (
                    "List all orders placed by Aarav Sharma | "
                    "Which city has the highest total spending? | "
                    "Show average spending per customer"
                )
            elif "how many products" in q_lower or "product count" in q_lower or "products in each category" in q_lower:
                answer = (
                    "We have a balanced catalog with exactly **20 products** in each of our 6 categories, "
                    "for a total of 120 products in the database."
                )
                followups = (
                    "List all products in Electronics | "
                    "Show products with stock below 10 | "
                    "What is the total inventory value of our catalog?"
                )
            elif "amazon" in q_lower:
                answer = "Here are the top rated Amazon products from your test database."
                followups = (
                    "Show Amazon sales for electronics. | "
                    "List highest stock Amazon products."
                )
            else:
                answer = "Here is the query result showing the requested data from the database. See the details in the table below."
                followups = (
                    "Show the top selling products. | "
                    "List the most recent orders. | "
                    "What is our total revenue?"
                )

            return f"{answer}\n\nFOLLOWUPS: {followups}"

        else:
            return "Hello! I am the SQL Database Agent. Ask me anything about your database."
