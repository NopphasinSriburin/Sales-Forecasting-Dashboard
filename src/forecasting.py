"""
src/forecasting.py
Core forecasting logic: Prophet + XGBoost พร้อม time-based split และ feature engineering
ใช้ร่วมกันได้ทั้งโหมด demo และ upload
"""
import numpy as np
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings, logging

warnings.filterwarnings("ignore")
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)


def mape(y, yhat):
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    mask = y != 0
    return np.mean(np.abs((y[mask] - yhat[mask]) / y[mask])) * 100


def make_features(df):
    """สร้าง lag / rolling / calendar features สำหรับ XGBoost"""
    df = df.sort_values("ds").reset_index(drop=True).copy()
    df["dayofweek"] = df.ds.dt.dayofweek
    df["month"] = df.ds.dt.month
    df["day"] = df.ds.dt.day
    df["dayofyear"] = df.ds.dt.dayofyear
    df["is_weekend"] = (df.ds.dt.dayofweek >= 5).astype(int)
    for lag in [1, 7, 14, 30]:
        df[f"lag_{lag}"] = df.y.shift(lag)
    for win in [7, 30]:
        df[f"roll_mean_{win}"] = df.y.shift(1).rolling(win).mean()
        df[f"roll_std_{win}"] = df.y.shift(1).rolling(win).std()
    return df


FEATURE_COLS = [
    "dayofweek", "month", "day", "dayofyear", "is_weekend",
    "lag_1", "lag_7", "lag_14", "lag_30",
    "roll_mean_7", "roll_std_7", "roll_mean_30", "roll_std_30",
]


