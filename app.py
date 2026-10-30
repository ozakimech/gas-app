import base64
import calendar
from datetime import date, datetime
import io
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import streamlit as st

st.set_page_config(
    page_title="尾崎ガス配管 社内ポータル", page_icon="🔧", layout="wide"
)

# 1. フォルダ内にある icon.jpg を自動で読み込んでBase64（データ形式）に変換する
try:
  with open("icon.jpg", "rb") as f:
    encoded_img = base64.b64encode(f.read()).decode("utf-8")
  icon_data_url = f"data:image/jpeg;base64,{encoded_img}"
except FileNotFoundError:
  icon_data_url = ""  # 万が一ファイルが見つからない場合の対策

# 2. マニフェストにも直接埋め込む
manifest_json = f"""
{{
  "name": "尾崎ガス配管 社内ポータル",
  "short_name": "尾崎ポータル",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#1e293b",
  "icons": [
    {{
      "src": "{icon_data_url}",
      "sizes": "192x192",
      "type": "image/jpeg"
    }}
  ]
}}
"""

manifest_base64 = base64.b64encode(manifest_json.encode("utf-8")).decode("utf-8")

# 3. ブラウザに直接流し込む（Apple用アイコンにもデータを直接指定）
st.markdown(
    f"""
    <link rel="manifest" href="data:application/manifest+json;base64,{manifest_base64}">
    <link rel="apple-touch-icon" href="{icon_data_url}">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="尾崎ポータル">
    """,
    unsafe_allow_html=True,
)


# --- 1. ページの基本設定（最初に実行） ---
st.set_page_config(
    page_title="尾崎ガス配管 社内ポータル", page_icon="📄", layout="wide"
)

# --- 2. 日本語フォントの登録（セットでここに書くのが確実） ---
pdfmetrics.registerFont(TTFont('IPAexGothic', 'ipaexg.ttf'))
pdfmetrics.registerFont(TTFont('IPAexMincho', 'ipaexm.ttf'))

# ---- パスワード認証機能 ----
def check_password():
    """正しいパスワードが入力されたら True を返す"""
    def password_entered():
        if st.session_state["password_input"] == "ozagas":
            st.session_state["password_correct"] = True
            del st.session_state["password_input"]  # パスワードを保持しない
        else:
            st.session_state["password_correct"] = False

    # すでに認証済みの場合は True
    if st.session_state.get("password_correct", False):
        return True

    # ログイン画面の表示
    st.title("🔒 ログイン")
    st.text_input(
        "パスワードを入力せなあかん", 
        type="password", 
        on_change=password_entered, 
        key="password_input"
    )
    
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("パスワード間違っとる")
        
    return False

# パスワードチェックを通らない場合は、ここで処理を停止
if not check_password():
    st.stop()


# ==========================================
# これより下に、元々のメインのアプリコードを配置
# ==========================================

import base64
import calendar
from datetime import date, datetime
import io
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# --- ページの基本設定 ---
st.set_page_config(
    page_title="尾崎ガス配管 社内ポータル", page_icon="📄", layout="wide"
)

# --- 🎨 サイドバーの表示モードに応じたCSS動的適用（スマホ・PC切り替え） ---
if "view_mode_select" not in st.session_state:
  st.session_state["view_mode_select"] = "自動（レスポンシブ）"

mobile_constraint_css = ""
if st.session_state["view_mode_select"] == "モバイルコンパクト風":
  mobile_constraint_css = """
    .stApp {
        max-width: 480px;
        margin: 0 auto;
        border-left: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        box-shadow: 0 0 20px rgba(0,0,0,0.05);
    }
    """

st.markdown(
    f"""
    <style>
    {mobile_constraint_css}
    .stApp {{
        background-color: #f4f6f9;
    }}
    [data-testid="stSidebar"] {{
        background-color: #1e293b;
        color: white;
    }}
    [data-testid="stSidebar"] .stButton>button {{
        background-color: #334155;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 500;
    }}
    [data-testid="stSidebar"] .stButton>button:hover {{
        background-color: #3b82f6;
        color: white;
    }}
    .stButton>button {{
        border-radius: 10px;
        font-weight: 600;
        min-height: 44px;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 22px;
        color: #1e3d59;
    }}
    .timeline-card {{
        background-color: #ffffff;
        padding: 16px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-left: 5px solid #3b82f6;
    }}
    .stTextInput input, .stSelectbox select, .stTextArea textarea {{
        border-radius: 8px !important;
        font-size: 16px !important;
    }}
    </style>
""",
    unsafe_allow_html=True,
)

