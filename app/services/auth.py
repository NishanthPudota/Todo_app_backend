from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models.database import User
from typing import Optional


class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def get_user_by_username(self, username: str, db: Session) -> Optional[User]:
        return db.query(User).filter(User.name == username).first()

    def create_user(self, username: str, password: str, db: Session) -> User:
        hashed_password = self.get_password_hash(password)
        user = User(name=username, passwordhash=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate_user(self, username: str, password: str, db: Session) -> Optional[User]:
        user = self.get_user_by_username(username, db)
        if not user:
            return None
        if not self.verify_password(password, user.passwordhash):
            return None
        return user


auth_service = AuthService()
