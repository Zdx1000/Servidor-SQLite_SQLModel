from __future__ import annotations

from pathlib import Path

from sqlmodel import Session

from db.report_models import ReportRequest
from repositories import report_request_repository
from services.auth_service import AuthError, AuthService


class ReportService:
    def __init__(self, report_session: Session, user_session: Session | None = None) -> None:
        self.report_session = report_session
        self.user_session = user_session

    def request_report(self, title: str, description: str, file_name: str, file_path: str) -> ReportRequest:
        title = title.strip()
        description = description.strip()
        file_name = file_name.strip()
        file_path = file_path.strip()
        if not title or not description:
            raise AuthError("Título e descrição do relatório são obrigatórios.")
        if len(description) < 8:
            raise AuthError("Descrição muito curta. Forneça mais detalhes do relatório.")
        if not file_name or not file_path:
            raise AuthError("Selecione um arquivo para o relatório.")
        if not Path(file_path).exists():
            raise AuthError("Arquivo do relatório não encontrado após o envio.")
        return report_request_repository.create_request(
            self.report_session,
            title=title,
            description=description,
            file_name=file_name,
            file_path=file_path,
        )

    def approve_report_request(self, request_id: int) -> ReportRequest:
        req = report_request_repository.get_by_id(self.report_session, request_id)
        if req is None:
            raise AuthError("Solicitação não encontrada.")
        if req.status != "pendente":
            raise AuthError("Solicitação já foi processada.")
        req.status = "aprovado"
        self.report_session.add(req)
        self.report_session.commit()
        self.report_session.refresh(req)
        return req

    def reject_report_request(self, request_id: int) -> ReportRequest:
        req = report_request_repository.get_by_id(self.report_session, request_id)
        if req is None:
            raise AuthError("Solicitação não encontrada.")
        if req.status != "pendente":
            raise AuthError("Solicitação já foi processada.")
        req.status = "recusado"
        self.report_session.add(req)
        self.report_session.commit()
        self.report_session.refresh(req)
        return req

    def delete_report_request(self, request_id: int, identifier: str, password: str) -> None:
        if self.user_session is None:
            raise AuthError("Sessão de usuários não disponível para validar credenciais.")

        identifier = identifier.strip().lower()
        if not identifier or not password:
            raise AuthError("Informe usuário e senha para excluir o relatório.")

        auth = AuthService(self.user_session)
        user = auth.authenticate(identifier, password)
        if user is None:
            raise AuthError("Credenciais inválidas para exclusão do relatório.")

        req = report_request_repository.get_by_id(self.report_session, request_id)
        if req is None:
            raise AuthError("Relatório não encontrado.")

        try:
            if req.file_path and Path(req.file_path).exists():
                Path(req.file_path).unlink(missing_ok=True)
        except Exception:
            pass

        report_request_repository.delete_by_id(self.report_session, request_id)
