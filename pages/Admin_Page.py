import streamlit as st
import sqlite3
import os
import sys
import glob
import shutil
from datetime import datetime
from code.auth import check_password, add_user, update_user, delete_user
from code.db_helpers import (
    get_db_connection, 
    get_table_names, get_records, global_search_records, 
    get_record_by_id, update_record, delete_record, get_all_tags, 
    add_new_tag, update_tag, delete_tag,
    get_all_users, DB_FILE, BASE_URL
)
from code.i18n import t, language_selector
from code.ftp_helpers import upload_file_to_ftp, FTP_IMG_DIR

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# --- Настройка страницы и CSS ---
st.set_page_config(page_title=t('sidebar_admin'), page_icon="⚙️", layout="wide")
st.markdown("""
<style>
.img-container-admin, .edit-img-container {
    display: flex; justify-content: center; align-items: center; 
    background-color: var(--secondary-background-color); border-radius: 0.5rem;
}
.img-container-admin { width: 150px; height: 100px; }
.edit-img-container { width: 200px; height: 150px; margin-bottom: 1rem; }
.img-container-admin img, .edit-img-container img {
    max-width: 100%; max-height: 100%; object-fit: contain;
}
</style>
""", unsafe_allow_html=True)

# --- 1. Константы ---
RECORDS_PER_PAGE = 30

# --- 2. UI Функции ---
def login_form():
    st.title(t('login_form_title'))
    with st.form("Login"):
        username, password = st.text_input(t('login_form_username')), st.text_input(t('login_form_password'), type="password")
        if st.form_submit_button(t('login_form_button')):
            is_valid, user_name, role = check_password(username, password)
            if is_valid:
                st.session_state.update({'authenticated': True, 'username': username, 'name': user_name, 'role': role}); st.rerun()
            else: st.error(t('login_form_error'))

def role_management_tab():
    st.header(t('user_management_title'))

    ROLES = {t('role_admin'): 2, t('role_editor'): 1, t('role_user'): 0}
    ROLES_REVERSED = {v: k for k, v in ROLES.items()}

    with st.form("add_user_form", clear_on_submit=True):
        st.subheader(t('register_form_title'))
        new_username = st.text_input(t('register_form_username'))
        new_password = st.text_input(t('register_form_new_password'), type="password")
        confirm_password = st.text_input(t('register_form_confirm_password'), type="password")
        new_name = st.text_input(t('register_form_display_name'))
        new_user_role = st.selectbox(t('register_form_role'), options=list(ROLES.keys()))
        
        if st.form_submit_button(t('register_button')):
            if new_password and new_password == confirm_password:
                try:
                    add_user(new_username, new_password, new_name, ROLES[new_user_role])
                    st.success(t('register_success'))
                except sqlite3.IntegrityError:
                    st.error(f"User '{new_username}' already exists.")
            else:
                st.error(t('register_error_password_mismatch'))

    st.divider()

    st.subheader(t('existing_users_subheader'))
    users = get_all_users()
    for user in users:
        if st.session_state.get('editing_user_username') == user['username']:
            with st.form(key=f"edit_user_{user['username']}"):
                st.write(f"**{t('editing_user_form_title')}: {user['username']}**")
                edited_name = st.text_input(t('register_form_display_name'), value=user['name'])
                current_role_name = ROLES_REVERSED.get(user['admin'], t('role_user'))
                edited_role = st.selectbox(t('register_form_role'), options=list(ROLES.keys()), index=list(ROLES.keys()).index(current_role_name))
                edited_password = st.text_input(t('register_form_new_password'), type="password")

                c1, c2 = st.columns(2)
                if c1.form_submit_button(t('save_button')):
                    update_user(username=user['username'], new_name=edited_name, new_password=edited_password if edited_password else None, new_admin_status=ROLES[edited_role])
                    st.session_state.editing_user_username = None
                    st.rerun()
                if c2.form_submit_button(t('cancel_button')):
                    st.session_state.editing_user_username = None
                    st.rerun()
        else:
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1, 1])
            c1.write(user['username'])
            c2.write(user['name'])
            c3.write(ROLES_REVERSED.get(user['admin'], t('role_user')))
            if c4.button(t('edit_button'), key=f"edit_user_{user['username']}"):
                st.session_state.editing_user_username = user['username']
                st.rerun()
            if user['username'] != st.session_state.get('username'):
                if c5.button(t('delete_button'), key=f"del_user_{user['username']}"):
                    st.session_state.deleting_user_username = user['username']
                    st.rerun()
        st.divider()

