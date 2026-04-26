# -*- coding: utf-8 -*-
"""
МАДЖОНГ-ПАСЬЯНС — игра без рекламы
Версия для Android (собирается в APK через Buildozer)
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.core.window import Window
from kivy.clock import Clock
import random
from collections import deque


# ============================================================
# НАСТРОЙКИ
# ============================================================

COLS = 8
ROWS = 6
TILE_TYPES = 12
COPIES_PER_TYPE = 4

# Символы плиток. Используем простые крупные знаки, которые
# гарантированно есть на любом Android-телефоне.
TILE_SYMBOLS = [
    '1', '2', '3', '4',
    '5', '6', '7', '8',
    '9', 'A', 'B', 'C',
]

# Каждому типу плитки — свой яркий цвет.
# Так маме будет легко находить пары даже без чтения цифры.
TILE_COLORS = [
    (1.00, 0.42, 0.42),  # красный
    (1.00, 0.65, 0.30),  # оранжевый
    (1.00, 0.85, 0.30),  # жёлтый
    (0.55, 0.85, 0.40),  # салатовый
    (0.30, 0.75, 0.45),  # зелёный
    (0.40, 0.80, 0.85),  # бирюзовый
    (0.40, 0.65, 0.95),  # голубой
    (0.55, 0.50, 0.90),  # фиолетовый
    (0.90, 0.55, 0.85),  # розовый
    (0.85, 0.70, 0.55),  # бежевый
    (0.70, 0.50, 0.40),  # коричневый
    (0.60, 0.80, 0.70),  # мятный
]


# ============================================================
# ПЛИТКА
# ============================================================

class Tile:
    def __init__(self, tile_type, col, row):
        self.tile_type = tile_type
        self.col = col
        self.row = row
        self.removed = False
        self.selected = False

    @property
    def symbol(self):
        return TILE_SYMBOLS[self.tile_type]

    @property
    def color(self):
        return TILE_COLORS[self.tile_type]


# ============================================================
# ИГРОВОЕ ПОЛЕ
# ============================================================

class MahjongBoard(Widget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tiles = []
        self.first_selected = None
        self.score = 0
        self.total_pairs = 0
        self._create_tiles()
        self.bind(size=self._redraw, pos=self._redraw)
        Clock.schedule_once(lambda dt: self._redraw(), 0)

    def _create_tiles(self):
        types = []
        for t in range(TILE_TYPES):
            for _ in range(COPIES_PER_TYPE):
                types.append(t)
        random.shuffle(types)

        self.tiles = []
        index = 0
        for row in range(ROWS):
            for col in range(COLS):
                if index < len(types):
                    self.tiles.append(Tile(types[index], col, row))
                    index += 1
        self.total_pairs = len(self.tiles) // 2

    def _tile_size(self):
        margin = 0.05
        usable_w = self.width * (1 - 2 * margin)
        usable_h = self.height * (1 - 2 * margin)
        return min(usable_w / COLS, usable_h / ROWS)

    def _board_offset(self, tile_size):
        offset_x = (self.width - tile_size * COLS) / 2
        offset_y = (self.height - tile_size * ROWS) / 2
        return offset_x, offset_y

    def _tile_pos(self, tile, tile_size, offset_x, offset_y):
        x = offset_x + tile.col * tile_size
        y = offset_y + (ROWS - 1 - tile.row) * tile_size
        return x, y

    def _redraw(self, *args):
        self.canvas.clear()
        self.clear_widgets()

        tile_size = self._tile_size()
        offset_x, offset_y = self._board_offset(tile_size)

        with self.canvas:
            # Фон поля — тёмно-зелёный, спокойный для глаз
            Color(0.10, 0.30, 0.20, 1)
            Rectangle(pos=(0, 0), size=self.size)

        for tile in self.tiles:
            if tile.removed:
                continue
            x, y = self._tile_pos(tile, tile_size, offset_x, offset_y)
            pad = tile_size * 0.06
            tx, ty = x + pad, y + pad
            tw, th = tile_size - 2 * pad, tile_size - 2 * pad
            radius = tile_size * 0.12

            with self.canvas:
                # Тень под плиткой (для объёма)
                Color(0, 0, 0, 0.3)
                RoundedRectangle(
                    pos=(tx + 2, ty - 3),
                    size=(tw, th),
                    radius=[radius]
                )
                # Цвет плитки
                if tile.selected:
                    # Выбранная — белая с жёлтой обводкой
                    Color(1.0, 0.97, 0.85, 1)
                else:
                    r, g, b = tile.color
                    Color(r, g, b, 1)
                RoundedRectangle(
                    pos=(tx, ty),
                    size=(tw, th),
                    radius=[radius]
                )
                # Обводка
                if tile.selected:
                    Color(1.0, 0.7, 0.0, 1)
                    Line(
                        rounded_rectangle=(tx, ty, tw, th, radius),
                        width=3
                    )
                else:
                    Color(0.15, 0.10, 0.05, 0.5)
                    Line(
                        rounded_rectangle=(tx, ty, tw, th, radius),
                        width=1.5
                    )

            # Символ
            label = Label(
                text=tile.symbol,
                pos=(x, y),
                size=(tile_size, tile_size),
                font_size=tile_size * 0.5,
                bold=True,
                color=(0.1, 0.1, 0.1, 1)
            )
            self.add_widget(label)

    # ----------- Касания -----------
    def on_touch_down(self, touch):
        tile = self._tile_at(touch.x, touch.y)
        if tile is None:
            return

        if self.first_selected is not None:
            if self.first_selected is tile:
                tile.selected = False
                self.first_selected = None
                self._redraw()
                return

            if (tile.tile_type == self.first_selected.tile_type
                    and self._can_connect(self.first_selected, tile)):
                self.first_selected.removed = True
                tile.removed = True
                self.first_selected = None
                self.score += 1
                self._redraw()
                self._check_game_state()
            else:
                self.first_selected.selected = False
                tile.selected = True
                self.first_selected = tile
                self._redraw()
        else:
            tile.selected = True
            self.first_selected = tile
            self._redraw()

    def _tile_at(self, touch_x, touch_y):
        tile_size = self._tile_size()
        offset_x, offset_y = self._board_offset(tile_size)
        for tile in self.tiles:
            if tile.removed:
                continue
            x, y = self._tile_pos(tile, tile_size, offset_x, offset_y)
            if x <= touch_x <= x + tile_size and y <= touch_y <= y + tile_size:
                return tile
        return None

    # ----------- Проверка соединения -----------
    def _can_connect(self, t1, t2):
        grid = [[False] * COLS for _ in range(ROWS)]
        for t in self.tiles:
            if not t.removed and t is not t1 and t is not t2:
                grid[t.row][t.col] = True

        queue = deque()
        queue.append((t1.row, t1.col, -1, 0))
        visited = {(t1.row, t1.col, -1): 0}
        moves = [(-1, 0, 0), (0, 1, 1), (1, 0, 2), (0, -1, 3)]

        while queue:
            row, col, direction, turns = queue.popleft()
            if row == t2.row and col == t2.col:
                return True

            for drow, dcol, new_dir in moves:
                new_row = row + drow
                new_col = col + dcol
                if not (-1 <= new_row <= ROWS and -1 <= new_col <= COLS):
                    continue

                if direction == -1 or direction == new_dir:
                    new_turns = turns
                else:
                    new_turns = turns + 1
                if new_turns > 2:
                    continue

                inside = (0 <= new_row < ROWS and 0 <= new_col < COLS)
                if inside:
                    is_target = (new_row == t2.row and new_col == t2.col)
                    if grid[new_row][new_col] and not is_target:
                        continue

                key = (new_row, new_col, new_dir)
                if key in visited and visited[key] <= new_turns:
                    continue
                visited[key] = new_turns
                queue.append((new_row, new_col, new_dir, new_turns))

        return False

    # ----------- Проверка состояния -----------
    def _check_game_state(self):
        remaining = [t for t in self.tiles if not t.removed]
        if len(remaining) == 0:
            self._show_popup('Победа!',
                             f'Все плитки убраны!\nОтлично!')
            return

        has_moves = False
        for i in range(len(remaining)):
            for j in range(i + 1, len(remaining)):
                if (remaining[i].tile_type == remaining[j].tile_type
                        and self._can_connect(remaining[i], remaining[j])):
                    has_moves = True
                    break
            if has_moves:
                break

        if not has_moves:
            self._show_popup('Ходов нет',
                             f'Убрано пар: {self.score} из {self.total_pairs}\n'
                             f'Нажмите "Новая игра"')

    def _show_popup(self, title, message):
        popup = Popup(
            title=title,
            content=Label(text=message, font_size=22),
            size_hint=(0.8, 0.4)
        )
        popup.open()

    def restart(self):
        self.first_selected = None
        self.score = 0
        self._create_tiles()
        self._redraw()


# ============================================================
# ПРИЛОЖЕНИЕ
# ============================================================

class MahjongApp(App):
    def build(self):
        self.title = 'Маджонг'
        root = BoxLayout(orientation='vertical')

        top_panel = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=80,
            padding=10,
            spacing=10
        )

        self.score_label = Label(
            text='Пар: 0',
            font_size=24,
            bold=True,
            color=(1, 1, 1, 1)
        )
        top_panel.add_widget(self.score_label)

        restart_btn = Button(
            text='Новая игра',
            font_size=22,
            bold=True,
            size_hint_x=None,
            width=200,
            background_color=(0.3, 0.6, 0.4, 1)
        )
        restart_btn.bind(on_release=self._on_restart)
        top_panel.add_widget(restart_btn)

        root.add_widget(top_panel)

        self.board = MahjongBoard()
        root.add_widget(self.board)

        Clock.schedule_interval(self._update_score, 0.5)
        return root

    def _on_restart(self, button):
        self.board.restart()

    def _update_score(self, dt):
        self.score_label.text = (
            f'Пар: {self.board.score} из {self.board.total_pairs}'
        )


if __name__ == '__main__':
    MahjongApp().run()
