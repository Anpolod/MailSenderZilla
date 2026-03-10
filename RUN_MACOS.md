# Запуск MailSenderZilla на macOS

## 📋 Подготовка файлов на Windows

### Шаг 1: Подготовка проекта для копирования

Перед копированием на флешку, исключите ненужные файлы:

**НЕ копируйте следующие папки/файлы:**
- `.venv/` (виртуальное окружение Python)
- `__pycache__/` (кэш Python)
- `frontend/node_modules/` (зависимости Node.js)
- `*.db` (базы данных - можно скопировать, если нужны данные)
- `.DS_Store` (системные файлы macOS)
- `*.log` (логи)

**Что КОПИРОВАТЬ (основная структура проекта):**
```
MailSenderZilla/
├── backend/              # весь каталог (кроме __pycache__)
├── frontend/            # весь каталог (кроме node_modules и dist)
├── templates/           # весь каталог
├── examples/            # весь каталог
├── uploads/             # весь каталог
├── requirements.txt     # файл зависимостей Python
├── setup.sh            # скрипт установки для macOS/Linux
├── run_backend.sh      # скрипт запуска backend
├── run_frontend.sh     # скрипт запуска frontend
├── README.md           # документация
└── RUN_MACOS.md        # эта инструкция
```

### Шаг 2: Копирование на флешку

1. **Подключите флешку** к компьютеру с Windows
2. **Откройте проводник Windows** (File Explorer)
3. **Скопируйте папку проекта** `MailSenderZilla` на флешку
   - Убедитесь, что скопированы все файлы из списка выше
   - Не копируйте файлы из списка "НЕ копировать"

### Шаг 3: Безопасное извлечение флешки

1. В проводнике Windows **правой кнопкой** на флешке → **"Извлечь"**
2. Дождитесь сообщения "Безопасное извлечение устройства"
3. Только после этого **извлеките флешку**

---

## 🍎 Установка на macOS

### Предварительные требования

#### 1. Python 3.8+

**Проверьте, установлен ли Python:**
```bash
python3 --version
```

**Если Python не установлен:**
- **Способ 1 (рекомендуется):** Установите через Homebrew:
  ```bash
  # Установите Homebrew, если его нет:
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  
  # Установите Python:
  brew install python3
  ```

