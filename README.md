# Sales Forecasting Studio

เครื่องมือพยากรณ์ยอดขายแบบ interactive ด้วย Streamlit — อัปโหลดข้อมูลของตัวเอง เทรนโมเดล และเปรียบเทียบความแม่นยำได้ในหน้าเดียว รองรับทั้ง Prophet และ XGBoost

> พัฒนาเป็น portfolio project ครอบคลุมงาน Data Science ครบวงจร ตั้งแต่การเตรียมข้อมูล time series, การเทรนและเปรียบเทียบโมเดล, การทำ backtesting ไปจนถึงการทำ dashboard ที่ตอบโจทย์ธุรกิจ

---

## คุณสมบัติหลัก

| ด้าน | รายละเอียด |
|------|------------|
| **2 โหมดข้อมูล** | ใช้ข้อมูลตัวอย่าง (synthetic) หรืออัปโหลด CSV ของตัวเอง |
| **Column mapping** | อัปไฟล์ที่ชื่อคอลัมน์เป็นอะไรก็ได้ แล้วเลือกจับคู่ วันที่ / ยอดขาย / หมวด เอง |
| **2 โมเดลให้เทียบ** | Prophet (statistical) และ XGBoost (ML) — ระบบเลือกตัวที่ MAPE ต่ำสุดมาแสดงอัตโนมัติ |
| **Backtesting** | ทดสอบแบบ rolling-window หลายรอบ เพื่อดูความแม่นยำที่สม่ำเสมอ |
| **Feature importance** | แสดงว่าปัจจัยใดมีผลต่อยอดขายมากที่สุด (จาก XGBoost) |
| **Business dashboard** | KPI, กราฟ Actual vs Forecast พร้อมช่วงความมั่นใจ, ตารางสรุปรายเดือน, ดาวน์โหลดผลเป็น CSV |
| **UI** | ใช้ Lucide icon (inline SVG) ธีม indigo สะอาด ไม่มี emoji |

---

## หลักการทาง Time Series ที่ใช้

- **Time-based split** ไม่ใช้ random split — จำลองการพยากรณ์อนาคตจริงและป้องกัน data leakage
- **XGBoost feature engineering**: lag features (1/7/14/30 วัน), rolling mean/std (7/30 วัน), calendar features (วันในสัปดาห์, เดือน, วันหยุดสุดสัปดาห์)
- **Recursive forecasting**: XGBoost ป้อนค่าที่ทำนายกลับเป็น input ของวันถัดไป
- **Rolling-window backtesting**: เลื่อนช่วงทดสอบหลายรอบตามเวลา แทนการวัดผลเพียงรอบเดียว
- **Evaluation**: วัดผลด้วย MAPE / RMSE / MAE

---

## Tech Stack

- **Python** — pandas, numpy
- **Forecasting** — Prophet (Meta), XGBoost
- **ML utilities** — scikit-learn
- **Dashboard** — Streamlit
- **Visualization** — Plotly

---

## โครงสร้างโปรเจกต์

```
Sales-Forecasting-Dashboard/
├── app.py                  # แอปหลัก (Streamlit UI)
├── src/
│   ├── forecasting.py      # core: Prophet + XGBoost + feature engineering + backtesting
│   └── ui.py               # Lucide icons + CSS theme
├── data/
│   └── sales_raw.csv       # ข้อมูลตัวอย่างสำหรับโหมด Demo
├── 01_generate_data.py     # สคริปต์สร้างข้อมูลตัวอย่าง (ถ้าต้องการ regenerate)
├── requirements.txt        # Python dependencies
├── packages.txt            # system dependencies (สำหรับ Streamlit Cloud)
├── Dockerfile              # สำหรับ deploy ด้วย Docker
├── .streamlit/config.toml  # ธีมและ config ของ Streamlit
├── DEPLOY.md               # คู่มือ deploy
└── README.md
```

---

## วิธีติดตั้งและรัน

```bash
# 1. clone และเข้าโฟลเดอร์
git clone <repo-url>
cd Sales-Forecasting-Dashboard

# 2. สร้าง virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. ติดตั้ง dependencies
pip install -r requirements.txt

# 4. รันแอป
streamlit run app.py
```

เปิดเบราว์เซอร์ที่ `http://localhost:8501`

---

## รูปแบบ CSV สำหรับอัปโหลด

ต้องมีอย่างน้อย 2 คอลัมน์: **วันที่** และ **ยอดขาย** (ชื่ออะไรก็ได้ เลือกจับคู่ในแอป)
ถ้ามีคอลัมน์ **หมวดสินค้า** ก็เลือกเพิ่มเพื่อกรองดูรายหมวดได้

| date | sales | category |
|------|-------|----------|
| 2025-01-01 | 12500 | Electronics |
| 2025-01-02 | 9800 | Clothing |

---

## ผลลัพธ์ตัวอย่าง (ข้อมูล Demo)

- **MAPE เฉลี่ยจาก backtesting**: ~8% (ผ่านเกณฑ์ธุรกิจ < 15%)
- **ปัจจัยสำคัญที่สุด**: ยอดขาย 7 วันก่อนหน้า — สะท้อน pattern ยอดขายรายสัปดาห์

---

## การ Deploy

ดูรายละเอียดใน [DEPLOY.md](DEPLOY.md) — รองรับทั้ง Streamlit Community Cloud (ฟรี) และ Docker

---

## แนวทางพัฒนาต่อ

- เชื่อมต่อฐานข้อมูล (PostgreSQL) แทนไฟล์ CSV
- Retrain อัตโนมัติ + model monitoring (เฝ้าค่า MAPE)
- เพิ่มโมเดลอื่น เช่น SARIMA, LightGBM