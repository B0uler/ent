import os
from ftplib import FTP_TLS, error_perm
from code.ftp_helpers import FTP_HOST, FTP_PORT, FTP_USER, FTP_PASS, FTP_IMG_DIR

def check_ftp_directory():
    """
    Подключается к FTP и выводит список файлов в директории img.
    """
    try:
        ftp = FTP_TLS()
        ftp.connect(FTP_HOST, FTP_PORT)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        print("FTP connection successful.")
    except Exception as e:
        print(f"FTP connection failed: {e}")
        return

    try:
        print(f"Attempting to change directory to '{FTP_IMG_DIR}'...")
        ftp.cwd(FTP_IMG_DIR)
        print(f"Successfully changed directory to '{ftp.pwd()}'")
        
        print("Listing files in the directory:")
        files = ftp.nlst()
        if files:
            for file in files:
                print(f"- {file}")
        else:
            print("The directory is empty.")
            
    except error_perm:
        print(f"Error: The directory '{FTP_IMG_DIR}' does not exist on the FTP server.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        ftp.quit()
        print("FTP connection closed.")

if __name__ == '__main__':
    check_ftp_directory()
