# 📦 Инструкция по переносу проекта на macOS

## Шаг 1: Подготовка файлов на Windows

### Что нужно скопировать

✅ **Обязательно скопировать:**
- Вся папка `backend/` (кроме `__pycache__`)
- Вся папка `frontend/` (кроме `node_modules` и `dist`)
- Вся папка `templates/`
- Вся папка `examples/`
- Папка `uploads/` (можно пустую)
- Все файлы `.py` в корне
- `requirements.txt`
- `setup.sh`
- `run_backend.sh`
- `run_frontend.sh`
- `README.md`, `RUN_MACOS.md` и другие `.md` файлы

❌ **НЕ копировать:**
- `.venv/` - виртуальное окружение (будет создано заново на Mac)
- `__pycache__/` - кэш Python
- `*.pyc` - скомпилированные файлы Python
- `frontend/node_modules/` - зависимости Node.js (установятся заново)
- `frontend/dist/` - собранный frontend
- `*.db` - базы данных (можно скопировать, если нужны данные)
- `*.log` - файлы логов
- `.DS_Store` - служебные файлы macOS

### Быстрый способ копирования

1. **Откройте папку проекта** в проводнике Windows
2. **Выделите нужные папки и файлы** (Ctrl+Click для множественного выбора)
3. **Скопируйте** (Ctrl+C)
4. **Вставьте на флешку** (Ctrl+V)

### Альтернативный способ через командную строку

Откройте **PowerShell** в папке проекта и выполните:

```powershell
# Создайте папку для копирования на флешку (замените E: на букву вашей флешки)
$USB = "E:\MailSenderZilla"

# Создайте структуру папок
New-Item -ItemType Directory -Path "$USB" -Force
New-Item -ItemType Directory -Path "$USB\backend" -Force
New-Item -ItemType Directory -Path "$USB\frontend" -Force
New-Item -ItemType Directory -Path "$USB\templates" -Force
New-Item -ItemType Directory -Path "$USB\examples" -Force

# Скопируйте файлы и папки
Copy-Item -Path "backend\*" -Destination "$USB\backend\" -Recurse -Exclude "__pycache__","*.pyc"
Copy-Item -Path "frontend\*" -Destination "$USB\frontend\" -Recurse -Exclude "node_modules","dist","*.log"
Copy-Item -Path "templates\*" -Destination "$USB\templates\" -Recurse
Copy-Item -Path "examples\*" -Destination "$USB\examples\" -Recurse
Copy-Item -Path "requirements.txt","setup.sh","run_backend.sh","run_frontend.sh","*.md" -Destination "$USB\"

Write-Host "Копирование завершено! Проверьте флешку: $USB"
```

---

## Шаг 2: Копирование на флешку

1. **Подключите флешку** к компьютеру
2. **Откройте проводник** (File Explorer)
3. **Скопируйте папку** `MailSenderZilla` на флешку
   - Можно перетащить папку на флешку
   - Или скопировать (Ctrl+C) и вставить (Ctrl+V)
4. **Дождитесь завершения** копирования
5. **Проверьте**, что файлы скопировались:
   - Откройте флешку
   - Убедитесь, что видны папки: `backend`, `frontend`, `templates`
   - Убедитесь, что видны файлы: `requirements.txt`, `setup.sh`, `run_backend.sh`

### Безопасное извлечение флешки

⚠️ **Важно:** Всегда безопасно извлекайте флешку!

1. В проводнике **правой кнопкой мыши** на флешке
2. Выберите **"Извлечь"** (Eject)
3. Дождитесь сообщения **"Безопасное извлечение устройства"**
4. Только после этого **физически извлеките** флешку

---

## Шаг 3: Перенос на macOS

### Подключение флешки к Mac

1. **Подключите флешку** к Mac (через USB или адаптер)
2. Флешка появится на **рабочем столе** или в боковом меню **Finder**

### Копирование проекта с флешки

**Способ 1: Через Finder (проще)**

1. Откройте **Finder**
2. Найдите **флешку** в боковом меню (обычно называется "UNTITLED" или имеет имя)
3. Откройте флешку и найдите папку `MailSenderZilla`
4. **Перетащите** папку `MailSenderZilla` в удобное место:
   - `Документы` (Documents)
   - `Рабочий стол` (Desktop)
   - Или создайте папку `Проекты` (Projects) в Документах

**Способ 2: Через Terminal**

1. Откройте **Terminal** (⌘+Пробел, введите "Terminal")
2. Выполните команды:

```bash
# Перейдите в Документы
cd ~/Documents

# Найдите имя вашей флешки (обычно это /Volumes/UNTITLED или похожее)
ls /Volumes/

# Скопируйте проект (замените UNTITLED на имя вашей флешки)
cp -r /Volumes/UNTITLED/MailSenderZilla ./

# Проверьте, что скопировалось
ls -la MailSenderZilla
```

---

## Шаг 4: Установка на macOS

После копирования проекта на Mac, следуйте инструкции в файле **`RUN_MACOS.md`**

### Краткая версия:

1. Откройте **Terminal**
2. Перейдите в проект:
   ```bash
   cd ~/Documents/MailSenderZilla
   ```
3. Дайте права на выполнение скриптам:
   ```bash
   chmod +x setup.sh run_backend.sh run_frontend.sh
   ```
4. Запустите установку:
   ```bash
   ./setup.sh
   ```
5. После установки запустите backend (Terminal 1):
   ```bash
   ./run_backend.sh
   ```
6. Запустите frontend (Terminal 2):
   ```bash
   ./run_frontend.sh
   ```
7. Откройте в браузере: **http://localhost:3000**

---

## ⚠️ Важные замечания

1. **Файлы баз данных** (`.db`) можно скопировать, если хотите сохранить данные
2. **Логи** (`.log`) не нужно копировать
3. **Виртуальное окружение** (`.venv`) НЕ копируйте - оно будет создано заново
4. **Зависимости** (`node_modules`) НЕ копируйте - они установятся заново
5. Убедитесь, что на Mac установлены **Python 3.8+** и **Node.js 16+**

---

## 🔍 Проверка после переноса

После копирования на Mac, проверьте структуру:

```bash
cd ~/Documents/MailSenderZilla
ls -la
```

Должны быть видны:
- ✅ `backend/` - папка
- ✅ `frontend/` - папка
- ✅ `templates/` - папка
- ✅ `requirements.txt` - файл
- ✅ `setup.sh` - файл
- ✅ `run_backend.sh` - файл
- ✅ `run_frontend.sh` - файл

---

**Готово! Теперь следуйте инструкции `RUN_MACOS.md` для установки и запуска! 🚀**
