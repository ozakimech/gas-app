import base64
import calendar
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
def check_password():
  def password_entered():
    if st.session_state["password_input"] == "ozagas":
      st.session_state["password_correct"] = True
      del st.session_state["password_input"]
    else:
      st.session_state["password_correct"] = False

  if st.session_state.get("password_correct", False):
    return True

  st.title("🔒 ログイン")
  st.text_input(
      "パスワードを入力せなあかん",
      type="password",
      on_change=password_entered,
      key="password_input",
  )

  if (
      "password_correct" in st.session_state
      and not st.session_state["password_correct"]
  ):
    st.error("パスワード間違っとる")

  return False


if not check_password():
  st.stop()


# ---- 💾 データの永続保存（JSONファイル読み書き）機能 ----
REPORTS_FILE = BASE_DIR / "reports.json"
FEEDBACKS_FILE = BASE_DIR / "feedbacks.json"


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

if "invoice_history" not in st.session_state:
  st.session_state.invoice_history = []

# ファイルからデータを復元（無ければ初期値）
if "reports" not in st.session_state:
  default_reports = [
      {
          "id": 1,
          "timestamp": "2026-10-28 15:30",
          "staff": "尾崎",
          "category": "現場作業",
          "text": (
              "本日午前中の配管交換作業が無事完了しました。漏れテストもクリアしています。"
          ),
          "image": None,
      }
  ]
  st.session_state.reports = load_data(REPORTS_FILE, default_reports)

if "feedbacks" not in st.session_state:
  default_feedbacks = [
      {
          "id": 1,
          "timestamp": "2026-10-28 16:00",
          "name": "現場スタッフ",
          "category": "機能改善リクエスト",
          "text": (
              "スマホから写真アップロードするときの速度がもう少し速くなると嬉しいです！"
          ),
          "status": "確認中",
      }
  ]
  st.session_state.feedbacks = load_data(FEEDBACKS_FILE, default_feedbacks)


# --- 🎨 CSSの動的適用（波括弧のエスケープも最適化） ---
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
if st.sidebar.button("📝 業務内容共有", use_container_width=True):
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

# 👇 メニュー・サブメニューの一番下に問い合わせ窓口を配置
st.sidebar.divider()
if st.sidebar.button("💡 意見・問い合わせ窓口", use_container_width=True):
  change_page("意見ボックス")

st.sidebar.caption("© 2026 尾崎ガス配管 業務管理システム")


# ==========================================
# 1. ホーム（トップ・ポータル画面）
# ==========================================
if st.session_state.current_page == "ホーム":
  st.title("👨‍🔧🪏 業務管理場へようこそ")
  st.write("毎日の業務管理、情報共有、および請求書発行ができるで。")

  st.divider()

  col1, col2 = st.columns(2)

  with col1:
    st.subheader("📝 業務内容共有")
    st.write("現場写真や日報の共有・確認")
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
# 2. 業務内容共有のページ
# ==========================================
elif st.session_state.current_page == "業務内容共有":
  st.title("📝 業務内容共有（タイムライン）")
  st.write(
      "日々の作業内容や現場写真を投稿・共有できます。（投稿内容は永続保存されます）"
  )

  if "form_id" not in st.session_state:
    st.session_state["form_id"] = 0

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
            "作業種別", ["現場作業", "定期点検", "打ち合わせ", "緊急対応", "その他"]
        )

      report_body = st.text_area(
          "報告内容・詳細", placeholder="作業の進捗状態、現場の状況などを入力..."
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
          new_id = (
              max([r["id"] for r in st.session_state.reports], default=0) + 1
          )

          new_rep = {
              "id": new_id,
              "timestamp": now_str,
              "staff": reporter_name if reporter_name.strip() else "尾崎",
              "category": report_cat,
              "text": report_body,
              "image": None,
          }
          st.session_state.reports.insert(0, new_rep)

          # 💾 ファイルに保存！
          save_data(REPORTS_FILE, st.session_state.reports)

          st.success("業務報告を投稿したよ！（保存されました）")
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
      "🔍 キーワード検索", placeholder="例：尾崎、現場作業、配管 など..."
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

  if filtered_reports:
    for rep in filtered_reports:
      with st.container():
        st.markdown(
            f"### 🏷️ 【{rep['category']}】 {rep['staff']} スタッフ"
        )
        st.caption(f"🕒 投稿日時: {rep['timestamp']}")
        st.write(rep["text"])
        st.divider()
  else:
    st.info("該当する投稿が見つかりませんでした。")


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
          "pdf_bytes": pdf_bytes,
      }
      st.session_state.invoice_history.insert(0, new_hist)

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
          if kw in h["client_name"].lower()
          or kw in str(h["invoice_no"]).lower()
          or kw in h["timestamp"].lower()
          or kw in h["issue_date"].lower()
      ]

    if hist_list:
      for item in hist_list:
        with st.container():
          c_h1, c_h2, c_h3 = st.columns([2, 2, 1])
          with c_h1:
            st.markdown(
                f"**No.{item['invoice_no']}  {item['client_name']}**"
            )
            st.caption(
                f"発行日: {item['issue_date']} | ダウンロード日時:"
                f" {item['timestamp']}"
            )
          with c_h2:
            st.metric("請求額（税込）", f"¥{item['total_amount']:,}")
          with c_h3:
            st.download_button(
                label="再ダウンロード",
                data=item["pdf_bytes"],
                file_name=(
                    f"請求書_No{item['invoice_no']}_{item['client_name']}.pdf"
                ),
                mime="application/pdf",
                key=f"dl_hist_{item['id']}",
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

          # 💾 ファイルに保存！
          save_data(FEEDBACKS_FILE, st.session_state.feedbacks)

          st.success(
              "ご意見・問い合わせを送信しました！ありがとうございます。（保存されました）"
          )
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
            f"**【{fb['category']}】** （投稿者: {fb['name']}）"
        )
        st.caption(f"🕒 投稿日時: {fb['timestamp']}")
        st.write(fb["text"])
      with col_fb2:
        st.info(f"ステータス: {fb['status']}")
    st.divider()
