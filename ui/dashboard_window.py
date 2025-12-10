from __future__ import annotations

from typing import Dict
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
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
    QVBoxLayout,
    QWidget,
)

from sqlmodel import Session

from db.config import engine
from services.auth_service import AuthService, AuthError


class DashboardWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, user_info: Dict[str, str]) -> None:
        super().__init__()
        self.user_info = user_info
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
        self.btn_estoque = QPushButton("Estoque")
        self.btn_relatorios = QPushButton("Relatórios")
        self.btn_senha = QPushButton("Senha 167")
        self.btn_sindicancia = QPushButton("Sindicância")
        self.btn_senha171 = QPushButton("Senha 171")
        self.btn_config = QPushButton("Configurações")

        buttons = (
            self.btn_principal,
            self.btn_estoque,
            self.btn_relatorios,
            self.btn_senha,
            self.btn_sindicancia,
            self.btn_senha171,
            self.btn_config,
        )

        icon_map = {
            self.btn_principal: "home.png",
            self.btn_estoque: "boxes.png",
            self.btn_relatorios: "report.png",
            self.btn_senha: "lock-167.png",
            self.btn_sindicancia: "shield.png",
            self.btn_senha171: "lock-171.png",
            self.btn_config: "settings.png",
        }

        for idx, btn in enumerate(buttons):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self._switch_page(i))
            if btn not in (self.btn_principal, self.btn_config):
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
        self.stack.addWidget(self._build_placeholder_page("Estoque em breve"))
        self.stack.addWidget(self._build_placeholder_page("Relatórios em breve"))
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

    def _build_placeholder_page(self, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label = QLabel(text)
        label.setObjectName("placeholder")
        layout.addWidget(label)
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
        self.btn_senha.setChecked(index == 3)
        self.btn_sindicancia.setChecked(index == 4)
        self.btn_senha171.setChecked(index == 5)
        self.btn_config.setChecked(index == 6)
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
            #secondaryButton { background: #f3f4f6; color: #1f2933; border-color: #cfd6dd; }
            #secondaryButton:hover { background: #991b1b; color: #ffffff; border-color: #7f1d1d; }
            #pageTitle { font-size: 22px; font-weight: 700; color: #111827; }
            #infoCard {
                border: 1px solid #d8dde3;
                border-radius: 12px;
                background: #ffffff;
            }
            #cardTitle { font-size: 14px; font-weight: 700; color: #1f2933; }
            #infoList { background: transparent; border: none; color: #1f2933; }
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