- **Способ 2:** Скачайте с [python.org](https://www.python.org/downloads/)
  - Выберите версию 3.8 или новее
  - Запустите установщик и следуйте инструкциям

#### 2. Node.js 16+ и npm

**Проверьте, установлен ли Node.js:**
```bash
node --version
npm --version
```

**Если Node.js не установлен:**
- **Способ 1 (рекомендуется):** Через Homebrew:
  ```bash
  brew install node
  ```

- **Способ 2:** Скачайте с [nodejs.org](https://nodejs.org/)
  - Выберите LTS версию
  - Запустите установщик `.pkg`

**После установки Node.js** перезапустите Terminal (закройте и откройте заново)

#### 3. Git (опционально, но рекомендуется)

```bash
# Проверка
git --version

# Установка через Homebrew (если нужно)
brew install git
```

---

## 📦 Перенос проекта на macOS

### Шаг 1: Скопируйте проект с флешки

1. **Подключите флешку** к Mac
2. **Откройте Finder**
3. **Найдите флешку** в боковом меню (обычно называется "Untitled" или имеет имя)
4. **Скопируйте папку** `MailSenderZilla` в удобное место, например:
   - `~/Documents/` (Документы)
   - `~/Desktop/` (Рабочий стол)
   - Или создайте папку `~/Projects/` для проектов

**В Terminal:**
```bash
# Перейдите в папку, куда хотите скопировать проект
cd ~/Documents

# Скопируйте проект (замените /Volumes/USB_NAME на имя вашей флешки)
cp -r /Volumes/USB_NAME/MailSenderZilla ./

# Или через Finder: просто перетащите папку
```

### Шаг 2: Откройте Terminal и перейдите в проект

```bash
cd ~/Documents/MailSenderZilla
# или путь, куда вы скопировали проект
```

---

## 🔧 Установка проекта (первый раз)

### Автоматическая установка (рекомендуется)

```bash
# Перейдите в папку проекта
cd ~/Documents/MailSenderZilla

# Дайте права на выполнение скриптам
chmod +x setup.sh run_backend.sh run_frontend.sh

# Запустите скрипт установки
./setup.sh
```

Скрипт автоматически:
- ✅ Создаст виртуальное окружение Python
- ✅ Установит все зависимости Python
- ✅ Инициализирует базу данных
- ✅ Установит зависимости Node.js для frontend

### Ручная установка (если автоматическая не работает)

#### 1. Создайте виртуальное окружение Python

```bash
python3 -m venv .venv
```

#### 2. Активируйте виртуальное окружение

```bash
source .venv/bin/activate
```

Вы должны увидеть `(.venv)` в начале строки терминала.

#### 3. Обновите pip

```bash
pip install --upgrade pip
```

#### 4. Установите зависимости Python

```bash
pip install -r requirements.txt
```

#### 5. Инициализируйте базу данных

```bash
python -m backend.migrate
```

Это создаст файл `Main_DataBase.db` с необходимыми таблицами.

#### 6. Установите зависимости Frontend

```bash
cd frontend
npm install
cd ..
```

---

## 🚀 Запуск приложения

### Режим разработки (Development)

Вам понадобится **два окна Terminal**, работающие одновременно.

#### Terminal 1: Backend сервер

```bash
# Перейдите в папку проекта
cd ~/Documents/MailSenderZilla

# Дайте права на выполнение (только первый раз)
chmod +x run_backend.sh

# Запустите backend
./run_backend.sh
```

Или вручную:
```bash
cd ~/Documents/MailSenderZilla
source .venv/bin/activate
python -m backend.app
```

Backend будет доступен по адресу: **http://localhost:5000**

#### Terminal 2: Frontend сервер

Откройте **новое окно Terminal** (⌘+T или Terminal → New Window):

```bash
# Перейдите в папку проекта
cd ~/Documents/MailSenderZilla

# Дайте права на выполнение (только первый раз)
chmod +x run_frontend.sh

# Запустите frontend
./run_frontend.sh
```

Или вручную:
```bash
cd ~/Documents/MailSenderZilla/frontend
npm run dev
```

Frontend будет доступен по адресу: **http://localhost:3000**

### Откройте приложение в браузере

Откройте браузер и перейдите по адресу:
- **http://localhost:3000** (режим разработки)
- Или **http://localhost:5000** (если используется production режим)

---

## 📝 Режим production

Если хотите запустить приложение в режиме production (один сервер):

### 1. Соберите frontend

```bash
cd ~/Documents/MailSenderZilla/frontend
npm run build
cd ..
```

### 2. Запустите backend (он автоматически будет отдавать собранный frontend)

```bash
source .venv/bin/activate
python -m backend.app
```

Приложение будет доступно по адресу: **http://localhost:5000**

---

## 🔍 Решение проблем

### "Permission denied" при запуске скриптов

```bash
chmod +x setup.sh run_backend.sh run_frontend.sh
```

### "python3: command not found"

- Убедитесь, что Python установлен: `python3 --version`
- Если не установлен, установите через Homebrew: `brew install python3`

### "npm: command not found" или "node: command not found"

- Убедитесь, что Node.js установлен: `node --version`
- Если не установлен, установите через Homebrew: `brew install node`
- **Важно:** После установки **закройте и откройте Terminal заново**

### Порт 5000 или 3000 уже занят

**Проверьте, что использует порт:**
```bash
# Для порта 5000
lsof -i :5000

# Для порта 3000
lsof -i :3000
```

**Остановите процесс:**
```bash
# Найдите PID (первое число в выводе lsof) и убейте процесс:
kill -9 <PID>
```

Или измените порты в настройках:
- Backend: `backend/app.py` (строка ~309)
- Frontend: `frontend/vite.config.js` (строка ~7)

### Ошибки базы данных

Удалите базу данных и переинициализируйте:
```bash
rm Main_DataBase.db
source .venv/bin/activate
python -m backend.migrate
```

### Ошибки импорта модулей

Убедитесь, что виртуальное окружение активировано:
```bash
source .venv/bin/activate
```

Переустановите зависимости:
```bash
pip install -r requirements.txt
```

### "ModuleNotFoundError" или другие ошибки Python

```bash
# Убедитесь, что виртуальное окружение активировано
source .venv/bin/activate

# Переустановите зависимости
pip install --upgrade pip
pip install -r requirements.txt
```

### Проблемы с правами доступа

Если получаете ошибки "Permission denied":
```bash
# Дайте права на выполнение всем скриптам
chmod +x *.sh

# Проверьте права на папки
chmod -R 755 backend frontend
```

---

## 📚 Дополнительная информация

### Переменные окружения (опционально)

Создайте файл `.env` в корне проекта:

```bash
cd ~/Documents/MailSenderZilla
nano .env
```

Добавьте (при необходимости):
```
SECRET_KEY=your-secret-key-here
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
```

Сохраните: `Ctrl+O`, затем `Enter`, затем `Ctrl+X`

### Структура проекта

```
MailSenderZilla/
├── backend/              # Python backend (Flask)
│   ├── app.py           # Главный файл приложения
│   ├── models/          # Модели базы данных
│   ├── services/        # Бизнес-логика
│   └── utils/           # Утилиты
├── frontend/            # React frontend
│   └── src/             # Исходники React
├── templates/           # HTML шаблоны email
├── uploads/             # Загруженные CSV файлы
└── Main_DataBase.db     # База данных SQLite
```

### Быстрые команды

**Активация виртуального окружения:**
```bash
source .venv/bin/activate
```

**Деактивация виртуального окружения:**
```bash
deactivate
```

**Обновление зависимостей:**
```bash
# Python
pip install --upgrade -r requirements.txt

# Node.js
cd frontend && npm update && cd ..
```

---

## ✅ Следующие шаги

1. ✅ Откройте **http://localhost:3000** в браузере
2. ✅ Загрузите CSV файл с email адресами
3. ✅ Настройте email провайдера (MailerSend или Gmail)
4. ✅ Создайте и запустите кампанию!

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте раздел "Решение проблем" выше
2. Убедитесь, что все зависимости установлены
3. Проверьте логи в терминале на наличие ошибок

---

**Успешной работы! 🚀**
