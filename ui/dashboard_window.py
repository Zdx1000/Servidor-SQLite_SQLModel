from __future__ import annotations

from typing import Dict
from datetime import datetime
import shutil
from zoneinfo import ZoneInfo
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QGridLayout,
    QWidget,
    QProgressDialog,
    QSpacerItem,
    QSizePolicy,
)

from sqlmodel import Session

from db.config import engine
from services.auth_service import AuthService, AuthError
from repositories import password_request_repository, registration_request_repository, user_repository, pop_request_repository


class DashboardWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, user_info: Dict[str, str]) -> None:
        super().__init__()
        self.user_info = user_info
        self._static_pops = [
        ]
        self.setWindowTitle("Controle de Estoque - Principal")
        self.setMinimumSize(1100, 640)
        self._icon_dir = Path(__file__).resolve().parent / "assets" / "icons"
        app_icon = self._load_icon("app.png")
        if app_icon is not None:
            self.setWindowIcon(app_icon)
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_nav())
        layout.addWidget(self._build_stack(), 1)

        self.setCentralWidget(container)
        self._apply_style()

    def _build_nav(self) -> QWidget:
        nav = QFrame()
        nav.setObjectName("navPanel")
        nav.setFixedWidth(200)
        v = QVBoxLayout(nav)
        v.setContentsMargins(12, 16, 12, 16)
        v.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title_icon_lbl = QLabel()
        title_icon_lbl.setObjectName("navTitleIcon")
        title_icon = self._load_pixmap("menu.png", QSize(18, 18))
        if title_icon is not None:
            title_icon_lbl.setPixmap(title_icon)
        title = QLabel("Controle")
        title.setObjectName("navTitle")
        title_row.addWidget(title_icon_lbl)
        title_row.addWidget(title, 1)
        v.addLayout(title_row)

        self.btn_principal = QPushButton("Principal")
        self.btn_estoque = QPushButton("POPs CD Estoque")
        self.btn_relatorios = QPushButton("Relatórios")
        self.btn_solicitacoes = QPushButton("Solicitações")
        self.btn_senha = QPushButton("Senha 167")
        self.btn_sindicancia = QPushButton("Sindicância")
        self.btn_senha171 = QPushButton("Senha 171")
        self.btn_config = QPushButton("Configurações")

        buttons = (
            self.btn_principal,
            self.btn_estoque,
            self.btn_relatorios,
            self.btn_solicitacoes,
            self.btn_senha,
            self.btn_sindicancia,
            self.btn_senha171,
            self.btn_config,
        )

        icon_map = {
            self.btn_principal: "home.png",
            self.btn_estoque: "boxes.png",
            self.btn_relatorios: "report.png",
            self.btn_solicitacoes: "solicitacao.png",
            self.btn_senha: "lock-167.png",
            self.btn_sindicancia: "shield.png",
            self.btn_senha171: "lock-171.png",
            self.btn_config: "settings.png",
        }

        for idx, btn in enumerate(buttons):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self._switch_page(i))
            if btn not in (self.btn_principal, self.btn_estoque, self.btn_solicitacoes, self.btn_config):
                btn.setEnabled(False)
            icon_name = icon_map.get(btn)
            icon = self._load_icon(icon_name) if icon_name else None
            if icon is not None:
                btn.setIcon(icon)
                btn.setIconSize(QSize(18, 18))
            v.addWidget(btn)

        v.addStretch(1)

        user_box = QFrame()
        user_box.setObjectName("userBox")
        user_layout = QVBoxLayout(user_box)
        user_layout.setContentsMargins(10, 10, 10, 10)
        user_layout.setSpacing(4)

        user_name = QLabel(self.user_info.get("name", "Usuário"))
        user_name.setObjectName("userName")
        user_email = QLabel(self.user_info.get("email", "usuario@example.com"))
        user_email.setObjectName("userEmail")

        logout_btn = QPushButton("Sair")
        logout_btn.setObjectName("secondaryButton")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_icon = self._load_icon("logout.png")
        if logout_icon is not None:
            logout_btn.setIcon(logout_icon)
            logout_btn.setIconSize(QSize(16, 16))
        logout_btn.clicked.connect(self._handle_logout)

        user_layout.addWidget(user_name)
        user_layout.addWidget(user_email)
        user_layout.addWidget(logout_btn)

        v.addWidget(user_box)
        self.btn_principal.setChecked(True)
        return nav

    def _build_stack(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setObjectName("contentPanel")
        v = QVBoxLayout(wrapper)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)
        header_icon_lbl = QLabel()
        header_icon_lbl.setObjectName("pageTitleIcon")
        header_icon = self._load_pixmap("dashboard.png", QSize(20, 20))
        if header_icon is not None:
            header_icon_lbl.setPixmap(header_icon)
        header = QLabel("Principal")
        header.setObjectName("pageTitle")
        header_row.addWidget(header_icon_lbl)
        header_row.addWidget(header, 1)
        v.addLayout(header_row)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_home_page())
        self.stack.addWidget(self._build_pops_page())
        self.stack.addWidget(self._build_placeholder_page("Relatórios em breve"))
        self.stack.addWidget(self._build_requests_page())
        self.stack.addWidget(self._build_placeholder_page("Senha 167 (em breve)"))
        self.stack.addWidget(self._build_placeholder_page("Sindicância (em breve)"))
        self.stack.addWidget(self._build_placeholder_page("Senha 171 (em breve)"))
        self.stack.addWidget(self._build_settings_page())

        v.addWidget(self.stack, 1)
        return wrapper

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        user_card = QFrame()
        user_card.setObjectName("infoCard")
        card_layout = QVBoxLayout(user_card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(6)

        title = QLabel("Usuário")
        title.setObjectName("cardTitle")
        card_layout.addWidget(title)

        info_list = QListWidget()
        info_list.setObjectName("infoList")
        info_pairs = [
            ("Nome", self.user_info.get("name", "-")),
            ("E-mail", self.user_info.get("email", "-")),
            ("Perfil", self.user_info.get("role", "-")),
            ("Último acesso", self.user_info.get("last_login", "-")),
        ]
        for label, value in info_pairs:
            item = QListWidgetItem(f"{label}: {value}")
            info_list.addItem(item)

        card_layout.addWidget(info_list)

        layout.addWidget(user_card)
        layout.addStretch(1)
        return page

    def _build_pops_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        header = QLabel("POPs CD Estoque")
        header.setObjectName("pageTitle")
        header_row.addWidget(header, 1)

        request_btn = QPushButton("Solicitar POP")
        request_btn.setObjectName("primaryButton")
        request_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pop_icon = self._load_icon("pop.png")
        if pop_icon is not None:
            request_btn.setIcon(pop_icon)
            request_btn.setIconSize(QSize(18, 18))
        request_btn.clicked.connect(self._open_pop_request_dialog)
        header_row.addWidget(request_btn, 0, Qt.AlignmentFlag.AlignRight)

        layout.addLayout(header_row)

        subtitle = QLabel("Tutoriais e procedimentos operacionais do controle de estoque.")
        subtitle.setObjectName("mutedText")
        layout.addWidget(subtitle)

        self.pop_grid = QGridLayout()
        self.pop_grid.setSpacing(12)
        layout.addLayout(self.pop_grid)

        self._render_pop_cards()

        layout.addStretch(1)
        return page

    def _render_pop_cards(self) -> None:
        if not hasattr(self, "pop_grid"):
            return
        grid = self.pop_grid
        while grid.count():
            item = grid.takeAt(grid.count() - 1)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        pops = [
            {"title": title, "desc": desc, "file_path": None, "file_name": None, "id": None}
            for title, desc in self._static_pops
        ]
        try:
            with Session(engine) as session:
                approved = pop_request_repository.list_approved(session)
                pops.extend(
                    {
                        "title": req.title,
                        "desc": req.description,
                        "file_path": req.file_path,
                        "file_name": req.file_name,
                        "id": req.id,
                    }
                    for req in approved
                )
        except Exception:
            pass

        for idx, pop in enumerate(pops):
            row, col = divmod(idx, 2)
            card = QFrame()
            card.setObjectName("popCard")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(10)

            icon_lbl = QLabel()
            icon_lbl.setObjectName("popIcon")
            icon_pm = self._load_pixmap("pop.png", QSize(32, 32))
            if icon_pm is not None:
                icon_lbl.setPixmap(icon_pm)
            card_layout.addWidget(icon_lbl)

            text_col = QVBoxLayout()
            text_col.setSpacing(4)

            title_row = QHBoxLayout()
            title_row.setSpacing(6)

            title_lbl = QLabel(pop["title"])
            title_lbl.setObjectName("cardTitle")
            title_row.addWidget(title_lbl)
            title_row.addStretch(1)

            if pop.get("id") is not None:
                delete_btn = QPushButton()
                delete_btn.setFixedSize(32, 32)
                delete_btn.setObjectName("deleteIconButton")
                delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                delete_btn.setToolTip("Excluir POP")
                del_icon = self._load_icon("excluir.png")
                if del_icon is not None:
                    delete_btn.setIcon(del_icon)
                    delete_btn.setIconSize(QSize(16, 16))
                delete_btn.clicked.connect(lambda _, pid=pop["id"]: self._handle_delete_pop(pid))
                title_row.addWidget(delete_btn)

            text_col.addLayout(title_row)

            desc_lbl = QLabel(pop["desc"])
            desc_lbl.setWordWrap(True)
            desc_lbl.setObjectName("mutedText")
            text_col.addWidget(desc_lbl)

            if pop.get("file_path"):
                file_row = QHBoxLayout()
                file_row.setSpacing(6)
                file_label = QLabel(pop.get("file_name", "Arquivo"))
                file_label.setObjectName("mutedText")
                download_btn = QPushButton("Baixar POP")
                download_btn.setObjectName("primaryButton")
                download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                download_btn.clicked.connect(lambda _, p=pop["file_path"]: self._download_pop(p))
                file_row.addWidget(file_label, 1)
                file_row.addWidget(download_btn, 0)
                text_col.addLayout(file_row)

            text_col.addStretch(1)
            card_layout.addLayout(text_col)

            grid.addWidget(card, row, col)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

    def _open_pop_request_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Solicitar novo POP")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title_lbl = QLabel("Título do POP")
        title_input = QLineEdit()
        title_input.setPlaceholderText("Ex.: POP Conferência de Paletes")

        desc_lbl = QLabel("Descrição/objetivo")
        desc_input = QTextEdit()
        desc_input.setPlaceholderText("Explique o propósito e o que precisa constar no POP.")
        desc_input.setMinimumHeight(120)

        file_lbl = QLabel("Arquivo do POP (doc, docx, txt, xls, xlsx, ppt, pptx)")
        file_path_display = QLabel("Nenhum arquivo selecionado")
        file_path_display.setObjectName("mutedText")
        file_btn = QPushButton("Selecionar arquivo")
        file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        selected_file: Dict[str, str | None] = {"path": None}

        def _pick_file() -> None:
            filter_str = "Documentos (*.doc *.docx *.txt *.xls *.xlsx *.ppt *.pptx)"
            chosen, _ = QFileDialog.getOpenFileName(dialog, "Selecionar arquivo do POP", "", filter_str)
            if chosen:
                selected_file["path"] = chosen
                file_path_display.setText(Path(chosen).name)

        file_btn.clicked.connect(_pick_file)

        layout.addWidget(title_lbl)
        layout.addWidget(title_input)
        layout.addWidget(desc_lbl)
        layout.addWidget(desc_input)
        layout.addWidget(file_lbl)
        file_row = QHBoxLayout()
        file_row.setSpacing(6)
        file_row.addWidget(file_btn, 0)
        file_row.addWidget(file_path_display, 1)
        layout.addLayout(file_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setText("Enviar solicitação")
            ok_btn.setObjectName("primaryButton")
            ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if cancel_btn:
            cancel_btn.setText("Cancelar")
            cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        title = title_input.text().strip()
        description = desc_input.toPlainText().strip()
        source_file = selected_file.get("path")
        if not source_file:
            QMessageBox.warning(self, "POP", "Selecione um arquivo para anexar ao POP.")
            return
        try:
            stored_path = self._store_pop_file(Path(source_file))
            with Session(engine) as session:
                auth = AuthService(session)
                auth.request_pop(
                    title=title,
                    description=description,
                    file_name=Path(source_file).name,
                    file_path=str(stored_path),
                )
            QMessageBox.information(self, "POP", "Solicitação de POP enviada para aprovação.")
            self._load_requests()
        except AuthError as exc:
            QMessageBox.warning(self, "POP", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "POP", f"Erro ao enviar solicitação: {exc}")

    def _store_pop_file(self, source: Path) -> Path:
        storage_dir = Path(__file__).resolve().parent.parent / "data" / "pop_files"
        storage_dir.mkdir(parents=True, exist_ok=True)
        allowed_ext = {".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"}
        if source.suffix.lower() not in allowed_ext:
            raise AuthError("Tipo de arquivo não suportado para POP.")
        if not source.exists():
            raise AuthError("Arquivo selecionado não existe mais.")
        dest = storage_dir / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{source.name}"
        shutil.copy2(source, dest)
        return dest

    def _download_pop(self, file_path: str) -> None:
        target = Path(file_path)
        if not target.exists():
            QMessageBox.warning(self, "POP", "Arquivo do POP não foi encontrado no disco.")
            return
        suggested = str(Path.home() / target.name)
        dest_path, _ = QFileDialog.getSaveFileName(self, "Salvar POP", suggested)
        if not dest_path:
            return
        progress = QProgressDialog("Baixando POP...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()
        try:
            shutil.copy2(target, dest_path)
            QMessageBox.information(self, "POP", f"Arquivo salvo em:\n{dest_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "POP", f"Erro ao salvar POP: {exc}")
        finally:
            progress.close()

    def _handle_delete_pop(self, pop_id: int) -> None:
        confirm = QMessageBox.question(
            self,
            "Excluir POP",
            "Tem certeza que deseja excluir permanentemente este POP?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        password = self._prompt_password("Digite sua senha para confirmar a exclusão:")
        if password is None:
            return

        identifier = self.user_info.get("email") or self.user_info.get("name") or ""
        try:
            with Session(engine) as session:
                auth = AuthService(session)
                auth.delete_pop_request(pop_id, identifier=identifier, password=password)
            QMessageBox.information(self, "POP", "POP excluído com sucesso.")
            self._render_pop_cards()
        except AuthError as exc:
            QMessageBox.warning(self, "POP", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "POP", f"Erro ao excluir POP: {exc}")

    def _prompt_password(self, prompt: str) -> str | None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Confirmação")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        label = QLabel(prompt)
        layout.addWidget(label)

        pw_input = QLineEdit()
        pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(pw_input)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return pw_input.text()
        return None

    def _build_placeholder_page(self, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(text)
        label.setObjectName("placeholder")
        layout.addWidget(label)
        return page

    def _build_requests_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        header = QLabel("Solicitações e atualizações pendentes")
        header.setObjectName("cardTitle")
        layout.addWidget(header)

        subtitle = QLabel("Aprove ou recuse pedidos de registro, redefinição de senha e novos POPs enviados pelos usuários.")
        subtitle.setObjectName("mutedText")
        layout.addWidget(subtitle)

        self.requests_list = QListWidget()
        self.requests_list.setObjectName("requestList")
        self.requests_list.setSpacing(8)
        layout.addWidget(self.requests_list, 1)

        actions_row = QHBoxLayout()
        actions_row.setContentsMargins(0, 0, 0, 0)
        actions_row.setSpacing(8)

        refresh_btn = QPushButton("Atualizar lista")
        refresh_btn.setObjectName("primaryButton")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._load_requests)
        actions_row.addWidget(refresh_btn)

        actions_row.addStretch(1)
        layout.addLayout(actions_row)

        self._load_requests()
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        info_card = QFrame()
        info_card.setObjectName("infoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(6)
        title = QLabel("Configurações do usuário")
        title.setObjectName("cardTitle")
        info_layout.addWidget(title)

        details = QListWidget()
        details.setObjectName("infoList")
        details.addItem(f"Nome: {self.user_info.get('name', '-')}")
        details.addItem(f"E-mail: {self.user_info.get('email', '-')}")
        details.addItem("Alterar senha abaixo")
        info_layout.addWidget(details)

        pw_card = QFrame()
        pw_card.setObjectName("infoCard")
        pw_layout = QVBoxLayout(pw_card)
        pw_layout.setContentsMargins(16, 16, 16, 16)
        pw_layout.setSpacing(8)
        pw_title = QLabel("Alterar senha")
        pw_title.setObjectName("cardTitle")
        pw_layout.addWidget(pw_title)

        self.pw_current = QLineEdit()
        self.pw_current.setPlaceholderText("Senha atual")
        self.pw_current.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_new = QLineEdit()
        self.pw_new.setPlaceholderText("Nova senha")
        self.pw_new.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_confirm = QLineEdit()
        self.pw_confirm.setPlaceholderText("Confirmar nova senha")
        self.pw_confirm.setEchoMode(QLineEdit.EchoMode.Password)

        for widget in (self.pw_current, self.pw_new, self.pw_confirm):
            pw_layout.addWidget(widget)

        self.change_pw_btn = QPushButton("Atualizar senha")
        self.change_pw_btn.setObjectName("primaryButton")
        self.change_pw_btn.clicked.connect(self._handle_change_password)
        pw_layout.addWidget(self.change_pw_btn)

        layout.addWidget(info_card)
        layout.addWidget(pw_card)
        layout.addStretch(1)
        return page

    def _switch_page(self, index: int) -> None:
        self.btn_principal.setChecked(index == 0)
        self.btn_estoque.setChecked(index == 1)
        self.btn_relatorios.setChecked(index == 2)
        self.btn_solicitacoes.setChecked(index == 3)
        self.btn_senha.setChecked(index == 4)
        self.btn_sindicancia.setChecked(index == 5)
        self.btn_senha171.setChecked(index == 6)
        self.btn_config.setChecked(index == 7)
        self.stack.setCurrentIndex(index)

    def _clear_pw_errors(self) -> None:
        for widget in (self.pw_current, self.pw_new, self.pw_confirm):
            widget.setStyleSheet("")

    def _mark_pw_error(self, widget: QLineEdit) -> None:
        widget.setStyleSheet("border: 1px solid #dc2626;")

    def _handle_change_password(self) -> None:
        self._clear_pw_errors()
        current = self.pw_current.text()
        new = self.pw_new.text()
        confirm = self.pw_confirm.text()

        missing = []
        if not current:
            missing.append(self.pw_current)
        if not new:
            missing.append(self.pw_new)
        if not confirm:
            missing.append(self.pw_confirm)
        for widget in missing:
            self._mark_pw_error(widget)
        if missing:
            QMessageBox.warning(self, "Senha", "Preencha todos os campos de senha.")
            return

        if new != confirm:
            self._mark_pw_error(self.pw_new)
            self._mark_pw_error(self.pw_confirm)
            QMessageBox.warning(self, "Senha", "Nova senha e confirmação não conferem.")
            return

        identifier = self.user_info.get("email") or self.user_info.get("name") or ""
        try:
            with Session(engine) as session:
                auth = AuthService(session)
                user = auth.authenticate(identifier, current)
                if not user:
                    self._mark_pw_error(self.pw_current)
                    QMessageBox.warning(self, "Senha", "Senha atual incorreta.")
                    return
                auth.change_password(user, current_password=current, new_password=new)
                QMessageBox.information(self, "Senha", "Senha atualizada com sucesso.")
                self.pw_current.clear()
                self.pw_new.clear()
                self.pw_confirm.clear()
        except AuthError as exc:
            self._mark_pw_error(self.pw_new)
            self._mark_pw_error(self.pw_confirm)
            QMessageBox.warning(self, "Validação", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro: {exc}")

    def _handle_logout(self) -> None:
        self.logout_requested.emit()

    def _load_requests(self) -> None:
        if not hasattr(self, "requests_list"):
            return
        self.requests_list.clear()
        try:
            with Session(engine) as session:
                pw_requests = password_request_repository.list_pending(session)
                reg_requests = registration_request_repository.list_pending(session)
                pop_requests = pop_request_repository.list_pending(session)
            combined = (
                [("senha", req) for req in pw_requests]
                + [("registro", req) for req in reg_requests]
                + [("pop", req) for req in pop_requests]
            )
            if not combined:
                placeholder = QListWidgetItem("Nenhuma solicitação pendente.")
                placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
                self.requests_list.addItem(placeholder)
                return
            for kind, req in combined:
                item = QListWidgetItem()
                card = self._build_request_card(req, kind)
                item.setSizeHint(card.sizeHint())
                self.requests_list.addItem(item)
                self.requests_list.setItemWidget(item, card)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Solicitações", f"Erro ao carregar solicitações: {exc}")

    def _build_request_card(self, req, kind: str) -> QWidget:
        card = QFrame()
        card.setObjectName("requestCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setObjectName("requestIcon")
        icon_name = "pop.png" if kind == "pop" else ("registrado_solicitação.png" if kind == "registro" else "senha_solicitação.png")
        icon_pm = self._load_pixmap(icon_name, QSize(48, 48))
        if icon_pm is not None:
            icon_lbl.setPixmap(icon_pm)
        layout.addWidget(icon_lbl)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        if kind == "pop":
            title_lbl = QLabel(req.title)
            title_lbl.setObjectName("requestTitle")
            info_col.addWidget(title_lbl)

            detail = QLabel(f"Criado em {self._format_br_datetime(req.created_at)}")
            detail.setObjectName("requestMeta")
            info_col.addWidget(detail)

            status = QLabel(f"Status: {req.status}")
            status.setObjectName("requestStatus")
            info_col.addWidget(status)

            file_lbl = QLabel(f"Arquivo: {req.file_name}")
            file_lbl.setObjectName("requestStatus")
            info_col.addWidget(file_lbl)

            desc_lbl = QLabel(req.description)
            desc_lbl.setWordWrap(True)
            desc_lbl.setObjectName("requestStatus")
            info_col.addWidget(desc_lbl)

            req_kind_label = QLabel("Solicitação: POP")
            req_kind_label.setObjectName("requestStatus")
            info_col.addWidget(req_kind_label)
        else:
            display_name = req.name if hasattr(req, "name") else req.user_name
            title = QLabel(f"{display_name} • {req.email}")
            title.setObjectName("requestTitle")
            info_col.addWidget(title)

            detail = QLabel(f"Criado em {self._format_br_datetime(req.created_at)}")
            detail.setObjectName("requestMeta")
            info_col.addWidget(detail)

            status = QLabel(f"Status: {req.status}")
            status.setObjectName("requestStatus")
            info_col.addWidget(status)

            user_type = QLabel(f"Tipo usuário: {self._resolve_user_type(display_name, req.email)}")
            user_type.setObjectName("requestStatus")
            info_col.addWidget(user_type)

            req_kind_label = QLabel(
                "Solicitação: Registro" if kind == "registro" else "Solicitação: Redefinição de senha"
            )
            req_kind_label.setObjectName("requestStatus")
            info_col.addWidget(req_kind_label)

        layout.addLayout(info_col, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)

        accept_btn = QPushButton("Aceitar")
        accept_btn.setObjectName("acceptButton")
        accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        accept_btn.clicked.connect(lambda: self._handle_request_action(req.id, kind, approve=True))

        reject_btn = QPushButton("Recusar")
        reject_btn.setObjectName("rejectButton")
        reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reject_btn.clicked.connect(lambda: self._handle_request_action(req.id, kind, approve=False))

        btn_col.addWidget(accept_btn)
        btn_col.addWidget(reject_btn)
        layout.addLayout(btn_col)

        return card

    def _handle_request_action(self, request_id: int, kind: str, approve: bool) -> None:
        try:
            with Session(engine) as session:
                auth = AuthService(session)
                if kind == "registro":
                    if approve:
                        auth.approve_registration_request(request_id)
                        QMessageBox.information(self, "Solicitações", "Registro aprovado e usuário criado.")
                    else:
                        auth.reject_registration_request(request_id)
                        QMessageBox.information(self, "Solicitações", "Registro recusado.")
                elif kind == "senha":
                    if approve:
                        auth.approve_password_request(request_id)
                        QMessageBox.information(self, "Solicitações", "Solicitação aprovada e senha atualizada.")
                    else:
                        auth.reject_password_request(request_id)
                        QMessageBox.information(self, "Solicitações", "Solicitação recusada.")
                else:
                    if approve:
                        auth.approve_pop_request(request_id)
                        QMessageBox.information(self, "Solicitações", "Solicitação de POP aprovada.")
                        self._render_pop_cards()
                    else:
                        auth.reject_pop_request(request_id)
                        QMessageBox.information(self, "Solicitações", "Solicitação de POP recusada.")
            self._load_requests()
        except AuthError as exc:
            QMessageBox.warning(self, "Solicitações", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Solicitações", f"Erro ao processar solicitação: {exc}")

    def _format_br_datetime(self, dt) -> str:
        try:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
            br_dt = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
            return br_dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return dt.strftime("%d/%m/%Y %H:%M")

    def _resolve_user_type(self, user_name: str, email: str) -> str:
        try:
            with Session(engine) as session:
                user = user_repository.get_by_email(session, email)
            if user and "admin" in user.name.lower():
                return "Administrador"
            if "admin" in f"{user_name} {email}".lower():
                return "Administrador"
        except Exception:
            pass
        return "Usuário"

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #f5f6f7; color: #1f2933; }
            #navPanel {
                background: #ffffff;
                border-right: 1px solid #d8dde3;
            }
            #contentPanel { background: #f9fafb; }
            #navTitle { font-size: 16px; font-weight: 700; color: #111827; margin-bottom: 8px; }
            QPushButton {
                padding: 10px;
                border-radius: 8px;
                border: 1px solid #cfd6dd;
                background: #ffffff;
                color: #111827;
                text-align: left;
                padding-left: 12px;
            }
            QPushButton:hover { background: #eef2f6; }
            QPushButton:checked { background: #2563eb; border-color: #2563eb; color: #ffffff; }
            #primaryButton {
                background: #2563eb;
                border-color: #2563eb;
                color: #ffffff;
                font-weight: 600;
                text-align: center;
            }
            #primaryButton:hover { background: #1e40af; }
            #secondaryButton { background: #f3f4f6; color: #1f2933; border-color: #cfd6dd; }
            #secondaryButton:hover { background: #991b1b; color: #ffffff; border-color: #7f1d1d; }
                #deleteIconButton {
                    background: #fee2e2;
                    border: 1px solid #fecaca;
                    border-radius: 8px;
                    padding: 6px;
                }
                #deleteIconButton:hover {
                    background: #fecdd3;
                    border-color: #fca5a5;
                }
                #deleteIconButton:pressed {
                    background: #fca5a5;
                    border-color: #f87171;
                }
            #acceptButton {
                background: #16a34a;
                border-color: #16a34a;
                color: #ffffff;
                font-weight: 600;
                text-align: center;
            }
            #acceptButton:hover { background: #15803d; }
            #rejectButton {
                background: #dc2626;
                border-color: #dc2626;
                color: #ffffff;
                font-weight: 600;
                text-align: center;
            }
            #rejectButton:hover { background: #b91c1c; }
            #pageTitle { font-size: 22px; font-weight: 700; color: #111827; }
            #infoCard {
                border: 1px solid #d8dde3;
                border-radius: 12px;
                background: #ffffff;
            }
            #cardTitle { font-size: 14px; font-weight: 700; color: #1f2933; }
            #mutedText { color: #6b7280; font-size: 12px; }
            #infoList { background: transparent; border: none; color: #1f2933; }
            #requestList { background: transparent; border: none; }
            #requestCard {
                border: 1px solid #d8dde3;
                border-radius: 12px;
                background: #ffffff;
            }
            #requestTitle { font-size: 14px; font-weight: 700; color: #111827; }
            #requestMeta { color: #6b7280; font-size: 12px; }
            #requestStatus { color: #374151; font-size: 12px; }
            #popCard {
                border: 1px solid #d8dde3;
                border-radius: 12px;
                background: #ffffff;
            }
            #popIcon {
                max-width: 32px;
                max-height: 32px;
            }
            #placeholder { color: #6b7280; font-size: 14px; }
            #userBox {
                border: 1px solid #e5e7eb;
                border-radius: 10px;
                background: #f9fafb;
            }
            #userName { font-size: 14px; font-weight: 700; color: #111827; }
            #userEmail { font-size: 12px; color: #4b5563; }
            #navTitleIcon, #pageTitleIcon {
                max-width: 20px;
                max-height: 20px;
            }
            """
        )

    def _load_icon(self, name: str | None) -> QIcon | None:
        if not name:
            return None
        path = self._icon_dir / name
        if not path.exists():
            return None
        return QIcon(str(path))

    def _load_pixmap(self, name: str | None, size: QSize | None = None) -> QPixmap | None:
        if not name:
            return None
        path = self._icon_dir / name
        if not path.exists():
            return None
        pixmap = QPixmap(str(path))
        if size is not None and not pixmap.isNull():
            return pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return pixmap if not pixmap.isNull() else None


__all__ = ["DashboardWindow"]