# --- 初期データ＆セッションステートの準備 ---
if "current_page" not in st.session_state:
  st.session_state.current_page = "ホーム"

# 1. 予定データの保持
if "schedules" not in st.session_state:
  st.session_state.schedules = [
      {
          "id": 1,
          "date": date(2026, 10, 28),
          "time": "09:00",
          "title": "〇〇住宅 配管定期点検",
          "staff": "尾崎",
          "note": "現場での水圧確認作業あり",
      },
      {
          "id": 2,
          "date": date(2026, 10, 28),
          "time": "14:00",
          "title": "伊丹産業電設(株)様 打ち合わせ",
          "staff": "尾崎",
          "note": "請求書および来月工程の確認",
      },
      {
          "id": 3,
          "date": date(2026, 10, 29),
          "time": "10:30",
          "title": "大東建託AS(株)現場 下見",
          "staff": "スタッフA",
          "note": "見積もり用採寸",
      },
  ]

# 2. 業務報告データの保持
if "reports" not in st.session_state:
  st.session_state.reports = [
      {
          "id": 1,
          "timestamp": "2026-10-28 15:30",
          "staff": "尾崎",
          "category": "現場作業",
          "text": (
              "本日午前中の配管交換作業が無事完了しました。漏れテストもクリアしています。"
          ),
          "image": None,
      },
      {
          "id": 2,
          "timestamp": "2026-10-28 11:15",
          "staff": "スタッフA",
          "category": "定期点検",
          "text": (
              "南恩加島の物件にてメーター点検を実施。特に問題ありませんでした。"
          ),
          "image": None,
      },
  ]


def change_page(page_name):
  st.session_state.current_page = page_name


# --- サイドバー メニュー ---
st.sidebar.title("📌 メニュー")
st.sidebar.write("")
if st.sidebar.button("🏠 ホーム（トップ）", use_container_width=True):
  change_page("ホーム")
if st.sidebar.button("📅 予定表", use_container_width=True):
  change_page("予定表")
if st.sidebar.button("📝 業務内容共有", use_container_width=True):
  change_page("業務内容共有")
if st.sidebar.button("📄 請求書作成", use_container_width=True):
  change_page("請求書作成")

st.sidebar.divider()
st.sidebar.subheader("📱 表示モード設定")
selected_mode = st.sidebar.radio(
    "レイアウト選択",
    ["自動（レスポンシブ）", "モバイルコンパクト風", "PCワイド風"],
    key="view_mode_select",
    label_visibility="collapsed",
)
st.sidebar.caption(
    "※スマホ表示をテストしたい場合は「モバイルコンパクト風」を選択してください。"
)

st.sidebar.divider()
st.sidebar.caption("© 2026 尾崎ガス配管 業務管理システム")


# ==========================================
# 1. ホーム（トップ・ポータル画面）
# ==========================================
if st.session_state.current_page == "ホーム":
  st.title("👨‍🔧🪏 業務管理場へようこそ")
  st.write(
      "毎日の業務管理、スケジュール確認、および請求書発行ができるで。"
  )

  st.divider()

  col1, col2, col3 = st.columns(3)

  with col1:
    st.subheader("📅 予定表")
    st.write("スケジュールや作業予定を確認・追加")
    if st.button("予定表を開く", key="h_cal", use_container_width=True):
      change_page("予定表")
      st.rerun()

  with col2:
    st.subheader("📝 業務内容共有")
    st.write("現場の写真や本日の作業報告を共有")
    if st.button("業務共有を開く", key="h_work", use_container_width=True):
      change_page("業務内容共有")
      st.rerun()

  with col3:
    st.subheader("📄 請求書作成")
    st.write("PDF請求書を作成")
    if st.button("請求書作成を開く", key="h_rec", use_container_width=True):
      change_page("請求書作成")
      st.rerun()


