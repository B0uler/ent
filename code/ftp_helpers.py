from ftplib import FTP_TLS, error_perm
import io
import os
import streamlit as st
from PIL import Image

# FTP Configuration
FTP_HOST = "135.181.181.70"
FTP_PORT = 21
FTP_USER = "u162459_project"
FTP_PASS = "jX1hC4wO4n"
FTP_IMG_DIR = "img"
THUMBNAIL_DIR = "thumbnails" # Директория для миниатюр
THUMBNAIL_SIZE = (200, 200)

def get_ftp_session():
    """
    Получает существующее FTP-соединение из состояния сессии или создает новое.
    """
    if 'ftp_session' in st.session_state and st.session_state.ftp_session is not None:
        try:
            st.session_state.ftp_session.voidcmd("NOOP")
            return st.session_state.ftp_session
        except (error_perm, EOFError, OSError):
            st.session_state.ftp_session = None

    try:
        ftp = FTP_TLS()
        ftp.connect(FTP_HOST, FTP_PORT)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        st.session_state.ftp_session = ftp
        return ftp
    except Exception as e:
        print(f"FTP connection failed: {e}")
        st.session_state.ftp_session = None
        return None

def close_ftp_session():
    """Закрывает FTP-соединение в состоянии сессии, если оно существует."""
    if 'ftp_session' in st.session_state and st.session_state.ftp_session is not None:
        try:
            st.session_state.ftp_session.quit()
        except Exception as e:
            print(f"Error quitting FTP connection: {e}")
        finally:
            st.session_state.ftp_session = None

def create_ftp_directory_recursive(ftp, path):
    """
    Рекурсивно создает директории на FTP-сервере.
    """
    path = path.replace("\\", "/")
    parts = [p for p in path.split('/') if p]
    try:
        ftp.cwd('/')
    except Exception as e:
        print(f"Error changing to FTP root: {e}")
        return False

    for part in parts:
        try:
            ftp.cwd(part)
        except error_perm:
            try:
                ftp.mkd(part)
                ftp.cwd(part)
            except Exception as e:
                print(f"Failed to create or change to FTP directory {part}: {e}")
                return False
    return True

def upload_file_to_ftp(file_object, remote_path):
    """
    Загружает файл и его миниатюру в FTP, используя сессионное соединение.
    Возвращает кортеж (путь_к_оригиналу, путь_к_миниатюре).
    """
    ftp = get_ftp_session()
    if not ftp:
        return None, None

    try:
        # --- Загрузка оригинала ---
        remote_path = remote_path.replace("\\", "/")
        remote_dir = os.path.dirname(remote_path)
        if not create_ftp_directory_recursive(ftp, remote_dir):
            return None, None
        
        file_object.seek(0)
        ftp.storbinary(f'STOR {os.path.basename(remote_path)}', file_object)

        # --- Создание и загрузка миниатюры ---
        file_object.seek(0)
        img = Image.open(file_object)
        img.thumbnail(THUMBNAIL_SIZE)
        
        thumb_buffer = io.BytesIO()
        img.save(thumb_buffer, format='PNG') # Сохраняем в формате PNG
        thumb_buffer.seek(0)

        # Создаем путь для миниатюры
        thumb_dir = os.path.join(THUMBNAIL_DIR, remote_dir).replace("\\", "/")
        thumb_path = os.path.join(thumb_dir, os.path.basename(remote_path))
        
        if not create_ftp_directory_recursive(ftp, thumb_dir):
            return remote_path, None # Возвращаем хотя бы путь к оригиналу

        ftp.storbinary(f'STOR {os.path.basename(thumb_path)}', thumb_buffer)

        return remote_path, thumb_path

    except Exception as e:
        print(f"FTP upload failed: {e}")
        return None, None

def download_file_from_ftp(remote_path):
    """Скачивает файл с FTP, используя сессионное соединение."""
    ftp = get_ftp_session()
    if not ftp:
        print("DEBUG: download_file_from_ftp - No FTP connection.")
        return None
    try:
        full_remote_path = remote_path.replace("\\", "/")
        if not full_remote_path.startswith('/'):
            full_remote_path = '/' + full_remote_path

        print(f"DEBUG: Attempting to retrieve FTP file: {full_remote_path}")
        bio = io.BytesIO()
        ftp.retrbinary(f'RETR {full_remote_path}', bio.write)
        bio.seek(0)
        print(f"DEBUG: Successfully retrieved {full_remote_path}")
        return bio
    except error_perm as e:
        print(f"DEBUG: FTP file not found or permission error for {full_remote_path}: {e}")
        return None
    except Exception as e:
        print(f"DEBUG: FTP download failed for {full_remote_path}: {e}")
        return None

def delete_file_from_ftp(remote_path):
    """Удаляет файл с FTP, используя сессионное соединение."""
    ftp = get_ftp_session()
    if not ftp:
        return False
    try:
        full_remote_path = remote_path.replace("\\", "/")
        if not full_remote_path.startswith('/'):
            full_remote_path = '/' + full_remote_path

        ftp.delete(full_remote_path)
        return True
    except Exception as e:
        print(f"FTP delete failed: {e}")
        return False
