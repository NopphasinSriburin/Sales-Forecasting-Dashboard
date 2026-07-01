# Sales Forecasting Studio

เครื่องมือพยากรณ์ยอดขายแบบ interactive ด้วย Streamlit — อัปโหลดข้อมูลของตัวเอง เทรนโมเดล และเปรียบเทียบความแม่นยำได้ในหน้าเดียว รองรับทั้ง Prophet และ XGBoost

Link : https://sales-forecasting-dashboard-l2fbcibjbqnaegybzdgmex.streamlit.app/

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ภาพรวม

โปรเจกต์นี้เป็น end-to-end forecasting tool ที่ครอบคลุมงาน Data Science ครบวงจร ตั้งแต่การเตรียมข้อมูล time series, การเทรนและเปรียบเทียบโมเดล, การทำ backtesting, ไปจนถึง dashboard ที่ตอบโจทย์ธุรกิจ ออกแบบให้ใช้งานได้จริง ไม่ใช่แค่ notebook ทดลอง

## คุณสมบัติหลัก

| ด้าน | รายละเอียด |
|------|------------|
| **2 โหมดข้อมูล** | ใช้ข้อมูลตัวอย่าง (synthetic) หรืออัปโหลด CSV ของตัวเอง |
| **Column mapping อัตโนมัติ** | ระบบเดาคอลัมน์วันที่/ยอดขาย/หมวดให้ พร้อมให้ปรับเอง รองรับไฟล์ที่ชื่อคอลัมน์ต่างกัน |
| **Validation + แจ้งเตือน** | ตรวจจับการเลือกคอลัมน์ผิด (เช่น เลือกยอดขายเป็นข้อความ) และเตือนพร้อมวิธีแก้ |
| **2 โมเดลให้เทียบ** | Prophet (statistical) และ XGBoost (ML) — เลือกตัวที่ MAPE ต่ำสุดมาแสดงอัตโนมัติ |
| **Backtesting** | ทดสอบแบบ rolling-window หลายรอบ เพื่อดูความแม่นยำที่สม่ำเสมอ |
| **Feature importance** | แสดงว่าปัจจัยใดมีผลต่อยอดขายมากที่สุด (จาก XGBoost) |
| **Performance** | Cache การเทรน + เทรน horizon คงที่ — เลื่อน slider ไม่ต้องเทรนใหม่ |
| **Business dashboard** | KPI, กราฟ Actual vs Forecast พร้อมช่วงความมั่นใจ, ตารางสรุปรายเดือน, ดาวน์โหลด CSV |
| **UI** | Lucide icon (inline SVG) ธีม indigo สะอาด ไม่มี emoji |

## Tech Stack

- **Python** — pandas, numpy
- **Forecasting** — Prophet (Meta), XGBoost
- **ML utilities** — scikit-learn
- **Dashboard** — Streamlit + Plotly

## โครงสร้างโปรเจกต์

```
Sales-Forecasting-Dashboard/
├── app.py                  # แอปหลัก (Streamlit UI + validation + caching)
├── src/
│   ├── forecasting.py      # core: Prophet + XGBoost + feature engineering + backtesting
│   └── ui.py               # Lucide icons + CSS theme
├── data/
│   └── sales_raw.csv       # ข้อมูลตัวอย่างสำหรับโหมด Demo
├── 01_generate_data.py     # สคริปต์สร้างข้อมูลตัวอย่าง (ถ้าต้องการ regenerate)
├── requirements.txt        # Python dependencies
├── packages.txt            # system dependencies (สำหรับ Streamlit Cloud)
├── Dockerfile              # สำหรับ deploy ด้วย Docker
├── .streamlit/config.toml  # ธีมและ config
├── DEPLOY.md               # คู่มือ deploy
└── README.md
```

## วิธีติดตั้งและรัน

```bash
# 1. clone
git clone https://github.com/<username>/Sales-Forecasting-Dashboard.git
cd Sales-Forecasting-Dashboard

# 2. สร้าง virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. ติดตั้ง dependencies
pip install -r requirements.txt

# 4. รัน
streamlit run app.py
```

เปิดเบราว์เซอร์ที่ `http://localhost:8501`

## รูปแบบ CSV สำหรับอัปโหลด

ต้องมีอย่างน้อย 2 คอลัมน์: **วันที่** และ **ยอดขาย** (ชื่ออะไรก็ได้ ระบบเดาให้/เลือกเองได้)
ถ้ามีคอลัมน์ **หมวดสินค้า** ก็เลือกเพิ่มเพื่อกรองรายหมวดได้

| date | sales | category |
|------|-------|----------|
| 2025-01-01 | 12500 | Electronics |
| 2025-01-02 | 9800 | Clothing |

## หลักการทาง Time Series ที่ใช้

- **Time-based split** ไม่ใช้ random split — จำลองการพยากรณ์อนาคตจริงและป้องกัน data leakage
- **XGBoost feature engineering** — lag (1/7/14/30 วัน), rolling mean/std (7/30 วัน), calendar features
- **Recursive forecasting** — XGBoost ป้อนค่าที่ทำนายกลับเป็น input วันถัดไป
- **Rolling-window backtesting** — เลื่อนช่วงทดสอบหลายรอบตามเวลา
- **Evaluation** — MAPE / RMSE / MAE

## ผลลัพธ์ตัวอย่าง (ข้อมูล Demo)

- **MAPE เฉลี่ยจาก backtesting**: ~8% (ผ่านเกณฑ์ธุรกิจ < 15%)
- **ปัจจัยสำคัญที่สุด**: ยอดขาย 7 วันก่อนหน้า — สะท้อน pattern ยอดขายรายสัปดาห์

## การ Deploy

ดูรายละเอียดใน [DEPLOY.md](DEPLOY.md) — รองรับทั้ง Streamlit Community Cloud (ฟรี) และ Docker

## แนวทางพัฒนาต่อ

- เชื่อมต่อฐานข้อมูล (PostgreSQL) แทนไฟล์ CSV
- Retrain อัตโนมัติ + model monitoring (เฝ้าค่า MAPE)
- เพิ่มโมเดลอื่น เช่น SARIMA, LightGBM

## License

MIT