# ==========================================
# 2. 予定表のページ
# ==========================================
elif st.session_state.current_page == "予定表":
  st.title("📅 予定表・スケジュール管理")

  if "selected_schedule_date" not in st.session_state:
    st.session_state["selected_schedule_date"] = date.today()

  if "sched_form_id" not in st.session_state:
    st.session_state["sched_form_id"] = 0

  with st.expander("➕ 【新規予定の作成】ここをクリックして開く", expanded=False):
    with st.form(
        key=f"add_schedule_form_{st.session_state['sched_form_id']}",
        clear_on_submit=True,
    ):
      st.subheader("新しい予定の登録")
      f_col1, f_col2, f_col3 = st.columns(3)
      with f_col1:
        new_date = st.date_input("日付", value=date.today())
      with f_col2:
        new_time = st.time_input("時間")
      with f_col3:
        new_staff = st.text_input("担当者名", "尾崎")

      new_title = st.text_input(
          "予定タイトル", placeholder="例：〇〇様宅 配管工事"
      )
      new_note = st.text_area("詳細メモ・備考", placeholder="持ち物や注意事項など")

      c_s1, c_s2 = st.columns(2)
      with c_s1:
        submit_sched = st.form_submit_button(
            "📅 予定を登録", use_container_width=True
        )
      with c_s2:
        reset_sched = st.form_submit_button(
            "🔄 入力クリア", use_container_width=True
        )

      if submit_sched:
        if new_title.strip() != "":
          new_entry = {
              "id": len(st.session_state.schedules) + 1,
              "date": new_date,
              "time": new_time.strftime("%H:%M"),
              "title": new_title,
              "staff": new_staff,
              "note": new_note,
          }
          st.session_state.schedules.append(new_entry)
          st.session_state["selected_schedule_date"] = new_date
          st.success(
              f"✅ 「{new_title}」（{new_date} {new_time.strftime('%H:%M')}）を追加登録しました！下のスケジュール一覧に表示されます。"
          )
          st.session_state["sched_form_id"] += 1
          st.rerun()
        else:
          st.error("予定タイトルを入力してください。")

      elif reset_sched:
        st.session_state["sched_form_id"] += 1
        st.rerun()

  st.divider()

  col_left, col_right = st.columns([1, 1])

  with col_left:
    st.subheader("🔍 スケジュールの確認")
    selected_date = st.date_input(
        "確認したい日付を選択してみ", key="selected_schedule_date"
    )

    day_schedules = [
        s for s in st.session_state.schedules if s["date"] == selected_date
    ]

    st.markdown(
        f"#### 🗓️ **{selected_date.strftime('%Y年%m月%d日')}** の予定一覧"
    )

    if day_schedules:
      for item in day_schedules:
        with st.container():
          st.info(
              f"⏰ **{item['time']}**  |  👤 担当: **{item['staff']}**\n\n"
              f"📌 **{item['title']}**\n\n"
              f"📝 メモ: {item['note'] if item['note'] else 'なし'}"
          )
    else:
      st.write("✅ この日の予定はありません。")

  with col_right:
    st.subheader("🗓️ 月間スケジュール")
    show_year = selected_date.year
    show_month = selected_date.month
    st.caption(f"{show_year}年 {show_month}月（🔴印＝予定ありの日）")

    month_events = [
        s["date"].day
        for s in st.session_state.schedules
        if s["date"].year == show_year and s["date"].month == show_month
    ]

    cal = calendar.monthcalendar(show_year, show_month)
    cal_data = []
    for week in cal:
      week_row = []
      for day in week:
        if day == 0:
          week_row.append("")
        else:
          mark = "🔴 " if day in month_events else ""
          week_row.append(f"{mark}{day}日")
      cal_data.append(week_row)

    df_cal = pd.DataFrame(
        cal_data, columns=["月", "火", "水", "木", "金", "土", "日"]
    )
    st.dataframe(df_cal, use_container_width=True, hide_index=True)


