#!/usr/bin/env python3
# 実行方法: ターミナルで次を実行してください →  streamlit run app.py
# 依存関係: streamlit, pandas, plotly

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ===== 基本設定 ============================================================
# データ保存場所
DATA_DIR = Path("data")
WEIGHTS_CSV = DATA_DIR / "weights.csv"
SETTINGS_JSON = DATA_DIR / "settings.json"
EXERCISES_CSV = DATA_DIR / "exercises.csv"


# ===== ユーティリティ関数 ==================================================
def ensure_storage() -> None:
    """データ保存先の存在を保証。初回は空ファイルを作成する。

    - weights.csv: ヘッダのみ(date,weight)
    - settings.json: {"goal_weight": null}
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not WEIGHTS_CSV.exists():
        # ヘッダのみの空CSVを作成
        empty = pd.DataFrame(columns=["date", "weight"])
        empty.to_csv(WEIGHTS_CSV, index=False)

    if not SETTINGS_JSON.exists():
        SETTINGS_JSON.write_text(json.dumps({"goal_weight": None}, ensure_ascii=False, indent=2), encoding="utf-8")
    # 運動CSV（空。ヘッダ: date,activity,duration_min）
    if not EXERCISES_CSV.exists():
        empty_ex = pd.DataFrame(columns=["date", "activity", "duration_min"])
        empty_ex.to_csv(EXERCISES_CSV, index=False)


def load_weights() -> pd.DataFrame:
    """体重データを読み込み、日付で昇順に整形して返す。"""
    try:
        df = pd.read_csv(WEIGHTS_CSV, dtype={"date": str}, encoding="utf-8")
    except Exception:
        df = pd.DataFrame(columns=["date", "weight"])  # 壊れている場合のフォールバック

    if "date" not in df.columns or "weight" not in df.columns:
        df = pd.DataFrame(columns=["date", "weight"])  # 列が足りない場合のフォールバック

    # 型整形
    if not df.empty:
        # 日付をdatetimeに
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        # 重量をfloatに
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce").round(1)  # 小数1位に丸め
        # 壊れ行を除去
        df = df.dropna(subset=["date", "weight"]).copy()
        # 昇順整列 & 重複があれば最終出現を優先
        df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    else:
        df = pd.DataFrame(columns=["date", "weight"])  # 空統一

    return df.reset_index(drop=True)


def save_weights(df: pd.DataFrame) -> None:
    """体重データを保存する。"""
    out = df.copy()
    if not out.empty:
        # 保存時はISO形式の文字列に
        out["date"] = pd.to_datetime(out["date"]).dt.date.astype(str)
        out["weight"] = pd.to_numeric(out["weight"], errors="coerce").round(1)  # 小数1位に丸め
        out = out.dropna(subset=["date", "weight"])  # 念のため
        out = out.sort_values("date")
    out.to_csv(WEIGHTS_CSV, index=False, encoding="utf-8")


def load_settings() -> dict:
    """設定（目標体重など）を読み込む。"""
    try:
        data = json.loads(SETTINGS_JSON.read_text(encoding="utf-8"))
    except Exception:
        data = {"goal_weight": None}
    gw = data.get("goal_weight")
    if gw is not None:
        try:
            gw = round(float(gw), 1)  # 小数1位に正規化
        except Exception:
            gw = None
    return {"goal_weight": gw}


def save_settings(settings: dict) -> None:
    """設定を保存する。"""
    SETTINGS_JSON.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def load_exercises() -> pd.DataFrame:
    """運動データを読み込み、整形して返す。キーは (date, activity)。"""
    try:
        df = pd.read_csv(EXERCISES_CSV, dtype={"date": str, "activity": str}, encoding="utf-8")
    except Exception:
        df = pd.DataFrame(columns=["date", "activity", "duration_min"])  # フォールバック

    if set(["date", "activity", "duration_min"]) - set(df.columns):
        df = pd.DataFrame(columns=["date", "activity", "duration_min"])  # 列不足時

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df["activity"] = df["activity"].astype(str)
        df["duration_min"] = pd.to_numeric(df["duration_min"], errors="coerce").round(1)
        df = df.dropna(subset=["date", "activity", "duration_min"]).copy()
        # 範囲: 0〜1440分（24h）
        df = df[(0 <= df["duration_min"]) & (df["duration_min"] <= 1440)]
        df = df.sort_values(["date", "activity"]).drop_duplicates(subset=["date", "activity"], keep="last")
    else:
        df = pd.DataFrame(columns=["date", "activity", "duration_min"])  # 空統一

    return df.reset_index(drop=True)


def save_exercises(df: pd.DataFrame) -> None:
    out = df.copy()
    if not out.empty:
        out["date"] = pd.to_datetime(out["date"]).dt.date.astype(str)
        out["activity"] = out["activity"].astype(str)
        out["duration_min"] = pd.to_numeric(out["duration_min"], errors="coerce").round(1)
        out = out.dropna(subset=["date", "activity", "duration_min"]).sort_values(["date", "activity"]) 
    out.to_csv(EXERCISES_CSV, index=False, encoding="utf-8")


def merge_uploaded_csv(df: pd.DataFrame, csv_bytes: bytes) -> pd.DataFrame:
    """アップロードCSVをマージ（同日重複はアップロード側を優先）。"""
    text = csv_bytes.decode("utf-8")
    up = pd.read_csv(StringIO(text), dtype={"date": str})

    # 必須列チェック
    required = {"date", "weight"}
    if not required.issubset(set(up.columns)):
        raise ValueError("CSVに必要な列がありません（date, weight）。")

    # 整形
    up["date"] = pd.to_datetime(up["date"], errors="coerce").dt.date
    up["weight"] = pd.to_numeric(up["weight"], errors="coerce").round(1)  # 小数1位に丸め
    up = up.dropna(subset=["date", "weight"])  # 壊れ行を除去

    # バリデーション: 範囲外の体重を除外
    up = up[(20 <= up["weight"]) & (up["weight"] <= 300)]

    # 既存データを日付インデックス化
    base = df.copy()
    if not base.empty:
        base = base.set_index("date")
    else:
        base = pd.DataFrame(columns=["weight"]).set_index(pd.Index([], name="date"))

    # アップロード側を優先で更新
    if not up.empty:
        up_idx = up.set_index("date")["weight"]
        base.loc[up_idx.index, "weight"] = up_idx  # 既存に上書き
        # 既存にない日付を追加
        new_dates = up_idx.index.difference(base.index)
        if len(new_dates) > 0:
            base = pd.concat([base, up_idx.loc[new_dates].to_frame("weight")])

    # 戻す
    merged = base.reset_index().sort_values("date").reset_index(drop=True)
    return merged


def compute_stats(df: pd.DataFrame, days: int) -> dict:
    """直近days日の統計（平均, 増減, 最小, 最大）を返す。"""
    if df.empty:
        return {"avg": None, "delta": None, "min": None, "max": None}

    today = date.today()
    start = today - timedelta(days=days - 1)
    mask = pd.to_datetime(df["date"]).dt.date >= start
    d = df.loc[mask].copy()
    if d.empty:
        return {"avg": None, "delta": None, "min": None, "max": None}

    d = d.sort_values("date")
    avg = round(float(d["weight"].mean()), 1)
    first = float(d["weight"].iloc[0])
    last = float(d["weight"].iloc[-1])
    delta = round(last - first, 1)
    wmin = round(float(d["weight"].min()), 1)
    wmax = round(float(d["weight"].max()), 1)
    return {"avg": avg, "delta": delta, "min": wmin, "max": wmax}


def filter_range(df: pd.DataFrame, range_label: str) -> pd.DataFrame:
    """表示範囲でフィルタリングする。range_labelは '30日', '90日', '180日', '全期間' 想定。"""
    if df.empty:
        return df
    if range_label == "全期間":
        return df

    today = date.today()
    days_map = {"30日": 30, "90日": 90, "180日": 180}
    days = days_map.get(range_label)
    if not days:
        return df
    start = today - timedelta(days=days - 1)
    mask = pd.to_datetime(df["date"]).dt.date >= start
    return df.loc[mask].copy()


# ===== Streamlit UI ========================================================
st.set_page_config(page_title="日々の体重トラッカー", layout="centered")

# ストレージ初期化
ensure_storage()

# データ読み込み
df = load_weights()
settings = load_settings()


# ----- サイドバー（設定） --------------------------------------------------
st.sidebar.header("設定")
goal = st.sidebar.number_input(
    "目標体重 (kg)",
    min_value=20.0,
    max_value=300.0,
    value=(float(settings["goal_weight"]) if settings.get("goal_weight") is not None else 60.0),
    step=0.1,
    format="%.1f",
    help="グラフに目標体重の水平線を表示します",
)
save_goal = st.sidebar.button("目標を保存")
if save_goal:
    save_settings({"goal_weight": round(float(goal), 1)})
    st.sidebar.success("目標体重を保存しました。")


# ----- タイトル ------------------------------------------------------------
st.title("日々の体重可視化アプリ")
st.caption("CSVに保存し、折れ線と移動平均で推移を可視化します。")


# ----- 入力フォーム（追加/更新/削除） ------------------------------------
with st.form("edit_form", clear_on_submit=False):
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        d_input = st.date_input("日付", value=date.today())
    with col2:
        # 入力表示も小数1位で固定
        w_input = st.number_input("体重 (kg)", min_value=20.0, max_value=300.0, step=0.1, format="%.1f")
    with col3:
        st.write("")
        st.write("")
        submitted_add = st.form_submit_button("追加/更新")
        submitted_del = st.form_submit_button("削除")

if submitted_add:
    # 追加または更新（同日があれば上書き）
    new_row = pd.DataFrame({"date": [d_input], "weight": [round(float(w_input), 1)]})  # 小数1位に丸めて保存
    if df.empty:
        df = new_row
    else:
        df = df.copy()
        # 同日の既存を削除してから追加
        df = df[df["date"] != d_input]
        df = pd.concat([df, new_row], ignore_index=True)
    df = df.sort_values("date").reset_index(drop=True)
    save_weights(df)
    st.success(f"{d_input} のデータを保存しました。")

if submitted_del:
    if not df.empty:
        before = len(df)
        df = df[df["date"] != d_input].reset_index(drop=True)
        if len(df) != before:
            save_weights(df)
            st.success(f"{d_input} のデータを削除しました。")
        else:
            st.info("削除対象の日付のデータがありませんでした。")
    else:
        st.info("データがありません。")


# ----- CSVアップロードで追記マージ ----------------------------------------
st.subheader("CSVアップロードで追記マージ")
uploaded = st.file_uploader("weights.csv形式のファイルを選択 (date,weight)", type=["csv"]) 
col_u1, col_u2 = st.columns([1, 2])
with col_u1:
    merge_btn = st.button("アップロードをマージ")
if merge_btn and uploaded is not None:
    try:
        merged = merge_uploaded_csv(load_weights(), uploaded.read())
        save_weights(merged)
        st.success("アップロード内容をマージしました（同日重複はアップロード側を優先）。")
        df = merged
    except Exception as e:
        st.error(f"マージに失敗しました: {e}")


# ----- ダウンロード --------------------------------------------------------
st.subheader("データのダウンロード")
csv_buf = StringIO()
export_df = load_weights().copy()
if not export_df.empty:
    export_df["date"] = pd.to_datetime(export_df["date"]).dt.date.astype(str)
    export_df["weight"] = pd.to_numeric(export_df["weight"], errors="coerce").round(1)
export_df.to_csv(csv_buf, index=False, encoding="utf-8")
st.download_button(
    "現在のデータをCSVでダウンロード",
    data=csv_buf.getvalue().encode("utf-8"),
    file_name="weights_export.csv",
    mime="text/csv",
)


# ----- 表示範囲切替 ------------------------------------------------------
st.subheader("表示範囲")
range_label = st.radio("表示期間を選択", options=["30日", "90日", "180日", "全期間"], horizontal=True, index=0)
show_df = filter_range(load_weights(), range_label)


# ----- グラフ描画 ---------------------------------------------------------
st.subheader("体重の推移")
if show_df.empty:
    st.info("表示するデータがありません。まずはデータを追加してください。")
else:
    gdf = show_df.sort_values("date").copy()
    # 7日移動平均も表示上は小数1位
    gdf["ma7"] = gdf["weight"].rolling(window=7, min_periods=1).mean().round(1)

    fig = go.Figure()
    # 体重の折れ線
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(gdf["date"]),
        y=gdf["weight"],
        mode="lines+markers",
        name="体重",
        line=dict(color="#1f77b4"),
        marker=dict(size=6),
        hovertemplate="%{x|%Y-%m-%d}<br>体重: %{y:.1f} kg<extra></extra>",
    ))

    # 7日移動平均
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(gdf["date"]),
        y=gdf["ma7"],
        mode="lines",
        name="7日移動平均",
        line=dict(color="#ff7f0e", width=3, dash="solid"),
        hovertemplate="%{x|%Y-%m-%d}<br>7日平均: %{y:.1f} kg<extra></extra>",
    ))

    # 目標体重（水平線）
    g = load_settings().get("goal_weight")
    if g is not None:
        # データの期間と同じxで水平線を引く
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(gdf["date"]),
            y=[g] * len(gdf),
            mode="lines",
            name="目標体重",
            line=dict(color="#2ca02c", dash="dash", width=2),
            hovertemplate="%{x|%Y-%m-%d}<br>目標: %{y:.1f} kg<extra></extra>",
        ))

    fig.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=20, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="日付",
        yaxis_title="体重 (kg)",
    )
    fig.update_yaxes(tickformat=".1f")  # 目盛りも小数1位
    st.plotly_chart(fig, use_container_width=True)


# ----- 統計 ---------------------------------------------------------------
st.subheader("統計")
col_s1, col_s2 = st.columns(2)

def fmt(v: float | None) -> str:
    return "-" if v is None else f"{v:.1f}"

stats7 = compute_stats(load_weights(), 7)
stats30 = compute_stats(load_weights(), 30)

with col_s1:
    st.markdown("**直近7日の統計**")
    st.write(
        f"平均: {fmt(stats7['avg'])} kg / 増減: {fmt(stats7['delta'])} kg / 最小: {fmt(stats7['min'])} kg / 最大: {fmt(stats7['max'])} kg"
    )
with col_s2:
    st.markdown("**直近30日の統計**")
    st.write(
        f"平均: {fmt(stats30['avg'])} kg / 増減: {fmt(stats30['delta'])} kg / 最小: {fmt(stats30['min'])} kg / 最大: {fmt(stats30['max'])} kg"
    )


# ----- 表 ---------------------------------------------------------------
st.subheader("データ一覧")
disp = load_weights().copy()
if not disp.empty:
    disp = disp.sort_values("date", ascending=False).reset_index(drop=True)
    # 表示も小数1位
    try:
        st.dataframe(disp.style.format({"weight": "{:.1f}"}), use_container_width=True)
    except Exception:
        # Stylerがうまく使えない環境でも最低限の表示
        st.dataframe(disp, use_container_width=True)
else:
    st.dataframe(disp, use_container_width=True)