def db_management_tab():
    st.header(t('db_management_title'))

    # --- Backup ---
    st.subheader(t('db_backup_subheader'))
    if st.button(t('db_create_backup_button')):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"
            shutil.copyfile(DB_FILE, backup_filename)
            st.success(t('db_backup_success').format(filename=backup_filename))
        except Exception as e:
            st.error(t('db_backup_error').format(error=e))

    st.divider()

    # --- Restore ---
    st.subheader(t('db_restore_subheader'))
    backup_files = sorted(glob.glob("backup_*.db"), reverse=True)
    
    if not backup_files:
        st.info(t('db_no_backups_found'))
    else:
        selected_backup = st.selectbox(t('db_select_backup_label'), backup_files)
        if selected_backup:
            col1, col2 = st.columns(2)
            
            with open(selected_backup, "rb") as f:
                col1.download_button(t('db_download_button'), f, file_name=selected_backup)

            if col2.button(t('db_restore_button'), key=f"restore_{selected_backup}"):
                st.session_state.confirming_restore = selected_backup

            if st.session_state.get('confirming_restore') == selected_backup:
                st.warning(t('db_restore_confirm_warning').format(filename=selected_backup))
                c1, c2 = st.columns(2)
                if c1.button(t('db_restore_confirm_button'), key=f"confirm_restore_{selected_backup}"):
                    try:
                        shutil.copyfile(selected_backup, DB_FILE)
                        st.success(t('db_restore_success'))
                        st.session_state.confirming_restore = None
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(t('db_restore_error').format(error=e))
                if c2.form_submit_button(t('cancel_button')):
                    st.session_state.confirming_restore = None
                    st.rerun()

    st.divider()
    st.subheader(t('db_restore_from_upload_subheader'))
    uploaded_backup = st.file_uploader(t('db_upload_backup_label'), type=['db'])
    if uploaded_backup:
        st.warning(t('db_restore_upload_warning'))
        if st.button(t('db_restore_from_upload_button')):
            try:
                with open(DB_FILE, "wb") as f:
                    f.write(uploaded_backup.getbuffer())
                st.success(t('db_restore_success'))
                st.experimental_rerun()
            except Exception as e:
                st.error(t('db_restore_error').format(error=e))

# --- 3. Боковая панель ---
language_selector()
if st.session_state.get('authenticated'):
    st.sidebar.success(f"{t('logged_in_as_sidebar')} **{st.session_state.name}**")

# --- 4. Основная логика страницы ---
st.title(t('admin_panel_title'))

if not st.session_state.get('authenticated'):
    login_form()
elif st.session_state.get('role') not in ['admin', 'editor']:
    st.error(t('permission_denied'))
