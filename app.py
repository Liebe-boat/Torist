import streamlit as st
import pandas as pd
import os
import re

# ==========================================
# 0. 多語言配置 & 列名翻譯字典 (含簡繁區分)
# ==========================================
st.set_page_config(page_title="Torist Bird Index", layout="wide", page_icon="🐦")

# ==========================================
# 0. 多語言配置 & 列名翻譯字典 (已更新：區分簡繁)
# ==========================================
st.set_page_config(page_title="Torist Bird Index", layout="wide", page_icon="🐦")

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
        "folder_missing": "❌ 文件夹不存在"
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
        "folder_missing": "❌ 文件夾不存在"
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
        "folder_missing": "❌ Folder missing"
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
        "folder_missing": "❌ フォルダが見つかりません"
    }
}

# 核心：列名翻譯 (新增：不同視角下的名稱映射)
COLUMN_MAP = {
    "SC": { # 簡體視角
        "Index": "编号", "学名": "学名", "Scientific": "学名",
        "中文名": "中文名", "Chinese": "中文名", # 自己的語言
        "中文名_TW": "中文名(台)", "Chinese (Traditional)": "中文名(繁)", # 別人的語言
        "English": "英文名", "English_IOC": "英文名(IOC)",
        "Japanese": "日文名", "和名": "日文名",
        "Family": "科名", "科名": "科名"
    },
    "TC": { # 繁體視角
        "Index": "編號", "学名": "學名", "Scientific": "學名",
        "中文名_TW": "中文名", "Chinese (Traditional)": "中文名", # 自己的語言
        "中文名": "中文名(簡)", "Chinese": "中文名(簡)", # 別人的語言
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

# 列排序優先級 (新增：簡繁優先順序不同)
def get_column_priority(lang_code):
    base = ['Index', '学名', 'Link_Key']
    if lang_code == 'SC':
        # 簡體優先
        return base + ['中文名', 'Chinese', '中文名_TW', 'Chinese (Traditional)', 'English', 'Japanese', 'Family', '科名']
    elif lang_code == 'TC':
        # 繁體優先
        return base + ['中文名_TW', 'Chinese (Traditional)', '中文名', 'Chinese', 'English', 'Japanese', 'Family', '科名']
    elif lang_code == 'JP':
        return base + ['Japanese', '和名', 'English', '中文名', '中文名_TW', 'Family', '科名']
    else: # EN
        return base + ['English', 'English_IOC', 'Chinese (Traditional)', 'Chinese', 'Japanese', 'Family']

# 核心：列名翻譯 (區分簡繁)
# 這裡定義了 raw data 的列名 -> 界面顯示的列名
COLUMN_MAP = {
    "SC": { # 简体视角
        "Index": "编号", "学名": "学名", "Scientific": "学名",
        "中文名": "中文名", "Chinese": "中文名", # 自己的语言
        "中文名_TW": "中文名(台)", "Chinese (Traditional)": "中文名(繁)", # 别人的语言
        "English": "英文名", "English_IOC": "英文名(IOC)",
        "Japanese": "日文名", "和名": "日文名",
        "Family": "科名", "科名": "科名"
    },
    "TC": { # 繁体视角
        "Index": "編號", "学名": "學名", "Scientific": "學名",
        "中文名_TW": "中文名", "Chinese (Traditional)": "中文名", # 自己的语言
        "中文名": "中文名(簡)", "Chinese": "中文名(簡)", # 别人的语言
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

# 列排序優先級 (根據語言習慣調整)
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
# 1. 智能文件讀取與清洗
# ==========================================
# 1. 智能文件讀取與清洗
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

# --- 升級後的版本提取函數 ---
def extract_version(filename):
    """
    智能提取版本號，支持多種格式
    """
    # 1. 優先匹配 "7ed", "8ed" 這種明確的版次 (日本名錄常用)
    match = re.search(r'(\d+)ed', filename, re.IGNORECASE)
    if match:
        return f"{match.group(1)}th"

    # 2. 匹配 "JP 7", "JP 8", "ver 7", "v7" 這種格式
    # 邏輯：JP/ver/v 後面跟著數字，且數字後面沒有其他數字了
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

    if not os.path.exists(base_dir): return {}, {}, "Folder Missing"
    files = [f for f in os.listdir(base_dir) if f.endswith(('.xlsx', '.xls'))]
    
    for f in files:
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
                    
                    # === 改動點：這裡加上了 CBR 字樣 ===
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
            # v7 特徵：文件名含 7ed，內容無表頭，學名分兩列
            if "7ed" in f or "v7" in version:
                try:
                    # 1. 強制用 xlrd 讀取，且不設表頭 (header=None)，這樣我們可以用數字索引列
                    df = pd.read_excel(f_path, header=None, engine='xlrd')
                    
                    # 2. 篩選：第1列是等級，我們只要 "種" (Species)
                    # v7 結構通常是: [No, Rank, ID, Genus, Species, Auth, JapName...]
                    # 索引:           0    1    2     3       4       5       6
                    if 1 in df.columns:
                        df = df[df[1] == '種']
                    
                    # 3. 合併學名 (屬名 + 空格 + 種小名)
                    if 3 in df.columns and 4 in df.columns:
                        df['学名'] = df[3].astype(str) + " " + df[4].astype(str)
                        
                    # 4. 提取日文名 (通常在第 6 列，有時候在第 7 列，保險起見試一下)
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

            # === 處理第 8 版 (v8) 及標準格式 (保持不變) ===
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
                    
                    # === 這裡增加了 Chinese (Traditional) ===
                    keep_cols = ['学名', 'English_IOC', 'Chinese', 'Chinese (Traditional)', 'Japanese', 'Family']
                    
                    if 'Index' in df.columns: keep_cols.insert(0, 'Index')
                    keep_cols = [c for c in keep_cols if c in df.columns]
                    
                    df = df[keep_cols]
                    df['学名'] = df['学名'].str.strip()
                    if 'Index' in df.columns: df['Index'] = df['Index'].apply(clean_index)
                    data_store[f"IOC ({version})"] = df

    return data_store, syn_dict, "Success"

# ==========================================
# 3. 界面邏輯
# ==========================================
with st.sidebar:
    # 這裡增加了 "简体中文" 和 "繁體中文" 的選項
    lang_opt = st.radio("Language / 言語", ["简体中文", "繁體中文", "English", "日本語"], horizontal=True)
    
    # 邏輯映射
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
st.subheader(txt["col_view"].format(name=base_list))
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input(txt["search_label"], placeholder=txt["search_placeholder"])

# 排序
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

main_df = main_df[final_col_order]
display_df = translate_columns(main_df, lang_code)

if query:
    mask = main_df.astype(str).apply(lambda x: x.str.lower().str.contains(query.lower())).any(axis=1)
    res = display_df[mask]
    st.info(txt["found_res"].format(count=len(res)))
    st.dataframe(res, use_container_width=True, hide_index=True)
else:
    st.dataframe(display_df.head(200), use_container_width=True, hide_index=True)