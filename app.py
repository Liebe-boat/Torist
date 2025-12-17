import streamlit as st
import pandas as pd
import os
import re

# ==========================================
# 0. 多语言配置 & 智能列排序策略
# ==========================================
st.set_page_config(page_title="Torist Bird Index", layout="wide", page_icon="🐦")

# 界面翻译包
TRANSLATIONS = {
    "CN": {
        "title": "Torist 🐦 智能鸟名检索系统",
        "settings": "系统设置",
        "data_status": "已加载版本",
        "base_list": "选择基准名录 (Base)",
        "cross_ref": "添加对比版本 (Compare)",
        "search_label": "全库检索",
        "search_placeholder": "输入鸟名...",
        "found_res": "共找到 {count} 个匹配",
        "col_view": "📋 {name} 详情视图",
        "synonym_loaded": "🔗 同义词库: {count} 条规则",
        "no_data": "⚠️ 未检测到有效名录，请检查 original_index 文件夹",
        "folder_missing": "❌ 文件夹不存在"
    },
    "EN": {
        "title": "Torist 🐦 Smart Bird Index",
        "settings": "System Settings",
        "data_status": "Loaded Versions",
        "base_list": "Base Checklist",
        "cross_ref": "Compare With",
        "search_label": "Global Search",
        "search_placeholder": "Type bird name...",
        "found_res": "Found {count} matches",
        "col_view": "📋 View: {name}",
        "synonym_loaded": "🔗 Synonyms: {count} rules",
        "no_data": "⚠️ No valid checklists found.",
        "folder_missing": "❌ Folder missing"
    },
    "JP": {
        "title": "Torist 🐦 野鳥名検索システム",
        "settings": "設定",
        "data_status": "読込済みリスト",
        "base_list": "基準リスト (Base)",
        "cross_ref": "比較リスト (Compare)",
        "search_label": "検索",
        "search_placeholder": "鳥の名前を入力...",
        "found_res": "{count} 件ヒット",
        "col_view": "📋 {name} ビュー",
        "synonym_loaded": "🔗 シノニム: {count} 件",
        "no_data": "⚠️ データなし。フォルダを確認してください。",
        "folder_missing": "❌ フォルダが見つかりません"
    }
}

# 核心功能：根据当前语言，决定表格列的显示顺序
def get_column_priority(lang_code):
    """
    返回列名的优先顺序列表
    """
    base_cols = ['学名', 'Link_Key']
    if lang_code == 'CN':
        return base_cols + ['中文名', '中文名_TW', 'English', 'Japanese', '科名']
    elif lang_code == 'JP':
        return base_cols + ['Japanese', '和名', 'English', '中文名', '中文名_TW', 'Family']
    else: # EN
        return base_cols + ['English', 'English_IOC', 'Chinese', 'Japanese', 'Family']

# ==========================================
# 1. 智能文件读取 (支持多版本)
# ==========================================
def read_excel_smart(filepath, sheet_keywords, header_hints):
    """通用读取器，自动适配 xls/xlsx 和表头"""
    try:
        engine = 'openpyxl' if filepath.endswith('.xlsx') else 'xlrd'
        xls = pd.ExcelFile(filepath, engine=engine)
        
        # 1. 找 Sheet
        target_sheet = xls.sheet_names[0]
        if sheet_keywords:
            for name in xls.sheet_names:
                if any(k in name for k in sheet_keywords):
                    target_sheet = name
                    break
        
        # 2. 找表头行
        df_temp = pd.read_excel(xls, sheet_name=target_sheet, header=None, nrows=20)
        header_row = 0
        found_header = False
        
        for idx, row in df_temp.iterrows():
            row_str = row.astype(str).str.cat(sep=' ')
            # 只要包含任意一个提示词，就认为是表头
            if any(h in row_str for h in header_hints):
                header_row = idx
                found_header = True
                break
        
        # CBR 特殊处理
        if not found_header and "CBR" in filepath: header_row = 7

        df = pd.read_excel(xls, sheet_name=target_sheet, header=header_row)
        return df
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def extract_version(filename):
    """从文件名提取版本号 (例如 v10.0, 2023, 15.1)"""
    # 匹配 v10.0, 14.1, 2023 这种格式
    match = re.search(r'(v\d+\.\d+|\d+\.\d+|20\d{2})', filename)
    if match:
        return match.group(1)
    return "Unknown"

