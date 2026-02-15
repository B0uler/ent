from ftplib import FTP_TLS, error_perm
import io
import os

# FTP Configuration (formerly from config.py)
# В целях безопасности, рекомендуется хранить учетные данные
# не в коде, а в переменных окружения или другом безопасном месте.
FTP_HOST = "135.181.181.70"
FTP_PORT = 21
FTP_USER = "u162459_project"
FTP_PASS = "jX1hC4wO4n"
FTP_IMG_DIR = "img"

def get_ftp_connection():
    """Создает и возвращает FTP-соединение с использованием TLS."""
    try:
        ftp = FTP_TLS()
        ftp.connect(FTP_HOST, FTP_PORT)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p() # Включаем шифрование для канала данных
        return ftp
    except Exception as e:
        print(f"FTP connection failed: {e}")
        return None

def create_ftp_directory_recursive(ftp, path):
    """
    Рекурсивно создает директории на FTP-сервере.
    path - абсолютный путь на FTP-сервере, который нужно создать.
    """
    # Нормализуем путь для FTP (используем /)
    path = path.replace("\\", "/")
    parts = [p for p in path.split('/') if p]

    # Возвращаемся в корень, чтобы строить путь с нуля
    try:
        ftp.cwd('/')
    except error_perm:
        print("Warning: Could not change to FTP root directory. Assuming current directory is root.")
    except Exception as e:
        print(f"Error changing to FTP root: {e}")
        return False

    # Последовательно создаем директории
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
    """Загружает файл в FTP."""
    ftp = get_ftp_connection()
    if not ftp:
        return False
    try:
        # Нормализуем путь и извлекаем директорию
        remote_path = remote_path.replace("\\", "/")
        remote_dir = os.path.dirname(remote_path)

        # Создаем все необходимые директории рекурсивно
        if not create_ftp_directory_recursive(ftp, remote_dir):
            print(f"Failed to ensure remote directory structure for {remote_dir}")
            return False
        
        # create_ftp_directory_recursive оставляет нас в конечной директории (remote_dir),
        # поэтому дополнительный переход ftp.cwd(remote_dir) не нужен.

        file_object.seek(0)
        ftp.storbinary(f'STOR {os.path.basename(remote_path)}', file_object)
        return True
    except Exception as e:
        print(f"FTP upload failed: {e}")
        return False
    finally:
        ftp.quit()

def download_file_from_ftp(remote_path):
    """Скачивает файл с FTP в виде байтового объекта."""
    ftp = get_ftp_connection()
    if not ftp:
        print("DEBUG: download_file_from_ftp - No FTP connection.")
        return None
    try:
        # Нормализуем путь для FTP, заменяя бэкслэши и обеспечивая абсолютный путь от корня.
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
    finally:
        if ftp:
            try:
                ftp.quit()
                print("DEBUG: FTP connection quit.")
            except Exception as e:
                print(f"DEBUG: Error quitting FTP connection: {e}")

def delete_file_from_ftp(remote_path):
    """Удаляет файл с FTP."""
    ftp = get_ftp_connection()
    if not ftp:
        return False
    try:
        # Нормализуем путь для FTP, заменяя бэкслэши и обеспечивая абсолютный путь от корня.
        full_remote_path = remote_path.replace("\\", "/")
        if not full_remote_path.startswith('/'):
            full_remote_path = '/' + full_remote_path

        ftp.delete(full_remote_path)
        return True
    except Exception as e:
        print(f"FTP delete failed: {e}")
        return None
    finally:
        ftp.quit()