#!/usr/bin/env python3
"""
Скрипт для исправления сломанных игр в базе данных Играйки.

Запуск на сервере:
    cd /path/to/GameDev/backend
    python3 ../fix_broken_games.py

Что делает:
    - Читает исправленные HTML-файлы из папки fixes/
    - Обновляет html_content в SQLite-базе для каждой сломанной игры
    - Создаёт резервную копию перед изменениями
"""

import os
import shutil
import sqlite3
import sys
from pathlib import Path

# Путь к базе данных (относительно backend/)
DB_PATH = os.environ.get("DATABASE_PATH", "./data/games.db")
FIXES_DIR = Path(__file__).parent / "fixes"

# Список сломанных игр и описание фиксов
BROKEN_GAMES = {
    "3104c28a-499a-4be2-a97c-06ed51ce8720": "Counter Strike — неинициализированные массивы bullets, enemies, bombs, particles, shockwaves",
    "805fa164-681b-48aa-91e1-7e692a43cd4a": "Печатай буквы (refined v1) — синтаксическая ошибка в строке touchRows",
    "08a88179-16cb-467c-9c2a-02acddccfe63": "Котик на крышах — неинициализированные массивы plats, stars, parts, ftxts, bgB, clds + объект cat",
    "525cb456-4e10-4f3c-8adb-ec81ba98dbfe": "Буквопад (оригинал) — неинициализированные массивы letters, particles, bgStars",
    "270e9947-612b-47ae-a38a-82b97a80f1f6": "Котик на крышах (v2) — неинициализированный объект cat.trail + массив bgBuildings",
    "e6290cd8-1846-4bea-b77e-e16ae9d002ec": "Неоновый Бластер — неинициализированные массивы bullets, enemies, particles, powerups, stars",
    "ea7cf76b-89b5-44e6-9224-cf4b5da471ea": "Котик на крышах (v3) — неинициализированные массивы roofs, stars, gems, birds, pts, bgS, clouds",
    "7ba7f3b5-2912-42f3-8767-4031faef32d0": "Волк ловит яйца — неинициализированные массивы eggs, particles, popups",
    "ea983c70-dad7-4506-9bce-728f0d47209c": "Змейка-котик — CanvasRenderingContext2D not defined + неинициализированные массивы cat, dogs, particles, bgStars",
}


def main():
    if not os.path.exists(DB_PATH):
        print(f"ОШИБКА: База данных не найдена: {DB_PATH}")
        print("Запустите скрипт из папки backend/ или укажите DATABASE_PATH")
        sys.exit(1)

    if not FIXES_DIR.exists():
        print(f"ОШИБКА: Папка с фиксами не найдена: {FIXES_DIR}")
        sys.exit(1)

    # Резервная копия
    backup_path = DB_PATH + ".backup"
    print(f"Создаю резервную копию: {backup_path}")
    shutil.copy2(DB_PATH, backup_path)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    fixed = 0
    skipped = 0

    for game_id, description in BROKEN_GAMES.items():
        fix_file = FIXES_DIR / f"{game_id}.html"
        if not fix_file.exists():
            print(f"  ПРОПУСК: {game_id} — файл фикса не найден")
            skipped += 1
            continue

        html = fix_file.read_text(encoding="utf-8")

        # Проверяем, что игра существует
        cursor.execute("SELECT id, prompt FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        if not row:
            print(f"  ПРОПУСК: {game_id} — игра не найдена в БД")
            skipped += 1
            continue

        # Обновляем HTML
        cursor.execute(
            "UPDATE games SET html_content = ? WHERE id = ?",
            (html, game_id),
        )
        print(f"  ИСПРАВЛЕНО: {row[1][:50]}... — {description}")
        fixed += 1

    conn.commit()
    conn.close()

    print(f"\nГотово! Исправлено: {fixed}, пропущено: {skipped}")
    if fixed > 0:
        print(f"Резервная копия БД: {backup_path}")


if __name__ == "__main__":
    main()
