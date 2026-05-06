from pwdlib import PasswordHash
import jwt
from datetime import datetime,timezone,timedelta
import uuid 
import hashlib
from fastapi import HTTPException

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

def create_refresh_token(data:dict,exp_days=settings.REFRESH_TOKEN_DAYS)->tuple[str,uuid.UUID]:
    to_encode = data.copy()

    exp = datetime.now(timezone.utc) +timedelta(days=exp_days)
    jti = uuid.uuid4()
    iat = int(datetime.now(timezone.utc).timestamp())
    to_encode.update({"exp":exp,"typ":"refresh","jti":str(jti), "iat":iat })

    refresh_token = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)

    return refresh_token,jti

def decode_token(token:str):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def decode_token_or_401(token:str, typ:str):
    try:
        decoded_refresh_token = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if not decoded_refresh_token.get("typ") == typ:
        raise HTTPException(status_code=401, detail="Wrong token sent")
    return decoded_refresh_token

def hash_refresh_token(token:str)-> str:
    return hashlib.sha256(token.encode()).hexdigest()