# ==========================================
# 3. 業務内容共有のページ
# ==========================================
elif st.session_state.current_page == "業務内容共有":
  st.title("📝 業務内容共有（タイムライン）")
  st.write(
      "日々の作業内容や現場写真を投稿。投稿の編集・削除やキーワード検索が可能やで。"
  )

  if "form_id" not in st.session_state:
    st.session_state["form_id"] = 0
  if "editing_report_id" not in st.session_state:
    st.session_state["editing_report_id"] = None
  if "deleting_report_id" not in st.session_state:
    st.session_state["deleting_report_id"] = None

  with st.expander("✍️ 【新しい業務報告をポスト】", expanded=True):
    with st.form(
        key=f"new_report_form_{st.session_state['form_id']}",
        clear_on_submit=True,
    ):
      st.subheader("✍️ 新しい業務報告をポスト")
      c_a, c_b = st.columns(2)
      with c_a:
        reporter_name = st.text_input("投稿者名", placeholder="名前")
      with c_b:
        report_cat = st.selectbox(
            "作業種別", ["現場作業", "定期点検", "打ち合わせ", "緊急対応", "その他（希望の選択項目があれば変えます。）"]
        )

      report_body = st.text_area(
          "報告内容・詳細",
          placeholder="作業の進捗状態、現場の状況、特記事項を入力してください...",
      )
      upload_img = st.file_uploader(
          "📸 現場写真を取り付ける（任意）", type=["jpg", "jpeg", "png"]
      )

      col_btn1, col_btn2 = st.columns([1, 1])
      with col_btn1:
        btn_post = st.form_submit_button(
            "🚀 タイムラインに投稿する", use_container_width=True
        )
      with col_btn2:
        btn_reset = st.form_submit_button(
            "🔄 入力内容をリセット", use_container_width=True
        )

      if btn_post:
        if report_body.strip() != "":
          now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
          img_bytes = upload_img.read() if upload_img is not None else None
          new_id = (
              max([r["id"] for r in st.session_state.reports], default=0) + 1
          )

          new_rep = {
              "id": new_id,
              "timestamp": now_str,
              "staff": reporter_name if reporter_name.strip() else "尾崎",
              "category": report_cat,
              "text": report_body,
              "image": img_bytes,
          }
          st.session_state.reports.insert(0, new_rep)
          st.success("業務報告を投稿したよ！")
          st.session_state["form_id"] += 1
          st.rerun()
        else:
          st.error("報告内容を入力してください。")

      elif btn_reset:
        st.session_state["form_id"] += 1
        st.rerun()

  st.divider()

  st.subheader("🕒 業務共有タイムライン")
  search_keyword = st.text_input(
      "🔍 検索できるでぇ～（作業者名、作業種別、報告内容のキーワード）",
      placeholder="例：尾崎、現場作業、配管、パジェロ など...",
  )

  filtered_reports = st.session_state.reports
  if search_keyword.strip() != "":
    kw = search_keyword.strip().lower()
    filtered_reports = [
        r
        for r in st.session_state.reports
        if kw in r["staff"].lower()
        or kw in r["category"].lower()
        or kw in r["text"].lower()
    ]
    st.caption(f"「{search_keyword}」の検索結果: {len(filtered_reports)}件")

  if filtered_reports:
    for rep in filtered_reports:
      with st.container():
        if st.session_state["editing_report_id"] == rep["id"]:
          st.info(f"✏️ 投稿 ID:{rep['id']} の編集モード")
          with st.form(key=f"edit_form_{rep['id']}"):
            e_col1, e_col2 = st.columns(2)
            with e_col1:
              edit_staff = st.text_input("投稿者名", value=rep["staff"])
            with e_col2:
              cats = [
                  "現場作業",
                  "定期点検",
                  "打ち合わせ",
                  "緊急対応",
                  "その他",
              ]
              cat_idx = (
                  cats.index(rep["category"]) if rep["category"] in cats else 0
              )
              edit_cat = st.selectbox(
                  "作業種別", cats, index=cat_idx
              )

            edit_text = st.text_area("報告内容・詳細", value=rep["text"])
            edit_img = st.file_uploader(
                "📸 画像を変更・追加（未選択の場合は既存の画像を保持）",
                type=["jpg", "jpeg", "png"],
            )

            e_btn1, e_btn2 = st.columns(2)
            with e_btn1:
              btn_save = st.form_submit_button(
                  "💾 変更を保存する", use_container_width=True
              )
            with e_btn2:
              btn_cancel = st.form_submit_button(
                  "❌ キャンセル", use_container_width=True
              )

            if btn_save:
              rep["staff"] = (
                  edit_staff if edit_staff.strip() else "尾崎"
              )
              rep["category"] = edit_cat
              rep["text"] = edit_text
              if edit_img is not None:
                rep["image"] = edit_img.read()

              st.session_state["editing_report_id"] = None
              st.success("投稿内容を更新しました！")
              st.rerun()

            elif btn_cancel:
              st.session_state["editing_report_id"] = None
              st.rerun()

        elif st.session_state["deleting_report_id"] == rep["id"]:
          st.warning(
              f"⚠️ 投稿 ID:{rep['id']} （{rep['staff']}スタッフの「{rep['category']}」）をほんまに消してええん？？この操作は元に、戻らんで！"
          )
          d_col1, d_col2, _ = st.columns([1, 1, 3])
          with d_col1:
            if st.button("はい、削除します", key=f"confirm_del_{rep['id']}"):
              st.session_state.reports = [
                  r for r in st.session_state.reports if r["id"] != rep["id"]
              ]
              st.session_state["deleting_report_id"] = None
              st.success("投稿を削除しました。")
              st.rerun()
          with d_col2:
            if st.button("いいえ（キャンセル）", key=f"cancel_del_{rep['id']}"):
              st.session_state["deleting_report_id"] = None
              st.rerun()

        else:
          col_t1, col_t2 = st.columns([3, 1])
          with col_t1:
            st.markdown(
                f"### 🏷️ 【{rep['category']}】 {rep['staff']} スタッフ"
            )
            st.caption(f"🕒 投稿日時: {rep['timestamp']}")
            st.write(rep["text"])

            act_c1, act_c2, _ = st.columns([1, 1, 3])
            with act_c1:
              if st.button("✏️ 編集", key=f"btn_edit_{rep['id']}"):
                st.session_state["editing_report_id"] = rep["id"]
                st.session_state["deleting_report_id"] = None
                st.rerun()
            with act_c2:
              if st.button("🗑️ 削除", key=f"btn_del_{rep['id']}"):
                st.session_state["deleting_report_id"] = rep["id"]
                st.session_state["editing_report_id"] = None
                st.rerun()

          with col_t2:
            if rep["image"] is not None:
              st.image(
                  rep["image"], caption="添付写真", use_container_width=True
              )

        st.divider()
  else:
    st.info("その条件じゃ，見つからんわ")