# ==========================================
# 2. 数据加载核心 (动态加载所有文件)
# ==========================================
@st.cache_data
def load_data():
    data_store = {}
    base_dir = "original_index"
    syn_dict = {}

    if not os.path.exists(base_dir):
        return {}, {}, "Folder Missing"

    files = [f for f in os.listdir(base_dir) if f.endswith(('.xlsx', '.xls'))]
    
    # ---------------------------
    # A. 循环加载所有名录
    # ---------------------------
    for f in files:
        f_path = os.path.join(base_dir, f)
        version = extract_version(f)
        
        # 1. 识别：中国名录 (CBR)
        if "China" in f or "CBR" in f:
            df = read_excel_smart(f_path, ["Checklist", "正表"], ['学名', 'Scientific'])
            if df is not None:
                df.columns = df.columns.str.strip() # 去空格
                if '学名' in df.columns:
                    df = df[['学名', '中文名', '英文名']].dropna(subset=['学名'])
                    df['学名'] = df['学名'].str.strip()
                    # 关键：生成唯一的 Key，例如 "China (v10.0)"
                    key = f"China ({version})"
                    data_store[key] = df

        # 2. 识别：台湾名录 (TW)
        elif "TW" in f:
            # 顺便加载同义词 (如果这个文件里有变动表)
            # 注意：这里我们简化逻辑，每次遇到TW文件都试着读一下变动表
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

            # 加载正表
            df = read_excel_smart(f_path, ["正表", "List"], ['學名', 'Scientific'])
            if df is not None:
                df = df.rename(columns={'學名': '学名', '中文名': '中文名_TW'})
                if '学名' in df.columns:
                    df = df[['学名', '中文名_TW', '英文名']].dropna(subset=['学名'])
                    df['学名'] = df['学名'].str.strip()
                    key = f"Taiwan ({version})"
                    data_store[key] = df

        # 3. 识别：日本名录 (OSJ)
        elif "jp" in f.lower() or "osj" in f.lower():
            df = read_excel_smart(f_path, ["リスト", "List"], ['学名', 'Scientific'])
            if df is not None:
                if 'カテゴリ' in df.columns: df = df[df['カテゴリ'] == '種']
                if '学名' in df.columns and '和名' in df.columns:
                    df = df[['学名', '和名']].dropna(subset=['学名'])
                    df = df.rename(columns={'和名': 'Japanese'})
                    df['学名'] = df['学名'].str.strip()
                    key = f"Japan ({version})"
                    data_store[key] = df

        # 4. 识别：IOC (支持多版本!)
        elif "IOC" in f:
            df = read_excel_smart(f_path, ["List"], ['IOC', 'Scientific'])
            if df is not None:
                # 动态找学名列 (IOC_14.1, IOC_15.1...)
                ioc_sci_col = next((c for c in df.columns if 'IOC' in c and 'Order' not in c), None)
                if ioc_sci_col:
                    cols_map = {ioc_sci_col: '学名', 'English': 'English_IOC'}
                    keep_cols = [ioc_sci_col, 'English', 'Chinese', 'Japanese', 'Family']
                    keep_cols = [c for c in keep_cols if c in df.columns] # 只保留存在的
                    
                    df = df[keep_cols].rename(columns=cols_map)
                    df['学名'] = df['学名'].str.strip()
                    
                    # 这里的 Version 会自动变，比如 "IOC (14.1)" 和 "IOC (15.1)"
                    key = f"IOC ({version})"
                    data_store[key] = df

    return data_store, syn_dict, "Success"

# ==========================================
# 3. 界面逻辑 (UI)
# ==========================================

