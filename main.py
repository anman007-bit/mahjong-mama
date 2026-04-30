# -*- coding: utf-8 -*-
"""
МАДЖОНГ-СОЛИТЁР (Черепаха) — версия 2.2 ФИНАЛЬНАЯ
- Горизонтальная ориентация
- Все плитки рисуются графикой (точки, палочки, цифры)
- Без зависимости от китайских шрифтов
- Поле занимает весь экран, плитки крупные
"""

import math
import random
import os
import json

# Путь к файлу с рекордами
def get_records_file():
    """Возвращает путь к файлу с рекордами на устройстве."""
    try:
        from android.storage import app_storage_path
        path = app_storage_path()
    except ImportError:
        # Если не Android (например запуск на компьютере) - в текущей папке
        path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(path, 'mahjong_records.json')


def load_record():
    """Загружает лучшее время из файла. Возвращает None если рекорда ещё нет."""
    try:
        path = get_records_file()
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
                return data.get('best_time')
    except Exception:
        pass
    return None


def save_record(seconds):
    """Сохраняет лучшее время в файл."""
    try:
        path = get_records_file()
        with open(path, 'w') as f:
            json.dump({'best_time': seconds}, f)
        return True
    except Exception:
        return False

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle, Ellipse
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.clock import Clock


# ============================================================
# РАСКЛАДКА "ЧЕРЕПАХА" (144 плитки)
# ============================================================

def _build_turtle_layout():
    """Раскладка ПИРАМИДА: 94 плитки = 47 пар.
    Слой 0 = 60 (10x6), Слой 1 = 24 (8x3), Слой 2 = 8 (4x2), Слой 3 = 2.
    Все слои центрированы друг над другом."""
    layout = []

    # Слой 0 (основа) — 10 столбцов × 6 рядов = 60 плиток
    # Столбцы 1-10, ряды 0-5
    for row in range(0, 6):
        for col in range(1, 11):
            layout.append((0, row, col))

    # Слой 1 — 8 столбцов × 3 ряда = 24 плитки
    # Центрирован: столбцы 2-9, ряды 1-3 (визуально в центре основы)
    for row in range(1, 4):
        for col in range(2, 10):
            layout.append((1, row, col))

    # Слой 2 — 4 столбца × 2 ряда = 8 плиток
    # Ещё уже: столбцы 4-7, ряды 2-3
    for row in range(2, 4):
        for col in range(4, 8):
            layout.append((2, row, col))

    # Слой 3 — 2 плитки сверху
    layout.append((3, 2, 5))
    layout.append((3, 2, 6))

    return layout


TURTLE_LAYOUT = _build_turtle_layout()


# ============================================================
# ОПРЕДЕЛЕНИЯ ПЛИТОК (144 плитки)
# ============================================================

TILE_DEFINITIONS = []
for n in range(1, 10):
    TILE_DEFINITIONS.append({'suit': 'dots', 'value': n})
for n in range(1, 10):
    TILE_DEFINITIONS.append({'suit': 'bamboo', 'value': n})
for n in range(1, 10):
    TILE_DEFINITIONS.append({'suit': 'characters', 'value': n})
for w in ['east', 'south', 'west', 'north']:
    TILE_DEFINITIONS.append({'suit': 'wind', 'value': w})
for d in ['red', 'green', 'white']:
    TILE_DEFINITIONS.append({'suit': 'dragon', 'value': d})
for s in ['spring', 'summer', 'autumn', 'winter']:
    TILE_DEFINITIONS.append({'suit': 'season', 'value': s})
for f in ['plum', 'orchid', 'chrysanthemum', 'bamboo_flower']:
    TILE_DEFINITIONS.append({'suit': 'flower', 'value': f})


def build_tile_pool():
    """Создаём 94 плитки для пирамиды, ВСЕГДА парное количество каждой плитки.
    Берём по 2 копии каждой плитки (точки/бамбук/символы — 9 типов × 2 = 18),
    плюс ветры и драконы по 2 копии."""
    pool = []
    # Точки 1-9: по 2 копии = 18
    # Бамбук 1-9: по 2 копии = 18
    # Символы 1-9: по 2 копии = 18
    # Итого 54
    for td in TILE_DEFINITIONS:
        if td['suit'] in ('dots', 'bamboo', 'characters'):
            for _ in range(2):
                pool.append(dict(td))

    # Ветры (4 типа) и драконы (3 типа): по 4 копии каждого = 16+12 = 28
    # Итого 54 + 28 = 82
    for td in TILE_DEFINITIONS:
        if td['suit'] in ('wind', 'dragon'):
            for _ in range(4):
                pool.append(dict(td))

    # Дополнительно нужно довести до 94
    # Добавим ещё по 2 копии каждой основной плитки (точки/бамбук/символы)
    # выбранных случайно, но строго парами
    extra_needed = 94 - len(pool)  # сколько ещё нужно
    if extra_needed > 0:
        # extra_needed должно быть чётным
        if extra_needed % 2 != 0:
            extra_needed -= 1  # делаем чётным
        # Добавляем парами
        main_types = [td for td in TILE_DEFINITIONS
                      if td['suit'] in ('dots', 'bamboo', 'characters')]
        random.shuffle(main_types)
        idx = 0
        while extra_needed > 0 and idx < len(main_types):
            pool.append(dict(main_types[idx]))
            pool.append(dict(main_types[idx]))
            extra_needed -= 2
            idx += 1

    # На всякий случай обрезаем до 94 (если получилось больше)
    if len(pool) > 94:
        pool = pool[:94]

    return pool


def tiles_match(t1, t2):
    if t1['suit'] == t2['suit']:
        if t1['suit'] in ('season', 'flower'):
            return True
        return t1['value'] == t2['value']
    return False


# ============================================================
# КЛАСС ПЛИТКИ
# ============================================================

