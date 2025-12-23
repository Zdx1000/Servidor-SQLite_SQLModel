from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QDialog,
    QDialogButtonBox,
    QGraphicsOpacityEffect,
    QPushButton,
    QSpacerItem,
    QStackedWidget,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sqlmodel import Session

from db.config import engine
from services.auth_service import AuthError, AuthService


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    is_password: bool = False


class AuthForm(QWidget):
    def __init__(self, title: str, fields: List[FieldSpec], submit_label: str) -> None:
        super().__init__()
        self._inputs: Dict[str, QLineEdit] = {}
        self.submit_button = QPushButton(submit_label)
        self._build_ui(title, fields)

    def _build_ui(self, title: str, fields: List[FieldSpec]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)

        header = QLabel(title)
        header.setObjectName("formTitle")
        layout.addWidget(header)

        for field in fields:
            label = QLabel(field.label)
            input_box = QLineEdit()
            input_box.setObjectName(f"input_{field.key}")
            input_box.setClearButtonEnabled(True)
            input_box.setPlaceholderText(field.label)
            if field.is_password:
                input_box.setEchoMode(QLineEdit.EchoMode.Password)
            self._inputs[field.key] = input_box

            layout.addWidget(label)
            layout.addWidget(input_box)

        layout.addSpacerItem(QSpacerItem(0, 12, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.submit_button.setObjectName("primaryButton")
        self.submit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.submit_button)

    def values(self) -> Dict[str, str]:
        return {key: widget.text().strip() for key, widget in self._inputs.items()}

    def clear_fields(self) -> None:
        for widget in self._inputs.values():
            widget.clear()

    def clear_errors(self) -> None:
        for widget in self._inputs.values():
            widget.setStyleSheet("")

    def on_return_pressed(self, callback) -> None:
        for widget in self._inputs.values():
            widget.returnPressed.connect(callback)

    def mark_error(self, key: str) -> None:
        widget = self._inputs.get(key)
        if widget:
            widget.setStyleSheet("border: 1px solid #dc2626;")


class ForgotPasswordDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Recuperar acesso")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("Recuperar acesso")
        title.setObjectName("formTitle")
        layout.addWidget(title)

        info = QLabel("Solicite a atualização de senha para aprovação do administrador.")
        info.setObjectName("dialogSubtitle")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Usuário")
        self.user_input.setClearButtonEnabled(True)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("E-mail")
        self.email_input.setClearButtonEnabled(True)

        self.new_pass_input = QLineEdit()
        self.new_pass_input.setPlaceholderText("Nova senha")
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_input.setClearButtonEnabled(True)

        self.confirm_pass_input = QLineEdit()
        self.confirm_pass_input.setPlaceholderText("Confirmar nova senha")
        self.confirm_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pass_input.setClearButtonEnabled(True)

        for widget in (self.user_input, self.email_input, self.new_pass_input, self.confirm_pass_input):
            layout.addWidget(widget)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button:
            ok_button.setText("Solicitar atualizar senha")
            ok_button.setObjectName("primaryButton")
            ok_button.setCursor(Qt.CursorShape.PointingHandCursor)
        if cancel_button:
            cancel_button.setText("Cancelar")
            cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)

    def values(self) -> Dict[str, str]:
        return {
            "user": self.user_input.text().strip(),
            "email": self.email_input.text().strip(),
            "new_password": self.new_pass_input.text(),
            "confirm_password": self.confirm_pass_input.text(),
        }


