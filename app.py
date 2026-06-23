import streamlit as st
import pandas as pd
import os
import re
from rapidfuzz import fuzz

# ==========================================
# 0. 多語言配置 & 列名翻譯字典
# ==========================================
st.set_page_config(page_title="Torist Bird Index", layout="wide", page_icon="🐦")

st.markdown("""
<style>
/* multiselect 已選標籤背景色 */
span[data-baseweb="tag"] {
    background-color: rgb(211, 186, 227) !important;
}
/* 標籤文字顏色（深色確保可讀） */
span[data-baseweb="tag"] span {
    color: #2d2d2d !important;
}
</style>
""", unsafe_allow_html=True)

TRANSLATIONS = {
    "SC": { # 簡體中文
        "title": "Torist 🐦 多语言鸟类索引",
        "settings": "系统设置",
        "data_status": "已加载版本",
        "base_list": "选择基准名录 (Base)",
        "cross_ref": "添加对比名录 (Compare)",
        "search_label": "全库检索",
        "search_placeholder": "输入鸟名 / 编号...",
        "found_res": "共找到 {count} 个匹配",
        "col_view": "📋 {name}",
        "synonym_loaded": "🔗 同义词库: {count} 条规则",
        "no_data": "⚠️ 未检测到有效名录，请检查 original_index 文件夹",
        "folder_missing": "❌ 文件夹不存在",
        "search_scope": "搜索范围",
        "scope_all": "全部字段",
        "scope_sci": "学名",
        "scope_cn": "中文名",
        "scope_en": "英文名",
        "search_mode": "匹配方式",
        "mode_contains": "包含",
        "mode_startswith": "开头匹配",
        "mode_fuzzy": "模糊匹配",
        "fuzzy_threshold": "匹配阈值",
        "col_filter": "字段筛选",
        "export_btn": "导出 CSV",
        "export_all": "导出全部数据",
        "showing_all": "共 {count} 条记录"
    },
    "TC": { # 繁體中文
        "title": "Torist 🐦 多語言鳥類索引",
        "settings": "系統設置",
        "data_status": "已加載版本",
        "base_list": "選擇基準名錄 (Base)",
        "cross_ref": "添加對比名錄 (Compare)",
        "search_label": "全庫檢索",
        "search_placeholder": "輸入鳥名 / 編號...",
        "found_res": "共找到 {count} 個匹配",
        "col_view": "📋 {name}",
        "synonym_loaded": "🔗 同義詞庫: {count} 條規則",
        "no_data": "⚠️ 未檢測到有效名錄，請檢查 original_index 文件夾",
        "folder_missing": "❌ 文件夾不存在",
        "search_scope": "搜尋範圍",
        "scope_all": "全部欄位",
        "scope_sci": "學名",
        "scope_cn": "中文名",
        "scope_en": "英文名",
        "search_mode": "比對方式",
        "mode_contains": "包含",
        "mode_startswith": "開頭比對",
        "mode_fuzzy": "模糊比對",
        "fuzzy_threshold": "比對閾值",
        "col_filter": "欄位篩選",
        "export_btn": "匯出 CSV",
        "export_all": "匯出全部資料",
        "showing_all": "共 {count} 筆記錄"
    },
    "EN": {
        "title": "Torist 🐦 Smart Wild Bird Index",
        "settings": "System Settings",
        "data_status": "Loaded Versions",
        "base_list": "Base Checklist",
        "cross_ref": "Compare With",
        "search_label": "Global Search",
        "search_placeholder": "Type bird name / index...",
        "found_res": "Found {count} matches",
        "col_view": "📋 View: {name}",
        "synonym_loaded": "🔗 Synonyms: {count} rules",
        "no_data": "⚠️ No valid checklists found.",
        "folder_missing": "❌ Folder missing",
        "search_scope": "Search Scope",
        "scope_all": "All Fields",
        "scope_sci": "Scientific Name",
        "scope_cn": "Chinese Name",
        "scope_en": "English Name",
        "search_mode": "Match Mode",
        "mode_contains": "Contains",
        "mode_startswith": "Starts With",
        "mode_fuzzy": "Fuzzy Match",
        "fuzzy_threshold": "Threshold",
        "col_filter": "Column Filter",
        "export_btn": "Export CSV",
        "export_all": "Export All Data",
        "showing_all": "{count} records total"
    },
    "JP": {
        "title": "Torist 🐦 多語言野鳥名錄",
        "settings": "設定",
        "data_status": "読込済みリスト",
        "base_list": "基準リスト (Base)",
        "cross_ref": "比較リスト (Compare)",
        "search_label": "検索",
        "search_placeholder": "鳥の名前 / 番号を入力...",
        "found_res": "{count} 件ヒット",
        "col_view": "📋 {name} ビュー",
        "synonym_loaded": "🔗 シノニム: {count} 件",
        "no_data": "⚠️ データなし。フォルダを確認してください。",
        "folder_missing": "❌ フォルダが見つかりません",
        "search_scope": "検索範囲",
        "scope_all": "全フィールド",
        "scope_sci": "学名",
        "scope_cn": "中国語名",
        "scope_en": "英語名",
        "search_mode": "マッチ方式",
        "mode_contains": "含む",
        "mode_startswith": "前方一致",
        "mode_fuzzy": "あいまい検索",
        "fuzzy_threshold": "閾値",
        "col_filter": "フィールド絞込",
        "export_btn": "CSV 出力",
        "export_all": "全データ出力",
        "showing_all": "全 {count} 件"
    }
}