else: 
    user_role = st.session_state.get('role', 'user')
    is_admin = user_role == 'admin'

    tab_definitions = [t('tab_records'), t('tab_tags')]
    if is_admin:
        tab_definitions.extend([t('tab_user_management'), t('tab_db_management')])
    
    tabs = st.tabs(tab_definitions)

    with tabs[0]: # Records
        # We need the table options for initialization and for the widget
        table_options = [t('all_tables')] + get_table_names()

        # Initialize state for search and pagination if not already set
        if 'admin_selected_table' not in st.session_state:
            st.session_state.admin_selected_table = table_options[0]
        if 'admin_search_query' not in st.session_state:
            st.session_state.admin_search_query = ''
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 1
        
        editing_info = st.session_state.get('editing_record_info')
        if editing_info:
            record = get_record_by_id(editing_info['table'], editing_info['rowid'])
            if record:
                with st.form(key=f"edit_form_{record['rowid']}"):
                    st.subheader(f"{t('edit_form_title')} `{record['Путь']}`")
                    
                    image_path = record['Фото_thumb'] if 'Фото_thumb' in record.keys() and record['Фото_thumb'] else record['Фото']
                    if image_path:
                        image_url = image_path if image_path.startswith('http') else BASE_URL + image_path
                        st.markdown(f'<div class="edit-img-container"><img src="{image_url}"></div>', unsafe_allow_html=True)
                    
                    comment = st.text_area(t('edit_form_comment'), record['Комментарий'] or "")
                    all_tags_suggestions = get_all_tags()
                    current_tags = record['tags'].split(',') if record['tags'] else []
                    current_tags = [tag.strip() for tag in current_tags if tag.strip()]
                    selected_tags = st.multiselect(t('edit_form_tags'), options=all_tags_suggestions, default=current_tags)
                    
                    uploaded_file = None
                    if is_admin:
                        uploaded_file = st.file_uploader(t('edit_form_photo'))

                    save_col, detach_col, cancel_col = None, None, None
                    if is_admin:
                        save_col, detach_col, cancel_col = st.columns(3)
                    else:
                        save_col, cancel_col = st.columns(2)

                    if save_col.form_submit_button(t('save_button')):
                        tags_to_save = ",".join(selected_tags)
                        photo_url = record['Фото']
                        thumb_url = record['Фото_thumb'] if 'Фото_thumb' in record.keys() and record['Фото_thumb'] else None

                        if is_admin and uploaded_file:
                            ftp_dir = os.path.dirname(record['Путь']).replace("\\", "/")
                            ftp_path = os.path.join(FTP_IMG_DIR, ftp_dir, uploaded_file.name)
                            
                            new_ftp_path, new_thumb_ftp_path = upload_file_to_ftp(uploaded_file, ftp_path)
                            
                            if new_ftp_path:
                                photo_url = BASE_URL + new_ftp_path
                                thumb_url = BASE_URL + new_thumb_ftp_path if new_thumb_ftp_path else None
                                st.success("File uploaded successfully!")
                            else:
                                st.error("Failed to upload file.")
                        
                        update_record(editing_info['table'], record['rowid'], comment, tags_to_save, photo_url, thumb_url)
                        st.session_state.editing_record_info = None
                        st.rerun()

                    if is_admin and detach_col and detach_col.form_submit_button(t('detach_button')):
                        update_record(editing_info['table'], record['rowid'], comment, record['tags'], '', '')
                        st.session_state.editing_record_info = None
                        st.rerun()
                        
                    if cancel_col.form_submit_button(t('cancel_button')):
                        st.session_state.editing_record_info = None
                        st.rerun()
        else:
            st.header(t('tab_records'))
            c1, c2 = st.columns([1, 2])
            
            # The selectbox value is now controlled by the session state
            # We must ensure the index is correct on each run
            try:
                current_table_index = table_options.index(st.session_state.admin_selected_table)
            except ValueError:
                current_table_index = 0 # Default to 'all_tables'

            selected_table = c1.selectbox(
                t('table_header_table'), 
                table_options, 
                index=current_table_index, 
                key='admin_selected_table'
            )
            search_query = c2.text_input(t('search_by_text'), key='admin_search_query')
            
            all_records = []
            if selected_table == t('all_tables'):
                if search_query: all_records = global_search_records(search_query)
                else: st.info(t('enter_query_global_search'))
            else:
                all_records = get_records(selected_table, search_query)

            if all_records:
                total_records = len(all_records)
                total_pages = max(1, (total_records + RECORDS_PER_PAGE - 1) // RECORDS_PER_PAGE)
                current_page = st.session_state.get('current_page', 1)
                current_page = min(current_page, total_pages)
                st.session_state.current_page = current_page

                start_idx = (current_page - 1) * RECORDS_PER_PAGE
                end_idx = current_page * RECORDS_PER_PAGE
                records_to_display = all_records[start_idx:end_idx]

                st.write(f"{t('records_found')} {total_records}")
                
                cols_def = [2, 5, 2, 3, 2, 1]
                if is_admin:
                    cols_def.append(1)
                
                cols = st.columns(cols_def)
                cols[0].subheader(t('table_header_table'))
                cols[1].subheader(t('table_header_path'))
                cols[2].subheader(t('table_header_subfile'))
                cols[3].subheader(t('table_header_comment'))
                cols[4].subheader(t('table_header_photo'))

                deleting_info = st.session_state.get('deleting_record_info')
                for r in records_to_display:
                    row_cols = st.columns(cols_def)
                    row_cols[0].write(r['source_table'])
                    row_cols[1].markdown(f"`{r['Путь']}`")
                    row_cols[2].write(r['Подфайл'] or '')
                    row_cols[3].write(r['Комментарий'] or '')
                    image_path = r['Фото_thumb'] if 'Фото_thumb' in r.keys() and r['Фото_thumb'] else r['Фото']
                    if image_path:
                        image_url = image_path if image_path.startswith('http') else BASE_URL + image_path
                        row_cols[4].markdown(f'<div class="img-container-admin"><img src="{image_url}"></div>', unsafe_allow_html=True)
                    else:
                        row_cols[4].markdown('<div class="img-container-admin">---</div>', unsafe_allow_html=True)

                    if row_cols[5].button(t('edit_button'), key=f"edit_{r['rowid']}"):
                        st.session_state.editing_record_info = {'table': r['source_table'], 'rowid': r['rowid']}
                        st.rerun()

                    if is_admin:
                        if deleting_info and deleting_info['rowid'] == r['rowid']:
                            row_cols[6].write(t('are_you_sure')) 
                            if row_cols[6].button(t('confirm_delete_button'), key=f"del_confirm_{r['rowid']}"):
                                delete_record(deleting_info['table'], deleting_info['rowid'])
                                st.session_state.deleting_record_info = None
                                st.rerun()
                        else:
                            if row_cols[6].button(t('delete_button'), key=f"del_{r['rowid']}"):
                                st.session_state.deleting_record_info = {'table': r['source_table'], 'rowid': r['rowid']}
                                st.rerun()
                st.divider()
                p1,p2,p3 = st.columns([3,1,3]);
                if p1.button(t('pagination_prev'), disabled=current_page<=1): st.session_state.current_page-=1; st.rerun()
                p2.write(f"{t('pagination_page')} {current_page} {t('pagination_of')} {total_pages}")
                if p3.button(t('pagination_next'), disabled=current_page>=total_pages): st.session_state.current_page+=1; st.rerun()

    with tabs[1]:
        st.header(t('tag_management_title'))
        
        if is_admin:
            with st.form("add_tag_form", clear_on_submit=True):
                st.subheader(t('create_new_tag_subheader'))
                new_tag_name = st.text_input(t('tag_name_label'))
                new_tag_desc = st.text_area(t('tag_desc_label'))
                if st.form_submit_button(t('create_button')):
                    if new_tag_name:
                        try:
                            add_new_tag(new_tag_name, new_tag_desc)
                            st.success(t('tag_create_success').format(tag_name=new_tag_name))
                        except sqlite3.IntegrityError:
                            st.error(t('tag_create_error_exists').format(tag_name=new_tag_name))
                    else:
                        st.warning(t('tag_create_error_empty'))
            st.divider()

        tag_records = []
        with get_db_connection() as conn:
            tag_records = conn.cursor().execute("SELECT id, name, description FROM tags ORDER BY name").fetchall()
        
        st.subheader(f"{t('existing_tags_subheader')} ({len(tag_records)})")
        for tag in tag_records:
            if st.session_state.get('editing_tag_id') == tag['id']:
                with st.form(key=f"edit_tag_{tag['id']}"):
                    edited_name = st.text_input(t('tag_name_label'), value=tag['name'])
                    edited_desc = st.text_area(t('tag_desc_label'), value=tag['description'] or "")
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button(t('save_button')):
                        update_tag(tag['id'], edited_name, edited_desc)
                        st.session_state.editing_tag_id = None
                        st.rerun()
                    if c2.form_submit_button(t('cancel_button')):
                        st.session_state.editing_tag_id = None
                        st.rerun()
            else:
                cols_def = [2, 4, 1]
                if is_admin:
                    cols_def.append(1)
                
                row_cols = st.columns(cols_def)

                row_cols[0].write(f"**{tag['name']}**")
                row_cols[1].write(tag['description'] or "---")
                
                if row_cols[2].button(t('edit_button'), key=f"edit_tag_{tag['id']}"):
                    st.session_state.editing_tag_id = tag['id']
                    st.rerun()

                if is_admin:
                    if st.session_state.get('deleting_tag_id') == tag['id']:
                        if row_cols[3].button(t('confirm_delete_button'), key=f"del_confirm_tag_{tag['id']}"):
                            delete_tag(tag['id'])
                            st.session_state.deleting_tag_id = None
                            st.rerun()
                    else:
                        if row_cols[3].button(t('delete_button'), key=f"del_tag_{tag['id']}"):
                            st.session_state.deleting_tag_id = {'table': 'tags', 'id': tag['id']}
                            st.rerun()
            st.divider()

    if is_admin:
        with tabs[2]:
            role_management_tab()
        with tabs[3]:
            db_management_tab()