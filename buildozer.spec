[app]

# Название игры
title = Маджонг

# Внутреннее имя пакета
package.name = mahjongmama

# Уникальный идентификатор
package.domain = org.myfamily

# Папка с исходниками
source.dir = .
source.include_patterns = sounds/*

# Какие файлы включить
source.include_exts = py,png,jpg,kv,atlas,ttf,mp3,wav,ogg

# Версия
version = 2.0

# Зависимости
requirements = python3,kivy==2.3.0

# ГОРИЗОНТАЛЬНАЯ ОРИЕНТАЦИЯ (для маджонга так удобнее)
orientation = landscape

# Полноэкранный режим
fullscreen = 0

# Разрешения
android.permissions = 

# Минимальная версия Android (5.0)
android.minapi = 21

# Целевая версия
android.api = 33

# Архитектура
android.archs = arm64-v8a

# Принять лицензии
android.accept_sdk_license = True

[buildozer]

log_level = 2
warn_on_root = 1
