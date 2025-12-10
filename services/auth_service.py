from __future__ import annotations

import re
from typing import Optional

from passlib.context import CryptContext
from sqlmodel import Session

from db.models import User
from repositories import user_repository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthError(Exception):
    pass


def _validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise AuthError("A senha deve ter pelo menos 8 caracteres.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise AuthError("A senha deve conter letras e números.")
    if len(password.encode()) > 72:
        raise AuthError("A senha não pode passar de 72 bytes (limite do bcrypt).")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def register_user(self, name: str, email: str, password: str) -> User:
        name = name.strip()
        email = email.strip().lower()
        if not name or not email or not password:
            raise AuthError("Nome, e-mail e senha são obrigatórios.")

        _validate_password_strength(password)

        if user_repository.get_by_email(self.session, email):
            raise AuthError("E-mail já cadastrado.")
        if user_repository.get_by_name(self.session, name):
            raise AuthError("Nome de usuário já cadastrado.")

        hashed = hash_password(password)
        return user_repository.create_user(self.session, name=name, email=email, hashed_password=hashed)

    def authenticate(self, identifier: str, password: str) -> Optional[User]:
        identifier = identifier.strip().lower()
        if not identifier or not password:
            return None

        user = user_repository.get_by_email(self.session, identifier)
        if user is None:
            user = user_repository.get_by_name(self.session, identifier)
        if user is None:
            return None

        if verify_password(password, user.hashed_password):
            return user
        return None