class MahjongTile:
    def __init__(self, tile_def, layer, row, col):
        self.tile_def = tile_def
        self.layer = layer
        self.row = row
        self.col = col
        self.removed = False
        self.selected = False
        self.hint = False


# ============================================================
# ИГРОВОЕ ПОЛЕ
# ============================================================

class MahjongBoard(Widget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Звуки: пробуем только фоновую музыку
        self.sounds = {}
        self.sound_enabled = True
        try:
            self.sounds = self._load_sounds()
        except Exception as e:
            print(f'[SOUNDS] Ошибка загрузки: {e}')
            self.sounds = {}
        # Запускаем фоновую музыку (если загрузилась)
        try:
            bg = self.sounds.get('background')
            if bg:
                bg.loop = True
                bg.volume = 0.3
                bg.play()
        except Exception as e:
            print(f'[SOUNDS] Ошибка музыки: {e}')
        self.tiles = []
        self.first_selected = None
        self.score = 0
        self.total_pairs = 47  # 94 плитки / 2
        self.history = []
        self.shuffles_left = 10  # лимит перемешиваний
        self.undos_used = 0
        self.elapsed_seconds = 0  # секунды прошло с начала игры
        self.game_over = False  # игра завершена
        self.timer_running = True  # таймер активен
        self._create_tiles()
        self.bind(size=self._redraw, pos=self._redraw)
        Clock.schedule_once(lambda dt: self._redraw(), 0)
        # Таймер обновляется раз в секунду
        Clock.schedule_interval(self._tick_timer, 1.0)

    def _load_sounds(self):
        """Загружает все звуки игры."""
        import os
        # Папка где лежит main.py + sounds
        base = os.path.dirname(os.path.abspath(__file__))
        sounds_dir = os.path.join(base, 'sounds')
        files = {
            'knock': 'Knock.mp3',
            'dzin': 'Dzin.mp3',
            'clue': 'Clue.mp3',
            'mixing': 'Mixing.mp3',
            'gonk': 'Gonk.mp3',
            'bell': 'Bell.mp3',
            'background': 'Background.mp3',
        }
        sounds = {}
        for key, filename in files.items():
            path = os.path.join(sounds_dir, filename)
            if os.path.exists(path):
                snd = SoundLoader.load(path)
                if snd:
                    sounds[key] = snd
        return sounds

    def play_sound(self, key, volume=None):
        """Проигрывает звук по ключу с правильной громкостью."""
        if not self.sound_enabled:
            return
        # Громкость по умолчанию для каждого звука
        default_volumes = {
            'knock': 0.4,    # стук плитки
            'dzin': 0.4,     # тупик "нет ходов"
            'clue': 0.6,     # победа
            'mixing': 0.8,   # перемешивание
            'gonk': 0.7,     # новая игра
            'bell': 0.4,     # подсказка
        }
        if volume is None:
            volume = default_volumes.get(key, 0.6)
        try:
            snd = self.sounds.get(key)
            if snd:
                snd.volume = volume
                # НЕ останавливаем старый звук — пусть доиграет
                # Это убирает потрескивания
                snd.play()
        except Exception as e:
            print(f'[SOUNDS] Ошибка воспроизведения {key}: {e}')

    def _tick_timer(self, dt):
        if self.timer_running and not self.game_over:
            self.elapsed_seconds += 1

    def _create_tiles(self):
        pool = build_tile_pool()
        random.shuffle(pool)
        self.tiles = []
        for i, position in enumerate(TURTLE_LAYOUT):
            if i >= len(pool):
                break
            layer, row, col = position
            self.tiles.append(MahjongTile(pool[i], layer, row, col))

    def restart(self):
        self.play_sound('gonk')  # звук начала новой игры
        self.first_selected = None
        self.score = 0
        self.history = []
        self.shuffles_left = 10
        self.undos_used = 0
        self.game_over = False
        self.elapsed_seconds = 0
        self.timer_running = True
        self._create_tiles()
        self._redraw()

    # --------------------------------------------------------
    # ГЕОМЕТРИЯ — горизонтальное поле, занимает весь экран
    # --------------------------------------------------------

    def _tile_dims(self):
        """
        Поле: 14 столбцов x 9 рядов + смещение слоёв (4 * 0.08)
        Эффективный размер: 14.32 в ширину, 9.32 в высоту (в плитках)
        Плитка пропорция 1:1.25 (выше чем шире, но не сильно)
        """
        margin = 0.01  # минимальные поля
        usable_w = self.width * (1 - 2 * margin)
        usable_h = self.height * (1 - 2 * margin)

        # Поле должно поместиться по обоим осям
        # ширина = 14.32 * tile_w
        # высота = 9.32 * tile_h = 9.32 * 1.25 * tile_w = 11.65 * tile_w
        # Пирамида с увеличенным смещением слоёв
        max_w_by_width = usable_w / 12.6
        max_w_by_height = usable_h / 8.2
        tile_w = min(max_w_by_width, max_w_by_height)
        tile_h = tile_w * 1.25
        return tile_w, tile_h

    def _board_offset(self, tile_w, tile_h):
        board_w = tile_w * 12 + 3 * 0.15 * tile_w
        board_h = tile_h * 6 + 3 * 0.15 * tile_h
        offset_x = (self.width - board_w) / 2
        offset_y = (self.height - board_h) / 2
        return offset_x, offset_y

    def _tile_screen_pos(self, tile, tile_w, tile_h, offset_x, offset_y):
        layer_offset_x = tile_w * 0.15
        layer_offset_y = tile_h * 0.15
        x = offset_x + tile.col * tile_w + tile.layer * layer_offset_x
        y = offset_y + (5 - tile.row) * tile_h + tile.layer * layer_offset_y
        return x, y

    # --------------------------------------------------------
    # ПРАВИЛА МАДЖОНГА
    # --------------------------------------------------------

    def _is_free(self, tile):
        """
        Плитка свободна если:
        1. Сверху (на следующем слое) нет плитки которая её перекрывает
        2. Слева ИЛИ справа в том же ряду нет плитки впритык
        """
        if tile.removed:
            return False

        # === Проверка: НЕТ ЛИ ПЛИТКИ СВЕРХУ ===
        # В раскладке "Черепаха" плитки верхнего слоя ставятся точно
        # над плитками нижнего слоя (на ту же клетку).
        # Поэтому проверка простая: плитка верхнего слоя
        # на ТОЙ ЖЕ row и col перекрывает данную.
        for other in self.tiles:
            if other.removed or other is tile:
                continue
            if other.layer == tile.layer + 1:
                if other.row == tile.row and other.col == tile.col:
                    return False

        # === Проверка: СВОБОДНО СЛЕВА ИЛИ СПРАВА ===
        # Только в том же ряду и только на ВПРИТЫК соседних столбцах
        has_left = False
        has_right = False
        for other in self.tiles:
            if other.removed or other is tile:
                continue
            if other.layer != tile.layer:
                continue
            if other.row != tile.row:
                continue
            if other.col == tile.col - 1:
                has_left = True
            elif other.col == tile.col + 1:
                has_right = True

        # Свободна если хотя бы с одной стороны нет плитки
        return not (has_left and has_right)

    def _find_hint(self):
        free = [t for t in self.tiles if not t.removed and self._is_free(t)]
        for i in range(len(free)):
            for j in range(i + 1, len(free)):
                if tiles_match(free[i].tile_def, free[j].tile_def):
                    return (free[i], free[j])
        return None

    # --------------------------------------------------------
    # ОТРИСОВКА
    # --------------------------------------------------------

    def _redraw(self, *args):
        self.canvas.clear()
        self.clear_widgets()

        tile_w, tile_h = self._tile_dims()
        offset_x, offset_y = self._board_offset(tile_w, tile_h)

        with self.canvas:
            Color(0.13, 0.38, 0.23, 1)
            Rectangle(pos=(0, 0), size=self.size)

        sorted_tiles = sorted(
            [t for t in self.tiles if not t.removed],
            key=lambda t: (t.layer, -t.row, t.col)
        )
        for tile in sorted_tiles:
            x, y = self._tile_screen_pos(tile, tile_w, tile_h,
                                         offset_x, offset_y)
            is_free = self._is_free(tile)
            self._draw_tile(tile, x, y, tile_w, tile_h, is_free)

    def _draw_tile(self, tile, x, y, tile_w, tile_h, is_free):
        radius = tile_w * 0.10
        side = tile_w * 0.07

        with self.canvas:
            # Боковина (тёмная) - объём
            Color(0.20, 0.13, 0.08, 1)
            RoundedRectangle(
                pos=(x, y),
                size=(tile_w, tile_h),
                radius=[radius]
            )
            # Лицевая часть
            if tile.selected:
                Color(1.0, 0.92, 0.5, 1)  # ярко-жёлтый - выбрана
            elif tile.hint:
                Color(0.7, 1.0, 0.7, 1)   # зелёный - подсказка
            elif is_free:
                Color(1.00, 0.98, 0.92, 1)  # светло-кремовый - свободна
            else:
                Color(0.55, 0.52, 0.45, 1)  # тёмно-серый - заблокирована

            face_x = x + side
            face_y = y + side
            face_w = tile_w - side
            face_h = tile_h - side

            RoundedRectangle(
                pos=(face_x, face_y),
                size=(face_w, face_h),
                radius=[radius]
            )

            if tile.selected:
                Color(1.0, 0.6, 0.0, 1)
                Line(rounded_rectangle=(
                    face_x, face_y, face_w, face_h, radius
                ), width=2.5)
            else:
                Color(0.4, 0.3, 0.2, 0.5)
                Line(rounded_rectangle=(
                    face_x, face_y, face_w, face_h, radius
                ), width=1.0)

        # Содержимое
        content_pad = tile_w * 0.10
        content_x = face_x + content_pad
        content_y = face_y + content_pad
        content_w = face_w - 2 * content_pad
        content_h = face_h - 2 * content_pad

        dim = (not is_free) and (not tile.selected)
        bright = 0.55 if dim else 1.0

        suit = tile.tile_def['suit']
        value = tile.tile_def['value']

        if suit == 'dots':
            self._draw_dots(value, content_x, content_y,
                            content_w, content_h, bright)
        elif suit == 'bamboo':
            self._draw_bamboo(value, content_x, content_y,
                              content_w, content_h, bright)
        elif suit == 'characters':
            self._draw_character_label(value, content_x, content_y,
                                       content_w, content_h, bright)
        elif suit == 'wind':
            self._draw_wind(value, content_x, content_y,
                            content_w, content_h, bright)
        elif suit == 'dragon':
            self._draw_dragon(value, content_x, content_y,
                              content_w, content_h, bright)
        elif suit == 'season':
            self._draw_season(value, content_x, content_y,
                              content_w, content_h, bright)
        elif suit == 'flower':
            self._draw_flower(value, content_x, content_y,
                              content_w, content_h, bright)

    # --------------------------------------------------------
    # ОТРИСОВКА ОТДЕЛЬНЫХ ТИПОВ ПЛИТОК
    # --------------------------------------------------------

    def _draw_dots(self, value, x, y, w, h, bright):
        """Точки — кружки разных цветов, расположенные узором."""
        layouts = {
            1: [(0.5, 0.5)],
            2: [(0.5, 0.25), (0.5, 0.75)],
            3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
            4: [(0.27, 0.27), (0.73, 0.27), (0.27, 0.73), (0.73, 0.73)],
            5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5),
                (0.25, 0.75), (0.75, 0.75)],
            6: [(0.27, 0.2), (0.27, 0.5), (0.27, 0.8),
                (0.73, 0.2), (0.73, 0.5), (0.73, 0.8)],
            7: [(0.5, 0.18), (0.3, 0.4), (0.7, 0.4),
                (0.5, 0.55), (0.3, 0.78), (0.7, 0.78), (0.5, 0.92)],
            8: [(0.27, 0.18), (0.73, 0.18),
                (0.27, 0.42), (0.73, 0.42),
                (0.27, 0.65), (0.73, 0.65),
                (0.27, 0.88), (0.73, 0.88)],
            9: [(0.25, 0.2), (0.5, 0.2), (0.75, 0.2),
                (0.25, 0.5), (0.5, 0.5), (0.75, 0.5),
                (0.25, 0.8), (0.5, 0.8), (0.75, 0.8)],
        }
        positions = layouts[value]
        if value == 1:
            dot_size = w * 0.5
        elif value <= 4:
            dot_size = w * 0.28
        elif value <= 6:
            dot_size = w * 0.22
        else:
            dot_size = w * 0.20

        if value <= 3:
            col_outer = (0.75 * bright, 0.15 * bright, 0.15 * bright, 1)
        elif value <= 6:
            col_outer = (0.15 * bright, 0.4 * bright, 0.7 * bright, 1)
        else:
            col_outer = (0.15 * bright, 0.55 * bright, 0.25 * bright, 1)

        with self.canvas:
            for px, py in positions:
                Color(*col_outer)
                Ellipse(
                    pos=(x + px * w - dot_size / 2,
                         y + py * h - dot_size / 2),
                    size=(dot_size, dot_size)
                )
                Color(0.95 * bright, 0.95 * bright, 0.85 * bright, 1)
                inner = dot_size * 0.4
                Ellipse(
                    pos=(x + px * w - inner / 2,
                         y + py * h - inner / 2),
                    size=(inner, inner)
                )

    def _draw_bamboo(self, value, x, y, w, h, bright):
        """Бамбук — зелёные палочки. 1 = особый рисунок (птичка)."""
        if value == 1:
            cx = x + w / 2
            cy = y + h / 2
            with self.canvas:
                # Тело-овал
                Color(0.85 * bright, 0.15 * bright, 0.15 * bright, 1)
                Ellipse(pos=(cx - w * 0.28, cy - h * 0.3),
                        size=(w * 0.56, h * 0.6))
                # "Глаз"
                Color(0.95 * bright, 0.95 * bright, 0.85 * bright, 1)
                Ellipse(pos=(cx - w * 0.1, cy + h * 0.05),
                        size=(w * 0.2, h * 0.2))
                Color(0.05, 0.05, 0.05, 1)
                Ellipse(pos=(cx - w * 0.05, cy + h * 0.1),
                        size=(w * 0.1, h * 0.1))
            return

        layouts = {
            2: [(0.5, 0.3), (0.5, 0.7)],
            3: [(0.5, 0.22), (0.5, 0.5), (0.5, 0.78)],
            4: [(0.3, 0.3), (0.7, 0.3), (0.3, 0.7), (0.7, 0.7)],
            5: [(0.3, 0.25), (0.7, 0.25), (0.5, 0.5),
                (0.3, 0.75), (0.7, 0.75)],
            6: [(0.3, 0.22), (0.5, 0.22), (0.7, 0.22),
                (0.3, 0.78), (0.5, 0.78), (0.7, 0.78)],
            7: [(0.5, 0.15),
                (0.3, 0.45), (0.5, 0.45), (0.7, 0.45),
                (0.3, 0.78), (0.5, 0.78), (0.7, 0.78)],
            8: [(0.28, 0.18), (0.5, 0.18), (0.72, 0.18),
                (0.4, 0.5), (0.6, 0.5),
                (0.28, 0.82), (0.5, 0.82), (0.72, 0.82)],
            9: [(0.25, 0.18), (0.5, 0.18), (0.75, 0.18),
                (0.25, 0.5), (0.5, 0.5), (0.75, 0.5),
                (0.25, 0.82), (0.5, 0.82), (0.75, 0.82)],
        }

        col = (0.15 * bright, 0.55 * bright, 0.25 * bright, 1)
        col_inner = (0.55 * bright, 0.85 * bright, 0.55 * bright, 1)
        stick_w = w * 0.12
        stick_h = h * 0.20

        with self.canvas:
            for px, py in layouts[value]:
                Color(*col)
                RoundedRectangle(
                    pos=(x + px * w - stick_w / 2,
                         y + py * h - stick_h / 2),
                    size=(stick_w, stick_h),
                    radius=[stick_w * 0.3]
                )
                Color(*col_inner)
                inner_h = stick_h * 0.3
                RoundedRectangle(
                    pos=(x + px * w - stick_w / 4,
                         y + py * h - inner_h / 2),
                    size=(stick_w / 2, inner_h),
                    radius=[stick_w * 0.15]
                )

    def _draw_character_label(self, value, x, y, w, h, bright):
        """Символы — крупная цифра."""
        label = Label(
            text=str(value),
            pos=(x, y),
            size=(w, h),
            font_size=h * 0.7,
            bold=True,
            color=(0.7 * bright, 0.1 * bright, 0.1 * bright, 1),
            halign='center',
            valign='middle'
        )
        label.text_size = (w, h)
        self.add_widget(label)

    def _draw_wind(self, value, x, y, w, h, bright):
        """Ветры — стрелка + русская буква В/Ю/З/С."""
        cx = x + w / 2
        cy_arrow = y + h * 0.65
        arrow_size = min(w, h) * 0.4
        line_width = h * 0.05

        col = (0.1 * bright, 0.1 * bright, 0.1 * bright, 1)

        with self.canvas:
            Color(*col)
            if value == 'east':
                # Стрелка вправо
                Line(points=[
                    cx - arrow_size / 2, cy_arrow,
                    cx + arrow_size / 2, cy_arrow,
                ], width=line_width)
                Line(points=[
                    cx + arrow_size / 4, cy_arrow + arrow_size / 4,
                    cx + arrow_size / 2, cy_arrow,
                    cx + arrow_size / 4, cy_arrow - arrow_size / 4,
                ], width=line_width)
            elif value == 'south':
                Line(points=[
                    cx, cy_arrow + arrow_size / 2,
                    cx, cy_arrow - arrow_size / 2,
                ], width=line_width)
                Line(points=[
                    cx - arrow_size / 4, cy_arrow - arrow_size / 4,
                    cx, cy_arrow - arrow_size / 2,
                    cx + arrow_size / 4, cy_arrow - arrow_size / 4,
                ], width=line_width)
            elif value == 'west':
                Line(points=[
                    cx + arrow_size / 2, cy_arrow,
                    cx - arrow_size / 2, cy_arrow,
                ], width=line_width)
                Line(points=[
                    cx - arrow_size / 4, cy_arrow + arrow_size / 4,
                    cx - arrow_size / 2, cy_arrow,
                    cx - arrow_size / 4, cy_arrow - arrow_size / 4,
                ], width=line_width)
            elif value == 'north':
                Line(points=[
                    cx, cy_arrow - arrow_size / 2,
                    cx, cy_arrow + arrow_size / 2,
                ], width=line_width)
                Line(points=[
                    cx - arrow_size / 4, cy_arrow + arrow_size / 4,
                    cx, cy_arrow + arrow_size / 2,
                    cx + arrow_size / 4, cy_arrow + arrow_size / 4,
                ], width=line_width)

        # Буква под стрелкой
        letters = {'east': 'В', 'south': 'Ю', 'west': 'З', 'north': 'С'}
        label = Label(
            text=letters[value],
            pos=(x, y),
            size=(w, h * 0.4),
            font_size=h * 0.32,
            bold=True,
            color=(0.1 * bright, 0.1 * bright, 0.1 * bright, 1),
            halign='center',
            valign='middle'
        )
        label.text_size = (w, h * 0.4)
        self.add_widget(label)

    def _draw_dragon(self, value, x, y, w, h, bright):
        """Драконы: красный квадрат, зелёный круг, белая рамка."""
        cx = x + w / 2
        cy = y + h / 2
        size = min(w, h) * 0.6

        with self.canvas:
            if value == 'red':
                Color(0.85 * bright, 0.15 * bright, 0.15 * bright, 1)
                RoundedRectangle(
                    pos=(cx - size / 2, cy - size / 2),
                    size=(size, size),
                    radius=[size * 0.1]
                )
                Color(0.95 * bright, 0.92 * bright, 0.85 * bright, 1)
                Line(points=[
                    cx - size * 0.25, cy,
                    cx + size * 0.25, cy
                ], width=h * 0.04)
                Line(points=[
                    cx, cy - size * 0.25,
                    cx, cy + size * 0.25
                ], width=h * 0.04)
            elif value == 'green':
                Color(0.1 * bright, 0.55 * bright, 0.25 * bright, 1)
                Ellipse(
                    pos=(cx - size / 2, cy - size / 2),
                    size=(size, size)
                )
                Color(0.95 * bright, 0.92 * bright, 0.85 * bright, 1)
                inner = size * 0.45
                Ellipse(
                    pos=(cx - inner / 2, cy - inner / 2),
                    size=(inner, inner)
                )
                Color(0.1 * bright, 0.55 * bright, 0.25 * bright, 1)
                dot = size * 0.18
                Ellipse(
                    pos=(cx - dot / 2, cy - dot / 2),
                    size=(dot, dot)
                )
            elif value == 'white':
                Color(0.3 * bright, 0.3 * bright, 0.4 * bright, 1)
                Line(rounded_rectangle=(
                    cx - size / 2, cy - size / 2, size, size, size * 0.1
                ), width=h * 0.04)
                inner = size * 0.7
                Line(rounded_rectangle=(
                    cx - inner / 2, cy - inner / 2, inner, inner, inner * 0.1
                ), width=h * 0.025)

    def _draw_season(self, value, x, y, w, h, bright):
        """Сезоны: листик, солнце, ромб, снежинка."""
        cx = x + w / 2
        cy = y + h / 2
        size = min(w, h) * 0.55

        if value == 'spring':
            with self.canvas:
                Color(0.3 * bright, 0.7 * bright, 0.3 * bright, 1)
                Ellipse(pos=(cx - size / 2, cy - size / 3),
                        size=(size, size * 0.85))
                # Стебелёк
                Color(0.4 * bright, 0.3 * bright, 0.15 * bright, 1)
                Line(points=[cx, cy - size / 3,
                             cx, cy - size * 0.6], width=h * 0.025)
        elif value == 'summer':
            # Солнце
            with self.canvas:
                Color(0.95 * bright, 0.75 * bright, 0.1 * bright, 1)
                Ellipse(pos=(cx - size / 2, cy - size / 2),
                        size=(size, size))
                ray_len = size * 0.3
                for i in range(8):
                    angle = i * math.pi / 4
                    Line(points=[
                        cx + (size / 2) * math.cos(angle),
                        cy + (size / 2) * math.sin(angle),
                        cx + (size / 2 + ray_len) * math.cos(angle),
                        cy + (size / 2 + ray_len) * math.sin(angle),
                    ], width=h * 0.025)
        elif value == 'autumn':
            # Оранжевый ромб
            with self.canvas:
                Color(0.85 * bright, 0.5 * bright, 0.1 * bright, 1)
                Line(points=[
                    cx, cy + size / 2,
                    cx + size / 2, cy,
                    cx, cy - size / 2,
                    cx - size / 2, cy,
                    cx, cy + size / 2,
                ], width=h * 0.06)
        elif value == 'winter':
            # Снежинка
            with self.canvas:
                Color(0.4 * bright, 0.6 * bright, 0.85 * bright, 1)
                for i in range(6):
                    angle = i * math.pi / 3
                    Line(points=[
                        cx, cy,
                        cx + size / 2 * math.cos(angle),
                        cy + size / 2 * math.sin(angle),
                    ], width=h * 0.05)

    def _draw_flower(self, value, x, y, w, h, bright):
        """Цветы — 5 лепестков разных цветов."""
        cx = x + w / 2
        cy = y + h / 2
        size = min(w, h) * 0.55

        colors = {
            'plum': (0.85, 0.2, 0.4),
            'orchid': (0.7, 0.4, 0.8),
            'chrysanthemum': (0.95, 0.65, 0.15),
            'bamboo_flower': (0.4, 0.7, 0.3),
        }
        base = colors[value]
        col = (base[0] * bright, base[1] * bright, base[2] * bright, 1)

        with self.canvas:
            for i in range(5):
                angle = i * 2 * math.pi / 5 - math.pi / 2
                petal_x = cx + (size * 0.28) * math.cos(angle)
                petal_y = cy + (size * 0.28) * math.sin(angle)
                Color(*col)
                Ellipse(
                    pos=(petal_x - size * 0.22, petal_y - size * 0.22),
                    size=(size * 0.44, size * 0.44)
                )
            Color(0.95 * bright, 0.85 * bright, 0.2 * bright, 1)
            center_size = size * 0.3
            Ellipse(
                pos=(cx - center_size / 2, cy - center_size / 2),
                size=(center_size, center_size)
            )

    # --------------------------------------------------------
    # КАСАНИЯ
    # --------------------------------------------------------

    def on_touch_down(self, touch):
        tile = self._tile_at_touch(touch.x, touch.y)
        if tile is None or not self._is_free(tile):
            if self.first_selected is not None:
                self.first_selected.selected = False
                self.first_selected = None
                self._clear_hints()
                self._redraw()
            return

        self._clear_hints()

        if self.first_selected is not None:
            if self.first_selected is tile:
                tile.selected = False
                self.first_selected = None
                self._redraw()
                return

            if tiles_match(tile.tile_def, self.first_selected.tile_def):
                self.play_sound('knock')  # совпадение пары
                self.history.append((self.first_selected, tile))
                self.first_selected.removed = True
                tile.removed = True
                self.first_selected = None
                self.score += 1
                self._redraw()
                self._check_game_state()
            else:
                self.play_sound('knock')  # просто переключили выбор
                self.first_selected.selected = False
                tile.selected = True
                self.first_selected = tile
                self._redraw()
        else:
            self.play_sound('knock')  # выбор первой плитки
            tile.selected = True
            self.first_selected = tile
            self._redraw()

    def _tile_at_touch(self, tx, ty):
        tile_w, tile_h = self._tile_dims()
        offset_x, offset_y = self._board_offset(tile_w, tile_h)
        side = tile_w * 0.07

        candidates = sorted(
            [t for t in self.tiles if not t.removed],
            key=lambda t: -t.layer
        )
        for tile in candidates:
            x, y = self._tile_screen_pos(tile, tile_w, tile_h,
                                          offset_x, offset_y)
            if (x + side <= tx <= x + tile_w
                    and y + side <= ty <= y + tile_h):
                return tile
        return None

    # --------------------------------------------------------
    # ПОДСКАЗКА / ОТМЕНА / ПЕРЕМЕШИВАНИЕ
    # --------------------------------------------------------

    def show_hint(self):
        self._clear_hints()
        if self.first_selected:
            self.first_selected.selected = False
            self.first_selected = None
        hint = self._find_hint()
        if hint:
            self.play_sound('bell')  # подсказка - колокольчик
            hint[0].hint = True
            hint[1].hint = True
            self._redraw()
            Clock.schedule_once(lambda dt: self._clear_hints_redraw(), 2.5)
        else:
            self.play_sound('dzin')  # тупик - струна
            self._show_popup('Подсказка',
                             'Нет доступных пар.\nНажмите "Перемешать"')

    def _clear_hints(self):
        for t in self.tiles:
            t.hint = False

    def _clear_hints_redraw(self):
        self._clear_hints()
        self._redraw()

    def undo(self):
        if not self.history:
            return
        if not hasattr(self, 'undos_used'):
            self.undos_used = 0
        if self.undos_used >= 5:
            self._show_popup('Отмена', 'Больше нельзя отменять.\nМаксимум 5 раз за игру.')
            return
        self.undos_used += 1
        # Возвращаем последнюю снятую пару
        tile1, tile2 = self.history.pop()
        tile1.removed = False
        tile2.removed = False
        self.score -= 1
        # Сбрасываем выделение, если что-то выбрано
        if self.first_selected is not None:
            self.first_selected.selected = False
            self.first_selected = None
        self._clear_hints()
        self.play_sound('knock')
        self._redraw()

    def shuffle(self):
        if self.shuffles_left <= 0:
            self.play_sound('dzin')
            self._show_popup('Перемешивания закончились',
                             'Перемешать больше нельзя.\n'
                             'Нажмите "Новая игра"')
            return
        # Запускаем звук перемешивания и через 1.5 секунды само перемешивание
        self.play_sound('mixing')
        self.shuffles_left -= 1
        Clock.schedule_once(lambda dt: self._do_shuffle(), 1.5)

    def _do_shuffle(self):
        """Сам процесс перемешивания (вызывается через 1.5 сек после звука)."""
        remaining = [t for t in self.tiles if not t.removed]
        defs = [t.tile_def for t in remaining]

        # Умное перемешивание: пробуем до 50 раз, ищем расклад с минимум 5 ходами
        best_defs = None
        best_count = 0
        target_moves = 5
        for attempt in range(50):
            random.shuffle(defs)
            for t, d in zip(remaining, defs):
                t.tile_def = d
            free = [t for t in remaining if self._is_free(t)]
            count = 0
            for i in range(len(free)):
                for j in range(i + 1, len(free)):
                    if tiles_match(free[i].tile_def, free[j].tile_def):
                        count += 1
            if count >= target_moves:
                break
            if count > best_count:
                best_count = count
                best_defs = list(defs)

        if attempt == 49 and best_defs is not None:
            for t, d in zip(remaining, best_defs):
                t.tile_def = d

        self.first_selected = None
        for t in self.tiles:
            t.selected = False
        self._clear_hints()
        self._redraw()

    def _check_game_state(self):
        remaining = [t for t in self.tiles if not t.removed]
        if not remaining:
            self.game_over = True
            self.play_sound('clue')  # победа
            self._launch_fireworks()
            time_str = self._format_time(self.elapsed_seconds)
            # Проверяем рекорд
            old_record = load_record()
            current = self.elapsed_seconds
            is_new_record = (old_record is None) or (current < old_record)
            if is_new_record:
                save_record(current)
                message = (f'НОВЫЙ РЕКОРД!\n\n'
                           f'Время: {time_str}\n')
                if old_record is not None:
                    message += f'Прошлый: {self._format_time(old_record)}'
            else:
                message = (f'Все плитки убраны!\n\n'
                           f'Время: {time_str}\n'
                           f'Рекорд: {self._format_time(old_record)}')
            self._show_popup('ПОБЕДА!', message)
            return
        if not self._find_hint():
            self._show_popup('Тупик',
                             'Нет доступных пар.\n'
                             'Нажмите "Перемешать"')

    def _format_time(self, seconds):
        m = seconds // 60
        s = seconds % 60
        return f'{m:02d}:{s:02d}'

    def _launch_fireworks(self):
        """Запускает анимацию салюта при победе."""
        # Создаём фейерверк: несколько точек разлетающихся в разные стороны
        # Запускаем 5 залпов с разной задержкой
        for i in range(5):
            Clock.schedule_once(
                lambda dt, idx=i: self._single_firework(idx),
                i * 0.4
            )

    def _single_firework(self, idx):
        """Один залп салюта."""
        # Случайная позиция в верхней части экрана
        cx = self.width * (0.2 + 0.6 * random.random())
        cy = self.height * (0.5 + 0.4 * random.random())

        # Цвет залпа
        colors = [
            (1.0, 0.3, 0.3, 1),   # красный
            (0.3, 1.0, 0.3, 1),   # зелёный
            (0.3, 0.5, 1.0, 1),   # синий
            (1.0, 0.9, 0.3, 1),   # жёлтый
            (1.0, 0.5, 0.9, 1),   # розовый
        ]
        col = random.choice(colors)

        # Рисуем 12 искр вокруг центра
        num_sparks = 12
        for i in range(num_sparks):
            angle = i * 2 * math.pi / num_sparks
            # Анимируем "разлёт" искр через несколько кадров
            self._draw_spark(cx, cy, angle, col, 0)

    def _draw_spark(self, cx, cy, angle, col, frame):
        """Рисует искру и планирует следующий кадр анимации."""
        if frame >= 15:
            return  # анимация завершена
        # Радиус разлёта растёт с каждым кадром
        r = frame * 8
        spark_x = cx + r * math.cos(angle)
        spark_y = cy + r * math.sin(angle)
        # Размер искры уменьшается
        size = max(2, 8 - frame * 0.4)
        # Рисуем искру на canvas (after — чтобы поверх плиток)
        with self.canvas.after:
            r_col, g_col, b_col, a = col
            # Затухающий цвет
            fade = 1.0 - frame / 15.0
            Color(r_col, g_col, b_col, fade)
            Ellipse(
                pos=(spark_x - size / 2, spark_y - size / 2),
                size=(size, size)
            )
        # Планируем следующий кадр
        Clock.schedule_once(
            lambda dt: self._draw_spark(cx, cy, angle, col, frame + 1),
            0.05
        )
        # Очищаем canvas.after после окончания всей анимации
        if frame == 0:
            Clock.schedule_once(
                lambda dt: self.canvas.after.clear(),
                3.0
            )

    def _show_popup(self, title, message):
        popup = Popup(
            title=title,
            title_size='42sp',
            content=Label(text=message, font_size=44, halign='center', valign='middle'),
            size_hint=(0.85, 0.7),
            separator_color=(0.3, 0.6, 1, 1)
        )
        popup.open()


