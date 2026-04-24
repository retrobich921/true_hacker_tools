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
_VK_RETURN  = 0x0D
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
    """Умная печать через единый SendInput для гарантии порядка"""
    inputs = (INPUT * 2)()
    inputs[0].type = INPUT_KEYBOARD
    inputs[1].type = INPUT_KEYBOARD
    
    if char == '\n':
        inputs[0].ki.wVk = _VK_RETURN
        inputs[0].ki.wScan = 0x1C
        inputs[0].ki.dwFlags = 0
        inputs[1].ki.wVk = _VK_RETURN
        inputs[1].ki.wScan = 0x1C
        inputs[1].ki.dwFlags = _KEYEVENTF_KEYUP
    elif char == '\t':
        inputs[0].ki.wVk = _VK_TAB
        inputs[0].ki.wScan = 0x0F
        inputs[0].ki.dwFlags = 0
        inputs[1].ki.wVk = _VK_TAB
        inputs[1].ki.wScan = 0x0F
        inputs[1].ki.dwFlags = _KEYEVENTF_KEYUP
    else:
        inputs[0].ki.wVk = 0
        inputs[0].ki.wScan = ord(char)
        inputs[0].ki.dwFlags = KEYEVENTF_UNICODE
        inputs[1].ki.wVk = 0
        inputs[1].ki.wScan = ord(char)
        inputs[1].ki.dwFlags = KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP
        
    _user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

# --- State для Hacker Typer ---
_full_text: str = ""
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

def force_exit_hacker_mode():
    global _hacker_mode_active, _current_char_index
    if not _hacker_mode_active:
        return
    logger.info("Нажат Ctrl+F9, отключаем Hacker Mode!")
    if _current_char_index == len(_full_text):
        _user32.keybd_event(0x08, 0, 0, 0)
        _user32.keybd_event(0x08, 0, _KEYEVENTF_KEYUP, 0)
    threading.Thread(target=stop_hacker_mode, daemon=True).start()

def start_hacker_mode():
    """Включает перехват кнопок для непрерывной печати ВСЕГО кода"""
    global _hacker_hooks, _hacker_mode_active
    if _hacker_mode_active:
        return
    _hacker_mode_active = True
    
    # Перехватываем буквы, цифры, символы, пробел
    # (Enter специально убран, чтобы мы могли сами эмулировать его нажатие без блокировки)
    keys_to_intercept = list("abcdefghijklmnopqrstuvwxyz0123456789-=[]\\;',./`") + ['space']
    for k in keys_to_intercept:
        hook = keyboard.on_press_key(k, _on_hacker_key_pressed, suppress=True)
        _hacker_hooks.append(hook)
        
    logger.info("Full Hacker Mode ВКЛЮЧЕН. Стучи по клавиатуре без остановки! (Ctrl+F9 для выхода)")

def stop_hacker_mode():
    """Выключает перехват, клавиатура возвращается в норму"""
    global _hacker_hooks, _hacker_mode_active
    if not _hacker_mode_active:
        return
    _hacker_mode_active = False
    for hook in _hacker_hooks:
        try:
            keyboard.unhook_key(hook)
        except ValueError:
            pass
    _hacker_hooks.clear()
    logger.info("Hacker Mode ВЫКЛЮЧЕН. Код полностью вставлен.")

def prepare_line_by_line(text: str) -> None:
    """Подготавливает ВЕСЬ текст целиком для Hacker Mode"""
    global _full_text, _current_char_index
    if not text:
        return
    with _lines_lock:
        text = text.replace('\r', '')
        raw_lines = text.split('\n')
        processed_lines = []
        for line in raw_lines:
            spaces = len(line) - len(line.lstrip(' '))
            if spaces > 0:
                tabs = spaces // 4
                remainder = spaces % 4
                line = '\t' * tabs + ' ' * remainder + line.lstrip(' ')
            processed_lines.append(line)
        
        # Склеиваем всё обратно с переносами строк
        _full_text = '\n'.join(processed_lines)
        _current_char_index = 0
        
        if _full_text:
            logger.info(f"Весь ответ готов (символов: {len(_full_text)}).")
            # Активируем Hacker Mode
            start_hacker_mode()

def _on_hacker_key_pressed(event):
    """Callback: вызывается когда ты бьешь по клавиатуре"""
    if event.event_type != keyboard.KEY_DOWN:
        return
        
    global _current_char_index
    
    with _lines_lock:
        if _current_char_index < len(_full_text):
            # Печатаем НАСТОЯЩИЙ символ (включая пробелы, \n и \t)
            char = _full_text[_current_char_index]
            _current_char_index += 1
            _type_char(char)
            
            # Если код только что закончился
            if _current_char_index == len(_full_text):
                _type_char('\\') # Ставим слеш в САМОМ конце
                logger.info("Код полностью напечатан! Жми Ctrl+F9 для удаления \\ и выхода.")
        else:
            logger.debug(f"Нажата клавиша {event.name}, ждем Ctrl+F9.")
