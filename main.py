#!/usr/bin/env python3
"""Entry point for the pixel art editor.

Run with the project virtualenv active:

    . .venv/bin/activate
    python main.py
"""

from editor.app import Editor, HELP_TEXT


def main():
    print(HELP_TEXT)
    Editor().run()


if __name__ == "__main__":
    main()
