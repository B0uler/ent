import sqlite3
import os
import streamlit as st
import base64
from code.ftp_helpers import download_file_from_ftp, delete_file_from_ftp

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_FILE = 'app.db'

def get_db_connection():
    """Возвращает соединение с базой данных с row_factory и поддержкой многопоточности."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализирует базу данных и создает таблицы, если они не существуют."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT NOT NULL UNIQUE, password TEXT NOT NULL, name TEXT, admin INTEGER DEFAULT 0
            )
        ''')
        try:
            c.execute('ALTER TABLE users ADD COLUMN admin INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass # Колонка уже существует
        c.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, description TEXT
            )
        ''')
        conn.commit()

def get_table_names():
    with get_db_connection() as conn: 
        return [row['name'] for row in conn.cursor().execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('users', 'tags')")]

def get_records(table_name, search_query=""):
    if not table_name: return []
    with get_db_connection() as conn:
        sql_query = f'SELECT "{table_name}" as source_table, rowid, * FROM "{table_name}"'
        params = []
        if search_query: sql_query += ' WHERE "Путь" LIKE ?'; params.append(f'%{search_query}%')
        return conn.cursor().execute(sql_query, params).fetchall()

def global_search_records(search_query):
    if not search_query: return []
    with get_db_connection() as conn:
        table_names = get_table_names()
        if not table_names: return []
        union_parts = [f'SELECT "{table}" as source_table, rowid, * FROM "{table}" WHERE "Путь" LIKE ?' for table in table_names]
        sql_query = " UNION ALL ".join(union_parts)
        params = [f'%{search_query}%'] * len(table_names)
        return conn.cursor().execute(sql_query, params).fetchall()

def search_public(text_query="", tag_list=[]):
    """Выполняет публичный поиск по тексту и тегам."""
    with get_db_connection() as conn:
        table_names = get_table_names()
        if not table_names: return []

        where_clauses = []
        params_for_one_table = []
        if text_query:
            where_clauses.append('"Путь" LIKE ?')
            params_for_one_table.append(f'%{text_query}%')
        if tag_list:
            for tag in tag_list:
                where_clauses.append('"," || tags || "," LIKE ?')
                params_for_one_table.append(f'%,{tag},%')
        
        if not where_clauses: return []

        select_parts = []
        for table in table_names:
            query = f'SELECT "{table}" as source_table, "Путь", "Подфайл", "Комментарий", "Фото", "tags" FROM "{table}"'
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            select_parts.append(query)
        
        final_sql = " UNION ALL ".join(select_parts)
        final_params = params_for_one_table * len(table_names)

        if not final_sql or not final_params: return []

        return conn.cursor().execute(final_sql, final_params).fetchall()

def get_record_by_id(table_name, rowid):
    with get_db_connection() as conn: return conn.cursor().execute(f'SELECT rowid, * FROM "{table_name}" WHERE rowid = ?', (rowid,)).fetchone()

def update_record(table_name, rowid, comment, tags, photo_path):
    with get_db_connection() as conn: conn.cursor().execute(f'UPDATE "{table_name}" SET "Комментарий" = ?, "tags" = ?, "Фото" = ? WHERE rowid = ?', (comment, tags, photo_path, rowid)); conn.commit()

def delete_record(table_name, rowid):
    record = get_record_by_id(table_name, rowid)
    if record and record['Фото']:
        delete_file_from_ftp(record['Фото'])
    with get_db_connection() as conn: conn.cursor().execute(f'DELETE FROM "{table_name}" WHERE rowid = ?', (rowid,)); conn.commit()

def get_all_tags():
    with get_db_connection() as conn: return [row['name'] for row in conn.cursor().execute("SELECT name FROM tags ORDER BY name")]

def add_new_tag(name, description):
    with get_db_connection() as conn: conn.cursor().execute("INSERT INTO tags (name, description) VALUES (?, ?)", (name, description)); conn.commit()

def update_tag(tag_id, new_name, new_description):
    with get_db_connection() as conn: conn.cursor().execute("UPDATE tags SET name = ?, description = ? WHERE id = ?", (new_name, new_description, tag_id)); conn.commit()

def delete_tag(tag_id):
    with get_db_connection() as conn: conn.cursor().execute("DELETE FROM tags WHERE id = ?", (tag_id,)); conn.commit()

def get_all_users():
    with get_db_connection() as conn: return conn.cursor().execute("SELECT rowid, username, name, admin FROM users").fetchall()

def get_user_by_username(username):
    with get_db_connection() as conn:
        return conn.cursor().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

def update_user(username, new_name=None, new_admin_status=None, new_username=None, new_password=None):
    with get_db_connection() as conn:
        updates = []
        params = []
        if new_name is not None:
            updates.append("name = ?")
            params.append(new_name)
        if new_admin_status is not None:
            updates.append("admin = ?")
            params.append(new_admin_status)
        if new_username is not None:
            updates.append("username = ?")
            params.append(new_username)
        if new_password is not None:
            updates.append("password = ?")
            params.append(new_password)
        
        if updates:
            params.append(username)
            conn.cursor().execute(f"UPDATE users SET {', '.join(updates)} WHERE username = ?", tuple(params))
            conn.commit()

def delete_user(username):
    with get_db_connection() as conn: conn.cursor().execute("DELETE FROM users WHERE username = ?", (username,)); conn.commit()

def get_image_as_base64(path):
    """Downloads an image from FTP and returns it as a base64 string."""
    image_data = download_file_from_ftp(path)
    if image_data:
        return base64.b64encode(image_data.getvalue()).decode()
    return None
