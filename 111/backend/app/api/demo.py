"""/api/demo · 不依赖 LLM 的可视化 Demo。

匹配用户问题的关键词，挑选预定义 SQL 模板并真实执行，
返回数据 + 智能推断 chart。前端使用此端点可在无 API key 时
演示 ECharts 智能选图效果。
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db.engine import get_engine

router = APIRouter(prefix="/api/demo", tags=["demo"])


class DemoItem(BaseModel):
    keywords: list[str]
    title: str
    sql: str


_TEMPLATES: list[DemoItem] = [
    DemoItem(
        keywords=["趋势", "月份", "月度", "走势", "month", "trend"],
        title="月度销售趋势",
        sql=(
            "SELECT strftime('%Y-%m', order_date) AS month, "
            "ROUND(SUM(total_amount), 0) AS sales "
            "FROM orders "
            "WHERE order_date IS NOT NULL "
            "GROUP BY month "
            "ORDER BY month"
        ),
    ),
    DemoItem(
        keywords=["区域", "地区", "region", "按区"],
        title="各区域销售对比",
        sql=(
            "SELECT c.region, ROUND(SUM(o.total_amount), 0) AS sales "
            "FROM orders o JOIN customers c ON o.customer_id = c.id "
            "GROUP BY c.region ORDER BY sales DESC"
        ),
    ),
    DemoItem(
        keywords=["品类", "类目", "category"],
        title="品类销量",
        sql=(
            "SELECT cat.name AS category, "
            "ROUND(SUM(o.total_amount), 0) AS sales, "
            "SUM(o.quantity) AS qty "
            "FROM orders o "
            "JOIN products p ON o.product_id = p.id "
            "JOIN categories cat ON p.category_id = cat.id "
            "GROUP BY cat.name ORDER BY sales DESC"
        ),
    ),
    DemoItem(
        keywords=["等级", "tier", "vip", "客户"],
        title="客户等级销量",
        sql=(
            "SELECT c.tier, ROUND(SUM(o.total_amount), 0) AS sales, "
            "COUNT(DISTINCT c.id) AS customer_count "
            "FROM orders o JOIN customers c ON o.customer_id = c.id "
            "GROUP BY c.tier"
        ),
    ),
    DemoItem(
        keywords=["商品", "product", "top"],
        title="商品销量 Top10",
        sql=(
            "SELECT p.name AS product, ROUND(SUM(o.total_amount), 0) AS sales, "
            "SUM(o.quantity) AS qty "
            "FROM orders o JOIN products p ON o.product_id = p.id "
            "GROUP BY p.name ORDER BY sales DESC LIMIT 10"
        ),
    ),
    DemoItem(
        keywords=["订单", "状态", "status"],
        title="订单状态分布",
        sql=(
            "SELECT o.status, COUNT(*) AS cnt, "
            "ROUND(SUM(o.total_amount), 0) AS amount "
            "FROM orders o GROUP BY o.status"
        ),
    ),
    DemoItem(
        keywords=["城市", "城市销售", "city"],
        title="城市销量 Top15",
        sql=(
            "SELECT c.city, ROUND(SUM(o.total_amount), 0) AS sales "
            "FROM orders o JOIN customers c ON o.customer_id = c.id "
            "GROUP BY c.city ORDER BY sales DESC LIMIT 15"
        ),
    ),
    DemoItem(
        keywords=["价格", "price", "客单"],
        title="商品价格分布",
        sql=(
            "SELECT CASE "
            "WHEN price < 500 THEN '0-500' "
            "WHEN price < 1000 THEN '500-1000' "
            "WHEN price < 2000 THEN '1000-2000' "
            "WHEN price < 5000 THEN '2000-5000' "
            "ELSE '5000+' END AS price_range, "
            "COUNT(*) AS cnt FROM products GROUP BY price_range"
        ),
    ),
]


def _infer_chart_shape(data: list[dict]) -> dict:
    """智能推断 chart shape（不依赖前端 lib；后端走自己的启发式）。"""
    if not data:
        return {"type": "table", "title": "无数据"}
    cols = list(data[0].keys())
    # 简化版：含 month/date → line；行数 1 且多列 → bar；多行单数值 → bar
    if any("month" in c.lower() or "date" in c.lower() for c in cols):
        return {"type": "line", "title": "趋势", "x": cols[0], "y": cols[1] if len(cols) > 1 else cols[0]}
    if len(data) <= 6:
        return {"type": "pie", "title": cols[1] if len(cols) > 1 else cols[0], "x": cols[0], "y": cols[1] if len(cols) > 1 else cols[0]}
    return {"type": "bar", "title": cols[1] if len(cols) > 1 else cols[0], "x": cols[0], "y": cols[1] if len(cols) > 1 else cols[0]}


@router.get("/templates")
def list_templates() -> list[dict]:
    return [{"id": i, "keywords": t.keywords, "title": t.title} for i, t in enumerate(_TEMPLATES)]


@router.get("/ask")
def demo_ask(question: str = Query(..., description="用户问题")) -> dict:
    """根据 question 关键词匹配模板并执行，返回真实数据 + 推断 chart。"""
    matched: DemoItem = _TEMPLATES[0]  # 默认 trend
    score = 0
    for t in _TEMPLATES:
        s = sum(1 for kw in t.keywords if kw in question)
        if s > score:
            matched = t
            score = s

    eng = get_engine()
    with eng.connect() as conn:
        result = conn.exec_driver_sql(matched.sql)
        columns = list(result.keys())
        rows = result.fetchall()
    data = [dict(zip(columns, r)) for r in rows]
    chart = _infer_chart_shape(data)

    return {
        "matched_keywords": matched.keywords,
        "title": matched.title,
        "question": question,
        "sql": matched.sql,
        "chart": chart,
        "data": data,
        "row_count": len(data),
    }
