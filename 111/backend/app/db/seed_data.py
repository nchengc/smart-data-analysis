"""种子业务数据：4 张表共约 ~600 条记录。"""

import random
from datetime import date, timedelta

random.seed(42)  # 保证可复现

REGIONS = ["华东", "华南", "华北", "西南", "西北"]
CITIES = {
    "华东": ["上海", "杭州", "南京", "苏州", "宁波"],
    "华南": ["广州", "深圳", "厦门", "福州", "南宁"],
    "华北": ["北京", "天津", "石家庄", "太原", "济南"],
    "西南": ["成都", "重庆", "昆明", "贵阳", "拉萨"],
    "西北": ["西安", "兰州", "西宁", "乌鲁木齐", "银川"],
}
TIERS = ["normal", "normal", "normal", "gold", "vip"]

CATEGORIES = [
    ("家电", "家用电器"),
    ("服饰", "服装鞋帽"),
    ("美妆", "美妆护肤"),
    ("食品", "休闲食品"),
    ("数码", "手机配件"),
    ("母婴", "母婴用品"),
    ("运动", "运动户外"),
    ("图书", "书籍文具"),
]

PRODUCTS = [
    ("iPhone 15", "数码", 6999),
    ("小米电视", "家电", 2599),
    ("戴森吹风机", "美妆", 2999),
    ("Nike 跑步鞋", "运动", 899),
    ("Kindle 电子书", "图书", 599),
    ("戴森吸尘器", "家电", 4990),
    ("MacBook Pro", "数码", 14999),
    ("雅诗兰黛小棕瓶", "美妆", 880),
    ("三只松鼠坚果", "食品", 99),
    ("Lululemon 瑜伽裤", "运动", 750),
    ("宝宝奶粉", "母婴", 368),
    ("学习平板", "数码", 1299),
    ("羽绒服", "服饰", 1299),
    ("羊绒衫", "服饰", 999),
    ("咖啡豆", "食品", 159),
    ("无线耳机", "数码", 1299),
    ("智能手表", "数码", 2199),
    ("口红", "美妆", 320),
    ("面膜", "美妆", 99),
    ("球鞋", "运动", 599),
]


def seed_business_data(conn) -> None:
    """向 4 张业务表插入示例数据。"""

    # 1) customers（80 人）
    customers = []
    for i in range(1, 81):
        region = random.choice(REGIONS)
        city = random.choice(CITIES[region])
        register = date(2023, 1, 1) + timedelta(days=random.randint(0, 540))
        customers.append((f"用户{i:03d}", region, city, register.isoformat(), random.choice(TIERS)))

    conn.executemany(
        "INSERT INTO customers (name, region, city, register_date, tier) VALUES (?, ?, ?, ?, ?)",
        customers,
    )

    # 2) categories
    conn.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?)",
        CATEGORIES,
    )
    cat_id = {
        name: cid
        for cid, (name, _desc) in [(r[0], (r[1], r[2])) for r in conn.execute("SELECT id, name, description FROM categories").fetchall()]
    }

    # 3) products
    for name, cat, price in PRODUCTS:
        # 简单加几个变体以增加记录数
        for suffix in ["", " · 标准版", " · 旗舰版"]:
            conn.execute(
                "INSERT INTO products (name, category_id, price, stock) VALUES (?, ?, ?, ?)",
                (f"{name}{suffix}", cat_id[cat], price + random.randint(-100, 200), random.randint(20, 300)),
            )

    # 4) orders（约 500 条，最近 12 个月）
    prods = conn.execute("SELECT id, price FROM products").fetchall()
    custs = conn.execute("SELECT id FROM customers").fetchall()
    if not prods or not custs:
        return

    orders = []
    base = date.today()
    for _ in range(500):
        prod = random.choice(prods)
        cust = random.choice(custs)
        qty = random.randint(1, 5)
        days_back = random.randint(0, 365)
        order_date = base - timedelta(days=days_back)
        amount = round(prod[1] * qty * random.uniform(0.7, 1.0), 2)
        status = random.choice(["paid", "paid", "paid", "paid", "shipped", "refunded"])
        orders.append((cust[0], prod[0], qty, amount, order_date.isoformat(), status))

    conn.executemany(
        "INSERT INTO orders (customer_id, product_id, quantity, total_amount, order_date, status) VALUES (?, ?, ?, ?, ?, ?)",
        orders,
    )
