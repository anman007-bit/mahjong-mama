# -*- coding: utf-8 -*-
"""
МАДЖОНГ-СОЛИТЁР (Черепаха) — версия 2.0
Настоящий маджонг с многослойным полем, подсветкой свободных плиток,
подсказками и кнопкой перемешивания.
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle, Ellipse
from kivy.core.window import Window
from kivy.clock import Clock
import random


# ============================================================
# ТРАДИЦИОННАЯ РАСКЛАДКА "ЧЕРЕПАХА" (144 плитки)
# Координаты: (слой, ряд, столбец)
# Слой 0 — нижний, слой 4 — самая верхняя плитка
# ============================================================

def _build_turtle_layout():
    """Канонический Turtle layout: 144 плитки.
    87 (слой 0) + 36 (слой 1) + 16 (слой 2) + 4 (слой 3) + 1 (слой 4) = 144"""
    layout = []

    # Слой 0 (87 плиток) — основание черепахи, симметричный
    # Распределение по рядам: 12+8+10+12+12+12+10+8+3 = 87
    rows_layer0 = {
        0: [(c, ) for c in range(1, 13)],          # ряд 0: 12 плиток (cols 1-12)
        1: [(c, ) for c in range(3, 11)],          # ряд 1:  8 плиток (cols 3-10)
        2: [(c, ) for c in range(2, 12)],          # ряд 2: 10 плиток (cols 2-11)
        3: [(c, ) for c in range(1, 13)],          # ряд 3: 12 плиток (cols 1-12)
        4: [(c, ) for c in range(1, 13)],          # ряд 4: 12 плиток (cols 1-12)
        5: [(c, ) for c in range(1, 13)],          # ряд 5: 12 плиток (cols 1-12)
        6: [(c, ) for c in range(2, 12)],          # ряд 6: 10 плиток (cols 2-11)
        7: [(c, ) for c in range(3, 11)],          # ряд 7:  8 плиток (cols 3-10)
        8: [(c, ) for c in [4, 7, 9]],             # ряд 8:  3 плитки (декоративный хвост)
    }
    for row, cols in rows_layer0.items():
        for col_tuple in cols:
            layout.append((0, row, col_tuple[0]))

    # Слой 1 (36 плиток): прямоугольник 6x6 в центре
    for r in range(1, 7):  # ряды 1-6
        for c in range(4, 10):  # cols 4-9
            layout.append((1, r, c))

    # Слой 2 (16 плиток): прямоугольник 4x4
    for r in range(2, 6):  # ряды 2-5
        for c in range(5, 9):  # cols 5-8
            layout.append((2, r, c))

    # Слой 3 (4 плитки): квадрат 2x2
    for r in range(3, 5):  # ряды 3-4
        for c in range(6, 8):  # cols 6-7
            layout.append((3, r, c))

    # Слой 4 (1 плитка): вершина
    layout.append((4, 3, 6))

    return layout


TURTLE_LAYOUT = _build_turtle_layout()


# ============================================================
# ТИПЫ ПЛИТОК
# Маджонг: 3 масти по 9 плиток (1-9), 4 ветра, 3 дракона
# Каждый тип — 4 копии = 36*4 = 144 плитки
# ============================================================

# Все типы плиток (всего 36 уникальных)
TILE_DEFINITIONS = []

# Масть "Точки" (точки/круги) — 1-9
for n in range(1, 10):
    TILE_DEFINITIONS.append({'suit': 'dots', 'value': n})

# Масть "Бамбук" — 1-9
for n in range(1, 10):
    TILE_DEFINITIONS.append({'suit': 'bamboo', 'value': n})

# Масть "Символы" (числа иероглифами) — 1-9
for n in range(1, 10):
    TILE_DEFINITIONS.append({'suit': 'characters', 'value': n})

# Ветры: восток, юг, запад, север
for w in ['east', 'south', 'west', 'north']:
    TILE_DEFINITIONS.append({'suit': 'wind', 'value': w})

# Драконы: красный, зелёный, белый
for d in ['red', 'green', 'white']:
    TILE_DEFINITIONS.append({'suit': 'dragon', 'value': d})

# Сезоны (4 уникальных, по 1 штуке) — особые плитки
for s in ['spring', 'summer', 'autumn', 'winter']:
    TILE_DEFINITIONS.append({'suit': 'season', 'value': s})

# Цветы (4 уникальных, по 1 штуке) — особые плитки
for f in ['plum', 'orchid', 'chrysanthemum', 'bamboo_flower']:
    TILE_DEFINITIONS.append({'suit': 'flower', 'value': f})

# Сезоны и цветы парятся между собой по группам, остальные — по 4 копии


def build_tile_pool():
    """Возвращает 144 плитки для расклада."""
    pool = []
    for tile_def in TILE_DEFINITIONS:
        if tile_def['suit'] in ('season', 'flower'):
            # Сезоны и цветы — по одной штуке, но соединяются по группе
            pool.append(dict(tile_def))
        else:
            # Остальные — по 4 копии
            for _ in range(4):
                pool.append(dict(tile_def))
    return pool


def tiles_match(t1_def, t2_def):
    """Проверяет, можно ли соединить две плитки по правилам маджонга."""
    if t1_def['suit'] == t2_def['suit']:
        # Сезоны соединяются с любыми сезонами
        if t1_def['suit'] == 'season':
            return True
        # Цветы — с любыми цветами
        if t1_def['suit'] == 'flower':
            return True
        # Остальные — только идентичные
        return t1_def['value'] == t2_def['value']
    return False


# ============================================================
# СИМВОЛ И ЦВЕТ ДЛЯ КАЖДОЙ ПЛИТКИ
# ============================================================

# Китайские числа (используются для масти "Символы" и иногда для "Бамбука")
CHINESE_NUMBERS = ['一', '二', '三', '四', '五', '六', '七', '八', '九']

# Символы ветров (китайские)
WIND_SYMBOLS = {
    'east': '東', 'south': '南', 'west': '西', 'north': '北'
}

# Символы драконов
DRAGON_SYMBOLS = {
    'red': '中', 'green': '發', 'white': '白'  # белый дракон обычно пустой или с буквой 白
}

# Символы сезонов
SEASON_SYMBOLS = {
    'spring': '春', 'summer': '夏', 'autumn': '秋', 'winter': '冬'
}

# Символы цветов
FLOWER_SYMBOLS = {
    'plum': '梅', 'orchid': '蘭', 'chrysanthemum': '菊', 'bamboo_flower': '竹'
}


def get_tile_display(tile_def):
    """
    Возвращает (текст, цвет_текста) для отрисовки плитки.
    """
    suit = tile_def['suit']
    value = tile_def['value']

    if suit == 'characters':
        return (CHINESE_NUMBERS[value - 1] + '\n万', (0.1, 0.1, 0.1, 1))
    elif suit == 'bamboo':
        # Для бамбука используем зелёный цвет и число
        if value == 1:
            return ('🐦', (0.1, 0.5, 0.1, 1))  # 1 бамбук = птица (традиционно)
        return (str(value) + '\n竹', (0.1, 0.5, 0.1, 1))
    elif suit == 'dots':
        # Для точек — число и символ
        return (str(value) + '\n●', (0.6, 0.1, 0.1, 1))
    elif suit == 'wind':
        return (WIND_SYMBOLS[value], (0.1, 0.1, 0.1, 1))
    elif suit == 'dragon':
        if value == 'red':
            return (DRAGON_SYMBOLS[value], (0.85, 0.1, 0.1, 1))
        elif value == 'green':
            return (DRAGON_SYMBOLS[value], (0.1, 0.55, 0.2, 1))
        else:  # white
            return ('  ', (0.5, 0.5, 0.5, 1))  # белый дракон — почти пустая плитка
    elif suit == 'season':
        return (SEASON_SYMBOLS[value], (0.85, 0.5, 0.1, 1))
    elif suit == 'flower':
        return (FLOWER_SYMBOLS[value], (0.7, 0.2, 0.5, 1))
    return ('?', (0, 0, 0, 1))


# ============================================================
# ПЛИТКА
# ============================================================

class MahjongTile:
    """Одна плитка в игре."""

    def __init__(self, tile_def, layer, row, col):
        self.tile_def = tile_def       # тип плитки (suit, value)
        self.layer = layer             # номер слоя
        self.row = row                 # ряд
        self.col = col                 # столбец
        self.removed = False           # убрана ли с поля
        self.selected = False          # выделена ли игроком
        self.hint = False              # показывается ли как подсказка


# ============================================================
# ИГРОВОЕ ПОЛЕ
# ============================================================

class MahjongBoard(Widget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tiles = []
        self.first_selected = None
        self.score = 0
        self.total_pairs = 72  # 144 / 2
        self.history = []  # для отмены ходов

        self._create_tiles()

        self.bind(size=self._redraw, pos=self._redraw)
        Clock.schedule_once(lambda dt: self._redraw(), 0)

    # --------------------------------------------------------
    def _create_tiles(self):
        """Создаёт все 144 плитки и расставляет их в форме черепахи."""
        pool = build_tile_pool()
        random.shuffle(pool)

        self.tiles = []
        for i, position in enumerate(TURTLE_LAYOUT):
            if i >= len(pool):
                break
            layer, row, col = position
            self.tiles.append(MahjongTile(pool[i], layer, row, col))

    def restart(self):
        self.first_selected = None
        self.score = 0
        self.history = []
        self._create_tiles()
        self._redraw()

    # --------------------------------------------------------
    # ГЕОМЕТРИЯ ПОЛЯ
    # --------------------------------------------------------

    def _tile_dims(self):
        """Размер одной плитки. Поле 14 столбцов x 9 рядов."""
        margin = 0.04
        usable_w = self.width * (1 - 2 * margin)
        usable_h = self.height * (1 - 2 * margin)
        # Учитываем что плитки чуть смещаются вверх-вправо для слоёв
        tile_w = usable_w / 15  # 14 столбцов + запас на смещение слоёв
        tile_h = usable_h / 10  # 9 рядов + запас
        # Плитки выше чем шире (как настоящие)
        return tile_w, tile_w * 1.3

    def _board_offset(self, tile_w, tile_h):
        board_w = tile_w * 14
        board_h = tile_h * 9
        offset_x = (self.width - board_w) / 2
        offset_y = (self.height - board_h) / 2
        return offset_x, offset_y

    def _tile_screen_pos(self, tile, tile_w, tile_h, offset_x, offset_y):
        """Возвращает (x, y) — нижний левый угол плитки на экране с учётом слоя."""
        # Смещение для слоёв (создаёт эффект 3D-стопки)
        layer_offset_x = tile_w * 0.08
        layer_offset_y = tile_h * 0.08

        x = offset_x + tile.col * tile_w + tile.layer * layer_offset_x
        # Y инвертируем (row 0 — сверху)
        y = offset_y + (8 - tile.row) * tile_h + tile.layer * layer_offset_y
        return x, y

    # --------------------------------------------------------
    # ПРАВИЛА МАДЖОНГА
    # --------------------------------------------------------

    def _is_free(self, tile):
        """
        Плитка свободна, если:
        1. Сверху на ней нет другой плитки
        2. Слева ИЛИ справа есть свободное место (нет соседней плитки)
        """
        if tile.removed:
            return False

        for other in self.tiles:
            if other.removed or other is tile:
                continue
            # Проверка: лежит ли other на tile
            if other.layer == tile.layer + 1:
                if (other.row in (tile.row - 1, tile.row, tile.row + 1)
                        and other.col in (tile.col - 1, tile.col, tile.col + 1)):
                    # Точная проверка пересечения
                    if (abs(other.row - tile.row) <= 1
                            and abs(other.col - tile.col) <= 1):
                        return False

        # Проверка соседей слева и справа на том же слое
        has_left = False
        has_right = False
        for other in self.tiles:
            if other.removed or other is tile:
                continue
            if other.layer == tile.layer:
                if abs(other.row - tile.row) <= 1:  # на той же или соседней строке
                    if other.col == tile.col - 2 or other.col == tile.col - 1:
                        has_left = True
                    elif other.col == tile.col + 1 or other.col == tile.col + 2:
                        has_right = True

        # Свободна если хотя бы с одной стороны открыта
        return not (has_left and has_right)

    def _find_hint(self):
        """Находит пару плиток, которые можно убрать. Возвращает (t1, t2) или None."""
        free_tiles = [t for t in self.tiles if not t.removed and self._is_free(t)]
        for i in range(len(free_tiles)):
            for j in range(i + 1, len(free_tiles)):
                if tiles_match(free_tiles[i].tile_def, free_tiles[j].tile_def):
                    return (free_tiles[i], free_tiles[j])
        return None

    # --------------------------------------------------------
    # ОТРИСОВКА
    # --------------------------------------------------------

    def _redraw(self, *args):
        self.canvas.clear()
        self.clear_widgets()

        tile_w, tile_h = self._tile_dims()
        offset_x, offset_y = self._board_offset(tile_w, tile_h)

        # Фон
        with self.canvas:
            Color(0.15, 0.40, 0.25, 1)  # классический зелёный сукно
            Rectangle(pos=(0, 0), size=self.size)

        # Сортируем плитки по слою (сверху к низу при отрисовке: сначала нижние)
        sorted_tiles = sorted(
            [t for t in self.tiles if not t.removed],
            key=lambda t: (t.layer, -t.row, t.col)
        )

        for tile in sorted_tiles:
            x, y = self._tile_screen_pos(tile, tile_w, tile_h, offset_x, offset_y)
            is_free = self._is_free(tile)
            self._draw_tile(tile, x, y, tile_w, tile_h, is_free)

    def _draw_tile(self, tile, x, y, tile_w, tile_h, is_free):
        """Рисует одну плитку."""
        radius = tile_w * 0.10

        # Толщина "боковины" плитки (для эффекта объёма)
        side = tile_w * 0.06

        with self.canvas:
            # 1. Тёмная "боковина" плитки (тень внизу-справа создаёт объём)
            Color(0.25, 0.18, 0.10, 1)
            RoundedRectangle(
                pos=(x, y),
                size=(tile_w, tile_h),
                radius=[radius]
            )

            # 2. Лицевая часть плитки (чуть смещена вверх-влево от боковины)
            if tile.selected:
                Color(1.0, 0.95, 0.6, 1)  # жёлтый — выбрана
            elif tile.hint:
                Color(0.8, 1.0, 0.8, 1)   # зелёный — подсказка
            elif is_free:
                Color(0.99, 0.97, 0.92, 1)  # светло-кремовый — свободная
            else:
                Color(0.75, 0.72, 0.65, 1)  # серый — заблокирована

            RoundedRectangle(
                pos=(x + side, y + side),
                size=(tile_w - side, tile_h - side),
                radius=[radius]
            )

            # 3. Обводка лицевой части
            if tile.selected:
                Color(1.0, 0.6, 0.0, 1)
                Line(
                    rounded_rectangle=(x + side, y + side,
                                       tile_w - side, tile_h - side, radius),
                    width=2.5
                )
            else:
                Color(0.4, 0.3, 0.2, 0.6)
                Line(
                    rounded_rectangle=(x + side, y + side,
                                       tile_w - side, tile_h - side, radius),
                    width=1.0
                )

        # Символ плитки
        text, color = get_tile_display(tile.tile_def)

        # Если плитка не свободна — приглушаем цвет символа
        if not is_free and not tile.selected:
            r, g, b, a = color
            color = (r * 0.6, g * 0.6, b * 0.6, 1)

        label = Label(
            text=text,
            pos=(x + side, y + side),
            size=(tile_w - side, tile_h - side),
            font_size=tile_w * 0.42,
            bold=True,
            color=color,
            halign='center',
            valign='middle'
        )
        label.text_size = label.size
        self.add_widget(label)

    # --------------------------------------------------------
    # ОБРАБОТКА КАСАНИЙ
    # --------------------------------------------------------

    def on_touch_down(self, touch):
        tile = self._tile_at_touch(touch.x, touch.y)
        if tile is None or not self._is_free(tile):
            # Если кликнули вне свободной плитки — снимаем выделение
            if self.first_selected is not None:
                self.first_selected.selected = False
                self.first_selected = None
                self._clear_hints()
                self._redraw()
            return

        self._clear_hints()

        if self.first_selected is not None:
            if self.first_selected is tile:
                # Снимаем выделение
                tile.selected = False
                self.first_selected = None
                self._redraw()
                return

            if tiles_match(tile.tile_def, self.first_selected.tile_def):
                # Совпали — убираем
                self.history.append((self.first_selected, tile))
                self.first_selected.removed = True
                tile.removed = True
                self.first_selected = None
                self.score += 1
                self._redraw()
                self._check_game_state()
            else:
                # Не подходят
                self.first_selected.selected = False
                tile.selected = True
                self.first_selected = tile
                self._redraw()
        else:
            tile.selected = True
            self.first_selected = tile
            self._redraw()

    def _tile_at_touch(self, tx, ty):
        """Находит плитку под точкой касания. Идём от верхнего слоя вниз."""
        tile_w, tile_h = self._tile_dims()
        offset_x, offset_y = self._board_offset(tile_w, tile_h)
        side = tile_w * 0.06

        # Сортируем по убыванию слоя (верхние сначала)
        candidates = sorted(
            [t for t in self.tiles if not t.removed],
            key=lambda t: -t.layer
        )

        for tile in candidates:
            x, y = self._tile_screen_pos(tile, tile_w, tile_h, offset_x, offset_y)
            # Проверяем попадание в лицевую часть плитки
            if (x + side <= tx <= x + tile_w
                    and y + side <= ty <= y + tile_h):
                return tile
        return None

    # --------------------------------------------------------
    # ПОДСКАЗКА И ОТМЕНА
    # --------------------------------------------------------

    def show_hint(self):
        """Подсвечивает зелёным две плитки, которые можно соединить."""
        self._clear_hints()
        if self.first_selected:
            self.first_selected.selected = False
            self.first_selected = None
        hint = self._find_hint()
        if hint:
            hint[0].hint = True
            hint[1].hint = True
            self._redraw()
            # Через 2 секунды убираем подсветку
            Clock.schedule_once(lambda dt: self._clear_hints_and_redraw(), 2.5)
        else:
            self._show_popup('Подсказка',
                             'Нет доступных пар.\nНажмите "Перемешать"')

    def _clear_hints(self):
        for t in self.tiles:
            t.hint = False

    def _clear_hints_and_redraw(self):
        self._clear_hints()
        self._redraw()

    def undo(self):
        """Отменяет последний ход."""
        if not self.history:
            return
        t1, t2 = self.history.pop()
        t1.removed = False
        t2.removed = False
        self.score -= 1
        self._redraw()

    def shuffle(self):
        """Перемешивает оставшиеся плитки."""
        remaining = [t for t in self.tiles if not t.removed]
        defs = [t.tile_def for t in remaining]
        random.shuffle(defs)
        for t, d in zip(remaining, defs):
            t.tile_def = d
        self.first_selected = None
        for t in self.tiles:
            t.selected = False
        self._clear_hints()
        self._redraw()

    # --------------------------------------------------------
    # ПРОВЕРКА СОСТОЯНИЯ
    # --------------------------------------------------------

    def _check_game_state(self):
        remaining = [t for t in self.tiles if not t.removed]
        if not remaining:
            self._show_popup('Победа!',
                             f'Поздравляем!\nВсе плитки убраны!')
            return
        if not self._find_hint():
            self._show_popup('Тупик',
                             'Нет доступных пар.\n'
                             'Нажмите "Перемешать" или "Новая игра"')

    def _show_popup(self, title, message):
        popup = Popup(
            title=title,
            content=Label(text=message, font_size=22),
            size_hint=(0.8, 0.4)
        )
        popup.open()


# ============================================================
# ПРИЛОЖЕНИЕ
# ============================================================

class MahjongApp(App):
    def build(self):
        self.title = 'Маджонг Черепаха'
        root = BoxLayout(orientation='vertical')

        # Верхняя панель со счётом
        score_panel = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=60,
            padding=10
        )
        self.score_label = Label(
            text='Пар убрано: 0 из 72',
            font_size=22,
            bold=True,
            color=(1, 1, 1, 1)
        )
        score_panel.add_widget(self.score_label)
        root.add_widget(score_panel)

        # Игровое поле
        self.board = MahjongBoard()
        root.add_widget(self.board)

        # Нижняя панель с кнопками
        button_panel = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=80,
            padding=8,
            spacing=8
        )

        hint_btn = Button(
            text='Подсказка',
            font_size=18,
            bold=True,
            background_color=(0.4, 0.7, 0.5, 1)
        )
        hint_btn.bind(on_release=lambda b: self.board.show_hint())
        button_panel.add_widget(hint_btn)

        undo_btn = Button(
            text='Отменить',
            font_size=18,
            bold=True,
            background_color=(0.5, 0.6, 0.8, 1)
        )
        undo_btn.bind(on_release=lambda b: self.board.undo())
        button_panel.add_widget(undo_btn)

        shuffle_btn = Button(
            text='Перемешать',
            font_size=18,
            bold=True,
            background_color=(0.7, 0.5, 0.4, 1)
        )
        shuffle_btn.bind(on_release=lambda b: self.board.shuffle())
        button_panel.add_widget(shuffle_btn)

        new_btn = Button(
            text='Новая игра',
            font_size=18,
            bold=True,
            background_color=(0.6, 0.4, 0.7, 1)
        )
        new_btn.bind(on_release=lambda b: self.board.restart())
        button_panel.add_widget(new_btn)

        root.add_widget(button_panel)

        Clock.schedule_interval(self._update_score, 0.5)
        return root

    def _update_score(self, dt):
        self.score_label.text = (
            f'Пар убрано: {self.board.score} из {self.board.total_pairs}'
        )


if __name__ == '__main__':
    MahjongApp().run()
