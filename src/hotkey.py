import ctypes
import time
import threading
import pyperclip
from loguru import logger
import keyboard

# Windows VK codes
_VK_CONTROL = 0x11
_VK_C       = 0x43
_VK_TAB     = 0x09
_KEYEVENTF_KEYUP = 0x0002

_user32 = ctypes.windll.user32  # type: ignore[attr-defined]

# --- Windows API для набора символов ---
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1

class KEYBDINPUT(ctypes.Structure):
    _fields_ = (("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)))

class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = (("ki", KEYBDINPUT),
                    ("mi", ctypes.c_byte * 28),
                    ("hi", ctypes.c_byte * 32))
    _anonymous_ = ("i",)
    _fields_ = (("type", ctypes.c_ulong),
                ("i", _I))

def _type_unicode_char(char: str) -> None:
    """Отправляет один символ через Unicode WinAPI"""
    inputs = (INPUT * 2)()
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].ki.wVk = 0
    inputs[0].ki.wScan = ord(char)
    inputs[0].ki.dwFlags = KEYEVENTF_UNICODE
    
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].ki.wVk = 0
    inputs[1].ki.wScan = ord(char)
    inputs[1].ki.dwFlags = KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP
    
    _user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

def _type_char(char: str) -> None:
    """Умная печать: для Tab использует физическую кнопку (чтобы IDE не теряла табы), для остального Unicode"""
    if char == '\t':
        _user32.keybd_event(_VK_TAB, 0, 0, 0)
        _user32.keybd_event(_VK_TAB, 0, _KEYEVENTF_KEYUP, 0)
    else:
        _type_unicode_char(char)

# --- State для Hacker Typer ---
_answer_lines: list[str] = []
_current_line_index: int = 0
_current_char_index: int = 0
_lines_lock = threading.Lock()
_hacker_hooks = []
_hacker_mode_active = False

def _winapi_send_ctrl_c() -> None:
    _user32.keybd_event(_VK_CONTROL, 0, 0, 0)
    _user32.keybd_event(_VK_C, 0, 0, 0)
    time.sleep(0.05)
    _user32.keybd_event(_VK_C, 0, _KEYEVENTF_KEYUP, 0)
    _user32.keybd_event(_VK_CONTROL, 0, _KEYEVENTF_KEYUP, 0)

def get_selected_text() -> str:
    time.sleep(0.2)
    _user32.keybd_event(_VK_CONTROL, 0, _KEYEVENTF_KEYUP, 0)
    _user32.keybd_event(0x10, 0, _KEYEVENTF_KEYUP, 0) # Shift
    logger.debug("Отправка Ctrl+C через WinAPI...")
    old_clipboard = pyperclip.paste()
    pyperclip.copy("")
    _winapi_send_ctrl_c()
    time.sleep(0.1)
    text = pyperclip.paste()
    if text and text != old_clipboard:
        logger.debug(f"Текст из буфера получен, длина: {len(text)} символов.")
    else:
        text = ""
        pyperclip.copy(old_clipboard)
    return text

def start_hacker_mode():
    """Включает перехват кнопок: теперь нажатия будут печатать правильный код"""
    global _hacker_hooks, _hacker_mode_active
    if _hacker_mode_active:
        return
    _hacker_mode_active = True
    
    # Перехватываем только базовые клавиши (буквы, цифры, символы, пробел)
    keys_to_intercept = list("abcdefghijklmnopqrstuvwxyz0123456789-=[]\\;',./` ")
    for k in keys_to_intercept:
        hook = keyboard.on_press_key(k, _on_hacker_key_pressed, suppress=True)
        _hacker_hooks.append(hook)
    logger.info("Hacker Mode ВКЛЮЧЕН. Стучи по клавиатуре!")

def stop_hacker_mode():
    """Выключает перехват, клавиатура возвращается в норму"""
    global _hacker_hooks, _hacker_mode_active
    if not _hacker_mode_active:
        return
    _hacker_mode_active = False
    for hook in _hacker_hooks:
        keyboard.unhook_key(hook)
    _hacker_hooks.clear()
    logger.info("Hacker Mode ВЫКЛЮЧЕН. Сделай Backspace, Enter, затем F8.")

def prepare_line_by_line(text: str) -> None:
    global _answer_lines, _current_line_index, _current_char_index
    if not text:
        return
    with _lines_lock:
        raw_lines = text.split('\n')
        _answer_lines = []
        for line in raw_lines:
            spaces = len(line) - len(line.lstrip(' '))
            if spaces > 0:
                tabs = spaces // 4
                remainder = spaces % 4
                line = '\t' * tabs + ' ' * remainder + line.lstrip(' ')
            _answer_lines.append(line)
        
        _current_line_index = 0
        _current_char_index = 0
        
        if _answer_lines:
            logger.info(f"Ответ готов (строк: {len(_answer_lines)}).")
            # Сразу активируем печать первой строки
            start_hacker_mode()

def _on_hacker_key_pressed(event):
    """Callback: вызывается когда ты бьешь по любой букве/цифре"""
    if event.event_type != keyboard.KEY_DOWN:
        return
        
    global _current_line_index, _current_char_index
    
    with _lines_lock:
        if _current_line_index >= len(_answer_lines):
            return
            
        line = _answer_lines[_current_line_index]
        
        if _current_char_index < len(line):
            # Печатаем НАСТОЯЩИЙ символ из ответа LLM
            char = line[_current_char_index]
            _current_char_index += 1
            _type_char(char)
            
            # Если строка закончилась
            if _current_char_index == len(line):
                _type_char('\\') # Ставим слеш по твоей просьбе
                # Отключаем режим хакера в фоне (чтобы не заблокировать поток клавиатуры)
                threading.Thread(target=stop_hacker_mode, daemon=True).start()

def on_user_paste() -> None:
    """Вызывается по хоткею F8 - заряжает следующую строку"""
    global _current_line_index, _current_char_index
    with _lines_lock:
        if _current_line_index >= len(_answer_lines) - 1:
            logger.info("Это была последняя строка! Код полностью вставлен.")
            return
            
        _current_line_index += 1
        _current_char_index = 0
        logger.info(f"Загружена строка {_current_line_index + 1}/{len(_answer_lines)}.")
        # Снова включаем перехват
        threading.Thread(target=start_hacker_mode, daemon=True).start()
