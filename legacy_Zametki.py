import tkinter as tk
from tkinter import ttk
from datetime import datetime
import json
import os
import ctypes

DATA_FILE = "reminders_data.json"

THEMES = {
    "dark": {
        "bg_main": "#121214",
        "bg_card": "#1E1E22",
        "bg_entry": "#252529",
        "fg_main": "#FFFFFF",
        "fg_sub": "#A0A0A5",
        "fg_hint": "#8A8A90",
        "fg_done": "#606065",
        "accent": "#0866FF"
    },
    "light": {
        "bg_main": "#F0F2F5",
        "bg_card": "#FFFFFF",
        "bg_entry": "#E4E6EB",
        "fg_main": "#050505",
        "fg_sub": "#65676B",
        "fg_hint": "#8D949E",
        "fg_done": "#8C8D91",
        "accent": "#0866FF"
    }
}


def set_window_titlebar_color(hwnd, is_dark):
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1 if is_dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings_data, colors, on_save_callback):
        super().__init__(parent)
        self.title("Настройки")
        self.geometry("340x300")
        self.configure(bg=colors["bg_card"])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.settings_data = settings_data
        self.on_save_callback = on_save_callback
        self.colors = colors

        self.update_idletasks()
        set_window_titlebar_color(self.winfo_id(), parent.settings["theme"] == "dark")

        lbl_title = tk.Label(
            self, text="Настройки", bg=colors["bg_card"], fg=colors["fg_main"], font=("Segoe UI", 14, "bold")
        )
        lbl_title.pack(anchor="w", padx=20, pady=(15, 10))

        lbl_action = tk.Label(
            self, text="При отмечивании главной галочки:", bg=colors["bg_card"], fg=colors["fg_main"],
            font=("Segoe UI", 10, "bold")
        )
        lbl_action.pack(anchor="w", padx=20, pady=(10, 2))

        self.action_var = tk.StringVar(value=self.settings_data["main_check_action"])

        rb1 = tk.Radiobutton(
            self, text="Сделать серой и перенести вниз", variable=self.action_var, value="grey_and_down",
            bg=colors["bg_card"], fg=colors["fg_main"], selectcolor=colors["bg_entry"],
            activebackground=colors["bg_card"], activeforeground=colors["fg_main"], font=("Segoe UI", 9)
        )
        rb1.pack(anchor="w", padx=25, pady=2)

        rb2 = tk.Radiobutton(
            self, text="Удалить заметку", variable=self.action_var, value="delete",
            bg=colors["bg_card"], fg=colors["fg_main"], selectcolor=colors["bg_entry"],
            activebackground=colors["bg_card"], activeforeground=colors["fg_main"], font=("Segoe UI", 9)
        )
        rb2.pack(anchor="w", padx=25, pady=2)

        self.time_var = tk.BooleanVar(value=self.settings_data["show_creation_time"])

        cb_time = tk.Checkbutton(
            self, text="Показывать время создания заметок", variable=self.time_var,
            bg=colors["bg_card"], fg=colors["fg_main"], selectcolor=colors["bg_entry"],
            activebackground=colors["bg_card"], activeforeground=colors["fg_main"], font=("Segoe UI", 10, "bold")
        )
        cb_time.pack(anchor="w", padx=20, pady=(15, 5))

        btn_save = tk.Button(
            self, text="Сохранить (Enter)", bg=colors["accent"], fg="white",
            font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=self.save_settings
        )
        btn_save.pack(fill="x", padx=20, pady=(20, 10), ipady=4)
        self.bind("<Return>", lambda e: self.save_settings())

    def save_settings(self):
        self.settings_data["main_check_action"] = self.action_var.get()
        self.settings_data["show_creation_time"] = self.time_var.get()
        self.on_save_callback()
        self.destroy()


class ReminderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Напоминания")
        self.geometry("900x750")
        self.minsize(800, 600)

        self.settings = {
            "main_check_action": "grey_and_down",
            "show_creation_time": True,
            "theme": "dark"
        }

        self.colors = THEMES[self.settings["theme"]]
        self.configure(bg=self.colors["bg_main"])

        self.cards_registry = []
        self.history_registry = []
        self.task_entries = []

        # --- Шапка приложения ---
        self.header_frame = tk.Frame(self, bg=self.colors["bg_main"], bd=0, highlightthickness=0)
        self.header_frame.pack(fill="x", padx=20, pady=(15, 10))

        self.lbl_app_title = tk.Label(
            self.header_frame, text="Все напоминания", bg=self.colors["bg_main"], fg=self.colors["fg_main"],
            font=("Segoe UI", 16, "bold"), bd=0
        )
        self.lbl_app_title.pack(side="left")

        self.btn_settings = tk.Button(
            self.header_frame, text="⚙", bg=self.colors["bg_main"], fg=self.colors["fg_sub"],
            activebackground=self.colors["bg_main"], activeforeground=self.colors["fg_main"],
            bd=0, font=("Segoe UI", 14), cursor="hand2", command=self.open_settings
        )
        self.btn_settings.pack(side="right", padx=(8, 0))

        self.btn_theme = tk.Button(
            self.header_frame, text="🌙" if self.settings["theme"] == "dark" else "☀️",
            bg=self.colors["bg_main"], fg=self.colors["fg_sub"],
            activebackground=self.colors["bg_main"], activeforeground=self.colors["fg_main"],
            bd=0, font=("Segoe UI", 13), cursor="hand2", command=self.toggle_theme
        )
        self.btn_theme.pack(side="right")

        # --- Главный контейнер ---
        self.main_container = tk.Frame(self, bg=self.colors["bg_main"], bd=0, highlightthickness=0)
        self.main_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.left_frame = tk.Frame(self.main_container, bg=self.colors["bg_main"], bd=0, highlightthickness=0)
        self.left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.canvas_left = tk.Canvas(self.left_frame, bg=self.colors["bg_main"], bd=0, highlightthickness=0)
        self.scrollable_left = tk.Frame(self.canvas_left, bg=self.colors["bg_main"], bd=0, highlightthickness=0)
        self.scrollable_left.bind("<Configure>",
                                  lambda e: self.canvas_left.configure(scrollregion=self.canvas_left.bbox("all")))
        self.win_id_left = self.canvas_left.create_window((0, 0), window=self.scrollable_left, anchor="nw")
        self.canvas_left.bind('<Configure>', lambda e: self.canvas_left.itemconfig(self.win_id_left, width=e.width))
        self.canvas_left.pack(side="left", fill="both", expand=True)

        self.right_frame = tk.Frame(self.main_container, bg=self.colors["bg_main"], width=350, bd=0,
                                    highlightthickness=0)
        self.right_frame.pack(side="right", fill="both", expand=False)
        self.right_frame.pack_propagate(False)

        # 1. Форма ввода
        self.input_card = tk.Frame(self.right_frame, bg=self.colors["bg_card"], padx=10, pady=10, bd=0,
                                   highlightthickness=0)
        self.input_card.pack(fill="x", pady=(0, 10))

        self.placeholder_text = "Название группы (например, Завтра)"
        self.title_entry = tk.Entry(
            self.input_card, bg=self.colors["bg_entry"], fg=self.colors["fg_hint"],
            insertbackground=self.colors["fg_main"], bd=0, highlightthickness=0, font=("Segoe UI", 10, "bold")
        )
        self._reset_title_entry()
        self.title_entry.bind("<FocusIn>", lambda e: self._clear_placeholder(self.title_entry))
        self.title_entry.bind("<FocusOut>", lambda e: self._restore_placeholder(self.title_entry))
        self.title_entry.bind("<Return>", lambda e: self._focus_first_or_create())
        self.title_entry.bind("<Down>", lambda e: self._navigate_from_title("down"))
        self.title_entry.bind("<Left>", lambda e: self._navigate_horizontal(self.title_entry, "left"))
        self.title_entry.bind("<Right>", lambda e: self._navigate_horizontal(self.title_entry, "right"))
        self.title_entry.bind("<Control-v>", self._paste_text)
        self.title_entry.bind("<Control-V>", self._paste_text)
        self.title_entry.pack(fill="x", pady=(0, 8), ipady=4)

        self.items_container = tk.Frame(self.input_card, bg=self.colors["bg_card"], bd=0, highlightthickness=0)
        self.items_container.pack(fill="x", pady=(0, 8))

        self.input_items_canvas = tk.Canvas(self.items_container, bg=self.colors["bg_card"], bd=0, highlightthickness=0,
                                            height=180)
        self.input_items_frame = tk.Frame(self.input_items_canvas, bg=self.colors["bg_card"], bd=0,
                                          highlightthickness=0)
        self.input_items_frame.bind("<Configure>", lambda e: self.input_items_canvas.configure(
            scrollregion=self.input_items_canvas.bbox("all")))
        self.items_win_id = self.input_items_canvas.create_window((0, 0), window=self.input_items_frame, anchor="nw")
        self.input_items_canvas.bind('<Configure>',
                                     lambda e: self.input_items_canvas.itemconfig(self.items_win_id, width=e.width))
        self.input_items_canvas.pack(side="left", fill="both", expand=True)

        self.add_btn = tk.Button(
            self.input_card, text="+ Добавить заметку", bg=self.colors["accent"], fg="white",
            font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=self.add_new_card
        )
        self.add_btn.pack(fill="x", ipady=5)

        self.add_task_input_field()

        # 2. История
        self.history_card = tk.Frame(self.right_frame, bg=self.colors["bg_card"], padx=10, pady=10, bd=0,
                                     highlightthickness=0)
        self.history_card.pack(fill="both", expand=True)

        self.hist_header_frame = tk.Frame(self.history_card, bg=self.colors["bg_card"], bd=0, highlightthickness=0)
        self.hist_header_frame.pack(fill="x", pady=(0, 5))

        self.lbl_history_title = tk.Label(
            self.hist_header_frame, text="История заметок (до 50)", bg=self.colors["bg_card"],
            fg=self.colors["fg_sub"], font=("Segoe UI", 10, "bold"), bd=0
        )
        self.lbl_history_title.pack(side="left")

        self.btn_clear_hist = tk.Button(
            self.hist_header_frame, text="Очистить историю", bg=self.colors["bg_card"], fg=self.colors["fg_sub"],
            activebackground=self.colors["bg_card"], activeforeground=self.colors["accent"],
            bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2", command=self.clear_history
        )
        self.btn_clear_hist.pack(side="right")

        self.hist_container = tk.Frame(self.history_card, bg=self.colors["bg_card"], bd=0, highlightthickness=0)
        self.hist_container.pack(fill="both", expand=True)

        self.canvas_hist = tk.Canvas(self.hist_container, bg=self.colors["bg_card"], bd=0, highlightthickness=0)
        self.scrollable_hist = tk.Frame(self.canvas_hist, bg=self.colors["bg_card"], bd=0, highlightthickness=0)
        self.scrollable_hist.bind("<Configure>",
                                  lambda e: self.canvas_hist.configure(scrollregion=self.canvas_hist.bbox("all")))
        self.win_id_hist = self.canvas_hist.create_window((0, 0), window=self.scrollable_hist, anchor="nw")
        self.canvas_hist.bind('<Configure>', lambda e: self.canvas_hist.itemconfig(self.win_id_hist, width=e.width))
        self.canvas_hist.pack(side="left", fill="both", expand=True)

        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.update_idletasks()
        set_window_titlebar_color(self.winfo_id(), self.settings["theme"] == "dark")
        self.load_data()

    def _paste_text(self, event):
        try:
            text = self.clipboard_get()
            widget = self.focus_get()
            if isinstance(widget, tk.Entry):
                widget.insert(tk.INSERT, text)
        except Exception:
            pass
        return "break"

    def clear_history(self):
        self.history_registry.clear()
        self.render_history_ui()
        self.save_data()

    def toggle_theme(self):
        self.settings["theme"] = "light" if self.settings["theme"] == "dark" else "dark"
        self.colors = THEMES[self.settings["theme"]]
        self.btn_theme.config(text="🌙" if self.settings["theme"] == "dark" else "☀️")

        set_window_titlebar_color(self.winfo_id(), self.settings["theme"] == "dark")
        self.apply_theme()
        self.save_data()

    def apply_theme(self):
        c = self.colors
        self.configure(bg=c["bg_main"])
        self.header_frame.config(bg=c["bg_main"])
        self.lbl_app_title.config(bg=c["bg_main"], fg=c["fg_main"])
        self.btn_theme.config(bg=c["bg_main"], fg=c["fg_sub"], activebackground=c["bg_main"])
        self.btn_settings.config(bg=c["bg_main"], fg=c["fg_sub"], activebackground=c["bg_main"])

        self.main_container.config(bg=c["bg_main"])
        self.left_frame.config(bg=c["bg_main"])
        self.canvas_left.config(bg=c["bg_main"])
        self.scrollable_left.config(bg=c["bg_main"])

        self.right_frame.config(bg=c["bg_main"])
        self.input_card.config(bg=c["bg_card"])
        is_placeholder = (self.title_entry.get() == self.placeholder_text)
        self.title_entry.config(bg=c["bg_entry"], fg=c["fg_main"] if not is_placeholder else c["fg_hint"],
                                insertbackground=c["fg_main"])
        self.items_container.config(bg=c["bg_card"])
        self.input_items_canvas.config(bg=c["bg_card"])
        self.input_items_frame.config(bg=c["bg_card"])
        self.add_btn.config(bg=c["accent"])

        for row_frame, entry in self.task_entries:
            row_frame.config(bg=c["bg_card"])
            entry.config(bg=c["bg_entry"], fg=c["fg_main"], insertbackground=c["fg_main"])
            for child in row_frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.config(bg=c["bg_card"], fg=c["fg_sub"])

        self.history_card.config(bg=c["bg_card"])
        self.hist_header_frame.config(bg=c["bg_card"])
        self.lbl_history_title.config(bg=c["bg_card"], fg=c["fg_sub"])
        self.btn_clear_hist.config(bg=c["bg_card"], fg=c["fg_sub"], activebackground=c["bg_card"],
                                   activeforeground=c["accent"])
        self.hist_container.config(bg=c["bg_card"])
        self.canvas_hist.config(bg=c["bg_card"])
        self.scrollable_hist.config(bg=c["bg_card"])

        self.refresh_ui()

    def refresh_ui(self):
        cards_to_render = []
        for card in self.cards_registry:
            cards_to_render.append({
                "title": card["title"],
                "time": card["time"],
                "completed": card["card_state"]["completed"],
                "tasks": [{"text": text, "done": st["done"]} for text, st in card["tasks"]]
            })

        for widget in self.scrollable_left.winfo_children():
            widget.destroy()
        self.cards_registry.clear()

        for card_data in cards_to_render:
            self.create_card(card_data["title"], card_data["tasks"], card_data.get("time"),
                             card_data.get("completed", False))

        self.render_history_ui()

    def _reset_title_entry(self):
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, self.placeholder_text)
        self.title_entry.config(fg=self.colors["fg_hint"])

    def _clear_placeholder(self, entry):
        current_text = entry.get()
        if current_text.startswith(self.placeholder_text):
            user_input = current_text[len(self.placeholder_text):]
            entry.delete(0, tk.END)
            entry.insert(0, user_input)
            entry.config(fg=self.colors["fg_main"])
        elif current_text == "":
            entry.config(fg=self.colors["fg_main"])

    def _restore_placeholder(self, entry):
        if not entry.get().strip():
            self._reset_title_entry()

    def _focus_first_or_create(self):
        if self.task_entries:
            self._focus_and_scroll(self.task_entries[0][1], self.task_entries[0][0])
        else:
            self.add_task_input_field()

    def _focus_and_scroll(self, widget, row_frame=None):
        widget.focus_set()
        if row_frame:
            self.update_idletasks()
            row_y = row_frame.winfo_y()
            row_height = row_frame.winfo_height()
            canvas_height = self.input_items_canvas.winfo_height()
            scroll_region = self.input_items_canvas.bbox("all")
            if scroll_region:
                total_height = scroll_region[3]
                if total_height > canvas_height:
                    top_vis = self.input_items_canvas.canvasy(0)
                    bottom_vis = top_vis + canvas_height
                    if row_y < top_vis:
                        self.input_items_canvas.yview_moveto(row_y / total_height)
                    elif (row_y + row_height) > bottom_vis:
                        self.input_items_canvas.yview_moveto((row_y + row_height - canvas_height) / total_height)

    def _navigate_from_title(self, direction):
        if direction == "down" and self.task_entries:
            self._focus_and_scroll(self.task_entries[0][1], self.task_entries[0][0])
        return "break"

    def _navigate_horizontal(self, current_widget, direction):
        widgets = [self.title_entry] + [e for _, e in self.task_entries]
        if current_widget not in widgets:
            return

        idx = widgets.index(current_widget)
        cursor_pos = current_widget.index(tk.INSERT)
        text_len = len(current_widget.get())

        if direction == "left" and cursor_pos == 0:
            if idx > 0:
                prev_widget = widgets[idx - 1]
                prev_widget.focus_set()
                prev_widget.icursor(tk.END)
                self._ensure_visible_if_task(prev_widget)
                return "break"
        elif direction == "right" and cursor_pos == text_len:
            if idx < len(widgets) - 1:
                next_widget = widgets[idx + 1]
                next_widget.focus_set()
                next_widget.icursor(0)
                self._ensure_visible_if_task(next_widget)
                return "break"

    def _ensure_visible_if_task(self, widget):
        for row_frame, entry in self.task_entries:
            if entry == widget:
                self._focus_and_scroll(entry, row_frame)
                break

    def _navigate_entry_by_widget(self, current_entry, direction):
        for idx, (row_frame, entry) in enumerate(self.task_entries):
            if entry == current_entry:
                if direction == "up":
                    if idx == 0:
                        self.title_entry.focus_set()
                        self.input_items_canvas.yview_moveto(0.0)
                    else:
                        prev_row, prev_entry = self.task_entries[idx - 1]
                        self._focus_and_scroll(prev_entry, prev_row)
                elif direction == "down":
                    if idx < len(self.task_entries) - 1:
                        next_row, next_entry = self.task_entries[idx + 1]
                        self._focus_and_scroll(next_entry, next_row)
                break
        return "break"

    def _on_enter_press(self, current_entry):
        pos = current_entry.index(tk.INSERT)
        full_text = current_entry.get()

        text_before = full_text[:pos]
        text_after = full_text[pos:]

        current_entry.delete(0, tk.END)
        current_entry.insert(0, text_before)

        self.add_task_input_field(current_entry=current_entry, text_value=text_after)
        return "break"

    def add_task_input_field(self, current_entry=None, text_value=""):
        target_idx = len(self.task_entries)
        if current_entry is not None:
            for idx, (row_frame, entry) in enumerate(self.task_entries):
                if entry == current_entry:
                    target_idx = idx + 1
                    break

        row_frame = tk.Frame(self.input_items_frame, bg=self.colors["bg_card"], bd=0, highlightthickness=0)

        icon_lbl = tk.Label(row_frame, text="◯", fg=self.colors["fg_sub"], bg=self.colors["bg_card"],
                            font=("Segoe UI", 10), bd=0)
        icon_lbl.pack(side="left", padx=(0, 5))

        entry = tk.Entry(
            row_frame, bg=self.colors["bg_entry"], fg=self.colors["fg_main"],
            insertbackground=self.colors["fg_main"], bd=0, highlightthickness=0, font=("Segoe UI", 10)
        )
        if text_value:
            entry.insert(0, text_value)
        entry.pack(side="left", fill="x", expand=True, ipady=3)

        entry.bind("<Return>", lambda e, curr=entry: self._on_enter_press(curr))
        entry.bind("<BackSpace>",
                   lambda e, curr_row=row_frame, curr_entry=entry: self._on_backspace(e, curr_row, curr_entry))
        entry.bind("<Up>", lambda e, curr_entry=entry: self._navigate_entry_by_widget(curr_entry, "up"))
        entry.bind("<Down>", lambda e, curr_entry=entry: self._navigate_entry_by_widget(curr_entry, "down"))
        entry.bind("<Left>", lambda e, curr_widget=entry: self._navigate_horizontal(curr_widget, "left"))
        entry.bind("<Right>", lambda e, curr_widget=entry: self._navigate_horizontal(curr_widget, "right"))
        entry.bind("<Control-v>", self._paste_text)
        entry.bind("<Control-V>", self._paste_text)

        if target_idx < len(self.task_entries):
            existing_row = self.task_entries[target_idx][0]
            row_frame.pack(fill="x", pady=2, expand=True, before=existing_row)
            self.task_entries.insert(target_idx, (row_frame, entry))
        else:
            row_frame.pack(fill="x", pady=2, expand=True)
            self.task_entries.append((row_frame, entry))

        self._focus_and_scroll(entry, row_frame)
        if text_value:
            entry.icursor(0)

    def _on_backspace(self, event, row_frame, entry):
        if len(entry.get()) == 0:
            target_tuple = (row_frame, entry)
            if target_tuple in self.task_entries:
                idx = self.task_entries.index(target_tuple)
                if len(self.task_entries) > 1:
                    row_frame.destroy()
                    self.task_entries.remove(target_tuple)
                    prev_idx = max(0, idx - 1)
                    if self.task_entries:
                        prev_row, prev_entry = self.task_entries[prev_idx]
                        self._focus_and_scroll(prev_entry, prev_row)
                        prev_entry.icursor(tk.END)
                    else:
                        self.title_entry.focus_set()
                        self.title_entry.icursor(tk.END)
                    self.update_idletasks()
                    return "break"

    def open_settings(self):
        SettingsDialog(self, self.settings, self.colors, self.apply_settings)

    def apply_settings(self):
        self.apply_theme()
        self.save_data()

    def _on_mousewheel(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        if widget:
            parent = widget
            while parent and not isinstance(parent, tk.Canvas):
                parent = parent.master
            if parent in (self.canvas_left, self.input_items_canvas, self.canvas_hist):
                parent.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def add_new_card(self):
        title_text = self.title_entry.get().strip()
        if not title_text or title_text == self.placeholder_text:
            title_text = "Заметка"

        tasks = []
        for _, entry in self.task_entries:
            val = entry.get().strip()
            if val:
                tasks.append({"text": val, "done": False})

        new_hist_item = {"title": title_text, "tasks": tasks}

        matching_idx = -1
        for idx, item in enumerate(self.history_registry):
            if item["title"] == title_text and [t["text"] for t in item["tasks"]] == [t["text"] for t in tasks]:
                matching_idx = idx
                break

        if matching_idx != -1:
            item = self.history_registry.pop(matching_idx)
            self.history_registry.insert(0, item)
        else:
            self.history_registry.insert(0, new_hist_item)

        if len(self.history_registry) > 50:
            self.history_registry = self.history_registry[:50]

        self.create_card(title_text, tasks)
        self.render_history_ui()

        self._reset_title_entry()
        for widget in self.input_items_frame.winfo_children():
            widget.destroy()
        self.task_entries.clear()
        self.add_task_input_field()

        self.update_idletasks()
        self.input_items_canvas.yview_moveto(0.0)
        self.save_data()

    def create_card(self, title_text, tasks, creation_time=None, completed=False):
        if not creation_time:
            creation_time = datetime.now().strftime("%H:%M")

        c = self.colors
        card = tk.Frame(self.scrollable_left, bg=c["bg_card"], padx=15, pady=12, bd=0, highlightthickness=0)
        card.pack(fill="x", pady=8, expand=True)

        header_frame = tk.Frame(card, bg=c["bg_card"], bd=0, highlightthickness=0)
        header_frame.pack(fill="x", pady=(0, 8))

        main_circle = tk.Label(header_frame, text="◯", fg=c["fg_sub"], bg=c["bg_card"], font=("Segoe UI", 12),
                               cursor="hand2", bd=0)
        main_circle.pack(side="left", padx=(0, 8))

        title_lbl = tk.Label(header_frame, text=title_text, fg=c["fg_main"], bg=c["bg_card"],
                             font=("Segoe UI", 11, "bold"), cursor="hand2", bd=0)
        title_lbl.pack(side="left")

        time_lbl = tk.Label(header_frame, text=creation_time, fg=c["fg_sub"], bg=c["bg_card"], font=("Segoe UI", 8),
                            bd=0)
        if self.settings["show_creation_time"]:
            time_lbl.pack(side="left", padx=(8, 0))

        task_toggles = []
        task_states_ptrs = []
        task_data_ptrs = []

        for item_data in tasks:
            text = item_data["text"] if isinstance(item_data, dict) else item_data[0]
            is_done = item_data["done"] if isinstance(item_data, dict) else item_data[1]

            toggle_func, item_state = self.add_task_item(card, text, is_done)
            task_toggles.append(toggle_func)
            task_states_ptrs.append(item_state)
            task_data_ptrs.append((text, item_state))

        card_state = {"completed": completed, "saved_task_states": None}

        card_data = {
            "title": title_text,
            "time": creation_time,
            "card_state": card_state,
            "tasks": task_data_ptrs,
            "card_frame": card
        }

        def delete_card():
            card.destroy()
            if card_data in self.cards_registry:
                self.cards_registry.remove(card_data)
            self.save_data()

        def toggle_card(event=None):
            if self.settings["main_check_action"] == "delete":
                delete_card()
                return

            card_state["completed"] = not card_state["completed"]
            is_done = card_state["completed"]

            if is_done:
                card_state["saved_task_states"] = [st["done"] for st in task_states_ptrs]
                main_circle.config(text="☑", fg=c["fg_done"])
                title_lbl.config(fg=c["fg_done"])
                time_lbl.config(fg=c["fg_done"])
                for toggle_fn in task_toggles:
                    toggle_fn(set_state=True)
                card.pack_forget()
                card.pack(fill="x", pady=8, expand=True, side="bottom")
            else:
                main_circle.config(text="◯", fg=c["fg_sub"])
                title_lbl.config(fg=c["fg_main"])
                time_lbl.config(fg=c["fg_sub"])
                if card_state["saved_task_states"] is not None:
                    for toggle_fn, saved_state in zip(task_toggles, card_state["saved_task_states"]):
                        toggle_fn(set_state=saved_state)
                    card_state["saved_task_states"] = None
                else:
                    for toggle_fn in task_toggles:
                        toggle_fn(set_state=False)
                card.pack_forget()
                card.pack(fill="x", pady=8, expand=True, side="top")
            self.save_data()

        main_circle.bind("<Button-1>", toggle_card)
        title_lbl.bind("<Button-1>", toggle_card)

        if completed:
            main_circle.config(text="☑", fg=c["fg_done"])
            title_lbl.config(fg=c["fg_done"])
            time_lbl.config(fg=c["fg_done"])

        self.cards_registry.append(card_data)

    def add_task_item(self, parent_card, text, is_done):
        c = self.colors
        item_frame = tk.Frame(parent_card, bg=c["bg_card"], cursor="hand2", bd=0, highlightthickness=0)
        item_frame.pack(fill="x", pady=4, padx=(20, 0))

        state = {"done": is_done}
        icon = "☑" if state["done"] else "◯"
        color = c["fg_done"] if state["done"] else c["fg_sub"]

        chk_btn = tk.Label(item_frame, text=icon, fg=color, bg=c["bg_card"], font=("Segoe UI", 11), cursor="hand2",
                           bd=0)
        chk_btn.pack(side="left", padx=(0, 8))

        lbl = tk.Label(
            item_frame, text=text, fg=c["fg_done"] if state["done"] else c["fg_main"],
            bg=c["bg_card"], font=("Segoe UI", 10, "overstrike" if state["done"] else "normal"), cursor="hand2", bd=0
        )
        lbl.pack(side="left", anchor="w")

        def toggle(event=None, set_state=None):
            if set_state is not None:
                state["done"] = set_state
            else:
                state["done"] = not state["done"]

            if state["done"]:
                chk_btn.config(text="☑", fg=c["fg_done"])
                lbl.config(fg=c["fg_done"], font=("Segoe UI", 10, "overstrike"))
            else:
                chk_btn.config(text="◯", fg=c["fg_sub"])
                lbl.config(fg=c["fg_main"], font=("Segoe UI", 10, "normal"))
            self.save_data()

        item_frame.bind("<Button-1>", toggle)
        chk_btn.bind("<Button-1>", toggle)
        lbl.bind("<Button-1>", toggle)

        return toggle, state

    def render_history_ui(self):
        c = self.colors
        for widget in self.scrollable_hist.winfo_children():
            widget.destroy()

        for hist_item in self.history_registry:
            h_card = tk.Frame(self.scrollable_hist, bg=c["bg_entry"], padx=10, pady=8, cursor="hand2", bd=0,
                              highlightthickness=0)
            h_card.pack(fill="x", pady=4, expand=True)

            t_lbl = tk.Label(h_card, text=hist_item["title"], fg=c["fg_main"], bg=c["bg_entry"],
                             font=("Segoe UI", 9, "bold"), anchor="w", bd=0)
            t_lbl.pack(fill="x")

            tasks = hist_item["tasks"]
            if tasks:
                first_three = [t["text"] for t in tasks[:3]]
                inline_text = "・" + "・".join(first_three)

                remaining = len(tasks) - 3
                if remaining > 0:
                    inline_text += f" ...и еще {remaining} пунктов"

                p_lbl = tk.Label(h_card, text=inline_text, fg=c["fg_sub"], bg=c["bg_entry"], font=("Segoe UI", 8),
                                 anchor="w", bd=0)
                p_lbl.pack(fill="x", pady=(2, 0))
            else:
                s_lbl = tk.Label(h_card, text="Заметка без пунктов", fg=c["fg_hint"], bg=c["bg_entry"],
                                 font=("Segoe UI", 8, "italic"), anchor="w", bd=0)
                s_lbl.pack(fill="x", pady=(2, 0))

            def load_to_input(item=hist_item):
                self._reset_title_entry()
                self.title_entry.delete(0, tk.END)
                self.title_entry.insert(0, item["title"])
                self.title_entry.config(fg=c["fg_main"])

                for widget in self.input_items_frame.winfo_children():
                    widget.destroy()
                self.task_entries.clear()

                if item["tasks"]:
                    for task in item["tasks"]:
                        self.add_task_input_field(text_value=task["text"])
                else:
                    self.add_task_input_field()

            h_card.bind("<Button-1>", lambda e, item=hist_item: load_to_input(item))
            for child in h_card.winfo_children():
                child.bind("<Button-1>", lambda e, item=hist_item: load_to_input(item))

    def save_data(self):
        data = {
            "settings": self.settings,
            "cards": [],
            "history": self.history_registry
        }
        for card in self.cards_registry:
            card_info = {
                "title": card["title"],
                "time": card["time"],
                "completed": card["card_state"]["completed"],
                "tasks": [{"text": text, "done": st["done"]} for text, st in card["tasks"]]
            }
            data["cards"].append(card_info)

        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            self.render_history_ui()
            return

        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "settings" in data:
                self.settings.update(data["settings"])
                self.colors = THEMES[self.settings["theme"]]
                self.btn_theme.config(text="🌙" if self.settings["theme"] == "dark" else "☀️")

            if "history" in data:
                self.history_registry = data["history"][:50]

            if "cards" in data:
                for card_info in data["cards"]:
                    self.create_card(
                        title_text=card_info["title"],
                        tasks=card_info["tasks"],
                        creation_time=card_info.get("time"),
                        completed=card_info.get("completed", False)
                    )

            self.apply_theme()
            set_window_titlebar_color(self.winfo_id(), self.settings["theme"] == "dark")
        except Exception as e:
            print(f"Ошибка загрузки: {e}")

    def on_close(self):
        self.save_data()
        self.destroy()


if __name__ == "__main__":
    app = ReminderApp()
    app.mainloop()