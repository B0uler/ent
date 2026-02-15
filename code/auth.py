import bcrypt
from code.db_helpers import get_db_connection, update_user as db_update_user, delete_user as db_delete_user, get_user_by_username

def hash_password(password):
    """Хеширует пароль."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def add_user(username, password, name="", admin=0):
    """Добавляет нового пользователя."""
    with get_db_connection() as conn:
        hashed_password = hash_password(password)
        conn.cursor().execute("INSERT INTO users (username, password, name, admin) VALUES (?, ?, ?, ?)", (username, hashed_password, name, admin))
        conn.commit()

def check_password(username, password):
    """Проверяет пароль пользователя и возвращает его роль."""
    with get_db_connection() as conn:
        result = conn.cursor().execute("SELECT password, name, admin FROM users WHERE username = ?", (username,)).fetchone()
    if result:
        hashed_password_db, name, admin_status = result
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password_db.encode('utf-8')):
            # Определяем роль на основе значения admin_status
            if admin_status == 2:
                role = 'admin'
            elif admin_status == 1:
                role = 'editor'
            else:
                role = 'user'
            return True, name, role
    # В случае неудачи возвращаем роль 'user' по умолчанию
    return False, None, 'user'

def update_user(username, new_name=None, new_admin_status=None, new_username=None, new_password=None):
    """Обновляет информацию о пользователе."""
    hashed_password = hash_password(new_password) if new_password else None
    db_update_user(username, new_name=new_name, new_admin_status=new_admin_status, new_username=new_username, new_password=hashed_password)

def delete_user(username):
    """Удаляет пользователя."""
    db_delete_user(username)
