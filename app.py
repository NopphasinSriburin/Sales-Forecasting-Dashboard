"""
Sales Forecasting Studio — Streamlit
รัน: streamlit run app.py

ฟีเจอร์:
- 2 โหมด: Demo (ข้อมูล synthetic) / Upload (อัปโหลด CSV เอง)
- Column mapping ยืดหยุ่น: ผู้ใช้เลือกได้ว่าคอลัมน์ไหนคือ date/sales/category
- เลือกโมเดล: Prophet / XGBoost / เทียบทั้งคู่
- Lucide icon (ไม่มี emoji)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from forecasting import run_forecast, backtest
from ui import icon, CSS

st.set_page_config(page_title="Sales Forecasting Studio", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


# ---------- helpers ----------
def head(text, ic, size=17):
    st.markdown(
        f'<div class="sec-head">{icon(ic, 20, "#4F46E5")}<span>{text}</span></div>',
        unsafe_allow_html=True,
    )


def kpi(col, label, value, ic, sub="", sub_cls=""):
    col.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{icon(ic, 15, "#6B7280")}{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub {sub_cls}">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


@st.cache_data
def load_demo():
    df = pd.read_csv("data/sales_raw.csv", parse_dates=["date"])
    return df


def build_holidays(df_raw, date_col):
    """สร้าง holidays df สำหรับ Prophet ถ้ามีคอลัมน์ is_holiday / is_promo"""
    frames = []
    if "is_holiday" in df_raw.columns:
        h = df_raw[df_raw.is_holiday == 1][[date_col]].drop_duplicates()
        h.columns = ["ds"]; h["holiday"] = "holiday"; frames.append(h)
    if "is_promo" in df_raw.columns:
        p = df_raw[df_raw.is_promo == 1][[date_col]].drop_duplicates()
        p.columns = ["ds"]; p["holiday"] = "promo"; frames.append(p)
    return pd.concat(frames, ignore_index=True) if frames else None


@st.cache_data(show_spinner=False)
def cached_forecast(d_csv, model_choice, future_days, holidays_csv):
    """
    Cache การเทรน — ถ้า input เดิม (ข้อมูล+โมเดล+วัน+holiday) ดึงจาก cache แทนเทรนใหม่
    รับ input เป็น CSV string เพื่อให้ hashable
    """
    from io import StringIO
    d = pd.read_csv(StringIO(d_csv), parse_dates=["ds"])
    holidays = None
    if holidays_csv:
        holidays = pd.read_csv(StringIO(holidays_csv), parse_dates=["ds"])
    return run_forecast(d, model_choice, future_days=future_days, holidays=holidays)


# ---------- Header ----------
st.markdown(
    f'<div class="app-title">{icon("trending-up", 26, "#4F46E5")}Sales Forecasting Studio</div>'
    f'<div class="app-sub">พยากรณ์ยอดขายด้วย Prophet และ XGBoost พร้อมเปรียบเทียบความแม่นยำ</div>',
    unsafe_allow_html=True,
)
st.divider()


# ---------- Sidebar: control panel ----------
with st.sidebar:
    st.markdown(
        f'<div class="sec-head">{icon("settings", 20, "#4F46E5")}ตั้งค่า</div>',
        unsafe_allow_html=True,
    )

    mode = st.radio("แหล่งข้อมูล", ["ข้อมูลตัวอย่าง (Demo)", "อัปโหลด CSV"], index=0)

    raw = None
    date_col = cat_col = sales_col = None

    if mode == "ข้อมูลตัวอย่าง (Demo)":
        raw = load_demo()
        date_col, cat_col, sales_col = "date", "category", "sales"
        st.caption("ข้อมูลยอดขายสังเคราะห์ 3 ปี × 3 หมวด")
    else:
        up = st.file_uploader("เลือกไฟล์ CSV", type=["csv"])
        if up is not None:
            raw = pd.read_csv(up)
            cols = raw.columns.tolist()

            # เดาคอลัมน์อัตโนมัติจากชื่อ (ลดโอกาสเลือกผิด)
            def guess(cands, default_idx):
                for i, c in enumerate(cols):
                    if any(k in c.lower() for k in cands):
                        return i
                return default_idx
            date_guess = guess(["date", "วันที่", "time", "day"], 0)
            sales_guess = guess(["sales", "revenue", "amount", "ยอด", "sale"], min(1, len(cols) - 1))
            cat_guess = guess(["category", "หมวด", "type", "product", "segment"], -1)

            st.markdown("**จับคู่คอลัมน์**")
            st.caption("ระบบเดาให้อัตโนมัติ — ตรวจสอบว่าถูกต้องก่อนดำเนินการ")
            date_col = st.selectbox("คอลัมน์วันที่", cols, index=date_guess)
            sales_col = st.selectbox("คอลัมน์ยอดขาย", cols, index=sales_guess)
            cat_opts = ["(ไม่มี — รวมทั้งหมด)"] + cols
            cat_default = 0 if cat_guess == -1 else cat_guess + 1
            cat_pick = st.selectbox("คอลัมน์หมวดสินค้า (ถ้ามี)", cat_opts, index=cat_default)
            cat_col = None if cat_pick == cat_opts[0] else cat_pick
        else:
            st.info("อัปโหลดไฟล์ CSV เพื่อเริ่มพยากรณ์")

    st.divider()
    model_choice_label = st.radio(
        "โมเดล",
        ["Prophet", "XGBoost", "เทียบทั้งคู่"],
        index=2,
    )
    model_choice = {"Prophet": "Prophet", "XGBoost": "XGBoost",
                    "เทียบทั้งคู่": "Both"}[model_choice_label]

    future_days = st.slider("พยากรณ์ล่วงหน้า (วัน)", 30, 180, 90, step=30)


# ---------- ไม่มีข้อมูล -> หยุด ----------
if raw is None:
    st.info("เลือกข้อมูลตัวอย่าง หรืออัปโหลด CSV จากแถบด้านซ้ายเพื่อเริ่มต้น")
    st.stop()

# ---------- ตรวจสอบและแจ้งเตือน (validation) ----------
def validate_and_prepare(raw, date_col, sales_col, cat_col):
    """
    ตรวจสอบการเลือกคอลัมน์ก่อนเทรน คืน (raw ที่เตรียมแล้ว, ข้อความ error หรือ None)
    """
    # 1. เลือกวันที่กับยอดขายเป็นคอลัมน์เดียวกัน
    if date_col == sales_col:
        return None, "คอลัมน์วันที่และยอดขายเป็นคอลัมน์เดียวกัน — กรุณาเลือกให้ต่างกัน"

    # 2. คอลัมน์วันที่แปลงเป็นวันที่ได้ไหม
    parsed_date = pd.to_datetime(raw[date_col], errors="coerce")
    date_ok_ratio = parsed_date.notna().mean()
    if date_ok_ratio < 0.5:
        return None, (
            f"คอลัมน์ '{date_col}' ที่เลือกเป็นคอลัมน์วันที่ แปลงเป็นวันที่ได้เพียง "
            f"{date_ok_ratio*100:.0f}% — น่าจะเลือกคอลัมน์ผิด "
            f"กรุณาเลือกคอลัมน์ที่เป็นวันที่จริง (เช่น 2025-01-01)"
        )

    # 3. คอลัมน์ยอดขายเป็นตัวเลขไหม
    parsed_sales = pd.to_numeric(raw[sales_col], errors="coerce")
    sales_ok_ratio = parsed_sales.notna().mean()
    if sales_ok_ratio < 0.5:
        return None, (
            f"คอลัมน์ '{sales_col}' ที่เลือกเป็นคอลัมน์ยอดขาย เป็นตัวเลขเพียง "
            f"{sales_ok_ratio*100:.0f}% — น่าจะเลือกคอลัมน์ผิด "
            f"กรุณาเลือกคอลัมน์ที่เป็นตัวเลขยอดขาย (ไม่ใช่ข้อความ เช่น ชื่อหมวดสินค้า)"
        )

    # เตรียมข้อมูล
    raw = raw.copy()
    raw[date_col] = parsed_date
    raw[sales_col] = parsed_sales
    raw = raw.dropna(subset=[date_col, sales_col])

    if len(raw) == 0:
        return None, "หลังจากทำความสะอาดข้อมูลแล้วไม่เหลือข้อมูลเลย — กรุณาตรวจสอบไฟล์"

    return raw, None


raw, err = validate_and_prepare(raw, date_col, sales_col, cat_col)
if err:
    st.warning(err)
    st.info(
        "**วิธีจับคู่คอลัมน์ที่ถูกต้อง**\n"
        "- คอลัมน์วันที่ → คอลัมน์ที่เป็นวันที่ เช่น `date`, `Order Date`\n"
        "- คอลัมน์ยอดขาย → คอลัมน์ที่เป็นตัวเลข เช่น `sales`, `revenue`, `Sales`\n"
        "- คอลัมน์หมวดสินค้า → เลือกได้ถ้ามี (เป็นข้อความ เช่น `category`)"
    )
    st.stop()

# เลือกหมวด (ถ้ามี)
if cat_col:
    categories = sorted(raw[cat_col].dropna().unique().tolist())
    if len(categories) == 0:
        st.warning(f"คอลัมน์หมวด '{cat_col}' ไม่มีข้อมูล — จะรวมทั้งหมดแทน")
        sel_cat = "ทั้งหมด"
        sub = raw
    else:
        sel_cat = st.selectbox("เลือกหมวดสินค้า", categories)
        sub = raw[raw[cat_col] == sel_cat]
else:
    sel_cat = "ทั้งหมด"
    sub = raw

# aggregate เป็นรายวัน (กัน transaction ซ้ำวัน)
d = (sub.groupby(date_col)[sales_col].sum().reset_index())
d.columns = ["ds", "y"]
d = d.sort_values("ds").reset_index(drop=True)

# แจ้งเตือนระดับข้อมูล
if len(d) < 30:
    st.warning(
        f"ข้อมูลของหมวด '{sel_cat}' มีเพียง {len(d)} วัน — น้อยเกินไปสำหรับพยากรณ์ "
        f"(ต้องมีอย่างน้อย 30 วัน) ลองเลือกหมวดอื่น หรือใช้ข้อมูลที่ครอบคลุมช่วงเวลานานขึ้น"
    )
    st.stop()
elif len(d) < 60:
    st.warning(f"ข้อมูลมี {len(d)} วัน — พยากรณ์ได้ แต่แนะนำอย่างน้อย 60 วันเพื่อผลที่น่าเชื่อถือขึ้น")
else:
    st.success(f"ข้อมูลพร้อม: {len(d)} วัน ({d.ds.min().date()} ถึง {d.ds.max().date()})")

holidays = build_holidays(sub, date_col)

# ---------- รันโมเดล ----------
MAX_HORIZON = 180  # เทรนที่ค่าคงที่เสมอ -> เลื่อน slider ไม่ต้องเทรนใหม่ (cache hit)
try:
    with st.spinner("กำลังเทรนโมเดลและพยากรณ์..."):
        d_csv = d.to_csv(index=False)
        holidays_csv = holidays.to_csv(index=False) if holidays is not None else None
        results, last_actual, split_date = cached_forecast(
            d_csv, model_choice, MAX_HORIZON, holidays_csv
        )
except ValueError as e:
    st.warning(f"ไม่สามารถพยากรณ์ได้: {e}")
    st.info(
        "แนะนำให้ตรวจสอบว่า:\n"
        "- เลือกคอลัมน์วันที่และยอดขายถูกต้อง (คอลัมน์วันที่ต้องเป็นรูปแบบวันที่ เช่น 2025-01-01)\n"
        "- ข้อมูลมีอย่างน้อย 30 วัน\n"
        "- ถ้าเลือกหมวดสินค้า ลองเลือกหมวดที่มีข้อมูลมากขึ้น"
    )
    st.stop()
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดระหว่างเทรนโมเดล: {e}")
    st.stop()

# เลือกโมเดลที่ดีที่สุด (MAPE ต่ำสุด) เป็นตัวหลักที่โชว์
def _mape_key(k):
    v = results[k]["metrics"]["MAPE"]
    return float("inf") if pd.isna(v) else v

best_name = min(results, key=_mape_key)
best = results[best_name]
fc = best["forecast"].sort_values("ds")
future = fc[fc.ds > last_actual].head(future_days)

# ---------- KPI ----------
head(f"ภาพรวม — {sel_cat}", "target")
m = best["metrics"]
next_30 = future.head(30).yhat.sum()
lo_30 = future.head(30).yhat_lower.sum()
hi_30 = future.head(30).yhat_upper.sum()
mape_val = m["MAPE"]
has_mape = not pd.isna(mape_val)
mape_ok = has_mape and mape_val < 15
mape_str = f"{mape_val:.1f}%" if has_mape else "N/A"

c1, c2, c3, c4 = st.columns(4)
kpi(c1, "ยอดคาดการณ์ 30 วัน", f"฿{next_30:,.0f}", "trending-up",
    f"ช่วง ฿{lo_30:,.0f} – ฿{hi_30:,.0f}")
kpi(c2, "โมเดลที่แม่นสุด", best_name, "activity",
    f"MAPE {mape_str}")
kpi(c3, "ความแม่นยำ", mape_str, "check-circle" if mape_ok else "alert-triangle",
    "ผ่านเกณฑ์ธุรกิจ (<15%)" if mape_ok else ("ข้อมูลทดสอบไม่พอ" if not has_mape else "เกินเกณฑ์ 15%"),
    "good" if mape_ok else "warn")
rmse_str = f"฿{m['RMSE']:,.0f}" if not pd.isna(m["RMSE"]) else "N/A"
mae_str = f"MAE ฿{m['MAE']:,.0f}" if not pd.isna(m["MAE"]) else ""
kpi(c4, "RMSE", rmse_str, "bar-chart", mae_str)

st.write("")

# ---------- กราฟหลัก ----------
head("ยอดขายจริงเทียบกับพยากรณ์", "trending-up")

palette = {"Prophet": "#4F46E5", "XGBoost": "#059669"}
history = d[d.ds <= last_actual].tail(180)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=history.ds, y=history.y, mode="lines", name="ยอดขายจริง",
    line=dict(color="#111827", width=2),
))
fig.add_trace(go.Scatter(
    x=list(future.ds) + list(future.ds[::-1]),
    y=list(future.yhat_upper) + list(future.yhat_lower[::-1]),
    fill="toself", fillcolor="rgba(79,70,229,0.12)",
    line=dict(color="rgba(0,0,0,0)"), name="ช่วงความมั่นใจ", hoverinfo="skip",
))
for name, r in results.items():
    f_future = r["forecast"].sort_values("ds")
    f_future = f_future[f_future.ds > last_actual].head(future_days)
    fig.add_trace(go.Scatter(
        x=f_future.ds, y=f_future.yhat, mode="lines",
        name=f"พยากรณ์ ({name})",
        line=dict(color=palette.get(name, "#4F46E5"), width=2,
                  dash="dash" if name == best_name else "dot"),
    ))
fig.update_layout(
    height=440, hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=30, b=10),
    yaxis_title="ยอดขาย (บาท)", plot_bgcolor="white", paper_bgcolor="white",
)
fig.update_xaxes(showgrid=True, gridcolor="#F3F4F6")
fig.update_yaxes(showgrid=True, gridcolor="#F3F4F6")
st.plotly_chart(fig, use_container_width=True)

# ---------- เปรียบเทียบโมเดล ----------
if len(results) > 1:
    head("เปรียบเทียบโมเดล", "layers")
    comp = pd.DataFrame([
        {k: v for k, v in r["metrics"].items() if k != "importance"}
        for r in results.values()
    ])
    comp = comp.rename(columns={"model": "โมเดล", "MAPE": "MAPE (%)"})
    comp["ผู้ชนะ"] = comp["โมเดล"].apply(lambda x: "ดีที่สุด" if x == best_name else "")
    st.dataframe(comp, use_container_width=True, hide_index=True)
    st.caption("MAPE ยิ่งต่ำยิ่งดี — วัดบนช่วงทดสอบ (ข้อมูลท้ายที่โมเดลไม่เคยเห็น)")

# ---------- Feature importance (XGBoost) ----------
if "XGBoost" in results and "importance" in results["XGBoost"]["metrics"]:
    head("ปัจจัยที่มีผลต่อยอดขาย (XGBoost)", "bar-chart")
    imp = results["XGBoost"]["metrics"]["importance"].head(8).iloc[::-1]
    label_map = {
        "lag_1": "ยอดขายเมื่อวาน", "lag_7": "ยอดขาย 7 วันก่อน",
        "lag_14": "ยอดขาย 14 วันก่อน", "lag_30": "ยอดขาย 30 วันก่อน",
        "roll_mean_7": "ค่าเฉลี่ย 7 วัน", "roll_mean_30": "ค่าเฉลี่ย 30 วัน",
        "roll_std_7": "ความผันผวน 7 วัน", "roll_std_30": "ความผันผวน 30 วัน",
        "dayofweek": "วันในสัปดาห์", "month": "เดือน", "day": "วันที่",
        "dayofyear": "วันในปี", "is_weekend": "วันหยุดสุดสัปดาห์",
    }
    imp["label"] = imp.feature.map(lambda x: label_map.get(x, x))
    fig_imp = go.Figure(go.Bar(
        x=imp.importance, y=imp.label, orientation="h",
        marker_color="#4F46E5",
    ))
    fig_imp.update_layout(
        height=320, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="ความสำคัญ", plot_bgcolor="white", paper_bgcolor="white",
    )
    fig_imp.update_xaxes(showgrid=True, gridcolor="#F3F4F6")
    st.plotly_chart(fig_imp, use_container_width=True)
    st.caption("ยิ่งแท่งยาว ปัจจัยนั้นยิ่งมีผลต่อการพยากรณ์มาก")

# ---------- Backtesting ----------
head("ทดสอบความน่าเชื่อถือ (Backtesting)", "activity")
with st.expander("รันการทดสอบแบบเลื่อนหน้าต่างหลายรอบ (rolling-window)", expanded=False):
    st.caption(
        "แทนที่จะวัดผลรอบเดียว จะเลื่อนช่วงทดสอบหลายรอบตามเวลา "
        "เพื่อดูว่าโมเดลแม่นยำสม่ำเสมอหรือไม่ — สะท้อนการใช้งานจริงมากกว่า"
    )
    bt_model = st.selectbox("โมเดลที่จะทดสอบ", list(results.keys()))
    n_folds = st.slider("จำนวนรอบ (folds)", 3, 6, 4)
    if st.button("เริ่มทดสอบ"):
        with st.spinner("กำลังทดสอบหลายรอบ..."):
            bt = backtest(d, bt_model, n_folds=n_folds, horizon=30, holidays=holidays)
        if len(bt):
            st.dataframe(bt, use_container_width=True, hide_index=True)
            avg_mape = bt[bt.fold == "เฉลี่ย"].MAPE.values[0]
            if avg_mape < 15:
                st.success(f"MAPE เฉลี่ยทุกรอบ {avg_mape:.1f}% — ผ่านเกณฑ์ธุรกิจ (<15%)")
            else:
                st.warning(f"MAPE เฉลี่ยทุกรอบ {avg_mape:.1f}% — เกินเกณฑ์ 15%")
        else:
            st.info("ข้อมูลไม่พอสำหรับ backtesting — ต้องมีอย่างน้อย ~120 วัน")

# ---------- สรุปรายเดือน ----------
head("สรุปยอดพยากรณ์รายเดือน", "calendar")
fm = future.copy()
fm["month"] = fm.ds.dt.to_period("M").astype(str)
summary = (
    fm.groupby("month")[["yhat", "yhat_lower", "yhat_upper"]]
    .sum().round(0).reset_index()
)
summary.columns = ["เดือน", "ยอดพยากรณ์รวม", "ช่วงต่ำสุด", "ช่วงสูงสุด"]
disp = summary.copy()
for c in ["ยอดพยากรณ์รวม", "ช่วงต่ำสุด", "ช่วงสูงสุด"]:
    disp[c] = disp[c].map(lambda x: f"฿{x:,.0f}")
st.dataframe(disp, use_container_width=True, hide_index=True)

# ---------- ดาวน์โหลดผล ----------
out = future[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
out.columns = ["date", "forecast", "lower", "upper"]
st.download_button(
    "ดาวน์โหลดผลพยากรณ์ (CSV)",
    out.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"forecast_{sel_cat}.csv",
    mime="text/csv",
)