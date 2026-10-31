import base64
from datetime import date, datetime
import io
import json
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# --- 1. ページの基本設定 ---
st.set_page_config(
    page_title="尾崎ガス配管 社内ポータル", page_icon="🔧", layout="wide"
)

# --- 2. PWA設定（manifest / ホーム画面アイコン） ---
components.html(
    """
    <script>
    const doc = window.parent.document;
    const head = doc.head;
    head.querySelectorAll(
      'link[rel="manifest"], link[rel="apple-touch-icon"], link[rel="icon"],' +
      'meta[name="apple-mobile-web-app-capable"], meta[name="theme-color"],' +
      'meta[name="apple-mobile-web-app-title"]'
    ).forEach(el => el.remove());

    const add = (tag, attrs) => {
      const el = doc.createElement(tag);
      Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
      head.appendChild(el);
    };
    add('link', {rel: 'manifest', href: '/app/static/manifest.json'});
    add('link', {rel: 'icon', type: 'image/png', href: '/app/static/icon-192.png'});
    add('link', {rel: 'apple-touch-icon', href: '/app/static/apple-touch-icon.png'});
    add('meta', {name: 'apple-mobile-web-app-capable', content: 'yes'});
    add('meta', {name: 'apple-mobile-web-app-title', content: 'GAS'});
    add('meta', {name: 'theme-color', content: '#1e293b'});
    </script>
    """,
    height=0,
)

# --- 📱 タッチ操作改善（モバイルでメニュータップ時にサイドバーを自動で閉じるJS） ---
components.html(
    """
    <script>
    const parentDoc = window.parent.document;
    function closeSidebarOnMobile() {
        if (window.parent.innerWidth <= 768) {
            const closeBtn = parentDoc.querySelector('[data-testid="stSidebarCollapseButton"] button');
            if (closeBtn) {
                closeBtn.click();
            }
        }
    }
    setTimeout(() => {
        const sidebarButtons = parentDoc.querySelectorAll('[data-testid="stSidebar"] button');
        sidebarButtons.forEach(btn => {
            btn.addEventListener('click', closeSidebarOnMobile);
        });
    }, 1000);
    </script>
    """,
    height=0,
)

# --- 3. 日本語フォントの登録 ---
BASE_DIR = Path(__file__).parent
pdfmetrics.registerFont(TTFont("IPAexGothic", str(BASE_DIR / "ipaexg.ttf")))
pdfmetrics.registerFont(TTFont("IPAexMincho", str(BASE_DIR / "ipaexm.ttf")))


# ---- パスワード認証機能 ----
# def check_password():
#   def password_entered():
#     if st.session_state["password_input"] == "ozagas":
#       st.session_state["password_correct"] = True
#       del st.session_state["password_input"]
#     else:
#       st.session_state["password_correct"] = False

#   if st.session_state.get("password_correct", False):
#     return True

#   st.title("🔒 ログイン")
#   st.text_input(
#       "パスワードを入力せなあかん",
#       type="password",
#       on_change=password_entered,
#       key="password_input",
#   )

#   if (
#       "password_correct" in st.session_state
#       and not st.session_state["password_correct"]
#   ):
#     st.error("パスワード間違っとる")

#   return False


# if not check_password():
#   st.stop()


# ---- 💾 データの永続保存（JSONファイル読み書き）機能 ----
PROJECTS_FILE = BASE_DIR / "projects.json"
FEEDBACKS_FILE = BASE_DIR / "feedbacks.json"
INVOICE_HIST_FILE = BASE_DIR / "invoice_history.json"


def load_data(file_path, default_data):
  if file_path.exists():
    try:
      with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return default_data
  return default_data


def save_data(file_path, data):
  with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)


# --- 初期状態（セッションステート）の初期化 ---
if "current_page" not in st.session_state:
  st.session_state.current_page = "ホーム"

if "theme_mode" not in st.session_state:
  st.session_state.theme_mode = "ライト"

# 現場データの読み込み
if "projects" not in st.session_state:
  default_projects = [
      {
          "id": 1,
          "site_name": "〇〇マンション 配管更新",
          "floor_count": 8,
          "timestamp": "2026-10-28 15:30",
          "tasks": [
              {
                  "task_id": 1,
                  "task_name": "配管保温材巻き",
                  "task_memo": "資材置き場は2階通路。",
                  "floors": {f"{i}階": False for i in range(1, 9)},
              }
          ],
      }
  ]
  st.session_state.projects = load_data(PROJECTS_FILE, default_projects)