COLUMN_MAP = {
    "SC": { # 简体视角
        "Index": "编号", "学名": "学名", "Scientific": "学名",
        "中文名": "中文名", "Chinese": "中文名",
        "中文名_TW": "中文名(台)", "Chinese (Traditional)": "中文名(繁)",
        "English": "英文名", "English_IOC": "英文名(IOC)",
        "Japanese": "日文名", "和名": "日文名",
        "Family": "科名", "科名": "科名"
    },
    "TC": { # 繁体视角
        "Index": "編號", "学名": "學名", "Scientific": "學名",
        "中文名_TW": "中文名", "Chinese (Traditional)": "中文名",
        "中文名": "中文名(簡)", "Chinese": "中文名(簡)",
        "English": "英文名", "English_IOC": "英文名(IOC)",
        "Japanese": "日文名", "和名": "日文名",
        "Family": "科名", "科名": "科名"
    },
    "EN": {
        "Index": "#", "学名": "Sci-Name", 
        "中文名": "Chinese(S)", "中文名_TW": "Chinese(T)",
        "Chinese": "Chinese(S)", "Chinese (Traditional)": "Chinese(T)",
        "English": "English", "English_IOC": "English(IOC)",
        "Japanese": "Japanese", "和名": "Japanese",
        "Family": "Family", "科名": "Family"
    },
    "JP": {
        "Index": "No.", "学名": "学名", 
        "中文名": "中国語(簡)", "中文名_TW": "中国語(繁)",
        "Chinese": "中国語(簡)", "Chinese (Traditional)": "中国語(繁)",
        "English": "英語", "English_IOC": "英語(IOC)",
        "Japanese": "和名", "和名": "和名",
        "Family": "科", "科名": "科"
    }
}

# 始終顯示的列（不參與篩選）
ALWAYS_SHOW_COLS = {'Index', '学名'}

def get_col_label(col, lang_code):
    """將原始列名翻譯為當前 UI 語言的顯示標籤"""
    return COLUMN_MAP.get(lang_code, {}).get(col, col)

def filter_cols_by_selection(cols, selected_base_cols, selected_compare_cols):
    """根據所選列名集合過濾列表"""
    keep = []
    for col in cols:
        if col == 'Link_Key':
            continue
        if '[' in col and col.endswith(']'):
            base_col = col[:col.rindex(' [')]
            dataset = col[col.rindex('[') + 1:-1]
            sel = selected_compare_cols.get(dataset)
            if sel is None or base_col in sel:
                keep.append(col)
        else:
            if col in ALWAYS_SHOW_COLS or col in selected_base_cols:
                keep.append(col)
    return keep

def build_col_selector(caption, df_cols, lang_code, widget_key):
    """
    渲染字段選擇器，返回所選原始列名集合。
    列數 <= 6 時用 pills；> 6 時用可搜索的 multiselect（支持拼音/字母定位）。
    """
    selectable = [c for c in df_cols if c not in ALWAYS_SHOW_COLS]
    if not selectable:
        return set(df_cols)

    # 構建標籤 → 原始列名映射（多列可共用一個翻譯標籤）
    label_to_cols: dict[str, list[str]] = {}
    for c in selectable:
        lbl = get_col_label(c, lang_code)
        label_to_cols.setdefault(lbl, []).append(c)
    unique_labels = list(label_to_cols.keys())

    st.caption(f"▸ {caption}")
    sel = st.multiselect(
        caption, unique_labels, default=unique_labels,
        label_visibility="collapsed", key=widget_key,
    )

    selected = set()
    for lbl in sel:
        for c in label_to_cols[lbl]:
            selected.add(c)
    return selected