def train_prophet(d, split_date, future_days, holidays=None):
    """
    d: DataFrame มีคอลัมน์ ds, y
    return: (forecast_df, metrics_dict)  forecast_df มี ds, yhat, yhat_lower, yhat_upper
    """
    train = d[d.ds < split_date]
    test = d[d.ds >= split_date]

    m = Prophet(
        holidays=holidays,
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
    )
    m.fit(train[["ds", "y"]])
    future = m.make_future_dataframe(periods=len(test) + future_days)
    fcst = m.predict(future)

    merged = test.merge(fcst[["ds", "yhat"]], on="ds", how="left").dropna()
    metrics = {
        "model": "Prophet",
        "MAPE": round(mape(merged.y, merged.yhat), 2),
        "RMSE": round(np.sqrt(mean_squared_error(merged.y, merged.yhat)), 0),
        "MAE": round(mean_absolute_error(merged.y, merged.yhat), 0),
    }
    out = fcst[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    return out, metrics


def train_xgboost(d, split_date, future_days):
    """
    XGBoost regression บน lag/rolling/calendar features
    ทำนายอนาคตแบบ recursive (ใช้ค่าที่ทำนายมาสร้าง lag ของวันถัดไป)
    """
    from xgboost import XGBRegressor

    feat = make_features(d).dropna().reset_index(drop=True)
    train = feat[feat.ds < split_date]
    test = feat[feat.ds >= split_date]

    model = XGBRegressor(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42,
    )
    model.fit(train[FEATURE_COLS], train.y)

    # วัดผลบน test
    test_pred = model.predict(test[FEATURE_COLS])
    metrics = {
        "model": "XGBoost",
        "MAPE": round(mape(test.y, test_pred), 2),
        "RMSE": round(np.sqrt(mean_squared_error(test.y, test_pred)), 0),
        "MAE": round(mean_absolute_error(test.y, test_pred), 0),
    }

    # ทำนายอนาคตแบบ recursive
    hist = d.sort_values("ds")[["ds", "y"]].copy()
    last_date = hist.ds.max()
    future_rows = []
    for i in range(1, future_days + 1):
        next_date = last_date + pd.Timedelta(days=i)
        tmp = pd.concat([hist, pd.DataFrame({"ds": [next_date], "y": [np.nan]})], ignore_index=True)
        f = make_features(tmp).iloc[[-1]]
        yhat = float(model.predict(f[FEATURE_COLS])[0])
        future_rows.append({"ds": next_date, "yhat": yhat})
        hist = pd.concat([hist, pd.DataFrame({"ds": [next_date], "y": [yhat]})], ignore_index=True)

    # in-sample fitted (ไว้โชว์เส้นต่อเนื่อง) + future
    fitted = feat[["ds"]].copy()
    fitted["yhat"] = model.predict(feat[FEATURE_COLS])
    fut_df = pd.DataFrame(future_rows)
    # XGBoost ไม่มี CI ตรงๆ -> ใช้ residual std ประมาณช่วง
    resid_std = np.std(test.y.values - test_pred)
    fut_df["yhat_lower"] = fut_df.yhat - 1.96 * resid_std
    fut_df["yhat_upper"] = fut_df.yhat + 1.96 * resid_std
    fitted["yhat_lower"] = fitted.yhat - 1.96 * resid_std
    fitted["yhat_upper"] = fitted.yhat + 1.96 * resid_std

    out = pd.concat([fitted, fut_df], ignore_index=True)

    # feature importance (เรียงมากไปน้อย)
    imp = (
        pd.DataFrame({"feature": FEATURE_COLS, "importance": model.feature_importances_})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    metrics["importance"] = imp
    return out, metrics


def run_forecast(d, model_choice, split_ratio=0.85, future_days=90, holidays=None):
    """
    d: DataFrame ds, y (หมวดเดียว)
    model_choice: "Prophet" | "XGBoost" | "Both"
    return: dict {model_name: {"forecast": df, "metrics": dict}}, last_actual_date, split_date
    """
    d = d.sort_values("ds").reset_index(drop=True)
    if len(d) < 30:
        raise ValueError(
            f"ข้อมูลน้อยเกินไป ({len(d)} วัน) — ต้องมีอย่างน้อย 30 วันเพื่อพยากรณ์"
        )
    split_idx = int(len(d) * split_ratio)
    split_idx = min(max(split_idx, 1), len(d) - 1)   # กันเกินขอบเขต
    split_date = d.ds.iloc[split_idx]
    last_actual = d.ds.max()

    results = {}
    if model_choice in ("Prophet", "Both"):
        fc, mt = train_prophet(d, split_date, future_days, holidays)
        results["Prophet"] = {"forecast": fc, "metrics": mt}
    if model_choice in ("XGBoost", "Both"):
        fc, mt = train_xgboost(d, split_date, future_days)
        results["XGBoost"] = {"forecast": fc, "metrics": mt}

    return results, last_actual, split_date


def backtest(d, model_choice="Prophet", n_folds=4, horizon=30, holidays=None):
    """
    Rolling-window backtesting: เลื่อนหน้าต่างทดสอบหลายรอบ
    แต่ละ fold: เทรนด้วยข้อมูลถึงจุดหนึ่ง แล้วทดสอบ horizon วันถัดไป
    return: DataFrame ผล MAPE/RMSE/MAE ของแต่ละ fold + ค่าเฉลี่ย
    """
    d = d.sort_values("ds").reset_index(drop=True)
    n = len(d)
    # จุดเริ่มทดสอบของแต่ละ fold (เว้นระยะเท่าๆ กันด้านท้าย)
    min_train = int(n * 0.5)
    test_starts = np.linspace(min_train, n - horizon, n_folds, dtype=int)

    rows = []
    for i, start in enumerate(test_starts, 1):
        train = d.iloc[:start]
        test = d.iloc[start:start + horizon]
        if len(test) < 5 or len(train) < 60:
            continue
        split_date = d.ds.iloc[start]

        if model_choice == "XGBoost":
            _, mt = train_xgboost(d.iloc[:start + horizon], split_date, future_days=1)
        else:
            _, mt = train_prophet(
                pd.concat([train, test]), split_date, future_days=1, holidays=holidays
            )
        rows.append({
            "fold": i,
            "train_end": train.ds.max().date(),
            "MAPE": mt["MAPE"], "RMSE": mt["RMSE"], "MAE": mt["MAE"],
        })

    res = pd.DataFrame(rows)
    if len(res):
        avg = {
            "fold": "เฉลี่ย", "train_end": "",
            "MAPE": round(res.MAPE.mean(), 2),
            "RMSE": round(res.RMSE.mean(), 0),
            "MAE": round(res.MAE.mean(), 0),
        }
        res = pd.concat([res, pd.DataFrame([avg])], ignore_index=True)
    return res