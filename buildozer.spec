[app]

# Название игры (видно у мамы на телефоне под иконкой)
title = Маджонг

# Внутреннее имя пакета
package.name = mahjongmama

# Уникальный идентификатор. Можешь поменять "myfamily" на что-то своё.
package.domain = org.myfamily

# Папка с исходниками (точка = текущая папка)
source.dir = .

# Какие файлы включить в сборку
source.include_exts = py,png,jpg,kv,atlas,ttf

# Версия игры
version = 1.0

# Что должно быть установлено внутри APK
requirements = python3,kivy==2.3.0

# Ориентация экрана: all = и портрет, и ландшафт
orientation = sensor

# Полноэкранный режим: 0 = с верхней панелью телефона, 1 = совсем без неё
fullscreen = 0

# Разрешения Android (для простой игры почти ничего не нужно)
android.permissions = 

# Минимальная версия Android (5.0 — старые телефоны тоже потянут)
android.minapi = 21

# Целевая версия Android
android.api = 33

# Архитектуры процессоров. arm64 — для большинства современных телефонов.
# Если будет ошибка "не та архитектура", добавь сюда armeabi-v7a через запятую.
android.archs = arm64-v8a

# Принять лицензии Android SDK автоматически
android.accept_sdk_license = True

[buildozer]

# Уровень логов (2 = подробный, удобно если что-то сломается)
log_level = 2

# Не позволять buildozer запускаться от root (на случай локальной сборки)
warn_on_root = 1
