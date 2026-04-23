# True Hacker Tools

A stealth AI-powered tool designed for seamless, undetectable code generation and insertion into any environment (browser, IDE, terminal). 

## Features

- **Global Hotkey Capture:** Copies selected text (task description, WA/CE errors) from any application using a stealthy `Ctrl+Shift+F9` hotkey (bypasses default system hooks).
- **Context-Aware AI:** Powered by the Gemini API (default: `gemini-2.5-flash`), with built-in LangChain memory to understand follow-ups and error messages.
- **Hacker Typer Mode:** The ultimate stealth feature. Once the AI generates the code, you simply press any key on your keyboard (`a-z`, `0-9`, `Space`), and the script will automatically type the *correct* characters from the AI's response.
- **Bypass Protections:** Uses Windows API (`SendInput` and Unicode injection) to type characters, making it immune to keyboard layout mismatches and avoiding basic copy-paste detection.

## Setup

1. Make sure you have [uv](https://github.com/astral-sh/uv) and Python 3.12+ installed.
2. Clone the repository.
3. Copy `.env.example` to `.env` and insert your Google API Key:
   ```env
   GOOGLE_API_KEY=your_key_here
   ```
4. Install dependencies and start the tool:
   ```bash
   uv run python -m src.main
   ```

## Usage

1. **Capture:** Highlight the text/task you want to solve and press `Ctrl+Shift+F9`.
2. **Hacker Mode:** Wait for the tray notification or console log to say `Hacker Mode ВКЛЮЧЕН`.
3. **Type:** Just spam any alphanumeric keys! The tool will type out the correct code line-by-line. 
4. **Next Line:** At the end of each line, the tool types a `\` and stops. Press `Backspace` to remove it, press `Enter`, then press `F8` to load the next line and re-enable Hacker Mode.

## Disclaimer
This project is for educational purposes and demonstrating low-level WinAPI hooks in Python. Use responsibly.
