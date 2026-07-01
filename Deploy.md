# คู่มือ Deploy

## ทางเลือกที่ 1: Streamlit Community Cloud (แนะนำ — ฟรี ได้ลิงก์จริง)

เหมาะกับใส่ CV/portfolio มากที่สุด คนกดดูได้ทันทีไม่ต้องติดตั้งอะไร

### ขั้นตอน
1. **push โปรเจกต์ขึ้น GitHub** (ถ้ายังไม่ได้ทำ)
   ```
   git add .
   git commit -m "Sales Forecasting Studio"
   git push origin main
   ```
   ตรวจว่าไฟล์เหล่านี้อยู่ใน repo: `app.py`, `requirements.txt`, `src/`, `data/sales_raw.csv`, `.streamlit/config.toml`

2. ไปที่ **https://share.streamlit.io** แล้ว login ด้วย GitHub

3. กด **New app** → เลือก repo `Sales-Forecasting-Dashboard` → branch `main` → main file `app.py`

4. กด **Deploy** รอ 2-5 นาที (ครั้งแรก prophet/xgboost ใช้เวลา build นาน)

5. ได้ลิงก์รูปแบบ `https://<ชื่อ>.streamlit.app` — เอาไปใส่ CV ได้เลย

### ข้อควรระวัง
- ถ้า build ค้างที่ prophet ให้เพิ่มไฟล์ `packages.txt` (มีให้แล้ว) ที่ระบุ system dependency
- ไฟล์ demo `data/sales_raw.csv` ต้อง commit ขึ้นไปด้วย ไม่งั้นโหมด Demo จะพัง

---

## ทางเลือกที่ 2: Docker (สำหรับสาย DevOps / Smart Factory)

เหมาะถ้าจะ deploy บน server/cloud เองหรือโชว์ทักษะ containerization

```bash
# build
docker build -t sales-forecast .

# run
docker run -p 8501:8501 sales-forecast
```

เปิด `http://localhost:8501`

### deploy ขึ้น cloud (เช่น Render, Railway, GCP Cloud Run)
push image ขึ้น registry แล้ว deploy ได้เลย เพราะ containerized สมบูรณ์

---

## จุดขายตอนสัมภาษณ์
- **Backtesting**: อธิบายได้ว่าทำไมวัดผลรอบเดียวไม่พอ ต้องเลื่อนหน้าต่างทดสอบหลายรอบ
- **Feature importance**: lag_7 (ยอดขาย 7 วันก่อน) มีผลมากสุด → สะท้อน pattern รายสัปดาห์
- **Time-based split**: ห้าม random split ในงาน time series เพราะจะรั่วข้อมูลอนาคตเข้า train
- **Prophet vs XGBoost**: statistical vs ML — เลือกตามความแม่นและ interpretability