# 列排序優先級
def get_column_priority(lang_code):
    base = ['Index', '学名', 'Link_Key']
    if lang_code == 'SC':
        # 簡體優先：Simple Chinese > Trad Chinese
        return base + ['中文名', 'Chinese', '中文名_TW', 'Chinese (Traditional)', 'English', 'Japanese', 'Family', '科名']
    elif lang_code == 'TC':
        # 繁體優先：Trad Chinese > Simple Chinese
        return base + ['中文名_TW', 'Chinese (Traditional)', '中文名', 'Chinese', 'English', 'Japanese', 'Family', '科名']
    elif lang_code == 'JP':
        return base + ['Japanese', '和名', 'English', '中文名', '中文名_TW', 'Family', '科名']
    else: # EN
        return base + ['English', 'English_IOC', 'Chinese (Traditional)', 'Chinese', 'Japanese', 'Family']

def translate_columns(df, lang_code):
    new_cols = {}
    map_dict = COLUMN_MAP.get(lang_code, {})
    for col in df.columns:
        base_part = col
        suffix_part = ""
        if "[" in col and col.endswith("]"):
            parts = col.split(" [")
            base_part = parts[0]
            suffix_part = " [" + parts[1]
        trans_base = map_dict.get(base_part, base_part)
        new_cols[col] = trans_base + suffix_part
    return df.rename(columns=new_cols)

# ==========================================
# 1. 文件讀取與清洗
# ==========================================
def read_excel_smart(filepath, sheet_keywords, header_hints):
    try:
        engine = 'openpyxl' if filepath.endswith('.xlsx') else 'xlrd'
        xls = pd.ExcelFile(filepath, engine=engine)
        target_sheet = xls.sheet_names[0]
        if sheet_keywords:
            for name in xls.sheet_names:
                if any(k in name for k in sheet_keywords):
                    target_sheet = name
                    break
        df_temp = pd.read_excel(xls, sheet_name=target_sheet, header=None, nrows=20)
        header_row = 0
        found_header = False
        for idx, row in df_temp.iterrows():
            row_str = row.astype(str).str.cat(sep=' ')
            if any(h in row_str for h in header_hints):
                header_row = idx
                found_header = True
                break
        if not found_header and "CBR" in filepath: header_row = 7
        df = pd.read_excel(xls, sheet_name=target_sheet, header=header_row)
        return df
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

# --- 版本提取函數 ---
def extract_version(filename):
    """
    智能提取版本號，支持多種格式
    """
    # 1. 優先匹配 "7ed", "8ed" 
    match = re.search(r'(\d+)ed', filename, re.IGNORECASE)
    if match:
        return f"{match.group(1)}th"

    # 2. 匹配 "JP 7", "JP 8", "ver 7", "v7"
    match = re.search(r'(?:JP|ver|v)[ ._-]?(\d+)(?!\d)', filename, re.IGNORECASE)
    if match:
        return f"v{match.group(1)}"

    # 3. 原有的匹配規則 (v10.0, 15.1, 2023)
    match = re.search(r'(v\d+\.\d+|\d+\.\d+|20\d{2})', filename)
    if match:
        return match.group(1)

    return "Unknown"

def clean_index(val):
    try:
        if pd.isna(val): return ""
        s = str(val).strip()
        if s.endswith(".0"): return s[:-2]
        return s
    except: return str(val)

