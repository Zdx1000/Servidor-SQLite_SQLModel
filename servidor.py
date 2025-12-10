from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from db.config import init_db
from ui.dashboard_window import DashboardWindow
from ui.login_window import LoginWindow


def main() -> None:
	init_db()
	app = QApplication(sys.argv)
	login_window = LoginWindow()

	def open_dashboard(user: dict) -> None:
		dashboard = DashboardWindow(user)

		def on_logout() -> None:
			dashboard.close()
			login_window.show()

		dashboard.logout_requested.connect(on_logout)
		dashboard.show()
		login_window.close()

	login_window.login_success.connect(open_dashboard)
	login_window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()