if "feedbacks" not in st.session_state:
  default_feedbacks = [
      {
          "id": 1,
          "timestamp": "2026-10-28 16:00",
          "name": "現場スタッフ",
          "category": "機能改善リクエスト",
          "text": "階数の並びが綺麗になって見やすくなりました！",
          "status": "確認中",
      }
  ]
  st.session_state.feedbacks = load_data(FEEDBACKS_FILE, default_feedbacks)

if "invoice_history" not in st.session_state:
  raw_hist = load_data(INVOICE_HIST_FILE, [])
  restored_hist = []
  for item in raw_hist:
    pdf_b = b""
    if item.get("pdf_base64"):
      try:
        pdf_b = base64.b64decode(item["pdf_base64"].encode("utf-8"))
      except:
        pass
    elif isinstance(item.get("pdf_bytes"), bytes):
      pdf_b = item["pdf_bytes"]

    restored_hist.append({
        "id": item.get("id", 1),
        "timestamp": item.get("timestamp", ""),
        "invoice_no": item.get("invoice_no", ""),
        "client_name": item.get("client_name", ""),
        "issue_date": item.get("issue_date", ""),
        "total_amount": item.get("total_amount", 0),
        "pdf_bytes": pdf_b,
    })
  st.session_state.invoice_history = restored_hist


# --- 🎨 CSSの動的適用 ---
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

if st.session_state.theme_mode == "ダーク":
  theme_css = """
        .stApp {
            background-color: #0f172a !important;
            color: #f8fafc !important;
        }
        [data-testid="stSidebar"] {
            background-color: #1e293b !important;
        }
        .stButton>button {
            background-color: #334155 !important;
            color: #f8fafc !important;
            border: 1px solid #475569 !important;
        }
        .stButton>button:hover {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }
        .stTextInput input, .stSelectbox select, .stTextArea textarea {
            background-color: #1e293b !important;
            color: #f8fafc !important;
            border-color: #475569 !important;
        }
        [data-testid="stMetricValue"] {
            color: #38bdf8 !important;
        }
    """
else:
  theme_css = """
        .stApp {
            background-color: #f4f6f9;
            color: #0f172a;
        }
        [data-testid="stSidebar"] {
            background-color: #1e293b;
            color: white;
        }
        [data-testid="stSidebar"] .stButton>button {
            background-color: #334155;
            color: white;
            border: none;
        }
        [data-testid="stSidebar"] .stButton>button:hover {
            background-color: #3b82f6;
            color: white;
        }
        .stButton>button {
            border-radius: 10px;
            font-weight: 600;
            min-height: 44px;
        }
        [data-testid="stMetricValue"] {
            font-size: 22px;
            color: #1e3d59;
        }
    """

st.markdown(
    f"""
    <style>
    {mobile_constraint_css}
    {theme_css}
    button, input, select {{
        touch-action: manipulation;
    }}
    .stButton>button {{
        border-radius: 10px;
        font-weight: 600;
        min-height: 46px;
    }}
    .stTextInput input, .stSelectbox select, .stTextArea textarea {{
        border-radius: 8px !important;
        font-size: 16px !important;
    }}
    </style>
""",
    unsafe_allow_html=True,
)


def change_page(page_name):
  st.session_state.current_page = page_name


# --- サイドバー メニュー ---
st.sidebar.title("📌 メニュー")
st.sidebar.write("")
if st.sidebar.button("🏠 ホーム（トップ）", use_container_width=True):
  change_page("ホーム")
if st.sidebar.button("📝 業務内容共有（現場チェック）", use_container_width=True):
  change_page("業務内容共有")
if st.sidebar.button("📄 請求書作成＆履歴", use_container_width=True):
  change_page("請求書作成")

st.sidebar.divider()
st.sidebar.subheader("🌓 テーマ設定")
selected_theme = st.sidebar.radio(
    "表示モード",
    ["ライト", "ダーク"],
    index=0 if st.session_state.theme_mode == "ライト" else 1,
    key="theme_radio",
)
if selected_theme != st.session_state.theme_mode:
  st.session_state.theme_mode = selected_theme
  st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📱 表示レイアウト")