# ==========================================
# 2. 數據加載核心
# ==========================================
@st.cache_data
def load_data():
    data_store = {}
    base_dir = "original_index"
    syn_dict = {}

    print("🚀 开始加载数据...")

    if not os.path.exists(base_dir): return {}, {}, "Folder Missing"
    files = [f for f in os.listdir(base_dir) if f.endswith(('.xlsx', '.xls'))]
    
    for f in files:
        print(f"🔍 正在加载文件: {f}")
        f_path = os.path.join(base_dir, f)
        version = extract_version(f)
        
        # 1. China (CBR) - 修改這裡！
        if "China" in f or "CBR" in f:
            df = read_excel_smart(f_path, ["Checklist", "正表"], ['学名', 'Scientific'])
            if df is not None:
                df.columns = df.columns.str.strip()
                if '学名' in df.columns:
                    if '编号' in df.columns: df = df.rename(columns={'编号': 'Index'})
                    else: df['Index'] = range(1, len(df) + 1)
                    df = df[['Index', '学名', '中文名', '英文名']].dropna(subset=['学名'])
                    df['学名'] = df['学名'].str.strip()
                    df['Index'] = df['Index'].apply(clean_index)
                    
                    key = f"China CBR ({version})" 
                    data_store[key] = df

        # 2. Taiwan
        elif "TW" in f:
            try:
                syn_df = read_excel_smart(f_path, ["變動", "Change"], ['變動細項'])
                if syn_df is not None:
                    col = next((c for c in syn_df.columns if '變動細項' in c), None)
                    if col:
                        for txt in syn_df[col].dropna():
                            m = re.search(r'學名：([A-Za-z ]+)→([A-Za-z ]+)', str(txt))
                            if m:
                                syn_dict[m.group(1).strip()] = m.group(2).strip()
                                syn_dict[m.group(2).strip()] = m.group(1).strip()
            except: pass

            df = read_excel_smart(f_path, ["正表", "List"], ['學名', 'Scientific'])
            if df is not None:
                rename_map = {'學名': '学名', '中文名': '中文名_TW'}
                if '編碼' in df.columns: rename_map['編碼'] = 'Index'
                elif 'Code' in df.columns: rename_map['Code'] = 'Index'
                
                df = df.rename(columns=rename_map)
                
                if '学名' in df.columns:
                    cols = ['学名', '中文名_TW', '英文名']
                    if 'Index' in df.columns: cols.insert(0, 'Index')
                    df = df[cols].dropna(subset=['学名'])
                    df['学名'] = df['学名'].str.strip()
                    if 'Index' in df.columns: df['Index'] = df['Index'].apply(clean_index)
                    data_store[f"Taiwan ({version})"] = df

        # 3. Japan (OSJ)
        elif "jp" in f.lower() or "osj" in f.lower():
            # === 專門處理第 7 版 (舊格式 .xls) ===
            if "7ed" in f or "v7" in version:
                try:
                    df = pd.read_excel(f_path, header=None, engine='xlrd')
                    
                    # 2.  "種" (Species)
                    if 1 in df.columns:
                        df = df[df[1] == '種']
                    
                    # 3. 合併學名 (屬名 + 空格 + 種小名)
                    if 3 in df.columns and 4 in df.columns:
                        df['学名'] = df[3].astype(str) + " " + df[4].astype(str)
                        
                    # 4. 提取日文名 
                    if 6 in df.columns:
                        df['Japanese'] = df[6]
                    
                    # 5. 提取編號 (第 0 列)
                    if 0 in df.columns:
                        df['Index'] = df[0]
                        
                    # 6. 整理並存入
                    if '学名' in df.columns and 'Japanese' in df.columns:
                        df = df[['Index', '学名', 'Japanese']]
                        df['学名'] = df['学名'].str.strip()
                        if 'Index' in df.columns: df['Index'] = df['Index'].apply(clean_index)
                        
                        key = f"Japan ({version})"
                        data_store[key] = df
                        
                except Exception as e:
                    print(f"Error reading Japan v7: {e}")

            # === 處理第 8 版 (v8) 及標準格式 ===
            else:
                df = read_excel_smart(f_path, ["リスト", "List"], ['学名', 'Scientific'])
                if df is not None:
                    if 'カテゴリ' in df.columns: df = df[df['カテゴリ'] == '種']
                    
                    idx_col = None
                    for c in ['種番号', '掲載順', 'No', 'Seq']:
                        if c in df.columns:
                            idx_col = c
                            break
                    
                    rename_map = {'和名': 'Japanese'}
                    if idx_col: rename_map[idx_col] = 'Index'
                    
                    df = df.rename(columns=rename_map)
                    
                    if '学名' in df.columns and 'Japanese' in df.columns:
                        cols = ['学名', 'Japanese']
                        if 'Index' in df.columns: cols.insert(0, 'Index')
                        df = df[cols].dropna(subset=['学名'])
                        df['学名'] = df['学名'].str.strip()
                        if 'Index' in df.columns: df['Index'] = df['Index'].apply(clean_index)
                        data_store[f"Japan ({version})"] = df

