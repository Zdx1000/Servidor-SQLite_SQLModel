from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from db.models import User


def get_by_email(session: Session, email: str) -> Optional[User]:
    return session.exec(select(User).where(User.email == email)).first()


def get_by_name(session: Session, name: str) -> Optional[User]:
    return session.exec(select(User).where(User.name == name)).first()


def create_user(session: Session, name: str, email: str, hashed_password: str) -> User:
    user = User(name=name, email=email, hashed_password=hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
