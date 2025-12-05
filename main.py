import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime
import calendar
import jpholiday
import re

# --- 1. ページ設定 ---
st.set_page_config(page_title="店舗記録ログ", layout="centered")

# --- 2. デザイン ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    .block-container { padding-top: 2rem; padding-bottom: 5rem; max_width: 600px; }

    /* カレンダーリスト行 */
    .cal-list-row {
        display: flex; align-items: stretch; border-bottom: 1px solid #333; padding: 8px 0; min-height: 60px;
    }
    .cal-date-box {
        width: 50px; display: flex; flex-direction: column; align-items: center; justify-content: center;
        margin-right: 15px; border-right: 1px solid #333; padding-right: 10px;
    }
    .date-num { font-size: 20px; font-weight: bold; line-height: 1; }
    .date-week { font-size: 12px; font-weight: bold; }
    
    .day-sat { color: #4da6ff; }
    .day-sun { color: #ff6666; }
    .day-hol { color: #ff6666; }
    .day-wkd { color: #ddd; }
    
    .cal-info-box { flex-grow: 1; display: flex; flex-direction: column; justify-content: center; }
    .cal-store-name { font-size: 15px; font-weight: bold; color: #eee; margin-bottom: 2px; }
    .cal-store-sub { font-size: 12px; color: #aaa; }
    
    .row-today { background-color: rgba(77, 166, 255, 0.1); border-left: 3px solid #4da6ff; }

    /* 日次詳細カード */
    .day-card {
        background-color: #1f2933; border: 1px solid #444; border-radius: 6px;
        padding: 15px; margin-bottom: 15px; display: flex; flex-direction: column; gap: 5px;
    }
    .day-card-store { font-size: 16px; font-weight: bold; color: #4da6ff; }
    .day-card-info { font-size: 13px; color: #ddd; }

    /* ヘッダー類 */
    .store-header { font-size: 24px; font-weight: bold; color: #fff; border-bottom: 2px solid #4da6ff; padding-bottom: 10px; margin-bottom: 5px; }
    .store-sub-header { font-size: 14px; color: #aaa; margin-bottom: 20px; display: flex; gap: 15px; align-items: center; }
    .rating-star { color: #ffd700; font-weight: bold; }
    
    .section-title { font-size: 14px; font-weight: bold; color: #666; margin-top: 40px; margin-bottom: 5px; border-bottom: 1px solid #333; padding-bottom: 2px; }
    
    /* 訪問履歴行 */
    .visit-row-container { border-bottom: 1px solid #333; padding: 12px 0; }
    .visit-date { font-size: 14px; font-weight: bold; color: #8ab4f8; display: inline-block; margin-bottom: 4px; }
    .visit-time { font-size: 11px; color: #bbb; margin-left: 10px; }
    
    .cal-header { text-align: center; font-weight: bold; font-size: 12px; margin-bottom: 5px; color: #aaa; }

    /* フォーム */
    .stTextInput input, .stDateInput input, .stTextArea textarea, .stMultiSelect div[data-baseweb="select"], .stTimeInput input {
        color: #e0e0e0 !important; background-color: #1f2933 !important; border: 1px solid #444 !important;
    }
    .stTextInput label, .stDateInput label, .stTextArea label, .stMultiSelect label, .stTimeInput label, .stSlider label { color: #bbb !important; }
    .stMultiSelect span[data-baseweb="tag"] { background-color: #4da6ff !important; color: #0e1117 !important; }
    
    /* ボタン */
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #1f77b4 !important; color: white !important; border: none !important; font-weight: bold; width: 100%;
    }
    .list-btn-box button {
        text-align: left !important; border: none !important; border-bottom: 1px solid #333 !important; background: transparent !important;
    }
    div[data-testid="stButton"] button[kind="secondary"] {
         background-color: #262730 !important; color: #e0e0e0 !important; border: 1px solid #555 !important;
         width: 100%;
    }
    
    [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] { border: none; }
    </style>
""", unsafe_allow_html=True)

# --- 3. データベース接続 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- データ操作 ---
@st.cache_data(ttl=60)
def get_visits_data():
    try:
        df = conn.read(worksheet="visits", ttl=0)
        df = df.fillna("")
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        # 新しいカラムの型変換 (ない場合は初期値)
        if 'rating' not in df.columns: df['rating'] = 0
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0).astype(int)
        return df
    except:
        # カラム定義を更新
        return pd.DataFrame(columns=['id', 'store_name', 'visit_date', 'visit_time', 'start_time', 'end_time', 'rating', 'members', 'sv_members', 'count_area', 'notices', 'memo', 'record_memo'])

@st.cache_data(ttl=60)
def get_stores_data():
    try:
        df = conn.read(worksheet="stores", ttl=0)
        df = df.fillna("")
        return df
    except:
        return pd.DataFrame(columns=['store_name', 'notices', 'memo'])

@st.cache_data(ttl=60)
def get_employees_list():
    try:
        df = conn.read(worksheet="employees", ttl=0)
        if df.empty or 'name' not in df.columns: return []
        return sorted(df['name'].dropna().unique().tolist())
    except: return []

def clear_all_cache():
    get_visits_data.clear()
    get_stores_data.clear()
    get_employees_list.clear()

def add_visit_data(data):
    try:
        df = conn.read(worksheet="visits", ttl=0)
        df = df.fillna("")
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
    except:
        df = pd.DataFrame(columns=['id', 'store_name', 'visit_date', 'visit_time', 'start_time', 'end_time', 'rating', 'members', 'sv_members', 'count_area', 'notices', 'memo', 'record_memo'])

    new_id = df['id'].max() + 1 if not df.empty and 'id' in df.columns else 1
    data['id'] = new_id
    
    new_row = pd.DataFrame([data])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="visits", data=updated_df)
    clear_all_cache()

def update_visit_data(record_id, updated_data):
    with st.spinner("更新中..."):
        try:
            df = conn.read(worksheet="visits", ttl=0)
            df = df.fillna("")
            df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
            
            if not df.empty and record_id in df['id'].values:
                idx = df.index[df['id'] == record_id][0]
                for key, value in updated_data.items():
                    df.at[idx, key] = value
                conn.update(worksheet="visits", data=df)
                clear_all_cache()
        except: pass

def delete_visit_data(record_id):
    with st.spinner("削除中..."):
        df = conn.read(worksheet="visits", ttl=0)
        df = df.fillna("")
        df['id'] = pd.to_numeric(df['id'], errors='coerce').fillna(0).astype(int)
        if not df.empty:
            updated_df = df[df['id'] != record_id]
            conn.update(worksheet="visits", data=updated_df)
            clear_all_cache()

def register_new_store(store_name, notices, memo):
    try:
        df = conn.read(worksheet="stores", ttl=0)
        df = df.fillna("")
    except:
        df = pd.DataFrame(columns=['store_name', 'notices', 'memo'])
        
    if not df.empty and store_name in df['store_name'].values: return False
    new_row = pd.DataFrame([{"store_name": store_name, "notices": notices, "memo": memo}])
    updated_df = pd.concat([df, new_row], ignore_index=True)
    conn.update(worksheet="stores", data=updated_df)
    clear_all_cache()
    return True

def update_store_info(store_name, new_notices, new_memo):
    with st.spinner("更新中..."):
        try:
            df = conn.read(worksheet="stores", ttl=0)
            df = df.fillna("")
        except: return

        if not df.empty and store_name in df['store_name'].values:
            df.loc[df['store_name'] == store_name, 'notices'] = new_notices
            df.loc[df['store_name'] == store_name, 'memo'] = new_memo
            conn.update(worksheet="stores", data=df)
            clear_all_cache()
        else:
            register_new_store(store_name, new_notices, new_memo)

def check_and_add_employees(names_list):
    if not names_list: return 0
    try:
        df = conn.read(worksheet="employees", ttl=0)
    except: df = pd.DataFrame(columns=['name'])
    curr = df['name'].tolist() if not df.empty and 'name' in df.columns else []
    news = [n for n in names_list if n not in curr]
    if news:
        new_rows = pd.DataFrame([{'name': n} for n in news])
        updated_df = pd.concat([df, new_rows], ignore_index=True)
        conn.update(worksheet="employees", data=updated_df)
        clear_all_cache()
        return len(news)
    return 0

# --- 4. セッション管理 ---
if 'selected_store' not in st.session_state:
    st.session_state.selected_store = None
if 'cal_view_mode' not in st.session_state:
    st.session_state.cal_view_mode = 'month'
if 'cal_selected_date' not in st.session_state:
    st.session_state.cal_selected_date = datetime.date.today()
if 'cal_year' not in st.session_state:
    st.session_state.cal_year = datetime.date.today().year
if 'cal_month' not in st.session_state:
    st.session_state.cal_month = datetime.date.today().month
if 'edit_record_id' not in st.session_state:
    st.session_state.edit_record_id = None
if 'search_add_mode' not in st.session_state:
    st.session_state.search_add_mode = False

def navigate_to(store_name=None):
    if store_name: st.session_state.selected_store = store_name

def change_cal_month(amount):
    m = st.session_state.cal_month + amount
    y = st.session_state.cal_year
    if m > 12: m = 1; y += 1
    elif m < 1: m = 12; y -= 1
    st.session_state.cal_month = m
    st.session_state.cal_year = y

# --- 5. UIコンポーネント ---
def member_selector(label, key_suffix, default_vals=None):
    st.markdown(f"<label style='font-size:14px; color:#bbb;'>{label}</label>", unsafe_allow_html=True)
    employees = get_employees_list()
    
    def_selected = []
    if default_vals:
        def_selected = [n.strip() for n in default_vals.split(',') if n.strip() in employees]

    selected = st.multiselect("メンバーを選択", options=employees, default=def_selected, placeholder="名前を検索...", label_visibility="collapsed", key=f"ms_{key_suffix}")
    st.caption("リストにない人は↓に入力 (改行区切り)。保存時に自動追加されます。")
    new_members_text = st.text_area("新規追加", placeholder="例:\n佐藤\n高橋", label_visibility="collapsed", height=60, key=f"new_{key_suffix}")
    return selected, new_members_text

def render_add_visit_screen(store, back_callback, mode_prefix="default"):
    c1, c2 = st.columns([0.3, 0.7])
    if c1.button("◀ キャンセル", type="secondary", key=f"cncl_{mode_prefix}"):
        back_callback()
    
    st.markdown(f'<div class="store-header">記録の追加</div>', unsafe_allow_html=True)
    st.caption(f"店舗: {store}")
    
    c_d, _ = st.columns([0.5, 0.5])
    new_date = c_d.date_input("日付", value=datetime.date.today(), key=f"date_add_{mode_prefix}")
    
    # ★ 時間入力 (開始〜終了)
    st.markdown("<label style='font-size:14px; color:#bbb;'>時間 (開始 〜 終了)</label>", unsafe_allow_html=True)
    c_t1, c_t2 = st.columns(2)
    start_t = c_t1.time_input("開始", value=None, key=f"time_s_{mode_prefix}", label_visibility="collapsed")
    end_t = c_t2.time_input("終了", value=None, key=f"time_e_{mode_prefix}", label_visibility="collapsed")
    
    # ★ 評価 (1-5)
    st.markdown("<label style='font-size:14px; color:#bbb;'>評価 (1-5)</label>", unsafe_allow_html=True)
    rating_val = st.slider("評価", 1, 5, 3, key=f"rate_{mode_prefix}", label_visibility="collapsed")
    
    st.write("")
    sel_sv, txt_sv = member_selector("SV", f"sv_{mode_prefix}")
    st.write("")
    sel_mems, txt_mems = member_selector("メンバー", f"mem_{mode_prefix}")
    
    st.markdown("<label style='font-size:14px; color:#bbb;'>アサイン</label>", unsafe_allow_html=True)
    new_area = st.text_input("アサイン", placeholder="例: 1Fフロア", label_visibility="collapsed", key=f"area_{mode_prefix}")
    
    st.markdown("<label style='font-size:14px; color:#bbb;'>記録メモ</label>", unsafe_allow_html=True)
    new_rec_memo = st.text_area("記録メモ", placeholder="その日の特記事項など", label_visibility="collapsed", height=80, key=f"rec_memo_{mode_prefix}")
    
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    
    if st.button("保存して戻る", type="primary", key=f"save_btn_{mode_prefix}", use_container_width=True):
        with st.spinner("保存処理中..."):
            d_str = new_date.strftime("%Y-%m-%d") if new_date else ""
            # 時間の文字列化
            s_time_str = start_t.strftime("%H:%M") if start_t else ""
            e_time_str = end_t.strftime("%H:%M") if end_t else ""
            
            sv_manual = [n.strip() for n in txt_sv.splitlines() if n.strip()]
            final_sv = list(set(sel_sv + sv_manual))
            check_and_add_employees(sv_manual)
            
            mem_manual = [n.strip() for n in txt_mems.splitlines() if n.strip()]
            final_mem = list(set(sel_mems + mem_manual))
            check_and_add_employees(mem_manual)
            
            new_data = {
                "store_name": store, "visit_date": d_str, "visit_time": "", # visit_timeは互換用
                "start_time": s_time_str, "end_time": e_time_str,
                "rating": rating_val,
                "sv_members": ", ".join(final_sv),
                "members": ", ".join(final_mem), 
                "count_area": new_area,
                "record_memo": new_rec_memo,
                "notices": "", "memo": "" 
            }
            add_visit_data(new_data)
            st.success("追加しました")
            back_callback()
            st.rerun()

def render_edit_visit_screen(record_id, store, back_callback, mode_prefix="edit"):
    df = get_visits_data()
    record = df[df['id'] == record_id].iloc[0]
    
    c1, c2 = st.columns([0.3, 0.7])
    if c1.button("◀ キャンセル", type="secondary", key=f"cncl_edit_{mode_prefix}"):
        back_callback()
    
    st.markdown(f'<div class="store-header">記録の編集</div>', unsafe_allow_html=True)
    st.caption(f"店舗: {store}")

    init_date = None
    if record['visit_date']:
        try: init_date = datetime.datetime.strptime(record['visit_date'], "%Y-%m-%d").date()
        except: pass
    
    # 時間の初期値
    init_s_time = None
    init_e_time = None
    if 'start_time' in record and record['start_time']:
        try: init_s_time = datetime.datetime.strptime(record['start_time'], "%H:%M").time()
        except: pass
    if 'end_time' in record and record['end_time']:
        try: init_e_time = datetime.datetime.strptime(record['end_time'], "%H:%M").time()
        except: pass
        
    # 評価の初期値
    init_rating = int(record.get('rating', 3))
    if init_rating < 1: init_rating = 1
    if init_rating > 5: init_rating = 5

    c_d, _ = st.columns([0.5, 0.5])
    new_date = c_d.date_input("日付", value=init_date, key=f"date_edit_{mode_prefix}_{record_id}")
    
    st.markdown("<label style='font-size:14px; color:#bbb;'>時間 (開始 〜 終了)</label>", unsafe_allow_html=True)
    c_t1, c_t2 = st.columns(2)
    start_t = c_t1.time_input("開始", value=init_s_time, key=f"time_s_edit_{mode_prefix}_{record_id}", label_visibility="collapsed")
    end_t = c_t2.time_input("終了", value=init_e_time, key=f"time_e_edit_{mode_prefix}_{record_id}", label_visibility="collapsed")
    
    st.markdown("<label style='font-size:14px; color:#bbb;'>評価 (1-5)</label>", unsafe_allow_html=True)
    rating_val = st.slider("評価", 1, 5, init_rating, key=f"rate_edit_{mode_prefix}_{record_id}", label_visibility="collapsed")

    init_sv = record.get('sv_members', '')
    init_mem = record.get('members', '')
    
    sel_sv, txt_sv = member_selector("SV", f"sv_edit_{mode_prefix}_{record_id}", default_vals=init_sv)
    st.write("")
    sel_mems, txt_mems = member_selector("メンバー", f"mem_edit_{mode_prefix}_{record_id}", default_vals=init_mem)
    
    st.markdown("<label style='font-size:14px; color:#bbb;'>アサイン</label>", unsafe_allow_html=True)
    new_area = st.text_input("アサイン", value=record.get('count_area', ''), label_visibility="collapsed", key=f"area_edit_{mode_prefix}_{record_id}")
    
    st.markdown("<label style='font-size:14px; color:#bbb;'>記録メモ</label>", unsafe_allow_html=True)
    new_rec_memo = st.text_area("記録メモ", value=record.get('record_memo', ''), label_visibility="collapsed", height=80, key=f"rec_memo_edit_{mode_prefix}_{record_id}")
    
    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    
    if st.button("更新して戻る", type="primary", key=f"upd_btn_{mode_prefix}_{record_id}", use_container_width=True):
        with st.spinner("更新処理中..."):
            d_str = new_date.strftime("%Y-%m-%d") if new_date else ""
            s_time_str = start_t.strftime("%H:%M") if start_t else ""
            e_time_str = end_t.strftime("%H:%M") if end_t else ""
            
            sv_manual = [n.strip() for n in txt_sv.splitlines() if n.strip()]
            final_sv = list(set(sel_sv + sv_manual))
            check_and_add_employees(sv_manual)
            
            mem_manual = [n.strip() for n in txt_mems.splitlines() if n.strip()]
            final_mem = list(set(sel_mems + mem_manual))
            check_and_add_employees(mem_manual)
            
            updated_data = {
                "visit_date": d_str,
                "start_time": s_time_str,
                "end_time": e_time_str,
                "rating": rating_val,
                "sv_members": ", ".join(final_sv),
                "members": ", ".join(final_mem),
                "count_area": new_area,
                "record_memo": new_rec_memo
            }
            update_visit_data(record_id, updated_data)
            st.success("更新しました")
            back_callback()
            st.rerun()

def render_store_detail_content(store, back_callback, add_callback, mode_prefix="default"):
    if st.session_state.edit_record_id:
        def close_edit():
            st.session_state.edit_record_id = None
            st.rerun()
        render_edit_visit_screen(st.session_state.edit_record_id, store, close_edit, mode_prefix)
        return

    c_back, _ = st.columns([0.25, 0.75])
    if c_back.button("◀ 戻る", type="secondary", key=f"back_{mode_prefix}"):
        back_callback()
    
    # ★ 店舗ヘッダーと平均評価
    visits_df = get_visits_data()
    stores_df = get_stores_data()
    store_visits = visits_df[visits_df['store_name'] == store].sort_values(by='visit_date', ascending=False)
    
    # 平均評価の計算
    avg_rating = 0.0
    valid_ratings = store_visits[store_visits['rating'] > 0]['rating']
    if not valid_ratings.empty:
        avg_rating = valid_ratings.mean()
    
    st.markdown(f'<div class="store-header">{store}</div>', unsafe_allow_html=True)
    
    # 評価表示
    star_str = "★" * int(round(avg_rating)) + "☆" * (5 - int(round(avg_rating)))
    st.markdown(f"""
    <div class="store-sub-header">
        <span>平均評価: <span class="rating-star">{avg_rating:.1f}</span></span>
        <span style="color:#888;">{star_str}</span>
        <span style="color:#666; font-size:12px;">({len(store_visits)}件の記録)</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">記録</div>', unsafe_allow_html=True)
    if store_visits.empty:
        st.caption("記録なし")
    else:
        for _, row in store_visits.iterrows():
            date_disp = row['visit_date'] if row['visit_date'] else "日付なし"
            
            # 時間表示
            t_s = row.get('start_time', '')
            t_e = row.get('end_time', '')
            time_disp = f"{t_s} ~ {t_e}" if (t_s or t_e) else ""
            
            mem_disp = row['members'] if row['members'] else "-"
            sv_disp = row.get('sv_members', '-')
            if not sv_disp: sv_disp = "-"
            area_disp = row['count_area'] if row['count_area'] else "-"
            rec_memo = row.get('record_memo', '')
            
            # 評価 (リスト内表示)
            r_val = int(row.get('rating', 0))
            r_star = "★" * r_val if r_val > 0 else "-"
            
            st.markdown('<div class="visit-row-container">', unsafe_allow_html=True)
            c_info, c_memo, c_act = st.columns([0.4, 0.4, 0.2])
            
            with c_info:
                st.markdown(f"""
                <div>
                    <div class="visit-date">{date_disp} <span class="visit-time">{time_disp}</span></div>
                    <div style="font-size:11px; color:#ffd700; margin-bottom:2px;">{r_star}</div>
                    <div style="font-size:12px; color:#ccc;">SV: {sv_disp} <br>Mem: {mem_disp}</div>
                    <div style="font-size:12px; color:#aaa; margin-top:2px;">アサイン: {area_disp}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with c_memo:
                if rec_memo:
                    st.markdown(f"""<div style="font-size:12px; color:#eee; border-left:1px solid #444; padding-left:10px; height:100%; white-space: pre-wrap;">{rec_memo}</div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div style="font-size:12px; color:#555; border-left:1px solid #444; padding-left:10px; height:100%;">(メモなし)</div>""", unsafe_allow_html=True)
            
            with c_act:
                st.markdown('<div style="height: 0px;"></div>', unsafe_allow_html=True)
                if st.button("詳細", key=f"edit_{mode_prefix}_{row['id']}", type="secondary"):
                    st.session_state.edit_record_id = row['id']
                    st.rerun()
                if st.button("削除", key=f"del_{mode_prefix}_{row['id']}", type="secondary"):
                    delete_visit_data(row['id'])
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    if st.button("新しい記録を追加", key=f"add_btn_{mode_prefix}", type="primary", use_container_width=True):
        add_callback()

    st.markdown('<div class="section-title">店舗情報 (編集可)</div>', unsafe_allow_html=True)
    this_store = stores_df[stores_df['store_name'] == store]
    init_notices = this_store.iloc[0]['notices'] if not this_store.empty else ""
    init_memo = this_store.iloc[0]['memo'] if not this_store.empty else ""

    with st.form(f"update_info_{mode_prefix}"):
        new_notices = st.text_area("注意事項", value=init_notices, height=100)
        new_memo = st.text_area("メモ", value=init_memo, height=100)
        if st.form_submit_button("保存", type="primary"):
            update_store_info(store, new_notices, new_memo)
            st.success("更新しました")
            st.rerun()

# --- 6. メインUI ---
st.title("店舗記録ログ")

tab_calendar, tab_search, tab_register = st.tabs(["カレンダー", "店舗一覧・検索", "新規登録"])

# ==========================================
# TAB 1: カレンダー
# ==========================================
with tab_calendar:
    year = st.session_state.cal_year
    month = st.session_state.cal_month
    
    # --- 画面F: 日次詳細画面 ---
    if st.session_state.cal_view_mode == 'day':
        target_date = st.session_state.cal_selected_date
        d_str = target_date.strftime("%Y-%m-%d")
        
        if st.button("◀ カレンダー戻る", type="secondary", use_container_width=True):
            st.session_state.cal_view_mode = 'month'
            st.rerun()
            
        st.markdown(f"###  {d_str} の記録")
        
        visits_df = get_visits_data()
        day_visits = visits_df[visits_df['visit_date'] == d_str]
        
        if day_visits.empty:
            st.info("この日の記録はありません")
        else:
            for _, row in day_visits.iterrows():
                s_name = row['store_name']
                mem = row['members']
                area = row['count_area']
                # 評価と時間
                r_val = int(row.get('rating', 0))
                r_star = "★" * r_val if r_val > 0 else "-"
                t_s = row.get('start_time', '')
                t_e = row.get('end_time', '')
                time_lbl = f"{t_s}~{t_e}" if (t_s or t_e) else ""
                
                with st.container():
                    st.markdown(f"""
                    <div class="day-card">
                        <div class="day-card-store">{s_name} <span style="font-size:12px; color:#ffd700;">{r_star}</span></div>
                        <div class="day-card-info">{time_lbl}</div>
                        <div class="day-card-info">メンバー: {mem}</div>
                        <div class="day-card-info">アサイン: {area}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"詳細へ", key=f"cal_day_btn_{row['id']}", type="secondary", use_container_width=True):
                        st.session_state.cal_view_mode = 'store'
                        st.session_state.selected_store = s_name
                        st.rerun()

    # --- 画面G: カレンダー内店舗詳細 ---
    elif st.session_state.cal_view_mode == 'store' and st.session_state.selected_store:
        def back_to_day():
            st.session_state.cal_view_mode = 'day'
            st.session_state.edit_record_id = None
            st.rerun()
        def go_to_add():
            st.session_state.cal_view_mode = 'add'
            st.rerun()
        render_store_detail_content(st.session_state.selected_store, back_to_day, go_to_add, mode_prefix="cal")

    # --- 画面H: カレンダー内追加 ---
    elif st.session_state.cal_view_mode == 'add' and st.session_state.selected_store:
        def back_to_store():
            st.session_state.cal_view_mode = 'store'
            st.rerun()
        render_add_visit_screen(st.session_state.selected_store, back_to_store, mode_prefix="cal")

    # --- 画面E: 月表示カレンダー (縦リスト) ---
    else:
        st.write("")
        c1, c2, c3 = st.columns([1, 3, 1])
        
        if c1.button("◀", key="cal_prev", use_container_width=True):
            change_cal_month(-1)
            st.rerun()
        c2.markdown(f"<div style='text-align:center; font-weight:bold; padding-top:5px;'>{year}年 {month}月</div>", unsafe_allow_html=True)
        if c3.button("▶", key="cal_next", use_container_width=True):
            change_cal_month(1)
            st.rerun()
            
        st.write("")
        
        df = get_visits_data()
        visits_map = {}
        if not df.empty:
            for _, row in df.iterrows():
                try:
                    d_obj = datetime.datetime.strptime(row['visit_date'], "%Y-%m-%d").date()
                    if d_obj.year == year and d_obj.month == month:
                        day = d_obj.day
                        if day not in visits_map: visits_map[day] = []
                        visits_map[day].append(row['store_name'])
                except: continue

        with st.container(height=600, border=False):
            num_days = calendar.monthrange(year, month)[1]
            today = datetime.date.today()
            weekday_map = ["日", "月", "火", "水", "木", "金", "土"]
            
            for day in range(1, num_days + 1):
                curr_date = datetime.date(year, month, day)
                wk_idx = int(curr_date.strftime('%w'))
                
                day_class = "day-wkd"
                if wk_idx == 0: day_class = "day-sun"
                elif wk_idx == 6: day_class = "day-sat"
                elif jpholiday.is_holiday(curr_date): day_class = "day-hol"
                
                has_visit = day in visits_map
                stores = visits_map[day] if has_visit else []
                
                stores_html = ""
                if stores:
                    for s in stores:
                        stores_html += f'<div class="cal-store-name">{s}</div>'
                else:
                    stores_html = '<div class="cal-store-sub">記録なし</div>'

                row_class = "row-today" if curr_date == today else ""
                
                c_row = st.columns([0.85, 0.15])
                with c_row[0]:
                    st.markdown(f"""
                    <div class="cal-list-row {row_class}">
                        <div class="cal-date-box">
                            <div class="date-num {day_class}">{day}</div>
                            <div class="date-week {day_class}">{weekday_map[wk_idx]}</div>
                        </div>
                        <div class="cal-info-box">{stores_html}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with c_row[1]:
                    st.markdown('<div style="height: 15px;"></div>', unsafe_allow_html=True)
                    btn_type = "primary" if has_visit else "secondary"
                    if st.button("詳細", key=f"cal_list_btn_{day}", type=btn_type):
                        st.session_state.cal_selected_date = curr_date
                        st.session_state.cal_view_mode = 'day'
                        st.rerun()

# ==========================================
# TAB 2: 検索・詳細
# ==========================================
with tab_search:
    
    # --- 画面C: 訪問追加画面 ---
    if st.session_state.search_add_mode and st.session_state.selected_store:
        def back_from_add():
            st.session_state.search_add_mode = False
            st.rerun()
        render_add_visit_screen(st.session_state.selected_store, back_from_add, mode_prefix="search")

    # --- 画面B: 店舗詳細画面 ---
    elif st.session_state.selected_store:
        def back_to_list():
            st.session_state.selected_store = None
            st.session_state.edit_record_id = None
            st.rerun()
        def to_add():
            st.session_state.search_add_mode = True
            st.rerun()
        render_store_detail_content(st.session_state.selected_store, back_to_list, to_add, mode_prefix="search")
    
    # --- 画面A: 店舗一覧画面 ---
    else:
        st.write("")
        search_query = st.text_input("キーワード検索", placeholder="店舗名 / メンバー名 / 注意事項など")
        stores_df = get_stores_data()
        visits_df = get_visits_data()
        
        if stores_df.empty:
            st.info("データがありません")
        else:
            all_names = stores_df['store_name'].unique()
            matched = set()
            
            c_opt1, c_opt2, c_opt3 = st.columns(3)
            use_store = c_opt1.checkbox("店舗名", True)
            use_member = c_opt2.checkbox("メンバー")
            use_memo = c_opt3.checkbox("注意事項・メモ")

            if search_query:
                q = search_query.strip()
                if use_store:
                    hits = stores_df[stores_df['store_name'].astype(str).str.contains(q, case=False, na=False)]
                    matched.update(hits['store_name'].tolist())
                if use_memo:
                    hits = stores_df[stores_df['notices'].astype(str).str.contains(q, case=False, na=False) | stores_df['memo'].astype(str).str.contains(q, case=False, na=False)]
                    matched.update(hits['store_name'].tolist())
                if use_member and not visits_df.empty:
                    hits = visits_df[visits_df['members'].astype(str).str.contains(q, case=False, na=False)]
                    matched.update(hits['store_name'].unique().tolist())
                filtered = sorted(list(matched))
            else:
                filtered = sorted(all_names)
            
            st.markdown(f"<div style='margin-bottom:10px; color:#888; font-size:12px;'>全 {len(filtered)} 店舗</div>", unsafe_allow_html=True)
            
            st.markdown('<div class="list-btn-box">', unsafe_allow_html=True)
            for s_name in filtered:
                if st.button(f"{s_name}", key=f"btn_search_{s_name}", type="secondary", use_container_width=True):
                    st.session_state.selected_store = s_name
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 3: 新規登録
# ==========================================
with tab_register:
    st.write("")
    
    with st.form("new_store_form", clear_on_submit=True):
        st.subheader("新規店舗の登録")
        st.caption("※ 記録データは登録後の詳細画面から追加してください")
        
        store_name_in = st.text_input("店舗名 (必須)", placeholder="例: ○○店")
        st.markdown("---")
        notices_in = st.text_area("注意事項", height=100)
        memo_in = st.text_area("メモ", height=100)
        
        if st.form_submit_button("登録", type="primary", use_container_width=True):
            if not store_name_in:
                st.error("店舗名を入力してください")
            else:
                current_stores = get_stores_data()
                if not current_stores.empty and store_name_in in current_stores['store_name'].values:
                    st.warning("その店舗は既に存在します")
                    if st.button("詳細へ移動", type="secondary"):
                        st.session_state.selected_store = store_name_in
                        st.rerun()
                else:
                    with st.spinner("登録処理中..."):
                        register_new_store(store_name_in, notices_in, memo_in)
                        st.success(f"登録しました: {store_name_in}")
                        st.session_state.selected_store = store_name_in

                        st.rerun()
