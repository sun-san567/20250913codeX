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
        # 小数なし（整数分）。読み込み時に四捨五入して整数化
        df["duration_min"] = (
            pd.to_numeric(df["duration_min"], errors="coerce").round(0).astype("Int64")
        )
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
        out["duration_min"] = (
            pd.to_numeric(out["duration_min"], errors="coerce").round(0).astype(int)
        )
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
    """表示範囲でフィルタリングする。

    サポートするラベル:
      - '1週間', '1ヶ月', '3ヶ月', '半年', '1年', '全期間'
      - 後方互換: '30日', '90日', '180日'
    """
    if df.empty:
        return df
    if range_label == "全期間":
        return df

    today = date.today()
    days_map = {
        "1週間": 7,
        "1ヶ月": 30,
        "3ヶ月": 90,
        "半年": 180,
        "1年": 365,
        # 後方互換
        "30日": 30,
        "90日": 90,
        "180日": 180,
    }
    days = days_map.get(range_label)
    if not days:
        return df
    start = today - timedelta(days=days - 1)
    mask = pd.to_datetime(df["date"]).dt.date >= start
    return df.loc[mask].copy()


# ===== Streamlit UI ========================================================
st.set_page_config(page_title="日々の体重トラッカー", layout="wide")

# ストレージ初期化
ensure_storage()

# データ読み込み
df = load_weights()
settings = load_settings()

# ---- サイドバー: テーマ/詳細表示 -----------------------------------------
st.sidebar.markdown("### 表示設定")
ui_theme = st.sidebar.selectbox("テーマ", ["ライト", "ダーク"], index=0)
PLOTLY_TEMPLATE = "plotly_dark" if ui_theme == "ダーク" else "plotly_white"
# 詳細セクションは常時表示
show_advanced = True