# ============================================================
# КНОПКА С ИКОНКОЙ (рисуется графикой, без зависимости от шрифтов)
# ============================================================

class IconButton(Button):
    """Кнопка, рисующая на себе иконку графикой."""

    def __init__(self, icon_type='hint', **kwargs):
        # Скрываем текст
        kwargs['text'] = ''
        super().__init__(**kwargs)
        self.icon_type = icon_type
        # Перерисовываем иконку при изменении размера/позиции
        self.bind(size=self._update_icon, pos=self._update_icon)

    def _update_icon(self, *args):
        # Очищаем предыдущую иконку
        self.canvas.after.clear()

        cx = self.center_x
        cy = self.center_y
        size = min(self.width, self.height) * 0.45

        with self.canvas.after:
            Color(1, 1, 1, 1)  # белый цвет иконки

            if self.icon_type == 'hint':
                self._draw_lightbulb(cx, cy, size)
            elif self.icon_type == 'undo':
                self._draw_undo_arrow(cx, cy, size)
            elif self.icon_type == 'shuffle':
                self._draw_shuffle(cx, cy, size)
            elif self.icon_type == 'new':
                self._draw_plus(cx, cy, size)

    def _draw_lightbulb(self, cx, cy, size):
        """Лампочка — кружок с цоколем снизу."""
        # Колба (круг)
        bulb_size = size * 0.85
        Ellipse(
            pos=(cx - bulb_size / 2, cy - bulb_size / 2 + size * 0.1),
            size=(bulb_size, bulb_size)
        )
        # Цоколь — прямоугольник снизу
        base_w = size * 0.5
        base_h = size * 0.25
        Color(0.85, 0.85, 0.85, 1)
        Rectangle(
            pos=(cx - base_w / 2, cy - size * 0.55),
            size=(base_w, base_h)
        )
        # Лучики света
        Color(1, 1, 1, 1)
        for i in range(8):
            angle = i * math.pi / 4
            inner = bulb_size / 2 + size * 0.15
            outer = bulb_size / 2 + size * 0.35
            Line(points=[
                cx + inner * math.cos(angle),
                cy + size * 0.1 + inner * math.sin(angle),
                cx + outer * math.cos(angle),
                cy + size * 0.1 + outer * math.sin(angle),
            ], width=2)

    def _draw_undo_arrow(self, cx, cy, size):
        """Стрелка-разворот (как на знаке)."""
        # Дуга (полукруг сверху) — рисуем точками для имитации
        radius = size * 0.55
        # Линия дуги через много точек
        arc_points = []
        for i in range(20):
            angle = math.pi * (1.0 - i / 19.0)  # от 180° до 0°
            arc_points.extend([
                cx + radius * math.cos(angle),
                cy + radius * math.sin(angle) * 0.7  # немного сплющенный
            ])
        Line(points=arc_points, width=size * 0.12)

        # Стрелка-наконечник на левом конце дуги (указывает вниз-влево)
        arrow_x = cx - radius
        arrow_y = cy
        Line(points=[
            arrow_x - size * 0.25, arrow_y + size * 0.15,
            arrow_x, arrow_y - size * 0.2,
            arrow_x + size * 0.25, arrow_y + size * 0.15,
        ], width=size * 0.12)
        # Палочка вниз от конца дуги
        Line(points=[
            arrow_x, arrow_y,
            arrow_x, arrow_y - size * 0.3,
        ], width=size * 0.12)

    def _draw_shuffle(self, cx, cy, size):
        """Две стрелки в разных направлениях (туда-сюда)."""
        # Верхняя стрелка вправо
        y_top = cy + size * 0.25
        Line(points=[
            cx - size * 0.6, y_top,
            cx + size * 0.5, y_top,
        ], width=size * 0.13)
        # Наконечник
        Line(points=[
            cx + size * 0.3, y_top + size * 0.2,
            cx + size * 0.5, y_top,
            cx + size * 0.3, y_top - size * 0.2,
        ], width=size * 0.13)

        # Нижняя стрелка влево
        y_bot = cy - size * 0.25
        Line(points=[
            cx + size * 0.6, y_bot,
            cx - size * 0.5, y_bot,
        ], width=size * 0.13)
        # Наконечник
        Line(points=[
            cx - size * 0.3, y_bot + size * 0.2,
            cx - size * 0.5, y_bot,
            cx - size * 0.3, y_bot - size * 0.2,
        ], width=size * 0.13)

    def _draw_plus(self, cx, cy, size):
        """Плюсик."""
        thickness = size * 0.22
        # Горизонтальная палка
        Rectangle(
            pos=(cx - size * 0.55, cy - thickness / 2),
            size=(size * 1.1, thickness)
        )
        # Вертикальная палка
        Rectangle(
            pos=(cx - thickness / 2, cy - size * 0.55),
            size=(thickness, size * 1.1)
        )


