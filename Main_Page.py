import streamlit as st
import os
import sys

# --- Импорты и настройка пути ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from code.db_helpers import init_db, get_all_tags, search_public, get_image_as_base64, BASE_DIR
from code.i18n import t, language_selector
from code.auth import check_password, add_user

# --- 1. Настройка, инициализация и CSS ---
st.set_page_config(
    page_title=t('sidebar_home'),
    page_icon="🏠",
    layout="wide",
)
RECORDS_PER_PAGE = 30
init_db()

st.markdown("""
<style>
.img-container {
    width: 150px; height: 100px; display: flex; justify-content: center;
    align-items: center; background-color: var(--secondary-background-color); border-radius: 0.5rem;
}
.img-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
</style>
""", unsafe_allow_html=True)

# --- 2. Инициализация состояния сессии ---
if 'lang' not in st.session_state:
    st.session_state.lang = 'en'
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'main_search_query' not in st.session_state:
    st.session_state.main_search_query = ""
if 'main_selected_tags' not in st.session_state:
    st.session_state.main_selected_tags = []
if 'main_search_results' not in st.session_state:
    st.session_state.main_search_results = []
if 'main_current_page' not in st.session_state:
    st.session_state.main_current_page = 1

# --- 3. Боковая панель ---
language_selector()
st.sidebar.divider()
if st.session_state.get('authenticated'):
    st.sidebar.success(f"{t('logged_in_as_sidebar')} **{st.session_state.name}**")

# --- 4. UI и логика главной страницы ---
st.title(t('app_title'))
st.write(t('search_title'))

all_tags = get_all_tags()
c1, c2 = st.columns([2, 1])
search_query = c1.text_input(t('search_by_path'), st.session_state.get('main_search_query', ''))
selected_tags = c2.multiselect(t('filter_by_tags'), options=all_tags, default=st.session_state.get('main_selected_tags', []))

if st.button(t('find_button')):
    st.session_state.main_search_query = search_query
    st.session_state.main_selected_tags = selected_tags
    st.session_state.main_current_page = 1
    with st.spinner(t('searching_spinner')):
        st.session_state.main_search_results = search_public(text_query=search_query, tag_list=selected_tags)
    st.rerun()

# --- Отображение результатов ---
search_results = st.session_state.get('main_search_results', [])
if search_results:
    total_records = len(search_results)
    total_pages = max(1, (total_records + RECORDS_PER_PAGE - 1) // RECORDS_PER_PAGE)
    current_page = st.session_state.get('main_current_page', 1); current_page = min(current_page, total_pages); st.session_state.main_current_page = current_page
    start_idx, end_idx = (current_page - 1) * RECORDS_PER_PAGE, current_page * RECORDS_PER_PAGE
    records_to_display = search_results[start_idx:end_idx]
    
    st.write(f"{t('records_found')} {total_records}")
    st.divider()

    cols = st.columns([2, 4, 2, 3, 2, 2])
    cols[0].subheader(t('table_header_table')); cols[1].subheader(t('table_header_path')); cols[2].subheader(t('table_header_subfile'))
    cols[3].subheader(t('table_header_comment')); cols[4].subheader(t('table_header_photo')); cols[5].subheader(t('table_header_tags'))

    for r in records_to_display:
        row_cols = st.columns([2, 5, 1, 3, 2, 2])
        row_cols[0].write(r['source_table'])
        row_cols[1].markdown(f"`{r['Путь']}`")
        row_cols[2].write(r['Подфайл'] or '')
        row_cols[3].write(r['Комментарий'] or '')
        if r['Фото']:
            b64_image = get_image_as_base64(r['Фото'])
            if b64_image:
                row_cols[4].markdown(f'<div class="img-container"><img src="data:image/png;base64,{b64_image}"></div>', unsafe_allow_html=True)
            else:
                row_cols[4].markdown('<div class="img-container">---</div>', unsafe_allow_html=True)
        else:
            row_cols[4].markdown('<div class="img-container">---</div>', unsafe_allow_html=True)
        row_cols[5].write(r['tags'] or '')
        st.divider()

    p1, p2, p3 = st.columns([3, 1, 3])
    if p1.button(t('pagination_prev'), disabled=(current_page <= 1)):
        st.session_state.main_current_page -= 1; st.rerun()
    p2.write(f"{t('pagination_page')} {current_page} {t('pagination_of')} {total_pages}")
    if p3.button(t('pagination_next'), disabled=(current_page >= total_pages)):
        st.session_state.main_current_page += 1; st.rerun()
elif st.session_state.get('main_search_query') or st.session_state.get('main_selected_tags'):
    st.info(t('no_records_found'))
