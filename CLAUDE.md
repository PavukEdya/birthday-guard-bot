Ты senior Python engineer и architect.
Нужно реализовать production-ready Telegram bot на Python 3.12+.

Цель проекта

Создать Telegram-бота, который:

Читает сотрудников из Google Sheets.
Отслеживает дни рождения.
За N дней до дня рождения:
исключает сотрудника из Telegram-группы;
отправляет сообщение в группу.
Через X дней после дня рождения:
автоматически возвращает сотрудника в группу.
Также должна быть команда /add_all, которая возвращает всех ранее исключенных сотрудников.
Стек

Используй:

Python 3.12+
aiogram 3.x
APScheduler
gspread + Google Service Account
pydantic-settings
python-dotenv
structlog
tenacity
uv
Docker + docker-compose
Ruff
MyPy

Не использовать устаревшие библиотеки.

Архитектурные требования

Используй clean architecture/lightweight service architecture.

Структура проекта должна быть примерно такой:

app/
    bot/
        handlers/
        middlewares/
        keyboards/
    services/
        birthday_service.py
        telegram_service.py
        google_sheets_service.py
        scheduler_service.py
    repositories/
    models/
    core/
        config.py
        logging.py
    utils/
    main.py

tests/

Dockerfile
docker-compose.yml
pyproject.toml
.env.example
README.md
Формат Google Sheets

Есть Google Sheet.

Колонки:

tg_username	full_name	birth_date	wishes	comment

Пример:

| ivan_petrov | Иван Петров | 21.05.1991 | Любит кофе | Работает в QA |

Логика бота
1. Проверка дней рождения

Scheduler должен запускаться ежедневно.

Нужно:

вычислять ближайшие дни рождения;
корректно учитывать год;
игнорировать год рождения при сравнении;
учитывать високосные годы;
timezone configurable.
2. Исключение сотрудника

За REMOVE_BEFORE_DAYS дней:

найти пользователя по tg username;
исключить его из группы.

Использовать:

banChatMember
unbanChatMember(only_if_banned=True)

чтобы сделать "kick without permanent ban".

После исключения отправить сообщение:

🎉 Скоро день рождения!

Через N дней день рождения у:
ФИО (@username)

Пожелания:
...

Комментарий:
...

Если wishes/comment пустые:

красиво обработать;
не выводить пустые блоки.
3. Возврат сотрудника

Через RETURN_AFTER_DAYS после дня рождения:

вернуть сотрудника в чат.
4. Команда /add_all

Команда должна:

вернуть всех исключенных ботом сотрудников;
быть доступной только администраторам.
Очень важные требования
Telegram ограничения

Перед исключением/добавлением:

проверять что бот admin;
проверять права:
ban_users
invite_users

Обрабатывать ошибки:

user not found
user never joined
bot has no rights
flood control
username invalid
Idempotency

Система не должна:

исключать пользователя повторно;
возвращать пользователя повторно;
спамить одинаковыми сообщениями.

Нужен persistent state.

Используй SQLite.

Таблица:

birthday_events

пример полей:

id
username
birth_date
year
removed_at
restored_at
status
Scheduler

Используй APScheduler AsyncIOScheduler.

Job должен:

безопасно переживать рестарты;
не запускаться параллельно;
иметь retry;
логироваться.
Google Sheets

Использовать Service Account.

Нужен отдельный service layer.

Реализовать:

retries;
caching;
validation строк;
пропуск битых строк;
логирование ошибок.
Конфиг

Использовать .env.

Пример:

BOT_TOKEN=
GROUP_CHAT_ID=
GOOGLE_SHEET_ID=
GOOGLE_CREDENTIALS_JSON=

REMOVE_BEFORE_DAYS=3
RETURN_AFTER_DAYS=2

TIMEZONE=Europe/Moscow
CHECK_HOUR=9
CHECK_MINUTE=0
Валидация

Использовать pydantic models.

Для даты:

строго формат dd.mm.yyyy.
Логирование

Использовать structlog.

Логировать:

старт scheduler;
исключение пользователя;
возврат пользователя;
ошибки Telegram API;
ошибки Google Sheets;
skipped users;
retries.
Тесты

Написать pytest тесты для:

вычисления ближайших дней рождения;
leap year cases;
duplicate prevention;
state transitions;
parsing rows.
Docker

Сделать production-ready Dockerfile.

Требования:

multistage build;
non-root user;
slim image;
healthcheck.
README

README должен содержать:

setup;
создание Telegram bot;
как выдать права;
как получить chat_id;
как подключить Google Sheets API;
как создать Service Account;
как расшарить Google Sheet;
запуск локально;
запуск Docker;
troubleshooting.
Код-стандарты

Обязательно:

type hints everywhere;
async/await;
no global mutable state;
no hardcoded values;
SOLID;
graceful shutdown;
dependency injection where reasonable.
Что нужно выдать

Сгенерируй полностью:

Структуру проекта.
Все файлы.
Полный код.
SQL schema.
Dockerfile.
docker-compose.yml.
pyproject.toml.
.env.example
README.md
Инструкцию запуска.