# ============================================================
# ПРИЛОЖЕНИЕ — ГОРИЗОНТАЛЬНАЯ КОМПОНОВКА
# ============================================================

class MahjongApp(App):
    def build(self):
        self.title = 'Маджонг'

        # Главный контейнер: горизонтальный (поле слева, кнопки справа)
        root = BoxLayout(orientation='horizontal')

        # ===== ИГРОВОЕ ПОЛЕ (занимает большую часть слева) =====
        self.board = MahjongBoard()
        root.add_widget(self.board)

        # ===== ПРАВАЯ ПАНЕЛЬ С КНОПКАМИ И СЧЁТОМ =====
        side_panel = BoxLayout(
            orientation='vertical',
            size_hint_x=None,
            width=180,
            padding=10,
            spacing=10
        )

        # Счёт сверху панели (компактно)
        self.score_label = Label(
            text='00:00',
            font_size=42,
            bold=True,
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=80
        )
        self.score_label.bind(size=lambda l, s: setattr(l, 'text_size', s))
        side_panel.add_widget(self.score_label)

        # Создаём кнопки и сохраняем ссылки на счётчики
        self.btn_counters = {}
        for icon_type, color, callback in [
            ('hint', (0.4, 0.7, 0.5, 1),
             lambda b: self.board.show_hint()),
            ('undo', (0.5, 0.6, 0.8, 1),
             lambda b: self.board.undo()),
            ('shuffle', (0.7, 0.5, 0.4, 1),
             lambda b: self.board.shuffle()),
            ('new', (0.6, 0.4, 0.7, 1),
             lambda b: self.board.restart()),
        ]:
            # Контейнер: кнопка сверху, счётчик снизу
            container = BoxLayout(orientation='vertical', spacing=2)
            btn = IconButton(icon_type=icon_type, background_color=color)
            btn.bind(on_release=callback)
            container.add_widget(btn)
            # Счётчик — крупная цифра
            counter = Label(
                text='5',
                font_size=28,
                bold=True,
                color=(1, 1, 1, 1),
                size_hint_y=None,
                height=35
            )
            self.btn_counters[icon_type] = counter
            container.add_widget(counter)
            side_panel.add_widget(container)

        root.add_widget(side_panel)

        Clock.schedule_interval(self._update_score, 0.5)
        return root

    def _update_score(self, dt):
        m = self.board.elapsed_seconds // 60
        s = self.board.elapsed_seconds % 60
        self.score_label.text = f'{m:02d}:{s:02d}'
        
        # Обновляем счётчики под кнопками
        if hasattr(self, 'btn_counters'):
            self.btn_counters['hint'].text = '∞'
            undos_left = max(0, 5 - getattr(self.board, 'undos_used', 0))
            self.btn_counters['undo'].text = str(undos_left)
            self.btn_counters['shuffle'].text = str(self.board.shuffles_left)
            self.btn_counters['new'].text = ''


if __name__ == '__main__':
    MahjongApp().run()
