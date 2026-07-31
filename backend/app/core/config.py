import os
from dotenv import load_dotenv

# WHY this line is the fix: load_dotenv() reads the .env file and copies its
# contents into os.environ BEFORE any os.getenv() calls below run. Without
# it, .env is just an inert text file Python never looks at.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cams_user:cams_pass@localhost:5432/retail_db")
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_RETAIL_KEY_9921_ATTENTION_MAPPING")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60