# ---- 共通: 軽いカスタムスタイル -----------------------------------------
st.markdown(
    """
    <style>
      .card {
        padding: 1rem; border-radius: 12px; border: 1px solid rgba(0,0,0,0.08);
        background: rgba(255,255,255,0.65); box-shadow: 0 4px 14px rgba(0,0,0,0.06);
      }
      [data-theme="dark"] .card { background: rgba(0,0,0,0.25); border-color: rgba(255,255,255,0.08); }
      .muted { color: rgba(0,0,0,0.6); }
      /* 余白の最適化（ワイドレイアウトで最大幅を広げ、左右の無駄を減らす）*/
      .block-container { padding-top: 0.75rem; padding-bottom: 1rem; }
      [data-testid="block-container"] { padding-top: 0.75rem; padding-bottom: 1rem; }
      /* テーブルのコンパクト表示（フォント・セル余白の最適化） */
      div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] { font-size: 0.9rem; }
      div[data-testid="stDataFrame"] div[role="gridcell"],
      div[data-testid="stDataEditor"] div[role="gridcell"] { padding: 4px 8px !important; }
      div[data-testid="stDataFrame"] div[role="columnheader"],
      div[data-testid="stDataEditor"] div[role="columnheader"] { padding: 6px 8px !important; }
      /* フォーム内コントロールの余白を統一 */
      div[data-testid="stForm"] > div { margin-bottom: 10px; }
      div[data-testid="stForm"] .stRadio { margin-bottom: 6px; }
      div[data-testid="stForm"] .stSelectbox, 
      div[data-testid="stForm"] .stNumberInput, 
      div[data-testid="stForm"] .stDateInput { margin-bottom: 6px; }
      /* フォーム（詳細: 体重/運動）を横並びに */
      @media (min-width: 992px) {
        div[data-testid="stForm"] { display: inline-block; vertical-align: top; width: 49%; margin-right: 1%; }
        div[data-testid="stForm"] + div[data-testid="stForm"] { margin-right: 0; }
      }
      .stButton > button { 
        white-space: nowrap; 
        min-height: 2.5rem;
        font-size: 0.875rem;
        font-weight: 500;
      }
      
      /* Modern green buttons with subtle depth */
      /* Base button size */
      .stButton > button,
      .stDownloadButton > button {
        height: 40px !important;
        padding: 0 16px !important;
        min-width: 140px !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        cursor: pointer !important;
      }
      /* Primary (追加/更新、目標を保存) */
      .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 60%, #0ea5e9 100%) !important;
        border: 0 !important; color: #ffffff !important;
        box-shadow: 0 10px 20px rgba(34,197,94,0.25), 0 6px 8px rgba(14,165,233,0.15) !important;
        transition: transform 160ms ease, filter 160ms ease, box-shadow 160ms ease !important;
      }
      /* Danger (削除): 各フォーム内の2つ目のボタンを赤系に */
      div[data-testid="stForm"] .stButton:nth-of-type(2) > button {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 60%) !important;
        border: 0 !important; color: #ffffff !important;
        box-shadow: 0 10px 20px rgba(239,68,68,0.25) !important;
      }
      /* Secondary (CSVダウンロード) */
      .stDownloadButton > button {
        background: linear-gradient(135deg, #e5e7eb 0%, #cbd5e1 60%) !important;
        border: 1px solid #d1d5db !important; color: #111827 !important;
        box-shadow: 0 4px 10px rgba(17,24,39,0.08) !important;
      }
      [data-theme="dark"] .stDownloadButton > button {
        background: linear-gradient(135deg, #475569 0%, #334155 60%) !important;
        border-color: #334155 !important; color: #ffffff !important;
      }
      .stButton > button:hover { transform: translateY(-1px); filter: brightness(1.02); }
      .stButton > button:active { transform: translateY(0); filter: brightness(0.98); }
      .stButton > button:focus { outline: none; box-shadow: 0 0 0 3px rgba(14,165,233,0.35) !important; }
      /* Ensure sidebar buttons (目標を保存) も同一スタイル */
      section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 60%, #0ea5e9 100%) !important;
        color: #ffffff !important;
      }
      .stDownloadButton > button:hover { transform: translateY(-1px); filter: brightness(1.02); }
      .stDownloadButton > button:active { transform: translateY(0); filter: brightness(0.98); }
      
      /* 入力フィールドの統一 */
      .stNumberInput > div > div > input,
      .stDateInput > div > div > input {
        min-height: 2.5rem;
        font-size: 0.875rem;
      }
      
      /* サブヘッダーのスタイル */
      .stSubheader {
        margin-bottom: 1rem !important;
        font-size: 1.25rem !important;
        font-weight: 600 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- モダン ダッシュボード ----------------------------------------------
# テーマに応じたフォント色を設定
is_dark = st.get_option("theme.base") == "dark"
_font = "#FFFFFF" if is_dark else "#2e3a59"

st.title("日々の体重可視化アプリ 🧭")
st.caption("ダッシュボードでトレンドを把握。詳細はサイドバーから切替。")

tab_dash, = st.tabs(["ダッシュボード"])
with tab_dash:
    # 表示範囲（セグメント風UI。未対応環境ではラジオにフォールバック）
    _range_options = ["1週間", "1ヶ月", "3ヶ月", "半年", "1年", "全期間"]
    try:
        range_label = st.segmented_control("期間", options=_range_options, default=st.session_state.get("range_label", "1週間"))
    except Exception:
        default_idx = _range_options.index(st.session_state.get("range_label", "1週間"))
        range_label = st.radio("表示期間", _range_options, horizontal=True, index=default_idx)
    st.session_state["range_label"] = range_label

    # 指標
    c1, c2, c3 = st.columns(3)
    # 体重: 最新値 + 7日差分
    latest_w = df["weight"].iloc[-1] if not df.empty else None
    s7 = compute_stats(df, 7)
    with c1:
        if latest_w is not None:
            st.metric(label="最新体重 (kg)", value=f"{latest_w:.1f}", delta=(f"{s7['delta']:.1f} kg" if s7["delta"] is not None else None))
        else:
            st.metric(label="最新体重 (kg)", value="-")
    # 目標差: 現在 - 目標（負が良い）
    with c2:
        g = settings.get("goal_weight")
        if g is not None and latest_w is not None:
            diff = latest_w - float(g)
            st.metric(label="目標差 (現在-目標)", value=f"{diff:.1f} kg", delta=None)
        else:
            st.metric(label="目標差 (現在-目標)", value="-")
    # 直近7日 運動合計
    ex_all = load_exercises()
    with c3:
        if not ex_all.empty:
            today = date.today()
            start = today - timedelta(days=6)
            ex7 = ex_all[pd.to_datetime(ex_all["date"]).dt.date >= start]
            total7 = int(pd.to_numeric(ex7["duration_min"], errors="coerce").fillna(0).sum()) if not ex7.empty else 0
            st.metric(label="直近7日 運動合計", value=f"{total7} 分")
        else:
            st.metric(label="直近7日 運動合計", value="0 分")

    # グラフ行
    gc1, gc2 = st.columns(2)
    # 体重グラフ（期間適用）
    with gc1:
        st.markdown("<div class='card'>📉 体重推移</div>", unsafe_allow_html=True)
        show_df_dash = filter_range(df, range_label)
        if show_df_dash.empty:
            st.info("データがありません")
        else:
            gdf = show_df_dash.sort_values("date").copy()
            gdf["ma7"] = gdf["weight"].rolling(window=7, min_periods=1).mean().round(1)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=pd.to_datetime(gdf["date"]), y=gdf["weight"], mode="lines+markers", name="体重", line=dict(color="#636EFA"), marker=dict(size=6), hovertemplate="%{x|%Y-%m-%d}<br>体重: %{y:.1f} kg<extra></extra>"))
            fig.add_trace(go.Scatter(x=pd.to_datetime(gdf["date"]), y=gdf["ma7"], mode="lines", name="7日移動平均", line=dict(color="#EF553B", width=3), hovertemplate="%{x|%Y-%m-%d}<br>7日平均: %{y:.1f} kg<extra></extra>"))
            gg = settings.get("goal_weight")
            if gg is not None:
                fig.add_trace(go.Scatter(x=pd.to_datetime(gdf["date"]), y=[gg]*len(gdf), mode="lines", name="目標体重", line=dict(color="#00CC96", dash="dash", width=2), hovertemplate="%{x|%Y-%m-%d}<br>目標: %{y:.1f} kg<extra></extra>"))
            fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), xaxis_title="", yaxis_title="体重 (kg)", template=PLOTLY_TEMPLATE)
            fig.update_xaxes(type="date", tickformat="%Y-%m-%d")
            fig.update_yaxes(tickformat=".1f")
            st.plotly_chart(fig, use_container_width=True)

    # 運動グラフ（期間適用）
    with gc2:
        st.markdown("<div class='card'>🏃‍♂️ 日毎運動合計</div>", unsafe_allow_html=True)
        ex_show_dash = filter_range(ex_all, range_label)
        if ex_show_dash.empty:
            st.info("運動データがありません")
        else:
            daily = ex_show_dash.groupby("date", as_index=False)["duration_min"].sum().sort_values("date")
            daily["duration_min"] = pd.to_numeric(daily["duration_min"], errors="coerce").round(0).astype(int)
            daily["ma7"] = daily["duration_min"].rolling(window=7, min_periods=1).mean().round(0).astype(int)
            fig_ex = go.Figure()
            fig_ex.add_trace(go.Bar(x=pd.to_datetime(daily["date"]), y=daily["duration_min"], name="合計(分)", marker_color="#19D3F3", hovertemplate="%{x|%Y-%m-%d}<br>合計: %{y:.0f} 分<extra></extra>"))
            fig_ex.add_trace(go.Scatter(x=pd.to_datetime(daily["date"]), y=daily["ma7"], mode="lines", name="7日移動平均", line=dict(color="#FF6692", width=3), hovertemplate="%{x|%Y-%m-%d}<br>7日平均: %{y:.0f} 分<extra></extra>"))
            fig_ex.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), xaxis_title="", yaxis_title="時間 (分)", barmode="overlay", template=PLOTLY_TEMPLATE)
            fig_ex.update_xaxes(type="date", tickformat="%Y-%m-%d")
            fig_ex.update_yaxes(tickformat=".0f")
            st.plotly_chart(fig_ex, use_container_width=True)



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


# ----- 詳細セクション ------------------------------------------------------------
if show_advanced:
    col_w, col_e = st.columns(2)
    
    with col_w:
        # ----- 体重入力フォーム ------------------------------------
        st.subheader("📊 体重データ入力")
        
        # 直近で入力した体重をデフォルト値に設定
        if not df.empty and "weight" in df.columns:
            try:
                _latest_weight_default = round(float(df["weight"].iloc[-1]), 1)
            except Exception:
                _latest_weight_default = 60.0
        else:
            _latest_weight_default = 60.0
            
        with st.form("edit_form", clear_on_submit=False):
            # 入力フィールドを統一されたサイズで配置
            col1, col2 = st.columns([1, 1])
            with col1:
                d_input = st.date_input("日付", value=date.today(), key="w_date")
            with col2:
                # 入力表示も小数1位で固定
                w_input = st.number_input(
                    "体重 (kg)",
                    min_value=20.0,
                    max_value=300.0,
                    value=st.session_state.get("w_input", _latest_weight_default),
                    step=0.1,
                    format="%.1f",
                    key="w_input",
                )
            
            # ボタンを統一されたサイズで横並び配置
            btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])
            with btn_col2: submitted_add = st.form_submit_button("追加/更新", type="primary", use_container_width=True)
            with btn_col3: submitted_del = st.form_submit_button("削除", use_container_width=True)

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


# CSVアップロードによる追記マージ機能は削除（ユーザー要望）


    with col_e:
        # ----- 運動データ入力フォーム ------------------------------------
        st.subheader("🏃‍♂️ 運動データ入力")
        
        ex_df = load_exercises()
        # 過去の種目一覧（重複排除）
        past_activities = (
            sorted(ex_df["activity"].dropna().astype(str).unique()) if not ex_df.empty else []
        )
        with st.form("exercise_form", clear_on_submit=False):
            # 入力方法（先頭に配置して縦横バランスを整える）
            mode = st.radio(
                "入力方法",
                options=["過去から選択", "新規入力"],
                horizontal=True,
                key="ex_mode",
            )
            force_new = (not past_activities)

            ex_c1, ex_c2, ex_c3 = st.columns([1, 1, 1])
            with ex_c1:
                ex_date = st.date_input("日付(運動)", value=date.today(), key="ex_date")
            with ex_c2:
                # 種目の選択/新規入力を切替（1つの場所で完結）
                if mode == "新規入力" or force_new:
                    st.session_state["ex_mode"] = "新規入力"
                    st.text_input(
                        "種目",
                        value=st.session_state.get("ex_activity_text", ""),
                        key="ex_activity_text",
                        placeholder="例: ウォーキング",
                        help=("過去の候補がないため新規入力のみ利用可" if force_new else None),
                    )
                else:
                    st.selectbox(
                        "種目",
                        options=(past_activities if past_activities else ["(候補なし)"]),
                        key="ex_activity_select",
                        help="過去の種目から選択",
                    )
            with ex_c3:
                ex_duration = st.number_input(
                    "時間 (分)", min_value=0, max_value=1440, step=1, format="%d", key="ex_duration"
                )
            # ボタンを統一されたサイズで横並び配置
            st.markdown("<br>", unsafe_allow_html=True)  # スペース追加
            ex_btn_col1, ex_btn_col2, ex_btn_col3 = st.columns([2, 1, 1])
            with ex_btn_col2:
                ex_add = st.form_submit_button("追加/更新", type="primary", use_container_width=True)
            with ex_btn_col3:
                ex_del = st.form_submit_button("削除", use_container_width=True)

if show_advanced and 'ex_date' in st.session_state:
    # 防御的に取り出し
    ex_date_val = st.session_state.get('ex_date', date.today())
elif show_advanced:
    ex_date_val = date.today()

if show_advanced and ex_add:
    # 選択優先。選択がない場合は新規入力を使用
    if st.session_state.get("ex_mode") == "新規入力" or not past_activities:
        chosen_activity = str(st.session_state.get("ex_activity_text", "")).strip()
    else:
        sel = str(st.session_state.get("ex_activity_select", "")).strip()
        chosen_activity = "" if sel == "(候補なし)" else sel
    if chosen_activity == "":
        st.warning("種目名を入力してください。")
    elif int(ex_duration) < 0 or int(ex_duration) > 1440:
        st.warning("時間(分)は 0〜1440 の範囲で入力してください。")
    else:
        new_ex = pd.DataFrame({
            "date": [ex_date],
            "activity": [chosen_activity],
            "duration_min": [int(ex_duration)],
        })
        if ex_df.empty:
            ex_df = new_ex
        else:
            ex_df = ex_df.copy()
            ex_df = ex_df[~((ex_df["date"] == ex_date) & (ex_df["activity"] == chosen_activity))]
            ex_df = pd.concat([ex_df, new_ex], ignore_index=True)
        ex_df = ex_df.sort_values(["date", "activity"]).reset_index(drop=True)
        save_exercises(ex_df)
        st.success(f"{ex_date} / {chosen_activity} を保存しました。")

if show_advanced and ex_del:
    if not ex_df.empty:
        before = len(ex_df)
        if st.session_state.get("ex_mode") == "新規入力" or not past_activities:
            chosen_activity = str(st.session_state.get("ex_activity_text", "")).strip()
        else:
            sel = str(st.session_state.get("ex_activity_select", "")).strip()
            chosen_activity = "" if sel == "(候補なし)" else sel
        ex_df = ex_df[~((ex_df["date"] == ex_date) & (ex_df["activity"] == chosen_activity))].reset_index(drop=True)
        if len(ex_df) != before:
            save_exercises(ex_df)
            st.success(f"{ex_date} / {chosen_activity} を削除しました。")
        else:
            st.info("削除対象が見つかりませんでした。")
    else:
        st.info("運動データがありません。")

"""
上記の運動ダウンロードボタンは、フォーム真下（右カラム）に配置してレイアウトを揃える
"""
if show_advanced:
    with col_e:
        ex_csv = StringIO()
        ex_export = load_exercises().copy()
        if not ex_export.empty:
            ex_export["date"] = pd.to_datetime(ex_export["date"]).dt.date.astype(str)
            ex_export["duration_min"] = (
                pd.to_numeric(ex_export["duration_min"], errors="coerce").round(0).astype(int)
            )
        ex_export.to_csv(ex_csv, index=False, encoding="utf-8")
        st.download_button(
            "運動データをCSVでダウンロード",
            data=ex_csv.getvalue().encode("utf-8"),
            file_name="exercises_export.csv",
            mime="text/csv",
        )

# 表示範囲はダッシュボードの選択を共有
range_label = st.session_state.get("range_label", "1週間")

if show_advanced:
    # 可視化（運動）
    st.subheader("運動の可視化")
    ex_show = filter_range(load_exercises(), range_label)
    if ex_show.empty:
        st.info("表示する運動データがありません。まずは運動を記録してください。")
    else:
        # 種目別の推移（1つのグラフに集約）: 日付を1つに統合（全種目が同じ日付配列を共有）
        by_act = (
            ex_show.groupby(["date", "activity"], as_index=False)["duration_min"].sum().sort_values("date")
        )
        if not by_act.empty:
            by_act["date"] = pd.to_datetime(by_act["date"])  # 日付型
            by_act["duration_min"] = (
                pd.to_numeric(by_act["duration_min"], errors="coerce").round(0).astype(int)
            )
            # 期間内の連続日付を作成
            full_days = pd.date_range(by_act["date"].min(), by_act["date"].max(), freq="D")
            # 日付×種目のピボット（欠損は0）
            piv = (
                by_act.pivot_table(index="date", columns="activity", values="duration_min", aggfunc="sum")
                .reindex(full_days, fill_value=0)
            )
            piv.index.name = "date"

        fig_act = go.Figure()
        for activity in piv.columns:
            fig_act.add_trace(
                go.Bar(
                    x=piv.index,
                    y=piv[activity],
                    name=str(activity),
                    opacity=0.9,
                    hovertemplate="%{x|%Y-%m-%d}<br>%{fullData.name}: %{y:.0f} 分<extra></extra>",
                )
            )
        fig_act.update_layout(
            height=380,
            margin=dict(l=20, r=20, t=10, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title="",
            yaxis_title="時間 (分)",
            barmode="stack",
            template=PLOTLY_TEMPLATE,
        )
        fig_act.update_xaxes(type="date", tickformat="%Y-%m-%d")
        fig_act.update_yaxes(tickformat=".0f")
        st.plotly_chart(fig_act, use_container_width=True)

if show_advanced:
    # 一覧（運動）
    st.subheader("運動データ一覧")
    ex_disp = load_exercises().copy()
    if not ex_disp.empty:
        ex_disp = ex_disp.sort_values(["date", "activity"], ascending=[False, True]).reset_index(drop=True)
        # チェックボックス列を追加してインライン選択
        ex_view = ex_disp.copy()
        ex_view["選択"] = False
        try:
            ex_table = st.data_editor(
                ex_view,
                hide_index=True,
                use_container_width=True,
                key="ex_editor",
                column_config={
                    "選択": st.column_config.CheckboxColumn("選択", help="削除対象"),
                    "date": st.column_config.DateColumn("日付", format="YYYY-MM-DD", width="small"),
                    "activity": st.column_config.TextColumn("種目", width="medium"),
                    "duration_min": st.column_config.NumberColumn("時間 (分)", format="%d", width="small"),
                },
            )
        except Exception:
            # フォールバック
            ex_table = ex_view
            st.dataframe(ex_view, use_container_width=True)
        # 下に削除ボタンのみ配置
        if st.button("選択した運動記録を削除", key="ex_delete_btn"):
            sel = ex_table[ex_table.get("選択", False) == True]  # noqa: E712
            if sel.empty:
                st.info("削除対象が選択されていません。")
            else:
                base = load_exercises().copy()
                before = len(base)
                for _, row in sel.iterrows():
                    d = pd.to_datetime(row["date"]).date()
                    act = str(row["activity"]) if "activity" in row else str(row.get("activity", ""))
                    base = base[~((pd.to_datetime(base["date"]).dt.date == d) & (base["activity"].astype(str) == act))]
                if len(base) != before:
                    save_exercises(base)
                    st.success(f"{len(sel)} 件の運動記録を削除しました。")
                else:
                    st.info("該当する削除対象がありませんでした。")
    else:
        st.dataframe(ex_disp, use_container_width=True)


if show_advanced:
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


if show_advanced:
    # 体重の表示対象をフィルタ
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
            xaxis_title="",
            yaxis_title="体重 (kg)",
            template=PLOTLY_TEMPLATE,
        )
        # 横軸は日付単位（年月日）
        fig.update_xaxes(type="date", tickformat="%Y-%m-%d")
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
        # チェックボックス列を追加してインライン選択
        w_view = disp.copy()
        w_view["選択"] = False
        try:
            w_table = st.data_editor(
                w_view,
                hide_index=True,
                use_container_width=True,
                key="w_editor",
                column_config={
                    "選択": st.column_config.CheckboxColumn("選択", help="削除対象"),
                    "date": st.column_config.DateColumn("日付", format="YYYY-MM-DD", width="small"),
                    "weight": st.column_config.NumberColumn("体重 (kg)", format="%.1f", width="small"),
                },
            )
        except Exception:
            w_table = w_view
            st.dataframe(w_view, use_container_width=True)
        # 下に削除ボタンのみ配置
        if st.button("選択した体重データを削除", key="w_delete_btn"):
            sel = w_table[w_table.get("選択", False) == True]  # noqa: E712
            if sel.empty:
                st.info("削除対象が選択されていません。")
            else:
                base = load_weights().copy()
                before = len(base)
                if not base.empty:
                    base["_d"] = pd.to_datetime(base["date"]).dt.date
                    target_dates = pd.to_datetime(sel["date"]).dt.date.unique()
                    base = base[~base["_d"].isin(target_dates)].drop(columns=["_d"])  # 除外
                    if len(base) != before:
                        save_weights(base)
                        st.success(f"{len(target_dates)} 日の体重データを削除しました。")
                    else:
                        st.info("該当する削除対象がありませんでした。")
    else:
        st.dataframe(disp, use_container_width=True)
