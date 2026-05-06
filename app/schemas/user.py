from pydantic import BaseModel

class UserRegistration(BaseModel):
    name:str
    lastname: str
    username: str
    email: str
    password:str
