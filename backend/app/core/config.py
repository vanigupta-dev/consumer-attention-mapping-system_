import os
from dotenv import load_dotenv


load_dotenv()  # Reads the .env file automatically

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cams_user:cams_pass@localhost:5432/retail_db")
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_RETAIL_KEY_9921_ATTENTION_MAPPING")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60