# A. 语言切换
with st.sidebar:
    lang_opt = st.radio("Language / 言語", ["中文", "English", "日本語"], horizontal=True)
    lang_code = "CN" if lang_opt == "中文" else ("EN" if lang_opt == "English" else "JP")
    txt = TRANSLATIONS[lang_code]

st.title(txt["title"])

# B. 数据读取
data_dict, synonym_map, status = load_data()

if status == "Folder Missing":
    st.error(txt["folder_missing"])
    st.stop()
if not data_dict:
    st.error(txt["no_data"])
    st.stop()
if synonym_map:
    st.toast(txt["synonym_loaded"].format(count=len(synonym_map)), icon="🔗")

# C. 侧边栏设置
with st.sidebar:
    st.markdown("---")
    st.header(txt["settings"])
    
    # 显示已加载的所有版本
    with st.expander(txt["data_status"]):
        # 排序显示，好看一点
        for k in sorted(data_dict.keys()):
            st.success(f"✅ {k}")

    # 选择基准 (Base)
    # 这里的 keys 已经是动态的了，比如 "IOC (14.1)", "IOC (15.1)"
    base_list = st.selectbox(txt["base_list"], sorted(data_dict.keys()))
    
    # 选择对比 (Compare)
    avail_opts = sorted([k for k in data_dict.keys() if k != base_list])
    # 智能默认值：如果没选 IOC，默认勾选一个 IOC 的最新版
    default_vals = []
    ioc_versions = [x for x in avail_opts if "IOC" in x]
    if ioc_versions:
        default_vals = [ioc_versions[-1]] # 选最新的 IOC
        
    compare_lists = st.multiselect(txt["cross_ref"], avail_opts, default=default_vals)

# ==========================================
# 4. 核心合并与显示 (Display)
# ==========================================
main_df = data_dict[base_list].copy()

# 循环合并
for target_name in compare_lists:
    target_df = data_dict[target_name].copy()
    target_sci_names = set(target_df['学名'].values)
    
    # 同义词链接
    def find_link_key(name):
        if name in target_sci_names: return name
        if name in synonym_map:
            alias = synonym_map[name]
            if alias in target_sci_names: return alias
        return None

    main_df['Link_Key'] = main_df['学名'].apply(find_link_key)
    
    # 简化的后缀，去掉括号里的 redundant 信息
    # 例如 "IOC (15.1)" -> "_IOC_15.1"
    suffix = "_" + target_name.replace(" ", "").replace("(", "").replace(")", "")
    
    merged = pd.merge(
        main_df,
        target_df,
        left_on='Link_Key',
        right_on='学名',
        how='left',
        suffixes=('', suffix)
    )
    
    # 清理
    if 'Link_Key' in merged.columns: del merged['Link_Key']
    if '学名' + suffix in merged.columns: del merged['学名' + suffix]
        
    main_df = merged

# 界面显示
st.subheader(txt["col_view"].format(name=base_list))

col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input(txt["search_label"], placeholder=txt["search_placeholder"])

# --- 智能列排序逻辑 ---
# 1. 获取所有存在的列
all_cols = list(main_df.columns)
# 2. 获取当前语言推荐的优先列 (比如日语优先显示 'Japanese')
priority_cols = get_column_priority(lang_code)
# 3. 排序：先放优先列（如果存在），再放剩下的列
final_col_order = []
for c in priority_cols:
    # 模糊匹配列名 (比如 'Japanese' 可以匹配 'Japanese_IOC15.1')
    matched = [existing for existing in all_cols if c in existing or (c == '中文名' and '中文' in existing)]
    for m in matched:
        if m not in final_col_order:
            final_col_order.append(m)

# 把剩下的列补在后面
for c in all_cols:
    if c not in final_col_order:
        final_col_order.append(c)

# 重新排序列
main_df = main_df[final_col_order]
# --------------------

if query:
    mask = main_df.astype(str).apply(lambda x: x.str.lower().str.contains(query.lower())).any(axis=1)
    res = main_df[mask]
    st.info(txt["found_res"].format(count=len(res)))
    st.dataframe(res, use_container_width=True, hide_index=True)
else:
    st.dataframe(main_df.head(200), use_container_width=True, hide_index=True)