selected_mode = st.sidebar.radio(
    "レイアウト選択",
    ["自動（レスポンシブ）", "モバイルコンパクト風", "PCワイド風"],
    key="view_mode_select",
    label_visibility="collapsed",
)

st.sidebar.divider()
if st.sidebar.button("💡 意見・問い合わせ窓口", use_container_width=True):
  change_page("意見ボックス")

st.sidebar.caption("© 2026 尾崎ガス配管 業務管理システム")


# ==========================================
# 1. ホーム（トップ・ポータル画面）
# ==========================================
if st.session_state.current_page == "ホーム":
  st.title("👨‍🔧🪏 業務管理場へようこそ")
  st.write("毎日の業務管理、現場チェックリスト、および請求書発行ができるで。")

  st.divider()

  col1, col2 = st.columns(2)

  with col1:
    st.subheader("📝 業務内容共有")
    st.write("現場別・作業別の進捗チェック")
    if st.button("業務共有を開く", key="h_work", use_container_width=True):
      change_page("業務内容共有")
      st.rerun()

  with col2:
    st.subheader("📄 請求書作成")
    st.write("PDF作成＆過去履歴検索")
    if st.button("請求書を開く", key="h_rec", use_container_width=True):
      change_page("請求書作成")
      st.rerun()


# ==========================================
# 2. 業務内容共有（作業ごとの階数チェック＆配置型メモ）のページ
# ==========================================
elif st.session_state.current_page == "業務内容共有":
  st.title("📝 現場・作業別 階数チェックリスト")
  st.write("①現場と階数を作成 ➡ ②「＋」から作業を追加 ➡ ③チェックとメモを管理！")

  if "proj_form_id" not in st.session_state:
    st.session_state["proj_form_id"] = 0

  # ① 新規現場・階数の作成
  with st.expander("➕ 【新しい現場（フォルダ）の作成】", expanded=False):
    with st.form(
        key=f"new_proj_form_{st.session_state['proj_form_id']}",
        clear_on_submit=True,
    ):
      st.subheader("① 現場入力 ＋ 階数入力")
      new_site_name = st.text_input(
          "作業現場名（建物名など）", placeholder="例：〇〇マンション"
      )
      new_floor_count = st.number_input(
          "建物の階数（何階建てか）",
          min_value=1,
          max_value=50,
          value=3,
          step=1,
      )

      col_p1, col_p2 = st.columns(2)
      with col_p1:
        submit_proj = st.form_submit_button(
            "🏗️ 現場を作成する", use_container_width=True
        )
      with col_p2:
        reset_proj = st.form_submit_button(
            "🔄 入力リセット", use_container_width=True
        )

      if submit_proj:
        if new_site_name.strip() != "":
          now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
          new_id = (
              max([p["id"] for p in st.session_state.projects], default=0) + 1
          )

          # 階数は必ず「1階, 2階, 3階...」の順番で固定リストとして生成
          initial_floors = {f"{i}階": False for i in range(1, int(new_floor_count) + 1)}

          new_project = {
              "id": new_id,
              "site_name": new_site_name.strip(),
              "floor_count": int(new_floor_count),
              "timestamp": now_str,
              "tasks": [],
          }
          st.session_state.projects.insert(0, new_project)
          save_data(PROJECTS_FILE, st.session_state.projects)

          st.success(f"✅ 現場「{new_site_name}」（{new_floor_count}階建て）を作成しました！")
          st.session_state["proj_form_id"] += 1
          st.rerun()
        else:
          st.error("現場名を入力してください。")
      elif reset_proj:
        st.session_state["proj_form_id"] += 1
        st.rerun()

  st.divider()

  st.subheader("📋 現場フォルダ一覧")

  if not st.session_state.projects:
    st.info("登録されている現場はありません。上の「新しい現場（フォルダ）の作成」から追加してください。")
  else:
    for proj in st.session_state.projects:
      with st.container():
        st.markdown(
            f"### 【現場】 {proj['site_name']} （全 {proj['floor_count']} 階）"
        )
        st.caption(f"🕒 作成日時: {proj['timestamp']}")

        # ── 💡 修正点：階数を数値順（1階, 2階, 3階...）に必ずソートして正確に並べる ──
        floor_count_val = int(proj.get("floor_count", 3))
        floors = [f"{i}階" for i in range(1, floor_count_val + 1)]

        # ② 作業を追加する「＋」ボタン（エクスパンダー）
        with st.expander(
            f"➕ 作業内容を追加する（{proj['site_name']}）", expanded=False
        ):
          task_form_key = f"task_form_{proj['id']}"
          with st.form(key=task_form_key, clear_on_submit=True):
            st.subheader("② 作業内容とメモの記入")
            new_task_name = st.text_input(
                "作業名", placeholder="例：配管保温材巻き、水圧検査 など"
            )
            new_task_memo = st.text_area(
                "作業全体のメモ（初期メモ）", placeholder="この作業に関するメモ・特記事項を入力..."
            )

            add_task_btn = st.form_submit_button(
                "➕ 作業を登録する", use_container_width=True
            )

            if add_task_btn:
              if new_task_name.strip() != "":
                initial_floors_checked = {f: False for f in floors}
                new_task_id = (
                    max([t["task_id"] for t in proj["tasks"]], default=0) + 1
                    if proj["tasks"]
                    else 1
                )

                new_task = {
                    "task_id": new_task_id,
                    "task_name": new_task_name.strip(),
                    "task_memo": new_task_memo.strip(),
                    "floors": initial_floors_checked,
                }
                proj["tasks"].append(new_task)
                save_data(PROJECTS_FILE, st.session_state.projects)

                st.success(f"✅ 作業「{new_task_name}」を追加しました！")
                st.rerun()
              else:
                st.error("作業名を入力してください。")

        # ③ 作業ごとに、チェックリスト ➡ メモ ➡ 区切り線 ➡ まるごと削除ボタン
        if proj["tasks"]:
          st.write("#### 🛠️ 登録された作業一覧（チェックリスト）")
          for task in proj["tasks"]:
            with st.container():
              col_t1, col_t2 = st.columns([3, 1])
              with col_t1:
                st.markdown(f"###  作業名: {task['task_name']}")
              with col_t2:
                if st.button("🗑️ 作業削除", key=f"del_task_{proj['id']}_{task['task_id']}"):
                  proj["tasks"] = [
                      t for t in proj["tasks"] if t["task_id"] != task["task_id"]
                  ]
                  save_data(PROJECTS_FILE, st.session_state.projects)
                  st.success("作業を削除しました。")
                  st.rerun()

              # 互換性対策
              if "floors" not in task:
                old_floor_data = task.get("floor_data", {})
                task["floors"] = {
                    f: old_floor_data.get(f, {}).get("checked", False) for f in floors
                }

              # 1. 各階の完了チェック（スマホでも見やすいように4列グリッドに調整）
              st.write("##### 各階の完了チェック：")
              
              # 4列ずつ綺麗に並べるようにループ処理を修正
              cols_per_row = 4
              for i in range(0, len(floors), cols_per_row):
                row_floors = floors[i : i + cols_per_row]
                chk_cols = st.columns(len(row_floors))
                for idx, floor in enumerate(row_floors):
                  with chk_cols[idx]:
                    current_chk = task["floors"].get(floor, False)
                    new_chk = st.checkbox(
                        f"{floor}",
                        value=current_chk,
                        key=f"chk_{proj['id']}_{task['task_id']}_{floor}",
                    )
                    if new_chk != current_chk:
                      task["floors"][floor] = new_chk
                      save_data(PROJECTS_FILE, st.session_state.projects)
                      st.rerun()

              st.write("")  # 余白

              # 2. 作業メモ機能
              current_memo = task.get("task_memo", "")
              updated_memo = st.text_area(
                  "📝 作業メモ（備考・特記事項）",
                  value=current_memo,
                  placeholder="この作業に関するメモや特記事項を入力・修正できます...",
                  key=f"memo_input_{proj['id']}_{task['task_id']}",
                  height=100,
              )

              if updated_memo != current_memo:
                task["task_memo"] = updated_memo
                save_data(PROJECTS_FILE, st.session_state.projects)

              st.markdown("---")
        else:
          st.info("この現場にはまだ作業が登録されていません。「作業内容を追加する」から登録してください。")

        # 3. 現場フォルダ全体の丸ごと削除ボタン
        if st.button("🗑️ この現場を丸ごと削除", key=f"del_proj_{proj['id']}"):
          st.session_state.projects = [
              p for p in st.session_state.projects if p["id"] != proj["id"]
          ]
          save_data(PROJECTS_FILE, st.session_state.projects)
          st.success("現場フォルダを削除しました。")
          st.rerun()

        st.divider()