#       4. IOC
        elif "IOC" in f:
            df = read_excel_smart(f_path, ["List"], ['IOC', 'Scientific'])
            if df is not None:
                df.columns = [c.strip() for c in df.columns]
                idx_col = next((c for c in df.columns if c.lower() in ['seq', 'rank', 'no.']), None)
                ioc_sci_col = next((c for c in df.columns if 'IOC' in c and 'Order' not in c), None)
                
                if ioc_sci_col:
                    cols_map = {ioc_sci_col: '学名', 'English': 'English_IOC'}
                    if idx_col: cols_map[idx_col] = 'Index'
                    df = df.rename(columns=cols_map)

                    # 丟棄結構性列（IOC Order/Rank/Unnamed/純空列）
                    structural = {'IOC_order', 'IOC order', 'Order', 'Rank'}
                    keep_cols = [
                        c for c in df.columns
                        if str(c).strip()
                        and not str(c).startswith('Unnamed')
                        and c not in structural
                    ]
                    if 'Index' in df.columns and 'Index' not in keep_cols:
                        keep_cols.insert(0, 'Index')
                    df = df[keep_cols].dropna(subset=['学名'])
                    df['学名'] = df['学名'].str.strip()
                    if 'Index' in df.columns:
                        df['Index'] = df['Index'].apply(clean_index)
                    data_store[f"IOC ({version})"] = df

    print("🚀 数据加载完成！")
    return data_store, syn_dict, "Success"

# ==========================================
# 3. 界面邏輯
# ==========================================
with st.sidebar:
    lang_opt = st.radio("Language / 言語", ["简体中文", "繁體中文", "English", "日本語"], horizontal=True)
    
    if lang_opt == "简体中文": lang_code = "SC"
    elif lang_opt == "繁體中文": lang_code = "TC"
    elif lang_opt == "English": lang_code = "EN"
    else: lang_code = "JP"
    
    txt = TRANSLATIONS[lang_code]

st.title(txt["title"])

data_dict, synonym_map, status = load_data()

if status == "Folder Missing":
    st.error(txt["folder_missing"])
    st.stop()
if not data_dict:
    st.error(txt["no_data"])
    st.stop()
if synonym_map:
    st.toast(txt["synonym_loaded"].format(count=len(synonym_map)), icon="🔗")

with st.sidebar:
    st.markdown("---")
    st.header(txt["settings"])
    with st.expander(txt["data_status"]):
        for k in sorted(data_dict.keys()):
            st.success(f"✅ {k}")
            
    base_list = st.selectbox(txt["base_list"], sorted(data_dict.keys()))
    
    avail_opts = sorted([k for k in data_dict.keys() if k != base_list])
    default_vals = []
    ioc_versions = [x for x in avail_opts if "IOC" in x]
    if ioc_versions: default_vals = [ioc_versions[-1]]
    compare_lists = st.multiselect(txt["cross_ref"], avail_opts, default=default_vals)

    # 字段篩選（語言列選擇）
    st.markdown("---")
    st.caption(txt["col_filter"])

    selected_base_cols = build_col_selector(
        base_list, list(data_dict[base_list].columns), lang_code, "base_fields"
    )
    selected_compare_cols = {}
    for cname in compare_lists:
        selected_compare_cols[cname] = build_col_selector(
            cname, list(data_dict[cname].columns), lang_code, f"cmp_{cname}"
        )

# ==========================================
# 4. 核心合併
# ==========================================
main_df = data_dict[base_list].copy()

for target_name in compare_lists:
    target_df = data_dict[target_name].copy()
    target_sci_names = set(target_df['学名'].values)
    
    def find_link_key(name):
        if name in target_sci_names: return name
        if name in synonym_map:
            alias = synonym_map[name]
            if alias in target_sci_names: return alias
        return None

    main_df['Link_Key'] = main_df['学名'].apply(find_link_key)
    
    rename_map = {}
    for col in target_df.columns:
        if col == '学名': continue
        rename_map[col] = f"{col} [{target_name}]"
    
    target_df_renamed = target_df.rename(columns=rename_map)
    cols_to_use = ['学名'] + list(rename_map.values())
    
    merged = pd.merge(
        main_df,
        target_df_renamed[cols_to_use], 
        left_on='Link_Key',
        right_on='学名',
        how='left'
    )
    
    if 'Link_Key' in merged.columns: del merged['Link_Key']
    if '学名_y' in merged.columns: del merged['学名_y']
    if '学名_x' in merged.columns: merged = merged.rename(columns={'学名_x': '学名'})
    main_df = merged

# ==========================================
# 5. 顯示優化
# ==========================================