class LoginWindow(QMainWindow):
    login_success = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Controle de Estoque - Acesso")
        self.setMinimumSize(960, 560)
        self._fade_duration_ms = 180
        self._icon_dir = Path(__file__).resolve().parent / "assets" / "icons"
        app_icon = self._load_icon("app.png")
        if app_icon is not None:
            self.setWindowIcon(app_icon)
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget()
        root_layout = QHBoxLayout(container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_brand_panel())
        root_layout.addWidget(self._build_auth_panel(), 1)

        self.setCentralWidget(container)
        self._apply_style()

    def _build_brand_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("brandPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(16)

        logo_widget = self._build_logo()
        if logo_widget:
            layout.addWidget(logo_widget, 0, Qt.AlignmentFlag.AlignHCenter)

        badge = QLabel("Martins • Operações Internas")
        badge.setObjectName("brandBadge")

        title = QLabel("Controle de Estoque")
        title.setObjectName("brandTitle")
        subtitle = QLabel("Fluxo diário confiável para entradas, saídas e inventário da Martins.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("brandSubtitle")

        layout.addWidget(badge)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        info_card = QFrame()
        info_card.setObjectName("infoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(6)
        for text in (
            "Servidor local FastAPI integrado ao estoque Martins.",
            "Base SQLite + SQLModel; pronta para migração futura.",
            "Acesso restrito à equipe Martins com autenticação local.",
        ):
            line = QLabel(f"• {text}")
            line.setWordWrap(True)
            line.setObjectName("infoLine")
            info_layout.addWidget(line)
        layout.addWidget(info_card)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        stat_items = [
            ("0", "Movimentos hoje"),
            ("0", "Usuários ativos"),
            ("0", "Filiais conectadas"),
        ]
        for value, label in stat_items:
            card = QFrame()
            card.setObjectName("statCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(2)

            value_label = QLabel(value)
            value_label.setObjectName("statValue")
            label_label = QLabel(label)
            label_label.setObjectName("statLabel")

            card_layout.addWidget(value_label)
            card_layout.addWidget(label_label)
            stats.addWidget(card)
        layout.addLayout(stats)

        layout.addStretch(1)

        footer = QLabel("Backend FastAPI + SQLite/SQLModel • Interface PyQt6")
        footer.setObjectName("brandFooter")
        layout.addWidget(footer)

        contact = QLabel("Martins • suporte interno")
        contact.setObjectName("brandContact")
        layout.addWidget(contact)

        return panel

    def _build_logo(self) -> QLabel | None:
        logo_path = self._icon_dir / "martins.png"
        if not logo_path.exists():
            return None
        pixmap = QPixmap(str(logo_path))
        if pixmap.isNull():
            return None
        label = QLabel()
        label.setObjectName("brandLogo")
        label.setPixmap(
            pixmap.scaled(176, 176, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )
        return label

    def _build_auth_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("authPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(16)

        toggle_frame = QFrame()
        toggle_frame.setObjectName("toggleFrame")
        button_row = QHBoxLayout(toggle_frame)
        button_row.setContentsMargins(6, 6, 6, 6)
        button_row.setSpacing(8)
        self.login_button = QPushButton("Entrar")
        self.register_button = QPushButton("Solicitar registro")
        for button in (self.login_button, self.register_button):
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setObjectName("modeButton")
            button_row.addWidget(button)

        self.login_button.setChecked(True)
        self.login_button.clicked.connect(lambda: self._switch_form(0))
        self.register_button.clicked.connect(lambda: self._switch_form(1))

        layout.addWidget(toggle_frame)

        self.login_form = AuthForm(
            title="Acessar conta",
            fields=[
                FieldSpec("identifier", "E-mail ou usuário"),
                FieldSpec("password", "Senha", is_password=True),
            ],
            submit_label="Entrar",
        )
        self.login_form.on_return_pressed(lambda: self._handle_submit("login"))

        self.register_form = AuthForm(
            title="Solicitar registro",
            fields=[
                FieldSpec("name", "Nome"),
                FieldSpec("email", "E-mail"),
                FieldSpec("password", "Senha", is_password=True),
                FieldSpec("confirm", "Confirmar senha", is_password=True),
            ],
            submit_label="Solicitar registro",
        )

        for form in (self.login_form, self.register_form):
            self._ensure_opacity_effect(form)

        self.login_form.submit_button.clicked.connect(lambda: self._handle_submit("login"))
        self.register_form.submit_button.clicked.connect(lambda: self._handle_submit("register"))

        self.forgot_button = QPushButton("Esqueci a senha")
        self.forgot_button.setObjectName("linkButton")
        self.forgot_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.forgot_button.clicked.connect(self._handle_forgot_password)
        self.login_form.layout().addWidget(self.forgot_button)  # type: ignore[arg-type]

        self.stack = QStackedWidget()
        self.stack.addWidget(self.login_form)
        self.stack.addWidget(self.register_form)

        layout.addWidget(self.stack, 1)
        return panel

    def _switch_form(self, index: int) -> None:
        if index == self.stack.currentIndex():
            return
        self.login_button.setChecked(index == 0)
        self.register_button.setChecked(index == 1)
        self.stack.setCurrentIndex(index)
        target = self.stack.currentWidget()
        self._animate_fade_in(target)

    def _handle_submit(self, mode: str) -> None:
        form = self.login_form if mode == "login" else self.register_form
        data = form.values()

        # reset highlights
        self.login_form.clear_errors()
        self.register_form.clear_errors()

        try:
            with Session(engine) as session:
                auth = AuthService(session)

                if mode == "login":
                    user = auth.authenticate(data.get("identifier", ""), data.get("password", ""))
                    if user:
                        self.login_success.emit(
                            {
                                "name": user.name,
                                "email": user.email,
                                "role": "Administrador",  # Placeholder até termos perfis
                                "last_login": user.created_at.strftime("%d/%m/%Y %H:%M"),
                            }
                        )
                    else:
                        self.login_form.mark_error("identifier")
                        self.login_form.mark_error("password")
                        QMessageBox.warning(self, "Falha no login", "Credenciais inválidas.")
                else:
                    password = data.get("password", "")
                    confirm = data.get("confirm", "")
                    missing = [key for key in ("name", "email", "password", "confirm") if not data.get(key)]
                    for key in missing:
                        self.register_form.mark_error(key)
                    if missing:
                        QMessageBox.warning(self, "Cadastro", "Preencha todos os campos obrigatórios.")
                        return
                    if password != confirm:
                        self.register_form.mark_error("password")
                        self.register_form.mark_error("confirm")
                        QMessageBox.warning(self, "Senha", "As senhas não conferem.")
                        return
                    auth.request_registration(
                        name=data.get("name", ""),
                        email=data.get("email", ""),
                        password=password,
                    )
                    QMessageBox.information(
                        self,
                        "Solicitação enviada",
                        "Pedido de registro enviado para aprovação do administrador."
                        "\nVocê receberá acesso assim que for aprovado.",
                    )
                    self.register_form.clear_fields()
                    self._switch_form(0)
                    self.login_form.clear_fields()
        except AuthError as exc:
            QMessageBox.warning(self, "Validação", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro: {exc}")

    def _handle_forgot_password(self) -> None:
        dialog = ForgotPasswordDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.values()
            if data.get("new_password") != data.get("confirm_password"):
                QMessageBox.warning(self, "Solicitação", "Nova senha e confirmação não conferem.")
                return
            missing = [key for key in ("user", "email", "new_password", "confirm_password") if not data.get(key)]
            if missing:
                QMessageBox.warning(self, "Solicitação", "Preencha usuário, e-mail e as duas senhas.")
                return
            try:
                with Session(engine) as session:
                    auth = AuthService(session)
                    auth.request_password_update(
                        user_name=data.get("user", ""),
                        email=data.get("email", ""),
                        new_password=data.get("new_password", ""),
                    )
                QMessageBox.information(
                    self,
                    "Solicitação registrada",
                    "Pedido de atualização de senha enviado para aprovação do administrador.",
                )
            except AuthError as exc:
                QMessageBox.warning(self, "Solicitação", str(exc))
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Erro", f"Ocorreu um erro: {exc}")

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f5f6f7;
                color: #1f2933;
            }
            QWidget { color: #1f2933; }
            #brandPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #1d4ed8);
                color: #e5e7eb;
                border-right: none;
            }
            #brandPanel QLabel { color: #e5e7eb; }
            #authPanel { background: #f9fafb; color: #1f2933; border-left: 1px solid #d8dde3; }
            #brandBadge {
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                color: #cbd5e1;
            }
            #brandTitle { font-size: 26px; font-weight: 700; color: #ffffff; }
            #brandSubtitle { font-size: 14px; color: #e0e7ff; }
            #brandFooter { font-size: 12px; color: #cbd5e1; }
            #brandContact { font-size: 12px; color: #bfdbfe; }
            #brandLogo { margin-bottom: 6px; }
            QLabel { font-size: 13px; color: #1f2933; }
            #infoCard {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
            }
            #infoLine { font-size: 12px; color: #e5e7eb; }
            #statCard {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 12px;
            }
            #statValue { font-size: 18px; font-weight: 700; color: #ffffff; }
            #statLabel { font-size: 11px; color: #cbd5e1; }
            QDialog {
                background: #f5f6f7;
            }
            #dialogSubtitle {
                font-size: 13px;
                color: #4b5563;
            }
            QDialogButtonBox QPushButton {
                padding: 10px 14px;
                border-radius: 10px;
                border: 1px solid #cfd6dd;
                background: #ffffff;
                color: #111827;
                min-width: 110px;
            }
            QDialogButtonBox QPushButton:hover { background: #eef2f6; }
            QLineEdit {
                padding: 12px;
                border: 1px solid #cfd6dd;
                border-radius: 10px;
                background: #ffffff;
                color: #111827;
                selection-background-color: #2563eb;
            }
            QLineEdit::placeholder { color: #9aa4b5; }
            QLineEdit:focus { border-color: #2563eb; }
            #toggleFrame {
                background: #e5e7eb;
                border: 1px solid #d1d5db;
                border-radius: 14px;
            }
            QPushButton {
                padding: 12px;
                border-radius: 10px;
                border: 1px solid #cfd6dd;
                background: #ffffff;
                color: #111827;
            }
            QPushButton:hover { background: #eef2f6; }
            QPushButton:checked { background: #2563eb; border-color: #2563eb; color: #ffffff; }
            QPushButton:pressed { background: #e2e8f0; }
            #modeButton {
                background: transparent;
                border: none;
                color: #4b5563;
                font-weight: 600;
                padding: 12px 18px;
                border-radius: 12px;
                min-width: 120px;
            }
            #modeButton:hover { background: rgba(255, 255, 255, 0.9); color: #111827; }
            #modeButton:checked {
                background: #ffffff;
                color: #111827;
                border: 1px solid #2563eb;
            }
            #modeButton:pressed { background: #e2e8f0; }
            #primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
                border-color: #1d4ed8;
                color: #ffffff;
                font-weight: 700;
                letter-spacing: 0.01em;
            }
            #primaryButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3b82f6, stop:1 #2563eb); }
            #primaryButton:pressed { background: #1d4ed8; }
            #formTitle { font-size: 20px; font-weight: 600; margin-bottom: 8px; color: #111827; }
            #authPanel QPushButton { min-height: 42px; }
            #authPanel QLabel { font-weight: 500; }
            #linkButton {
                border: none;
                background: transparent;
                color: #2563eb;
                padding-left: 0;
                text-align: left;
            }
            #linkButton:hover { text-decoration: underline; background: transparent; }
            """
        )

    def _ensure_opacity_effect(self, widget: QWidget) -> QGraphicsOpacityEffect:
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            effect.setOpacity(1.0)
            widget.setGraphicsEffect(effect)
        return effect

    def _animate_fade_in(self, widget: QWidget) -> None:
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(self._fade_duration_ms)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _load_icon(self, name: str | None) -> QIcon | None:
        if not name:
            return None
        path = self._icon_dir / name
        if not path.exists():
            return None
        return QIcon(str(path))


__all__ = ["LoginWindow"]
