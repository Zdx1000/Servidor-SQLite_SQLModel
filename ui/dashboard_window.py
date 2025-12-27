from __future__ import annotations

from typing import Dict
import html
from datetime import datetime
import shutil
from zoneinfo import ZoneInfo
from pathlib import Path
import platform
import getpass
import pandas as pd

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QDesktopServices, QColor
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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QComboBox,
)

from sqlmodel import Session

from db.config import engine
from db.report_config import report_engine
from db.order_config import order_request_engine, order_data_engine
from services.auth_service import AuthService, AuthError
from services.report_service import ReportService
from services.senha171_service import AdicionarOrdensNovas
from services.senha167_service import AdicionarOrdensNovas2
from services.order_service import OrderService
from repositories import (
    password_request_repository,
    registration_request_repository,
    user_repository,
    pop_request_repository,
    report_request_repository,
    order_request_repository,
    order_repository,
)


class DashboardWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, user_info: Dict[str, str]) -> None:
        super().__init__()
        self.user_info = user_info
        role_val = (user_info.get("role") or "").strip().upper()
        self.is_admin = role_val == "ADMINISTRADOR"
        self._static_pops = [
        ]
        self._last_preview_df_171 = None
        self._last_preview_df_167 = None
        self._orders167_pending_confirm = False
        self.order_service = OrderService()
        self.setWindowTitle("Controle de Estoque - Principal")
        self.setMinimumSize(1100, 640)
        self._icon_dir = Path(__file__).resolve().parent / "assets" / "icons"
        app_icon = self._load_icon("app.png")
        if app_icon is not None:
            self.setWindowIcon(app_icon)
        self._build_ui()
        self._show_user_alert()

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

        title_box = QFrame()
        title_box.setObjectName("navTitleBox")
        title_row = QHBoxLayout(title_box)
        title_row.setContentsMargins(12, 10, 12, 10)
        title_row.setSpacing(8)
        title_icon_lbl = QLabel()
        title_icon_lbl.setObjectName("navTitleIcon")
        title_icon = self._load_pixmap("menu.png", QSize(18, 18))
        if title_icon is not None:
            title_icon_lbl.setPixmap(title_icon)
        title = QLabel("Painel")
        title.setObjectName("navTitle")
        title_row.addWidget(title_icon_lbl)
        title_row.addWidget(title, 1)

        title_tag = QLabel("Menu")
        title_tag.setObjectName("navTitleTag")
        title_row.addWidget(title_tag, 0, Qt.AlignmentFlag.AlignRight)
        v.addWidget(title_box)

        self.btn_principal = QPushButton("Principal")
        self.btn_estoque = QPushButton("POPs CD Estoque")
        self.btn_relatorios = QPushButton("Relatórios")
        self.btn_solicitacoes = QPushButton("Solicitações")
        self.btn_senha = QPushButton("Senha 167")
        self.btn_sindicancia = QPushButton("Sindicância")
        self.btn_senha171 = QPushButton("Senha 171")
        self.btn_users = QPushButton("Usuários")
        self.btn_config = QPushButton("Configurações")

        buttons = (
            self.btn_principal,
            self.btn_estoque,
            self.btn_relatorios,
            self.btn_solicitacoes,
            self.btn_senha,
            self.btn_sindicancia,
            self.btn_senha171,
            self.btn_users,
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
            self.btn_users: "users.png",
            self.btn_config: "settings.png",
        }

        for idx, btn in enumerate(buttons):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self._switch_page(i))
            if (btn is self.btn_users or btn is self.btn_solicitacoes) and not self.is_admin:
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
        self.stack.addWidget(self._build_reports_page())
        self.stack.addWidget(self._build_requests_page())
        self.stack.addWidget(self._build_password167_page())
        self.stack.addWidget(self._build_placeholder_page("Sindicância (em breve)"))
        self.stack.addWidget(self._build_password171_page())
        self.stack.addWidget(self._build_users_page())
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
        os_name = platform.system() or "-"
        os_release = platform.release() or "-"
        host = platform.node() or "-"
        os_user = self.user_info.get("os_user") or getpass.getuser() or "-"
        avg_daily_usage = self.user_info.get("avg_daily_usage", "-")
        if isinstance(avg_daily_usage, (int, float)):
            avg_daily_usage = f"{avg_daily_usage:.1f} h/dia"
        info_pairs = [
            ("Nome", self.user_info.get("name", "-")),
            ("E-mail", self.user_info.get("email", "-")),
            ("Perfil", self.user_info.get("role", "-")),
            ("Último acesso", self.user_info.get("last_login", "-")),
            ("Sistema", os_name),
            ("Versão do SO", os_release),
            ("Dispositivo", host),
            ("Usuário do SO", os_user),
            ("Tempo médio/dia", avg_daily_usage),
        ]
        for label, value in info_pairs:
            item = QListWidgetItem(f"{label}: {value}")
            info_list.addItem(item)

        card_layout.addWidget(info_list)

        layout.addWidget(user_card)

        activity_card = QFrame()
        activity_card.setObjectName("infoCard")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(16, 16, 16, 16)
        activity_layout.setSpacing(6)

        activity_title = QLabel("Atividade recente")
        activity_title.setObjectName("cardTitle")
        activity_layout.addWidget(activity_title)

        activity_list = QListWidget()
        activity_list.setObjectName("infoList")

        last_action = self.user_info.get("last_action", "-")
        last_action_at = self.user_info.get("last_action_at", "-")
        if isinstance(last_action_at, datetime):
            last_action_at = self._format_br_datetime(last_action_at)
        last_ip = self.user_info.get("last_ip", "-")
        last_device = self.user_info.get("last_device", "-")

        activity_items = [
            ("Última movimentação", last_action),
            ("Quando", last_action_at),
            ("Origem/IP", last_ip),
            ("Dispositivo", last_device),
        ]
        for label, value in activity_items:
            activity_list.addItem(f"{label}: {value}")

        activity_layout.addWidget(activity_list)
        layout.addWidget(activity_card)
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

    def _build_reports_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        header = QLabel("Relatórios")
        header.setObjectName("pageTitle")
        header_row.addWidget(header, 1)

        request_btn = QPushButton("Solicitar relatório")
        request_btn.setObjectName("primaryButton")
        request_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        report_icon = self._load_icon("report.png")
        if report_icon is not None:
            request_btn.setIcon(report_icon)
            request_btn.setIconSize(QSize(18, 18))
        request_btn.clicked.connect(self._open_report_request_dialog)
        header_row.addWidget(request_btn, 0, Qt.AlignmentFlag.AlignRight)

        layout.addLayout(header_row)

        subtitle = QLabel("Planilhas, dashboards e documentos de acompanhamento.")
        subtitle.setObjectName("mutedText")
        layout.addWidget(subtitle)

        self.report_grid = QGridLayout()
        self.report_grid.setSpacing(12)
        layout.addLayout(self.report_grid)

        self._render_report_cards()

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

            if pop.get("id") is not None and self.is_admin:
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
        if not self.is_admin:
            QMessageBox.warning(self, "POP", "Apenas administradores podem excluir POPs.")
            return
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

    def _render_report_cards(self) -> None:
        if not hasattr(self, "report_grid"):
            return
        grid = self.report_grid
        while grid.count():
            item = grid.takeAt(grid.count() - 1)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        reports = []
        try:
            with Session(report_engine) as report_session:
                approved = report_request_repository.list_approved(report_session)
                reports.extend(
                    {
                        "title": req.title,
                        "desc": req.description,
                        "file_path": req.file_path,
                        "file_name": req.file_name,
                        "id": req.id,
                        "is_order": False,
                    }
                    for req in approved
                )
        except Exception:
            pass

        # Append fixed reports for Senha 167/171 (dados aprovados das ordens)
        reports.append(
            {
                "title": "Senha 167 - Ordens aprovadas",
                "desc": "Exporta todas as ordens 167 aprovadas (banco orders.db).",
                "is_order": True,
                "origin": "Senha 167",
            }
        )
        reports.append(
            {
                "title": "Senha 171 - Ordens aprovadas",
                "desc": "Exporta todas as ordens 171 aprovadas (banco orders.db).",
                "is_order": True,
                "origin": "Senha 171",
            }
        )

        for idx, rep in enumerate(reports):
            row, col = divmod(idx, 2)
            card = QFrame()
            card.setObjectName("popCard")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(10)

            icon_lbl = QLabel()
            icon_lbl.setObjectName("popIcon")
            icon_pm = self._load_pixmap("report.png", QSize(32, 32))
            if icon_pm is not None:
                icon_lbl.setPixmap(icon_pm)
            card_layout.addWidget(icon_lbl)

            text_col = QVBoxLayout()
            text_col.setSpacing(4)

            title_row = QHBoxLayout()
            title_row.setSpacing(6)

            title_lbl = QLabel(rep["title"])
            title_lbl.setObjectName("cardTitle")
            title_row.addWidget(title_lbl)
            title_row.addStretch(1)

            if rep.get("id") is not None and not rep.get("is_order") and self.is_admin:
                delete_btn = QPushButton()
                delete_btn.setFixedSize(32, 32)
                delete_btn.setObjectName("deleteIconButton")
                delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                delete_btn.setToolTip("Excluir relatório")
                del_icon = self._load_icon("excluir.png")
                if del_icon is not None:
                    delete_btn.setIcon(del_icon)
                    delete_btn.setIconSize(QSize(16, 16))
                delete_btn.clicked.connect(lambda _, rid=rep["id"]: self._handle_delete_report(rid))
                title_row.addWidget(delete_btn)

            text_col.addLayout(title_row)

            desc_lbl = QLabel(rep["desc"])
            desc_lbl.setWordWrap(True)
            desc_lbl.setObjectName("mutedText")
            text_col.addWidget(desc_lbl)

            if rep.get("is_order"):
                file_row = QHBoxLayout()
                file_row.setSpacing(6)
                file_label = QLabel("Exportar .xlsx")
                file_label.setObjectName("mutedText")
                download_btn = QPushButton("Baixar ordens")
                download_btn.setObjectName("primaryButton")
                download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                download_btn.clicked.connect(lambda _, o=rep.get("origin", ""): self._download_order_report(o))
                file_row.addWidget(file_label, 1)
                file_row.addWidget(download_btn, 0)
                text_col.addLayout(file_row)
            elif rep.get("file_path"):
                file_row = QHBoxLayout()
                file_row.setSpacing(6)
                file_label = QLabel(rep.get("file_name", "Arquivo"))
                file_label.setObjectName("mutedText")
                download_btn = QPushButton("Baixar relatório")
                download_btn.setObjectName("primaryButton")
                download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                download_btn.clicked.connect(lambda _, p=rep["file_path"]: self._download_report(p))
                file_row.addWidget(file_label, 1)
                file_row.addWidget(download_btn, 0)
                text_col.addLayout(file_row)

            text_col.addStretch(1)
            card_layout.addLayout(text_col)

            grid.addWidget(card, row, col)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

    def _open_report_request_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Solicitar novo relatório")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        title_lbl = QLabel("Título do relatório")
        title_input = QLineEdit()
        title_input.setPlaceholderText("Ex.: Painel de inventário semanal")

        desc_lbl = QLabel("Descrição/objetivo")
        desc_input = QTextEdit()
        desc_input.setPlaceholderText("Explique o que o relatório deve conter ou monitorar.")
        desc_input.setMinimumHeight(120)

        file_lbl = QLabel("Arquivo (pdf, xls, xlsx, csv, doc, docx, ppt, pptx, txt)")
        file_path_display = QLabel("Nenhum arquivo selecionado")
        file_path_display.setObjectName("mutedText")
        file_btn = QPushButton("Selecionar arquivo")
        file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        selected_file: Dict[str, str | None] = {"path": None}

        def _pick_file() -> None:
            filter_str = "Documentos (*.pdf *.xls *.xlsx *.csv *.doc *.docx *.ppt *.pptx *.txt)"
            chosen, _ = QFileDialog.getOpenFileName(dialog, "Selecionar arquivo do relatório", "", filter_str)
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
            QMessageBox.warning(self, "Relatórios", "Selecione um arquivo para anexar ao relatório.")
            return
        try:
            stored_path = self._store_report_file(Path(source_file))
            with Session(report_engine) as report_session:
                report_service = ReportService(report_session)
                report_service.request_report(
                    title=title,
                    description=description,
                    file_name=Path(source_file).name,
                    file_path=str(stored_path),
                )
            QMessageBox.information(self, "Relatórios", "Solicitação de relatório enviada para aprovação.")
            self._load_requests()
        except AuthError as exc:
            QMessageBox.warning(self, "Relatórios", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Relatórios", f"Erro ao enviar solicitação: {exc}")

    def _store_report_file(self, source: Path) -> Path:
        storage_dir = Path(__file__).resolve().parent.parent / "data" / "report_files"
        storage_dir.mkdir(parents=True, exist_ok=True)
        allowed_ext = {".pdf", ".xls", ".xlsx", ".csv", ".doc", ".docx", ".ppt", ".pptx", ".txt"}
        if source.suffix.lower() not in allowed_ext:
            raise AuthError("Tipo de arquivo não suportado para relatório.")
        if not source.exists():
            raise AuthError("Arquivo selecionado não existe mais.")
        dest = storage_dir / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{source.name}"
        shutil.copy2(source, dest)
        return dest

    def _download_report(self, file_path: str) -> None:
        target = Path(file_path)
        if not target.exists():
            QMessageBox.warning(self, "Relatórios", "Arquivo do relatório não foi encontrado no disco.")
            return
        suggested = str(Path.home() / target.name)
        dest_path, _ = QFileDialog.getSaveFileName(self, "Salvar relatório", suggested)
        if not dest_path:
            return
        progress = QProgressDialog("Baixando relatório...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()
        try:
            shutil.copy2(target, dest_path)
            QMessageBox.information(self, "Relatórios", f"Arquivo salvo em:\n{dest_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Relatórios", f"Erro ao salvar relatório: {exc}")
        finally:
            progress.close()

    def _download_order_report(self, origin: str) -> None:
        origin_norm = origin.strip()
        try:
            with Session(order_data_engine) as data_session:
                rows = order_repository.list_all(data_session, origin_norm)
            if not rows:
                QMessageBox.information(self, "Relatórios", f"Nenhuma ordem aprovada para {origin_norm}.")
                return

            df = self._orders_to_df(origin_norm, rows)
            suggested_name = "ordens_167.xlsx" if "167" in origin_norm else "ordens_171.xlsx"
            dest_path, _ = QFileDialog.getSaveFileName(self, "Salvar ordens", str(Path.home() / suggested_name), "Planilha Excel (*.xlsx)")
            if not dest_path:
                return
            df.to_excel(dest_path, index=False)
            QMessageBox.information(self, "Relatórios", f"Arquivo salvo em:\n{dest_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Relatórios", f"Erro ao exportar ordens: {exc}")

    def _handle_delete_report(self, report_id: int) -> None:
        if not self.is_admin:
            QMessageBox.warning(self, "Relatórios", "Apenas administradores podem excluir relatórios.")
            return
        confirm = QMessageBox.question(
            self,
            "Excluir relatório",
            "Tem certeza que deseja excluir permanentemente este relatório?",
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
            with Session(engine) as user_session, Session(report_engine) as report_session:
                report_service = ReportService(report_session, user_session=user_session)
                report_service.delete_report_request(report_id, identifier=identifier, password=password)
            QMessageBox.information(self, "Relatórios", "Relatório excluído com sucesso.")
            self._render_report_cards()
        except AuthError as exc:
            QMessageBox.warning(self, "Relatórios", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Relatórios", f"Erro ao excluir relatório: {exc}")

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

    def _orders_to_df(self, origin: str, rows) -> pd.DataFrame:
        """Converte registros aprovados em DataFrame para exportação."""
        is_167 = "167" in origin
        if is_167:
            columns = [
                "Nro Ordem",
                "STATUS",
                "TRATATIVA",
                "Responsável",
                "Data Fechamento Divergência",
                "Conferente",
                "OBS",
                "OBS - 2",
                "Região",
                "Filial Contábil",
                "Tipo Devol.",
                "Carga",
                "Valor",
                "Falta",
                "MÊS",
                "Semana",
                "Data Ordem",
                "DATA LIMITE",
                "MÊS DE FECH",
                "ANO",
                "Semana-Limit",
                "Cód. Região",
                "Região - 2",
                "Gerencia",
                "STT",
                "Email",
                "Dias a Vencer",
            ]
        else:
            columns = [
                "Nro Ordem",
                "Status",
                "Tratativa",
                "Nome",
                "Data Tratativa",
                "Cliente",
                "Cód. Cli",
                "Tipo Devol.",
                "Carga",
                "Valor",
                "MÊS",
                "ANO",
                "Semana",
                "Data Ordem",
            ]

        records = []
        for r in rows:
            d = r.dict()
            if is_167:
                rec = {
                    "Nro Ordem": d.get("nro_ordem"),
                    "STATUS": d.get("status"),
                    "TRATATIVA": d.get("tratativa"),
                    "Responsável": d.get("responsavel"),
                    "Data Fechamento Divergência": d.get("data_fechamento_div"),
                    "Conferente": d.get("conferente"),
                    "OBS": d.get("obs"),
                    "OBS - 2": d.get("obs2"),
                    "Região": d.get("regiao"),
                    "Filial Contábil": d.get("filial_contabil"),
                    "Tipo Devol.": d.get("tipo_devolucao"),
                    "Carga": d.get("carga"),
                    "Valor": d.get("valor"),
                    "Falta": d.get("falta"),
                    "MÊS": d.get("mes"),
                    "Semana": d.get("semana"),
                    "Data Ordem": d.get("data_ordem"),
                    "DATA LIMITE": d.get("data_limite"),
                    "MÊS DE FECH": d.get("mes_fech"),
                    "ANO": d.get("ano"),
                    "Semana-Limit": d.get("semana_limit"),
                    "Cód. Região": d.get("cod_regiao"),
                    "Região - 2": d.get("regiao2"),
                    "Gerencia": d.get("gerencia"),
                    "STT": d.get("stt"),
                    "Email": d.get("email"),
                    "Dias a Vencer": d.get("dias_vencer"),
                }
            else:
                rec = {
                    "Nro Ordem": d.get("nro_ordem"),
                    "Status": d.get("status"),
                    "Tratativa": d.get("tratativa"),
                    "Nome": d.get("nome"),
                    "Data Tratativa": d.get("data_tratativa"),
                    "Cliente": d.get("cliente"),
                    "Cód. Cli": d.get("cod_cli"),
                    "Tipo Devol.": d.get("tipo_devolucao"),
                    "Carga": d.get("carga"),
                    "Valor": d.get("valor"),
                    "MÊS": d.get("mes"),
                    "ANO": d.get("ano"),
                    "Semana": d.get("semana"),
                    "Data Ordem": d.get("data_ordem"),
                }
            records.append(rec)

        df = pd.DataFrame.from_records(records, columns=columns)
        return df

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

        subtitle = QLabel(
            "Aprove ou recuse pedidos de registro, redefinição de senha, novos POPs e relatórios enviados pelos usuários."
        )
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

    def _build_users_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        header = QLabel("Usuários")
        header.setObjectName("pageTitle")
        header_row.addWidget(header, 1)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        actions.addStretch(1)
        self.btn_refresh_users = QPushButton("Atualizar lista")
        self.btn_refresh_users.setObjectName("primaryButton")
        self.btn_refresh_users.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh_users.clicked.connect(self._load_users)
        actions.addWidget(self.btn_refresh_users, 0)

        header_row.addLayout(actions, 0)
        layout.addLayout(header_row)

        if not self.is_admin:
            warning = QLabel("Acesso restrito a administradores.")
            warning.setObjectName("mutedText")
            layout.addWidget(warning)
            layout.addStretch(1)
            return page

        subtitle = QLabel("Gerencie perfis, acessos e últimas movimentações.")
        subtitle.setObjectName("mutedText")
        layout.addWidget(subtitle)

        self.table_users = QTableWidget()
        self.table_users.setObjectName("usersTable")
        self.table_users.setColumnCount(8)
        self.table_users.setHorizontalHeaderLabels(
            ["ID", "Nome", "E-mail", "Perfil", "Acessos", "Último movimento", "Mensagem", "Excluir"]
        )
        header_view = self.table_users.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table_users.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_users.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_users.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_users.hideColumn(0)
        layout.addWidget(self.table_users)

        layout.addStretch(1)
        self._load_users()
        return page

    def _build_password167_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        header = QLabel("Senha 167")
        header.setObjectName("pageTitle")
        header_row.addWidget(header, 1)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        self.btn_refresh167 = QPushButton("Inserir planilha Atualizada")
        self.btn_refresh167.setObjectName("primaryButton")
        self.btn_refresh167.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh167.clicked.connect(self._on_refresh_167_clicked)

        self.btn_add_orders167 = QPushButton("Adicionar ordens novas")
        self.btn_add_orders167.setObjectName("secondaryButton")
        self.btn_add_orders167.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_orders167.clicked.connect(self._on_add_orders_167_clicked)

        buttons_row.addWidget(self.btn_refresh167, 0)
        buttons_row.addWidget(self.btn_add_orders167, 0)
        buttons_row.addStretch(1)

        header_row.addLayout(buttons_row, 0)
        layout.addLayout(header_row)

        info = QLabel("Fluxo de ordens 167: importe e valide antes de confirmar.")
        info.setObjectName("mutedText")
        layout.addWidget(info)

        preview_label = QLabel("Prévia (clique no cabeçalho para ordenar)")
        preview_label.setObjectName("cardTitle")
        layout.addWidget(preview_label)

        preview_actions = QHBoxLayout()
        preview_actions.setContentsMargins(0, 0, 0, 0)
        preview_actions.setSpacing(8)
        preview_actions.addStretch(1)
        self.btn_download_preview_167 = QPushButton("Baixar Prévia")
        self.btn_download_preview_167.setObjectName("primaryButton")
        self.btn_download_preview_167.setCursor(Qt.CursorShape.PointingHandCursor)
        dl_icon_167 = self._load_icon("baixar.png")
        if dl_icon_167 is not None:
            self.btn_download_preview_167.setIcon(dl_icon_167)
            self.btn_download_preview_167.setIconSize(QSize(16, 16))
        self.btn_download_preview_167.clicked.connect(self._handle_download_preview_167)
        preview_actions.addWidget(self.btn_download_preview_167, 0)
        layout.addLayout(preview_actions)

        self.table_preview_167 = QTableWidget()
        self.table_preview_167.setObjectName("previewTable167")
        self.table_preview_167.setSortingEnabled(True)
        self.table_preview_167.setColumnCount(0)
        self.table_preview_167.setRowCount(0)
        header_view = self.table_preview_167.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_view.setMinimumSectionSize(90)
        self.table_preview_167.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.table_preview_167.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        row_height = self.table_preview_167.verticalHeader().defaultSectionSize()
        header_height = header_view.height()
        self.table_preview_167.setMinimumHeight(header_height + (row_height * 12) + 24)
        layout.addWidget(self.table_preview_167)

        layout.addStretch(1)
        return page

    def _build_password171_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        header = QLabel("Senha 171")
        header.setObjectName("pageTitle")
        header_row.addWidget(header, 1)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        self.btn_refresh171 = QPushButton("Inserir planilha Atualizada")
        self.btn_refresh171.setObjectName("primaryButton")
        self.btn_refresh171.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh171.clicked.connect(self._on_refresh_171_clicked)

        self.btn_add_orders171 = QPushButton("Adicionar ordens novas")
        self.btn_add_orders171.setObjectName("secondaryButton")
        self.btn_add_orders171.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_orders171.clicked.connect(self._on_add_orders_171_clicked)
        self._orders171_pending_confirm = False

        buttons_row.addWidget(self.btn_refresh171, 0)
        buttons_row.addWidget(self.btn_add_orders171, 0)
        buttons_row.addStretch(1)

        header_row.addLayout(buttons_row, 0)
        layout.addLayout(header_row)

        info = QLabel("Importe e depois solicite confirmação das novas ordens.")
        info.setObjectName("mutedText")
        layout.addWidget(info)

        preview_label = QLabel("Prévia (clique no cabeçalho para ordenar)")
        preview_label.setObjectName("cardTitle")
        layout.addWidget(preview_label)

        preview_actions = QHBoxLayout()
        preview_actions.setContentsMargins(0, 0, 0, 0)
        preview_actions.setSpacing(8)

        preview_actions.addStretch(1)
        self.btn_download_preview_171 = QPushButton("Baixar Prévia")
        self.btn_download_preview_171.setObjectName("primaryButton")
        self.btn_download_preview_171.setCursor(Qt.CursorShape.PointingHandCursor)
        dl_icon = self._load_icon("baixar.png")
        if dl_icon is not None:
            self.btn_download_preview_171.setIcon(dl_icon)
            self.btn_download_preview_171.setIconSize(QSize(16, 16))
        self.btn_download_preview_171.clicked.connect(self._handle_download_preview_171)
        preview_actions.addWidget(self.btn_download_preview_171, 0)

        layout.addLayout(preview_actions)

        self.table_preview_171 = QTableWidget()
        self.table_preview_171.setObjectName("previewTable171")
        self.table_preview_171.setSortingEnabled(True)
        self.table_preview_171.setColumnCount(0)
        self.table_preview_171.setRowCount(0)
        header_view = self.table_preview_171.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_view.setMinimumSectionSize(90)
        self.table_preview_171.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.table_preview_171.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        row_height = self.table_preview_171.verticalHeader().defaultSectionSize()
        header_height = header_view.height()
        self.table_preview_171.setMinimumHeight(header_height + (row_height * 12) + 24)
        layout.addWidget(self.table_preview_171)

        layout.addStretch(1)
        return page

    def _on_add_orders_167_clicked(self) -> None:
        if getattr(self, "_orders167_pending_confirm", False):
            self._submit_order_confirmation("Senha 167", "_last_preview_df_167", self._set_orders167_confirm_state)
            return
        self._handle_add_orders_167()

    def _on_refresh_167_clicked(self) -> None:
        if getattr(self, "_orders167_pending_confirm", False):
            self._set_orders167_confirm_state(False)
            QMessageBox.information(self, "Senha 167", "Alteração não confirmada. Estado revertido.")
        else:
            QMessageBox.information(self, "Senha 167", "Nenhuma alteração pendente para desfazer.")

    def _handle_add_orders_167(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Importar ordens (xlsx)")
        dialog.setModal(True)
        v = QVBoxLayout(dialog)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        label = QLabel("Selecione um arquivo XLSX com as ordens.")
        v.addWidget(label)

        file_display = QLabel("Nenhum arquivo selecionado")
        file_display.setObjectName("mutedText")
        pick_btn = QPushButton("Escolher arquivo")
        pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        selected: Dict[str, str | None] = {"path": None}

        def _pick() -> None:
            chosen, _ = QFileDialog.getOpenFileName(dialog, "Selecionar XLSX", "", "Planilhas (*.xlsx)")
            if chosen:
                selected["path"] = chosen
                file_display.setText(Path(chosen).name)

        pick_btn.clicked.connect(_pick)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(pick_btn, 0)
        row.addWidget(file_display, 1)
        v.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setText("Processar")
            ok_btn.setObjectName("primaryButton")
            ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if cancel_btn:
            cancel_btn.setText("Cancelar")
            cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        v.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        file_path = selected.get("path")
        if not file_path:
            QMessageBox.warning(self, "Senha 167", "Nenhum arquivo XLSX selecionado.")
            return

        try:
            helper = AdicionarOrdensNovas2(file_path)
            df = helper.load_xlsx()
            df_manip = helper.Manipular_Dados(df=df)
            print("=== XLSX processado (Senha 167) ===")
            if df_manip is None or isinstance(df_manip, str):
                print(df_manip)
            else:
                print(df_manip)
                self._populate_preview_table_167(df_manip)
                self._set_orders167_confirm_state(True)
                self._last_preview_df_167 = df_manip.copy()
            QMessageBox.information(self, "Senha 167", "Arquivo processado. Veja o console para prévia dos dados.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Senha 167", f"Erro ao processar o XLSX: {exc}")

    def _populate_preview_table_167(self, df) -> None:
        if not hasattr(self, "table_preview_167"):
            return
        table = self.table_preview_167
        table.setSortingEnabled(False)
        table.clear()

        if df is None:
            table.setRowCount(0)
            table.setColumnCount(0)
            table.setSortingEnabled(True)
            return

        columns = list(df.columns)
        table.setColumnCount(len(columns))

        header_items = []
        for col_name in columns:
            item = QTableWidgetItem(col_name)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(Qt.GlobalColor.white)
            item.setBackground(QColor("#0f265c"))
            if col_name.strip().lower() == "valor":
                item.setBackground(QColor("#ffeb00"))
                item.setForeground(Qt.GlobalColor.black)
            header_items.append(item)

        for idx, item in enumerate(header_items):
            table.setHorizontalHeaderItem(idx, item)

        rows = len(df.index)
        table.setRowCount(rows)

        for row_idx in range(rows):
            row_series = df.iloc[row_idx]
            for col_idx, col_name in enumerate(columns):
                val = row_series[col_name]
                val_str = "" if val is None else str(val)
                item = QTableWidgetItem(val_str)
                table.setItem(row_idx, col_idx, item)

        header_view = table.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_view.setMinimumSectionSize(90)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setSortingEnabled(True)
        self._last_preview_df_167 = df.copy()

    def _handle_download_preview_167(self) -> None:
        if self._last_preview_df_167 is None or getattr(self._last_preview_df_167, "empty", True):
            QMessageBox.information(self, "Senha 167", "Nenhuma prévia disponível para download.")
            return

        suggested = str(Path.home() / "previa_senha167.xlsx")
        dest_path, _ = QFileDialog.getSaveFileName(self, "Salvar prévia", suggested, "Planilha Excel (*.xlsx)")
        if not dest_path:
            return
        try:
            self._last_preview_df_167.to_excel(dest_path, index=False)
            QMessageBox.information(self, "Senha 167", f"Prévia salva em:\n{dest_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Senha 167", f"Erro ao salvar a prévia: {exc}")

    def _set_orders167_confirm_state(self, pending: bool) -> None:
        self._orders167_pending_confirm = pending
        if pending:
            self.btn_add_orders167.setText("Solicitar confirmação de novas Ordens")
            self.btn_add_orders167.setObjectName("acceptButton")
            self.btn_refresh167.setText("Não confirmar alteração")
            self.btn_refresh167.setObjectName("rejectButton")
        else:
            self.btn_add_orders167.setText("Adicionar ordens novas")
            self.btn_add_orders167.setObjectName("secondaryButton")
            self.btn_refresh167.setText("Inserir planilha Atualizada")
            self.btn_refresh167.setObjectName("primaryButton")
        self._repolish(self.btn_add_orders167)
        self._repolish(self.btn_refresh167)

    def _on_add_orders_171_clicked(self) -> None:
        if getattr(self, "_orders171_pending_confirm", False):
            self._submit_order_confirmation("Senha 171", "_last_preview_df_171", self._set_orders171_confirm_state)
            return
        self._handle_add_orders_171()

    def _on_refresh_171_clicked(self) -> None:
        if getattr(self, "_orders171_pending_confirm", False):
            self._set_orders171_confirm_state(False)
            QMessageBox.information(self, "Senha 171", "Alteração não confirmada. Estado revertido.")
        else:
            QMessageBox.information(self, "Senha 171", "Nenhuma alteração pendente para desfazer.")

    def _handle_add_orders_171(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Importar ordens (xlsx)")
        dialog.setModal(True)
        v = QVBoxLayout(dialog)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)

        label = QLabel("Selecione um arquivo XLSX com as ordens.")
        v.addWidget(label)

        file_display = QLabel("Nenhum arquivo selecionado")
        file_display.setObjectName("mutedText")
        pick_btn = QPushButton("Escolher arquivo")
        pick_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        selected: Dict[str, str | None] = {"path": None}

        def _pick() -> None:
            chosen, _ = QFileDialog.getOpenFileName(dialog, "Selecionar XLSX", "", "Planilhas (*.xlsx)")
            if chosen:
                selected["path"] = chosen
                file_display.setText(Path(chosen).name)

        pick_btn.clicked.connect(_pick)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(pick_btn, 0)
        row.addWidget(file_display, 1)
        v.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_btn:
            ok_btn.setText("Processar")
            ok_btn.setObjectName("primaryButton")
            ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if cancel_btn:
            cancel_btn.setText("Cancelar")
            cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        v.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        file_path = selected.get("path")
        if not file_path:
            QMessageBox.warning(self, "Senha 171", "Nenhum arquivo XLSX selecionado.")
            return

        try:
            helper = AdicionarOrdensNovas(file_path)
            df = helper.load_xlsx()
            df_manip = helper.Manipular_Dados(df=df)
            print("=== XLSX processado (Senha 171) ===")
            if df_manip is None or isinstance(df_manip, str):
                print(df_manip)
            else:
                print(df_manip)
                self._populate_preview_table_171(df_manip)
                self._set_orders171_confirm_state(True)
                self._last_preview_df_171 = df_manip.copy()
            QMessageBox.information(self, "Senha 171", "Arquivo processado. Veja o console para prévia dos dados.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Senha 171", f"Erro ao processar o XLSX: {exc}")

    def _populate_preview_table_171(self, df) -> None:
        if not hasattr(self, "table_preview_171"):
            return
        table = self.table_preview_171
        table.setSortingEnabled(False)
        table.clear()

        if df is None:
            table.setRowCount(0)
            table.setColumnCount(0)
            table.setSortingEnabled(True)
            return

        columns = list(df.columns)
        table.setColumnCount(len(columns))

        header_items = []
        for col_name in columns:
            item = QTableWidgetItem(col_name)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(Qt.GlobalColor.white)
            item.setBackground(QColor("#0f265c"))
            if col_name.strip().lower() == "valor":
                item.setBackground(QColor("#ffeb00"))
                item.setForeground(Qt.GlobalColor.black)
            header_items.append(item)

        for idx, item in enumerate(header_items):
            table.setHorizontalHeaderItem(idx, item)

        rows = len(df.index)
        table.setRowCount(rows)

        for row_idx in range(rows):
            row_series = df.iloc[row_idx]
            for col_idx, col_name in enumerate(columns):
                val = row_series[col_name]
                val_str = "" if val is None else str(val)
                item = QTableWidgetItem(val_str)
                table.setItem(row_idx, col_idx, item)

        header_view = table.horizontalHeader()
        header_view.setStretchLastSection(False)
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header_view.setMinimumSectionSize(90)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setSortingEnabled(True)
        self._last_preview_df_171 = df.copy()

    def _submit_order_confirmation(self, origin: str, df_attr: str, reset_state) -> None:
        df = getattr(self, df_attr, None)
        if df is None or getattr(df, "empty", True):
            QMessageBox.warning(self, origin, "Nenhuma prévia carregada para solicitar confirmação.")
            return
        try:
            self.order_service.submit_request(origin, df)
            QMessageBox.information(self, origin, "Solicitação enviada para 'Solicitações'.")
            reset_state(False)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, origin, f"Erro ao registrar a solicitação: {exc}")

    def _handle_download_preview_171(self) -> None:
        if self._last_preview_df_171 is None or getattr(self._last_preview_df_171, "empty", True):
            QMessageBox.information(self, "Senha 171", "Nenhuma prévia disponível para download.")
            return

        suggested = str(Path.home() / "previa_senha171.xlsx")
        dest_path, _ = QFileDialog.getSaveFileName(self, "Salvar prévia", suggested, "Planilha Excel (*.xlsx)")
        if not dest_path:
            return
        try:
            self._last_preview_df_171.to_excel(dest_path, index=False)
            QMessageBox.information(self, "Senha 171", f"Prévia salva em:\n{dest_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Senha 171", f"Erro ao salvar a prévia: {exc}")

    def _load_users(self) -> None:
        if not getattr(self, "is_admin", False):
            return
        if not hasattr(self, "table_users"):
            return
        table = self.table_users
        table.setSortingEnabled(False)
        table.clearContents()
        table.setRowCount(0)
        try:
            with Session(engine) as session:
                users = user_repository.list_all(session)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Usuários", f"Erro ao carregar usuários: {exc}")
            table.setRowCount(0)
            table.setSortingEnabled(True)
            return

        table.setRowCount(len(users))
        for row_idx, user in enumerate(users):
            # ID (hidden)
            id_item = QTableWidgetItem(str(user.id or ""))
            id_item.setData(Qt.ItemDataRole.UserRole, user.id)
            table.setItem(row_idx, 0, id_item)

            table.setItem(row_idx, 1, QTableWidgetItem(user.name))
            table.setItem(row_idx, 2, QTableWidgetItem(user.email))

            # Perfil drop-down
            combo = QComboBox()
            combo.addItems(["USUARIO", "ADMINISTRADOR"])
            current_role = (user.role or "USUARIO").upper()
            combo.blockSignals(True)
            idx = combo.findText(current_role)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)
            combo.currentIndexChanged.connect(lambda _, uid=user.id, cb=combo: self._on_role_changed(uid, cb))
            table.setCellWidget(row_idx, 3, combo)

            table.setItem(row_idx, 4, QTableWidgetItem(str(user.access_count or 0)))
            last_access = user.last_access_at.strftime("%d/%m/%Y %H:%M") if user.last_access_at else "-"
            table.setItem(row_idx, 5, QTableWidgetItem(last_access))

            # Mensagem / alerta
            msg_btn = QPushButton("Mensagem")
            msg_btn.setObjectName("secondaryButton")
            msg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            msg_btn.setFixedHeight(26)
            msg_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            msg_btn.setStyleSheet("padding: 2px 6px; text-align: center;")
            summary = user.alert_message or "Nenhuma mensagem"
            priority = (user.alert_priority or "-").upper()
            sender = user.alert_sender or "-"
            ts = user.alert_created_at.strftime("%d/%m/%Y %H:%M") if user.alert_created_at else "-"
            msg_btn.setToolTip(f"Prioridade: {priority}\nDe: {sender}\nQuando: {ts}\n\n{summary}")

            # Color hint by priority
            color_map = {
                "CRITICA": "#b91c1c",
                "ALTA": "#e11d48",
                "MEDIA": "#f59e0b",
                "BAIXA": "#0ea5e9",
            }
            pri_color = color_map.get(priority)
            if pri_color:
                msg_btn.setStyleSheet(
                    f"background-color: {pri_color}; color: white; padding: 2px 6px; text-align: center;"
                )
            msg_btn.clicked.connect(
                lambda _, uid=user.id, uname=user.name, cur_msg=user.alert_message, cur_pri=priority: self._edit_user_alert(uid, uname, cur_msg, cur_pri)
            )
            table.setCellWidget(row_idx, 6, msg_btn)

            # Delete button
            del_btn = QPushButton("Excluir")
            del_btn.setObjectName("rejectButton")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setFixedHeight(26)
            del_btn.setMinimumWidth(70)
            del_btn.setMaximumWidth(90)
            del_btn.setStyleSheet("padding: 2px 6px;")
            del_btn.clicked.connect(lambda _, uid=user.id, uname=user.name: self._handle_delete_user(uid, uname))
            table.setCellWidget(row_idx, 7, del_btn)
        table.setSortingEnabled(True)
        table.resizeColumnsToContents()
        table.setColumnWidth(7, 90)

    def _on_role_changed(self, user_id: int | None, combo: QComboBox) -> None:
        if not getattr(self, "is_admin", False):
            QMessageBox.warning(self, "Usuários", "Apenas administradores podem alterar perfis.")
            return
        if user_id is None:
            return
        new_role = combo.currentText().strip().upper()
        try:
            with Session(engine) as session:
                updated = user_repository.set_role(session, user_id, new_role)
            if updated is None:
                QMessageBox.warning(self, "Usuários", "Usuário não encontrado.")
                return
            QMessageBox.information(self, "Usuários", f"Perfil atualizado para {new_role}.")
            self._load_users()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Usuários", f"Erro ao alterar perfil: {exc}")

    def _ack_user_alert(self) -> None:
        user_id = self.user_info.get("id") or self.user_info.get("user_id")
        if user_id is None:
            return
        try:
            with Session(engine) as session:
                user_repository.ack_alert(session, user_id)
            now_iso = datetime.utcnow().isoformat()
            self.user_info["alert_ack_at"] = now_iso
            self.user_info["alert_message"] = None
            self.user_info["alert_priority"] = None
            self.user_info["alert_sender"] = None
            self.user_info["alert_created_at"] = None
        except Exception:
            pass

    def _edit_user_alert(self, user_id: int | None, name: str, current_msg: str | None, current_priority: str | None) -> None:
        if not getattr(self, "is_admin", False):
            QMessageBox.warning(self, "Usuários", "Apenas administradores podem definir mensagens.")
            return
        if user_id is None:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Mensagem para {name}")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        info = QLabel("Defina o texto e a prioridade. Deixe vazio para remover a mensagem.")
        info.setObjectName("mutedText")
        layout.addWidget(info)

        msg_edit = QTextEdit()
        msg_edit.setPlaceholderText("Digite a mensagem a exibir no login do colaborador")
        if current_msg:
            msg_edit.setText(current_msg)
        layout.addWidget(msg_edit)

        pri_combo = QComboBox()
        pri_combo.addItems(["BAIXA", "MEDIA", "ALTA", "CRITICA"])
        cur_pri = (current_priority or "").upper()
        idx = pri_combo.findText(cur_pri)
        pri_combo.setCurrentIndex(idx if idx >= 0 else 0)
        layout.addWidget(pri_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText("Salvar")
            ok_btn.setObjectName("primaryButton")
            ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn:
            cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_msg = msg_edit.toPlainText().strip()
        new_pri = pri_combo.currentText().strip().upper()
        if not new_msg:
            new_pri = None

        try:
            with Session(engine) as session:
                updated = user_repository.set_alert(
                    session,
                    user_id,
                    message=new_msg if new_msg else None,
                    priority=new_pri,
                    sender=self.user_info.get("name", "-"),
                )
            if updated is None:
                QMessageBox.warning(self, "Usuários", "Usuário não encontrado.")
                return
            QMessageBox.information(self, "Usuários", "Mensagem atualizada.")
            self._load_users()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Usuários", f"Erro ao salvar mensagem: {exc}")

    def _handle_delete_user(self, user_id: int | None, name: str) -> None:
        if not getattr(self, "is_admin", False):
            QMessageBox.warning(self, "Usuários", "Apenas administradores podem excluir usuários.")
            return
        if user_id is None:
            return
        confirm = QMessageBox.question(
            self,
            "Excluir usuário",
            f"Excluir definitivamente o usuário {name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            with Session(engine) as session:
                removed = user_repository.delete_user(session, user_id)
            if not removed:
                QMessageBox.warning(self, "Usuários", "Usuário não encontrado.")
                return
            QMessageBox.information(self, "Usuários", "Usuário excluído com sucesso.")
            self._load_users()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Usuários", f"Erro ao excluir usuário: {exc}")

    def _set_orders171_confirm_state(self, pending: bool) -> None:
        self._orders171_pending_confirm = pending
        if pending:
            self.btn_add_orders171.setText("Solicitar confirmação de novas Ordens")
            self.btn_add_orders171.setObjectName("acceptButton")
            self.btn_refresh171.setText("Não confirmar alteração")
            self.btn_refresh171.setObjectName("rejectButton")
        else:
            self.btn_add_orders171.setText("Adicionar ordens novas")
            self.btn_add_orders171.setObjectName("secondaryButton")
            self.btn_refresh171.setText("Inserir planilha Atualizada")
            self.btn_refresh171.setObjectName("primaryButton")
        self._repolish(self.btn_add_orders171)
        self._repolish(self.btn_refresh171)

    def _repolish(self, widget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _show_user_alert(self) -> None:
        msg = (self.user_info.get("alert_message") or "").strip()
        if not msg:
            return
        if self.user_info.get("alert_ack_at"):
            return
        pri = (self.user_info.get("alert_priority") or "").upper() or "BAIXA"
        sender = self.user_info.get("alert_sender") or "-"
        ts_raw = self.user_info.get("alert_created_at")
        ts_display = "-"
        if ts_raw:
            try:
                ts_display = datetime.fromisoformat(ts_raw).strftime("%d/%m/%Y %H:%M")
            except Exception:
                ts_display = str(ts_raw)

        icon = QMessageBox.Icon.Information
        if pri == "CRITICA":
            icon = QMessageBox.Icon.Critical
        elif pri == "ALTA":
            icon = QMessageBox.Icon.Warning
        elif pri == "MEDIA":
            icon = QMessageBox.Icon.Warning

        # Visual detalhado com badge de prioridade, remetente, data e bloco de mensagem
        color_map = {
            "CRITICA": "#b91c1c",
            "ALTA": "#e11d48",
            "MEDIA": "#f59e0b",
            "BAIXA": "#0ea5e9",
        }
        pri_color = color_map.get(pri, "#0ea5e9")
        msg_html = html.escape(msg).replace("\n", "<br>")
        sender_html = html.escape(sender)
        ts_html = html.escape(ts_display)

        text = (
            f"<div style='font-family: Segoe UI, Arial; font-size:13px; line-height:1.45;'>"
            f"<div style='margin-bottom:8px; display:flex; align-items:center; gap:8px;'>"
            f"<span style='display:inline-block; padding:4px 10px; border-radius:999px; background:{pri_color}; color:#fff; font-weight:600; letter-spacing:0.3px;'>{pri}</span>"
            f"<span style='color:#555;'>Enviado por <b>{sender_html}</b> em {ts_html}</span>"
            f"</div>"
            f"<div style='background:#f6f7fb; border:1px solid #e5e7eb; border-radius:10px; padding:10px;'>"
            f"{msg_html}"
            f"</div>"
            f"</div>"
        )

        mb = QMessageBox(icon, "Alerta", "")
        mb.setTextFormat(Qt.TextFormat.RichText)
        mb.setText(text)
        mb.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Yes)
        mb.setDefaultButton(QMessageBox.StandardButton.Yes)
        yes_btn = mb.button(QMessageBox.StandardButton.Yes)
        ok_btn = mb.button(QMessageBox.StandardButton.Ok)
        if yes_btn:
            yes_btn.setText("Marcar como lida")
        if ok_btn:
            ok_btn.setText("Fechar")
        result = mb.exec()
        if result == QMessageBox.StandardButton.Yes:
            self._ack_user_alert()

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
        if not self.is_admin and index in (3, 7):
            QMessageBox.warning(self, "Acesso restrito", "Apenas administradores podem acessar esta área.")
            return
        self.btn_principal.setChecked(index == 0)
        self.btn_estoque.setChecked(index == 1)
        self.btn_relatorios.setChecked(index == 2)
        self.btn_solicitacoes.setChecked(index == 3)
        self.btn_senha.setChecked(index == 4)
        self.btn_sindicancia.setChecked(index == 5)
        self.btn_senha171.setChecked(index == 6)
        self.btn_users.setChecked(index == 7)
        self.btn_config.setChecked(index == 8)
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
            with Session(order_request_engine) as order_session:
                order_requests = order_request_repository.list_pending(order_session)
            with Session(report_engine) as report_session:
                report_requests = report_request_repository.list_pending(report_session)
            combined = (
                [("senha", req) for req in pw_requests]
                + [("registro", req) for req in reg_requests]
                + [("pop", req) for req in pop_requests]
                + [("ordem", req) for req in order_requests]
                + [("relatorio", req) for req in report_requests]
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
        icon_name = "pop.png"
        if kind == "relatorio":
            icon_name = "report.png"
        elif kind == "registro":
            icon_name = "registrado_solicitação.png"
        elif kind == "senha":
            icon_name = "senha_solicitação.png"
        elif kind == "ordem":
            origin_txt = str(getattr(req, "origin", "")).lower()
            if "167" in origin_txt:
                icon_name = "lock-167.png"
            elif "171" in origin_txt:
                icon_name = "lock-171.png"
            else:
                icon_name = "solicitacao.png"
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
        elif kind == "relatorio":
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

            req_kind_label = QLabel("Solicitação: Relatório")
            req_kind_label.setObjectName("requestStatus")
            info_col.addWidget(req_kind_label)
        elif kind == "ordem":
            title_lbl = QLabel(f"Confirmação {req.origin}")
            title_lbl.setObjectName("requestTitle")
            info_col.addWidget(title_lbl)

            detail = QLabel(f"Criado em {self._format_br_datetime(req.created_at)}")
            detail.setObjectName("requestMeta")
            info_col.addWidget(detail)

            status = QLabel(f"Status: {req.status}")
            status.setObjectName("requestStatus")
            info_col.addWidget(status)

            if getattr(req, "total_orders", None) is not None:
                total_lbl = QLabel(f"Total de ordens: {req.total_orders}")
                total_lbl.setObjectName("requestStatus")
                info_col.addWidget(total_lbl)

            desc_lbl = QLabel(req.description)
            desc_lbl.setWordWrap(True)
            desc_lbl.setObjectName("requestStatus")
            info_col.addWidget(desc_lbl)

            req_kind_label = QLabel("Solicitação: Confirmação de Ordens")
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
            if kind in {"registro", "senha", "pop"}:
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
            elif kind == "ordem":
                self.order_service.approve(request_id, approve)
                if approve:
                    QMessageBox.information(self, "Solicitações", "Solicitação de ordens aprovada e armazenada.")
                else:
                    QMessageBox.information(self, "Solicitações", "Solicitação de ordens recusada.")
            else:
                with Session(report_engine) as report_session:
                    report_service = ReportService(report_session)
                    if approve:
                        report_service.approve_report_request(request_id)
                        QMessageBox.information(self, "Solicitações", "Solicitação de relatório aprovada.")
                        self._render_report_cards()
                    else:
                        report_service.reject_report_request(request_id)
                        QMessageBox.information(self, "Solicitações", "Solicitação de relatório recusada.")
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
            QMainWindow { background: #f5f6f7; color: #0f172a; }
            #navPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #1d4ed8);
                border-right: 1px solid #1e3a8a;
                color: #e5e7eb;
            }
            #navTitleBox {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 14px;
            }
            #contentPanel { background: #f9fafb; }
            #navTitle { font-size: 16px; font-weight: 800; color: #f8fafc; }
            #navTitleTag {
                padding: 4px 10px;
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.24);
                background: rgba(255, 255, 255, 0.12);
                color: #e0f2fe;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton {
                padding: 11px 12px;
                border-radius: 10px;
                border: 1px solid #cfd6dd;
                background: #ffffff;
                color: #0f172a;
                text-align: left;
            }
            QPushButton:hover { background: #eef2f6; }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
                border-color: #1d4ed8;
                color: #ffffff;
            }
            #primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
                border-color: #1d4ed8;
                color: #ffffff;
                font-weight: 700;
                letter-spacing: 0.01em;
                text-align: center;
            }
            #primaryButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #2563eb); }
            #primaryButton:pressed { background: #1d4ed8; }
            #secondaryButton {
                background: #f1f5f9;
                color: #0f172a;
                border-color: #cfd6dd;
                font-weight: 600;
            }
            #secondaryButton:hover {
                background: #fee2e2;
                border-color: #fca5a5;
                color: #991b1b;
            }
            #secondaryButton:pressed {
                background: #ef4444;
                border-color: #dc2626;
                color: #ffffff;
            }
            #deleteIconButton {
                background: rgba(248, 113, 113, 0.14);
                border: 1px solid rgba(248, 113, 113, 0.6);
                border-radius: 10px;
                padding: 6px;
            }
            #deleteIconButton:hover {
                background: rgba(248, 113, 113, 0.2);
                border-color: #f87171;
            }
            #deleteIconButton:pressed {
                background: #f87171;
                border-color: #ef4444;
            }
            #acceptButton {
                background: #16a34a;
                border-color: #16a34a;
                color: #ffffff;
                font-weight: 700;
                text-align: center;
            }
            #acceptButton:hover { background: #15803d; }
            #rejectButton {
                background: #dc2626;
                border-color: #dc2626;
                color: #ffffff;
                font-weight: 700;
                text-align: center;
            }
            #rejectButton:hover { background: #b91c1c; }
            #pageTitle { font-size: 22px; font-weight: 800; color: #0f172a; }
            #infoCard {
                border: 1px solid #d8dde3;
                border-radius: 14px;
                background: #ffffff;
            }
            #cardTitle { font-size: 15px; font-weight: 700; color: #0f172a; }
            #mutedText { color: #6b7280; font-size: 12px; }
            #infoList { background: transparent; border: none; color: #0f172a; }
            #requestList { background: transparent; border: none; }
            #requestCard {
                border: 1px solid #d8dde3;
                border-radius: 14px;
                background: #ffffff;
            }
            #requestTitle { font-size: 14px; font-weight: 700; color: #0f172a; }
            #requestMeta { color: #6b7280; font-size: 12px; }
            #requestStatus { color: #374151; font-size: 12px; }
            #popCard {
                border: 1px solid #d8dde3;
                border-radius: 14px;
                background: #ffffff;
            }
            #popIcon {
                max-width: 32px;
                max-height: 32px;
            }
            #placeholder { color: #6b7280; font-size: 14px; }
            #userBox {
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.06);
                color: #e5e7eb;
            }
            #userName { font-size: 14px; font-weight: 700; color: #e5e7eb; }
            #userEmail { font-size: 12px; color: #cbd5e1; }
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