# 列排序
all_cols = list(main_df.columns)
priority_basic_cols = get_column_priority(lang_code)
final_col_order = []

for p_col in priority_basic_cols:
    if p_col in all_cols: final_col_order.append(p_col)

for p_col in priority_basic_cols:
    matches = [c for c in all_cols if c.startswith(p_col + " [")]
    for m in matches:
        if m not in final_col_order: final_col_order.append(m)

for c in all_cols:
    if c not in final_col_order: final_col_order.append(c)

filtered_col_order = filter_cols_by_selection(final_col_order, selected_base_cols, selected_compare_cols)
main_df = main_df[filtered_col_order]
display_df = translate_columns(main_df, lang_code)

# 推斷各字段對應的 display_df 列名（翻譯後）
def get_scope_cols(scope, main_df, display_df, lang_code):
    """根據搜索範圍返回 display_df 中對應的列名列表"""
    if scope == "all":
        return list(display_df.columns)

    sci_raw = ['学名']
    cn_raw = ['中文名', '中文名_TW', 'Chinese', 'Chinese (Traditional)']
    en_raw = ['English', 'English_IOC', '英文名']

    raw_map = {"sci": sci_raw, "cn": cn_raw, "en": en_raw}
    target_raws = raw_map.get(scope, [])

    col_rename = {}
    for orig, renamed in zip(main_df.columns, display_df.columns):
        base = orig.split(" [")[0]
        if base in target_raws:
            col_rename[orig] = renamed

    return list(col_rename.values()) if col_rename else list(display_df.columns)

st.subheader(txt["col_view"].format(name=base_list))

# 搜索控件行
c1, c2, c3 = st.columns([4, 2, 2])
with c1:
    query = st.text_input(txt["search_label"], placeholder=txt["search_placeholder"], label_visibility="collapsed")
with c2:
    scope_options = {
        txt["scope_all"]: "all",
        txt["scope_sci"]: "sci",
        txt["scope_cn"]: "cn",
        txt["scope_en"]: "en",
    }
    scope_label = st.selectbox(txt["search_scope"], list(scope_options.keys()), label_visibility="collapsed")
    scope = scope_options[scope_label]
with c3:
    mode_options = {
        txt["mode_contains"]: "contains",
        txt["mode_startswith"]: "startswith",
        txt["mode_fuzzy"]: "fuzzy",
    }
    mode_label = st.selectbox(txt["search_mode"], list(mode_options.keys()), label_visibility="collapsed")
    mode = mode_options[mode_label]

fuzzy_threshold = 70
if mode == "fuzzy":
    fuzzy_threshold = st.slider(txt["fuzzy_threshold"], min_value=50, max_value=100, value=70, step=5)

# 編號列窄寬配置
index_label = get_col_label('Index', lang_code)
col_cfg = {index_label: st.column_config.TextColumn(width="small")} if index_label in display_df.columns else {}

# 搜索邏輯
if query:
    search_cols = get_scope_cols(scope, main_df, display_df, lang_code)
    q_lower = query.lower()

    if mode == "startswith":
        mask = display_df[search_cols].astype(str).apply(
            lambda x: x.str.lower().str.startswith(q_lower)
        ).any(axis=1)
    elif mode == "fuzzy":
        def row_fuzzy_match(row):
            for val in row:
                if fuzz.partial_ratio(q_lower, str(val).lower()) >= fuzzy_threshold:
                    return True
            return False
        mask = display_df[search_cols].apply(row_fuzzy_match, axis=1)
    else:
        mask = display_df[search_cols].astype(str).apply(
            lambda x: x.str.lower().str.contains(q_lower, regex=False)
        ).any(axis=1)

    res = display_df[mask]
    col_info, col_export = st.columns([3, 1])
    with col_info:
        st.info(txt["found_res"].format(count=len(res)))
    with col_export:
        st.download_button(
            label=txt["export_btn"],
            data=res.to_csv(index=False).encode("utf-8-sig"),
            file_name="torist_search.csv",
            mime="text/csv",
        )
    st.dataframe(res, use_container_width=True, hide_index=True, column_config=col_cfg)
else:
    col_info, col_export = st.columns([3, 1])
    with col_info:
        st.caption(txt["showing_all"].format(count=len(display_df)))
    with col_export:
        st.download_button(
            label=txt["export_all"],
            data=display_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="torist_full.csv",
            mime="text/csv",
        )
    st.dataframe(display_df, use_container_width=True, hide_index=True, column_config=col_cfg)