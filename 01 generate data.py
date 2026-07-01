"""
Phase 2: สร้าง dataset ยอดขายสังเคราะห์ที่สมจริง
- ยอดขายรายวัน 3 ปี (2023-2025), 3 หมวดสินค้า
- มี trend (ขาขึ้น), seasonality รายสัปดาห์/รายปี, promo, holiday, noise
โครงสร้างคอลัมน์เหมือนข้อมูลขายจริง -> สลับใส่ข้อมูลจริงทีหลังได้
"""
import numpy as np
import pandas as pd

np.random.seed(42)

# ช่วงเวลา 3 ปี
dates = pd.date_range("2023-01-01", "2025-12-31", freq="D")
categories = ["Electronics", "Clothing", "Groceries"]

# วันหยุด/โปรโมชันหลักของไทย (approx)
holidays = pd.to_datetime([
    "2023-01-01","2023-04-13","2023-04-14","2023-04-15","2023-12-31",
    "2024-01-01","2024-04-13","2024-04-14","2024-04-15","2024-12-31",
    "2025-01-01","2025-04-13","2025-04-14","2025-04-15","2025-12-31",
])
# วัน mega-sale (11.11, 12.12)
promo_days = pd.to_datetime([
    f"{y}-{m}-{d}" for y in [2023,2024,2025] for m,d in [(11,11),(12,12),(6,6),(9,9)]
])

rows = []
for cat in categories:
    base = {"Electronics": 5000, "Clothing": 3000, "Groceries": 8000}[cat]
    trend_slope = {"Electronics": 3.0, "Clothing": 1.5, "Groceries": 2.0}[cat]

    for i, d in enumerate(dates):
        # trend ขาขึ้นช้าๆ
        trend = base + trend_slope * i
        # seasonality รายปี (peak ปลายปี)
        yearly = 1 + 0.25 * np.sin(2 * np.pi * (d.dayofyear - 300) / 365)
        # seasonality รายสัปดาห์ (เสาร์-อาทิตย์ขายดี)
        weekly = 1.3 if d.dayofweek >= 5 else 1.0
        # holiday effect
        hol = 1.4 if d in holidays.values else 1.0
        # promo effect (แรงมาก)
        promo_flag = 1 if d in promo_days.values else 0
        promo = 2.5 if promo_flag else 1.0
        # noise
        noise = np.random.normal(1, 0.08)

        sales = trend * yearly * weekly * hol * promo * noise
        rows.append({
            "date": d,
            "category": cat,
            "sales": round(max(sales, 0), 2),
            "is_holiday": int(d in holidays.values),
            "is_promo": promo_flag,
        })

df = pd.DataFrame(rows)
df.to_csv("data/sales_raw.csv", index=False)

print(f"สร้างข้อมูลสำเร็จ: {len(df):,} แถว")
print(f"ช่วงเวลา: {df.date.min().date()} ถึง {df.date.max().date()}")
print(f"หมวดสินค้า: {df.category.unique().tolist()}")
print("\nตัวอย่างข้อมูล:")
print(df.head())
print("\nสรุปยอดขายรายหมวด:")
print(df.groupby("category")["sales"].agg(["mean", "min", "max"]).round(0))