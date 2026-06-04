"""
Run once to log into YouTube and save session cookies for the headless browser.

Usage:
    python scripts/yt_login.py

A Chrome window will open. Log into your Google/YouTube account, then press
Enter in this terminal. The session will be saved to yt_browser_state.json
and reused by all subsequent headless runs.
"""

import os
from pathlib import Path

STATE_PATH = Path(__file__).parent.parent / "yt_browser_state.json"

from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        channel="chrome",
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    ctx = browser.new_context(locale="pt-BR")
    page = ctx.new_page()
    page.goto("https://www.youtube.com")

    print("\nBrowser aberto. Faça login no YouTube/Google.")
    print("Quando terminar, pressione Enter aqui para salvar os cookies.\n")
    input("Pressione Enter após fazer login...")

    ctx.storage_state(path=str(STATE_PATH))
    print(f"\nCookies salvos em: {STATE_PATH}")
    print("Pode fechar o browser agora.")

    page.close()
    ctx.close()
    browser.close()
