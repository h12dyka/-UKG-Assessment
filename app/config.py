import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'ukg-default-secret-key-super-secure-2026')
    DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')

    # Database URI (Mendukung Supabase PostgreSQL / Local)
    # Catatan: SQLAlchemy 2.0 menggunakan prefix 'postgresql+psycopg2://' untuk driver psycopg2
    # raw_db_url = os.getenv(
    #     'DATABASE_URL', 
    #     'postgresql+psycopg2://postgres:postgres@localhost:5432/postgres'
    # )
    # if raw_db_url.startswith('postgres://'):
    #     raw_db_url = raw_db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    # elif raw_db_url.startswith('postgresql://') and not raw_db_url.startswith('postgresql+'):
    #     raw_db_url = raw_db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

    # # Otomatis aktifkan SSL untuk koneksi Supabase Cloud
    # # if ('supabase.co' in raw_db_url or 'pooler.supabase.com' in raw_db_url) and 'sslmode' not in raw_db_url:
    # #     separator = '&' if '?' in raw_db_url else '?'
    # #     raw_db_url += f"{separator}sslmode=require"
        
    # SQLALCHEMY_DATABASE_URI = raw_db_url
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLALCHEMY_ENGINE_OPTIONS = {
    #     'pool_recycle': 60,          # Daur ulang koneksi tiap 60 detik agar selalu segar
    #     'pool_pre_ping': True,        # Tes koneksi sebelum query, buat koneksi baru otomatis jika putus
    #     'connect_args': {
    #         'connect_timeout': 10,
    #         'keepalives': 1,
    #         'keepalives_idle': 30,
    #         'keepalives_interval': 10,
    #         'keepalives_count': 5,
    #     }
    # }
    
        # Database URI (Mendukung SQLite / Supabase PostgreSQL / MySQL)
    raw_db_url = os.getenv('DATABASE_URL', f"sqlite:///{BASE_DIR / 'ukg.db'}")
    if raw_db_url.startswith('postgres://'):
        raw_db_url = raw_db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif raw_db_url.startswith('postgresql://') and not raw_db_url.startswith('postgresql+'):
        raw_db_url = raw_db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    is_postgres = raw_db_url.startswith('postgresql') or raw_db_url.startswith('postgres')
    if is_postgres:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_recycle': 60,
            'pool_pre_ping': True,
            'connect_args': {
                'connect_timeout': 10,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
            }
        }
    else:
        # SQLite / MySQL (tanpa argumen khusus postgres)
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
        }

    # Uploads (Kapasitas Maksimal 100 MB)
    UPLOAD_FOLDER = BASE_DIR / os.getenv('UPLOAD_FOLDER', 'app/uploads/submissions')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 104857600))
    ALLOWED_EXTENSIONS = {
        'xlsx', 'xls', 'csv',
        'pdf', 'docx', 'doc',
        'pptx', 'ppt',
        'sb3', 'sb',
        'cpp', 'c', 'pas', 'py', 'java', 'js', 'html', 'css', 'txt',
        'png', 'jpg', 'jpeg', 'webp',
        'zip'
    }

    # AI Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')