# ==========================================
# 4. 請求書作成のページ
# ==========================================
elif st.session_state.current_page == "請求書作成":
  st.title("📄 本格 請求書作成システム")
  st.write(
      "このフォーマットで請求書作成できるようにしたけど、内容は確認して（修正可能）"
  )

  # 最初に登録した 'IPAexGothic' をそのまま使う
  FONT_NAME_G = "IPAexGothic"
  FONT_NAME_M = "IPAexMincho"


  with st.expander("📌 宛名・発行者情報の編集", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
      client_name = st.text_input("宛名", "伊丹産業電設(株) 御中")
      issue_date = st.text_input("発行日", "2026年 9月 30日")
    with col2:
      invoice_no = st.text_input("請求書番号 (No.)", "1")
      registration_no = st.text_input("登録番号", "T1810824577403")

    st.divider()
    col3, col4 = st.columns(2)
    with col3:
      issuer_name = st.text_input("発行者（屋号・会社名）", "尾崎ガス配管")
      issuer_postal = st.text_input("郵便番号", "〒583-0863")
    with col4:
      issuer_address = st.text_input(
          "住所", "大阪府羽曳野市蔵之内342-1"
      )
      issuer_tel = st.text_input("TEL・FAX", "072-956-5292")

  st.subheader("明細行の入力")

  initial_rows = [
      {
          "項目": (
              "テスト"
          ),
          "オーダー番号": "B682708",
          "金額": 246000,
      },
      {
          "項目": (
              "テスト２"
          ),
          "オーダー番号": "B683688",
          "金額": 82000,
      },
  ]
  while len(initial_rows) < 25:
    initial_rows.append({"項目": "", "オーダー番号": "", "金額": 0})

  initial_data = pd.DataFrame(initial_rows)
  edited_df = st.data_editor(
      initial_data, num_rows="fixed", use_container_width=True
  )

  valid_df = edited_df[
      (edited_df["項目"].astype(str).str.strip() != "")
      & (edited_df["金額"] > 0)
  ].copy()

  if not valid_df.empty:
    subtotal_all = valid_df["金額"].sum()
    tax_all = int(subtotal_all * 0.10)
  else:
    subtotal_all = 0
    tax_all = 0

  total_amount_inc = int(subtotal_all + tax_all)

  st.subheader("📊 計算結果サマリー")
  c1, c2, c3 = st.columns(3)
  c1.metric("小計（税抜）", f"¥{subtotal_all:,}")
  c2.metric("消費税（10%）", f"¥{tax_all:,}")
  c3.metric("ご請求金額（税込）", f"¥{total_amount_inc:,}")


  def create_invoice_pdf(
      client_name,
      issue_date,
      invoice_no,
      registration_no,
      issuer_name,
      issuer_postal,
      issuer_address,
      issuer_tel,
      df,
      subtotal_all,
      tax_all,
      total_amount_inc,
  ):
    buffer = io.BytesIO()
    width, height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    def draw_bold_string(x, y, text, offset=0.3):
        c.drawString(x, y, text)
        c.drawString(x + offset, y, text)
        c.drawString(x + offset, y + offset, text )

    def draw_bold_right_string(x, y, text, offset=0.3):
        c.drawRightString(x, y, text)
        c.drawRightString(x + offset, y, text)


    c.setFillColorRGB(0.15, 0.35, 0.65)
    c.rect(220, height - 60, 160, 25, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont(FONT_NAME_M, 18)
    draw_bold_string(270, height - 55, "請 求 書")

    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_NAME_G, 9)
    c.drawString(470, height - 35, "No.")
    c.drawString(510, height - 35, str(invoice_no))
    c.drawString(450, height - 55, f"{issue_date}")

    c.setLineWidth(1.0)
    c.setStrokeColorRGB(0, 0, 0)
    c.line(470, height - 36, 555, height - 36)

    c.setFont(FONT_NAME_M, 22)
    draw_bold_string(40, height - 85, f"{client_name}")

  
    c.setFillColorRGB(0.15, 0.35, 0.65)
    c.setFont(FONT_NAME_G, 12)
    c.drawString(45, height - 115, "下記の通りご請求申し上げますので、ご照会の上")
    c.drawString(45, height - 130, "お支払いくださいますようお願い申し上げます。")
    c.drawString(45, height - 150, "ご請求金額：")

    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_NAME_M, 14)
    draw_bold_string(125, height - 150, f"¥{total_amount_inc:,}")

    c.setLineWidth(1.5)
    c.setStrokeColorRGB(0.15, 0.35, 0.65)
    c.line(45, height - 155, 200, height - 155)

    c.setFont(FONT_NAME_G, 10)
    c.drawString(420, height - 75, f"{issuer_postal}")
    c.setFont(FONT_NAME_M, 10)
    c.drawString(410, height - 87, f"{issuer_address}")
    c.setFont(FONT_NAME_M, 14)
    draw_bold_string(410, height - 105, f"{issuer_name}")
    c.setFont(FONT_NAME_G, 10)
    c.drawString(410, height - 118, f"TEL･FAX {issuer_tel}")
    c.setFont(FONT_NAME_M, 10)
    draw_bold_string(410, height - 145, "登録番号")
    c.setFont(FONT_NAME_G, 10)
    c.drawString(455, height -145,f"{registration_no}" )

    y = height - 190
    c.setFillColorRGB(0.15, 0.35, 0.65)
    c.rect(40, y, width - 80, 20, fill=1, stroke=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont(FONT_NAME_G, 10)
    draw_bold_right_string(65, y + 8, "No.")
    c.setFont(FONT_NAME_M, 10)
    draw_bold_right_string(235, y + 8, "項目")
    draw_bold_right_string(445, y + 8, "オーダー番号")
    draw_bold_right_string(515, y + 8, "金額")

    c.setFillColorRGB(0, 0, 0)
    y -= 20
    MAX_ROWS = 25

    for i in range(MAX_ROWS):
      c.rect(40, y, width - 80, 20, fill=0, stroke=1)
      c.line(75, y, 75, y + 20)
      c.line(380, y, 380, y + 20)
      c.line(460, y, 460, y + 20)

      c.setFont(FONT_NAME_G, 13)
      c.drawCentredString(57, y + 5, str(i + 1))

      if i < len(df):
        row = df.iloc[i]
        item_val = str(row["項目"]).strip()

        if item_val != "" and item_val != "nan":
          order_val = (
              str(row["オーダー番号"])
              if pd.notna(row["オーダー番号"])
              else ""
          )
          try:
            amt_val = int(row["金額"])
            amt_str = f"{amt_val:,}"
          except:
            amt_str = ""

          c.drawString(82, y + 5, item_val)
          c.drawString(396, y + 5, order_val)
          if amt_str:
            c.drawRightString(width - 48, y + 5, amt_str)

      y -= 20

    c.rect(40, y - 60, 340, 60, fill=0, stroke=1)
    c.rect(380, y - 60, width - 420, 60, fill=0, stroke=1)
    c.line(380, y - 20, width - 40, y - 20)
    c.line(380, y - 40, width - 40, y - 40)
    c.line(460, y - 60, 460, y)

    c.setFont(FONT_NAME_M, 12)
    c.drawString(410, y - 13, "小 計")
    c.drawRightString(width - 48, y - 13, f"{int(subtotal_all):,}")
    c.drawString(388, y - 35, "消費税(10%)")
    c.drawRightString(width - 48, y - 35, f"{int(tax_all):,}")
    c.setFont(FONT_NAME_M, 12)
    c.drawString(410, y - 55, "合 計")
    draw_bold_string(width - 95, y - 55, f"{int(total_amount_inc):,}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


  pdf_buffer = create_invoice_pdf(
      client_name,
      issue_date,
      invoice_no,
      registration_no,
      issuer_name,
      issuer_postal,
      issuer_address,
      issuer_tel,
      edited_df,
      subtotal_all,
      tax_all,
      total_amount_inc,
  )

  st.divider()

  st.divider()

  # --- 🎛️ PDFプレビューの表示ON/OFF切り替え ---
  col_p1, col_p2 = st.columns([2, 1])
  with col_p1:
    st.subheader("📄 請求書プレビュー")
  with col_p2:
    show_preview = st.toggle("プレビューを表示する", value=False)

  if show_preview:
    base64_pdf = base64.b64encode(pdf_buffer.getvalue()).decode("utf-8")
    pdf_display = (
        f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%"'
        ' height="600px" type="application/pdf"></iframe>'
    )
    st.markdown(pdf_display, unsafe_allow_html=True)
  else:
    st.info(
        "💡 プレビューは非表示になっています。「プレビューを表示する」をONにすると画面上で確認できます。"
    )

  st.download_button(
      label="📥 請求書PDFをダウンロード",
      data=pdf_buffer,
      file_name="invoice.pdf",
      mime="application/pdf",
      use_container_width=True,
  )

 # --- 📄 請求書ダウンロード部分 ---
  #st.subheader("📄 請求書発行")
  #st.info("💡 下のボタンから、作成された請求書PDFをダウンロードしてご確認ください。")

  #st.download_button(
   #   label="📥 請求書PDFをダウンロード",
    #  data=pdf_buffer,
     ##mime="application/pdf",
      #use_container_width=True,
  #)