# ==========================================
# 3. 請求書作成＆履歴ダウンロードのページ
# ==========================================
elif st.session_state.current_page == "請求書作成":
  st.title("📄 請求書作成 ＆ 発行履歴")

  tab1, tab2 = st.tabs(["📝 請求書新規作成", "🔍 発行履歴・検索"])

  FONT_NAME_G = "IPAexGothic"
  FONT_NAME_M = "IPAexMincho"

  with tab1:
    with st.expander("📌 宛名・発行者情報の編集", expanded=True):
      col1, col2 = st.columns(2)
      with col1:
        client_name = st.text_input("宛名", placeholder="例：伊丹産業電設(株) 御中")
        selected_d = st.date_input("発行日を選択", value=date.today())
        issue_date = f"{selected_d.year}年 {selected_d.month}月 {selected_d.day}日"
        st.caption(f"📌 設定される発行日: **{issue_date}**")

      with col2:
        invoice_no = st.text_input("請求書番号 (No.)", placeholder="例：1")
        registration_no = st.text_input("登録番号", value="T1810824577403")

      st.divider()
      col3, col4 = st.columns(2)
      with col3:
        issuer_name = st.text_input("発行者（屋号・会社名）", value="尾崎ガス配管")
        issuer_postal = st.text_input("郵便番号", value="〒583-0863")
      with col4:
        issuer_address = st.text_input(
            "住所", value="大阪府羽曳野市蔵之内342-1"
        )
        issuer_tel = st.text_input("TEL・FAX", "072-956-5292")

    st.subheader("明細行の入力")

    initial_rows = [
        {"項目": "テスト", "オーダー番号": "B682708", "金額": 246000},
        {"項目": "テスト２", "オーダー番号": "B683688", "金額": 82000},
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
        c.drawString(x + offset, y + offset, text)

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
      c.drawString(
          45, height - 115, "下記の通りご請求申し上げますので、ご照会の上"
      )
      c.drawString(
          45, height - 130, "お支払いくださいますようお願い申し上げます。"
      )
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
      c.drawString(455, height - 145, f"{registration_no}")

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

    col_p1, col_p2 = st.columns([2, 1])
    with col_p1:
      st.subheader("📄 請求書プレビュー")
    with col_p2:
      show_preview = st.toggle("プレビューを表示する", value=False)

    if show_preview:
      base64_pdf = base64.b64encode(pdf_buffer.getvalue()).decode("utf-8")
      pdf_display = (
          f'<iframe src="data:application/pdf;base64,{base64_pdf}"'
          ' width="100%" height="600px" type="application/pdf"></iframe>'
      )
      st.markdown(pdf_display, unsafe_allow_html=True)

    pdf_bytes = pdf_buffer.getvalue()

    def record_download():
      new_hist = {
          "id": len(st.session_state.invoice_history) + 1,
          "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
          "invoice_no": invoice_no,
          "client_name": client_name,
          "issue_date": issue_date,
          "total_amount": total_amount_inc,
          "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
      }
      st.session_state.invoice_history.insert(0, new_hist)

      save_data(
          INVOICE_HIST_FILE,
          [
              {
                  "id": h.get("id", 1),
                  "timestamp": h.get("timestamp", ""),
                  "invoice_no": h.get("invoice_no", ""),
                  "client_name": h.get("client_name", ""),
                  "issue_date": h.get("issue_date", ""),
                  "total_amount": h.get("total_amount", 0),
                  "pdf_base64": (
                      base64.b64encode(h.get("pdf_bytes")).decode("utf-8")
                      if isinstance(h.get("pdf_bytes"), bytes)
                      else h.get("pdf_base64", "")
                  ),
              }
              for h in st.session_state.invoice_history
          ],
      )

    st.download_button(
        label="📥 請求書PDFをダウンロード（履歴に自動保存）",
        data=pdf_bytes,
        file_name=f"請求書_{invoice_no}_{client_name.replace(' ', '')}.pdf",
        mime="application/pdf",
        use_container_width=True,
        on_click=record_download,
    )

  with tab2:
    st.subheader(
        "🔍 過去に作成・ダウンロードした請求書の検索・再ダウンロード"
    )

    search_kw = st.text_input(
        "宛名・請求書No.・作成日時で検索",
        placeholder="例: 伊丹産業、No.1、2026-10...",
    )

    hist_list = st.session_state.invoice_history

    if search_kw.strip() != "":
      kw = search_kw.strip().lower()
      hist_list = [
          h
          for h in hist_list
          if kw in h.get("client_name", "").lower()
          or kw in str(h.get("invoice_no", "")).lower()
          or kw in h.get("timestamp", "").lower()
          or kw in h.get("issue_date", "").lower()
      ]

    if hist_list:
      for item in hist_list:
        with st.container():
          c_h1, c_h2, c_h3 = st.columns([2, 2, 1])
          with c_h1:
            st.markdown(
                f"**No.{item.get('invoice_no', '')}  {item.get('client_name', '')}**"
            )
            st.caption(
                f"発行日: {item.get('issue_date', '')} | ダウンロード日時:"
                f" {item.get('timestamp', '')}"
            )
          with c_h2:
            st.metric("請求額（税込）", f"¥{item.get('total_amount', 0):,}")
          with c_h3:
            st.download_button(
                label="再ダウンロード",
                data=item.get("pdf_bytes", b""),
                file_name=(
                    f"請求書_No{item.get('invoice_no', '1')}_{item.get('client_name', 'client')}.pdf"
                ),
                mime="application/pdf",
                key=f"dl_hist_{item.get('id', 0)}",
            )
        st.divider()
    else:
      st.info("ダウンロード履歴はまだありません。")


# ==========================================
# 4. 意見ボックス（問い合わせ窓口）のページ
# ==========================================
elif st.session_state.current_page == "意見ボックス":
  st.title("💡 意見ボックス・社内問い合わせ窓口")
  st.write(
      "システムの改善要望、不具合報告、現場からの意見や質問を匿名・実名で投稿できます。（投稿内容は保存されます）"
  )

  with st.expander("✍️ 意見・問い合わせを投稿する", expanded=True):
    with st.form(key="feedback_form", clear_on_submit=True):
      f_name = st.text_input(
          "お名前（空欄の場合は「匿名」になります）",
          placeholder="例: 尾崎、スタッフA",
      )
      f_cat = st.selectbox(
          "分類",
          [
              "機能改善リクエスト",
              "不具合・エラー報告",
              "現場からの意見・質問",
              "その他",
          ],
      )
      f_text = st.text_area(
          "ご意見・内容の詳細",
          placeholder=(
              "困っていることや「こうなったら便利！」と思うことを自由に書いてな..."
          ),
      )

      fb_submit = st.form_submit_button(
          "🚀 意見を送信する", use_container_width=True
      )

      if fb_submit:
        if f_text.strip() != "":
          now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
          new_fb = {
              "id": len(st.session_state.feedbacks) + 1,
              "timestamp": now_str,
              "name": f_name.strip() if f_name.strip() else "匿名",
              "category": f_cat,
              "text": f_text,
              "status": "受付済み",
          }
          st.session_state.feedbacks.insert(0, new_fb)
          save_data(FEEDBACKS_FILE, st.session_state.feedbacks)

          st.success("ご意見・問い合わせを送信しました！ありがとうございます。")
          st.rerun()
        else:
          st.error("内容を入力してください。")

  st.divider()

  st.subheader("📋 送信された意見・問い合わせ一覧")
  for fb in st.session_state.feedbacks:
    with st.container():
      col_fb1, col_fb2 = st.columns([3, 1])
      with col_fb1:
        st.markdown(
            f"**【{fb.get('category', '')}】** （投稿者: {fb.get('name', '匿名')}）"
        )
        st.caption(f"🕒 投稿日時: {fb.get('timestamp', '')}")
        st.write(fb.get("text", ""))
      with col_fb2:
        st.info(f"ステータス: {fb.get('status', '受付済み')}")
    st.divider()