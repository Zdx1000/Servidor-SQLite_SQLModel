from PyInstaller.utils.hooks import collect_submodules

# Inclui todos os handlers do passlib e o backend bcrypt
hiddenimports = collect_submodules("passlib.handlers") + ["bcrypt"]