Ничего не пропускай.
Если решение неоднозначно — выбери production best practice и объясни почему.<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
Ты senior Python engineer и architect.
Нужно реализовать production-ready Telegram bot на Python 3.12+.

Цель проекта

Создать Telegram-бота, который:

Читает сотрудников из Google Sheets.
Отслеживает дни рождения.
За N дней до дня рождения:
исключает сотрудника из Telegram-группы;
отправляет сообщение в группу.
Через X дней после дня рождения:
автоматически возвращает сотрудника в группу.
Также должна быть команда /add_all, которая возвращает всех ранее исключенных сотрудников.
Стек

Используй:

Python 3.12+
aiogram 3.x
APScheduler
gspread + Google Service Account
pydantic-settings
python-dotenv
structlog
tenacity
uv
Docker + docker-compose
Ruff
MyPy

Не использовать устаревшие библиотеки.

Архитектурные требования

Используй clean architecture/lightweight service architecture.

Структура проекта должна быть примерно такой:

app/
    bot/
        handlers/
        middlewares/
        keyboards/
    services/
        birthday_service.py
        telegram_service.py
        google_sheets_service.py
        scheduler_service.py
    repositories/
    models/
    core/
        config.py
        logging.py
    utils/
    main.py

tests/

Dockerfile
docker-compose.yml
pyproject.toml
.env.example
README.md
Формат Google Sheets

Есть Google Sheet.

Колонки:

tg_username	full_name	birth_date	wishes	comment

Пример:

| ivan_petrov | Иван Петров | 21.05.1991 | Любит кофе | Работает в QA |

Логика бота
1. Проверка дней рождения

Scheduler должен запускаться ежедневно.

Нужно:

вычислять ближайшие дни рождения;
корректно учитывать год;
игнорировать год рождения при сравнении;
учитывать високосные годы;
timezone configurable.
2. Исключение сотрудника

За REMOVE_BEFORE_DAYS дней:

найти пользователя по tg username;
исключить его из группы.

Использовать:

banChatMember
unbanChatMember(only_if_banned=True)

чтобы сделать "kick without permanent ban".

После исключения отправить сообщение:

🎉 Скоро день рождения!

Через N дней день рождения у:
ФИО (@username)

Пожелания:
...

Комментарий:
...

Если wishes/comment пустые:

красиво обработать;
не выводить пустые блоки.
3. Возврат сотрудника

Через RETURN_AFTER_DAYS после дня рождения:

вернуть сотрудника в чат.
4. Команда /add_all

Команда должна:

вернуть всех исключенных ботом сотрудников;
быть доступной только администраторам.
Очень важные требования
Telegram ограничения

Перед исключением/добавлением:

проверять что бот admin;
проверять права:
ban_users
invite_users

Обрабатывать ошибки:

user not found
user never joined
bot has no rights
flood control
username invalid
Idempotency

Система не должна:

исключать пользователя повторно;
возвращать пользователя повторно;
спамить одинаковыми сообщениями.

Нужен persistent state.

Используй SQLite.

Таблица:

birthday_events

пример полей:

id
username
birth_date
year
removed_at
restored_at
status
Scheduler

Используй APScheduler AsyncIOScheduler.

Job должен:

безопасно переживать рестарты;
не запускаться параллельно;
иметь retry;
логироваться.
Google Sheets

Использовать Service Account.

Нужен отдельный service layer.

Реализовать:

retries;
caching;
validation строк;
пропуск битых строк;
логирование ошибок.
Конфиг

Использовать .env.

Пример:

BOT_TOKEN=
GROUP_CHAT_ID=
GOOGLE_SHEET_ID=
GOOGLE_CREDENTIALS_JSON=

REMOVE_BEFORE_DAYS=3
RETURN_AFTER_DAYS=2

TIMEZONE=Europe/Moscow
CHECK_HOUR=9
CHECK_MINUTE=0
Валидация

Использовать pydantic models.

Для даты:

строго формат dd.mm.yyyy.
Логирование

Использовать structlog.

Логировать:

старт scheduler;
исключение пользователя;
возврат пользователя;
ошибки Telegram API;
ошибки Google Sheets;
skipped users;
retries.
Тесты

Написать pytest тесты для:

вычисления ближайших дней рождения;
leap year cases;
duplicate prevention;
state transitions;
parsing rows.
Docker

Сделать production-ready Dockerfile.

Требования:

multistage build;
non-root user;
slim image;
healthcheck.
README

README должен содержать:

setup;
создание Telegram bot;
как выдать права;
как получить chat_id;
как подключить Google Sheets API;
как создать Service Account;
как расшарить Google Sheet;
запуск локально;
запуск Docker;
troubleshooting.
Код-стандарты

Обязательно:

type hints everywhere;
async/await;
no global mutable state;
no hardcoded values;
SOLID;
graceful shutdown;
dependency injection where reasonable.
Что нужно выдать

Сгенерируй полностью:

Структуру проекта.
Все файлы.
Полный код.
SQL schema.
Dockerfile.
docker-compose.yml.
pyproject.toml.
.env.example
README.md
Инструкцию запуска.

Ничего не пропускай.
Если решение неоднозначно — выбери production best practice и объясни почему.