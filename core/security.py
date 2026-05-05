from pwdlib import PasswordHash
import jwt
from datetime import datetime,timezone,timedelta
import uuid 

from app.core.settings import settings
passwordhash = PasswordHash.recommended()


SECRET_KEY = settings.SECRET_KEY 
ALGORITHM = settings.ALGORITHM 

def hash_password(plain:str)-> str:
    return passwordhash.hash(plain)

def verify_password(plain:str, hashed:str)-> bool:
    return passwordhash.verify(plain,hashed)

def create_access_token(data:dict,exp_minutes=settings.ACCESS_TOKEN_MIN)->str:
    to_encode = data.copy()

    exp = datetime.now(timezone.utc) +timedelta(minutes=exp_minutes)
    iat = int(datetime.now(timezone.utc).timestamp())
    to_encode.update({"exp":exp,"typ":"access", "iat":iat })

    access_token = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)

    return access_token 

def create_refresh_token(data:dict,exp_days=settings.REFRESH_TOKEN_DAYS)->tuple[str,str]:
    to_encode = data.copy()

    exp = datetime.now(timezone.utc) +timedelta(days=exp_days)
    jti = str(uuid.uuid4())
    iat = int(datetime.now(timezone.utc).timestamp())
    to_encode.update({"exp":exp,"typ":"refresh","jti":jti, "iat":iat })

    refresh_token = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)

    return refresh_token,jti
