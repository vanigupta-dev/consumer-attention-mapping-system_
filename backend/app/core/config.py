import os

# We specify 'postgres' as user, 'admin123' as your password, and 'retail_db' as your database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/retail_db")
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_RETAIL_KEY_9921_ATTENTION_MAPPING")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60