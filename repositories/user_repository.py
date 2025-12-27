from __future__ import annotations

from typing import Optional, List

from sqlmodel import Session, select

from db.models import User


def get_by_email(session: Session, email: str) -> Optional[User]:
    return session.exec(select(User).where(User.email == email)).first()


def get_by_name(session: Session, name: str) -> Optional[User]:
    return session.exec(select(User).where(User.name == name)).first()


def create_user(session: Session, name: str, email: str, hashed_password: str, role: str = "USUARIO") -> User:
    user = User(name=name, email=email, hashed_password=hashed_password, role=role)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def list_all(session: Session) -> List[User]:
    return session.exec(select(User).order_by(User.name)).all()


def set_role(session: Session, user_id: int, role: str) -> Optional[User]:
    user = session.get(User, user_id)
    if user is None:
        return None
    user.role = role
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_access_info(session: Session, user: User, *, action: str | None = None) -> User:
    user.access_count = (user.access_count or 0) + 1
    from datetime import datetime

    user.last_access_at = datetime.utcnow()
    if action:
        user.last_action = action
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def delete_user(session: Session, user_id: int) -> bool:
    user = session.get(User, user_id)
    if user is None:
        return False
    session.delete(user)
    session.commit()
    return True


def set_alert(
    session: Session,
    user_id: int,
    *,
    message: str | None,
    priority: str | None,
    sender: str | None,
) -> Optional[User]:
    user = session.get(User, user_id)
    if user is None:
        return None
    user.alert_message = message if message else None
    user.alert_priority = priority if priority else None
    user.alert_sender = sender if sender else None
    from datetime import datetime

    user.alert_created_at = datetime.utcnow() if message and priority else None
    user.alert_ack_at = None  # reset acknowledgment on new message
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def ack_alert(session: Session, user_id: int) -> Optional[User]:
    user = session.get(User, user_id)
    if user is None:
        return None
    from datetime import datetime

    now = datetime.utcnow()
    user.alert_ack_at = now
    user.alert_message = None
    user.alert_priority = None
    user.alert_sender = None
    user.alert_created_at = None
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
