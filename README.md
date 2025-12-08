# Controle de Estoque (Desktop + FastAPI)

Interface desktop em PyQt6 para acesso local, com backend FastAPI/SQLite a ser integrado. Foco em camadas claras e prontidão para empacotamento em .exe.

## Requisitos
- Python 3.10+
- Dependências no `requirements.txt` (PyQt6 para a interface). Demais libs de backend serão adicionadas quando as rotas forem implementadas.

## Instalação
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Executar a interface (modo visual apenas)
```bash
python servidor.py
```

## Estrutura atual
```
servidor.py          # Ponto de entrada: sobe a janela PyQt6
ui/
  __init__.py        # Pacote UI
  login_window.py    # Tela de login/registro (apenas visual)
```

## Próximos passos
- Integrar backend FastAPI (auth, usuários) e conectar os botões via HTTP.
- Adicionar SQLModel/SQLite e serviços de repositório.
- Preparar empacotamento (PyInstaller/auto-py-to-exe).
