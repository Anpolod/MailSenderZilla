# MailSenderZilla

Веб-приложение для массовых email-кампаний (ASAP Marine Agency) с поддержкой MailerSend API и Gmail SMTP.

## Установка

Все установки выполняются в виртуальном окружении для изоляции зависимостей.

### Автоматическая установка

```bash
./setup.sh
```

Этот скрипт:
- Создаст виртуальное окружение Python (`.venv`)
- Установит все Python зависимости
- Инициализирует базу данных
- Установит Node.js зависимости (если Node.js установлен)

### Ручная установка

1. **Создать виртуальное окружение:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # На Windows: .venv\Scripts\activate
   ```

2. **Установить Python зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Инициализировать базу данных:**
   ```bash
   python -m backend.migrate
   ```

4. **Установить Node.js зависимости:**
   ```bash
   cd frontend
   npm install
   cd ..
   ```

## Запуск

### Backend (Flask)

В одном терминале:
```bash
./run_backend.sh
```

Или вручную:
```bash
source .venv/bin/activate
python -m backend.app
```

Backend будет доступен на `http://localhost:5000`

### Frontend (React)

В другом терминале:
```bash
./run_frontend.sh
```

Или вручную:
```bash
cd frontend
npm run dev
```

Frontend будет доступен на `http://localhost:3000`

## Структура проекта

```
MailSenderZilla/
├── .venv/                    # Виртуальное окружение Python (изолированные установки)
├── backend/                  # Flask backend
├── frontend/                 # React frontend
│   └── node_modules/         # Node.js зависимости (изолированные)
├── templates/                # HTML шаблоны
├── examples/                 # Примеры файлов
├── uploads/                  # Загруженные CSV файлы
├── Main_DataBase.db          # База данных SQLite
├── run_backend.sh            # Скрипт запуска backend
├── run_frontend.sh           # Скрипт запуска frontend
└── setup.sh                  # Скрипт установки
```

## Использование виртуального окружения

Все Python зависимости установлены в `.venv/`:
- Изолировано от системных пакетов
- Легко удалить: `rm -rf .venv`
- Легко переустановить: `./setup.sh`

Все Node.js зависимости установлены в `frontend/node_modules/`:
- Изолировано от глобальных пакетов
- Легко удалить: `rm -rf frontend/node_modules`
- Легко переустановить: `cd frontend && npm install`

## Требования

- Python 3.8+
- Node.js 16+ (установлен через Homebrew)
- Виртуальное окружение создано автоматически

## Дополнительная информация

См. `README.md` для полной документации на английском языке.

