# Автоматизирано генериране на проформа фактури и transfer.log (Microinvest)

## Изисквания:
- Python 3.9 или по-нов
- pip (Python package manager)
- На Linux/WSL/Ubuntu: допълнително трябва да се инсталират библиотеки за WeasyPrint:
    sudo apt-get install libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

## Инсталация:
1. Клонирай/копирай всички файлове в една папка.
2. Инсталирай зависимостите:
    pip install -r requirements.txt

## Стартиране:
1. Стартирай приложението:
    python app.py
2. Отвори браузър и посети:
    http://localhost:5000

## Работа с приложението:
1. На началната страница качи Excel (xls/xlsx) или CSV таблица по примера в документацията.
2. Въведи начален номер на проформа (примерно 1001).
3. Натисни "Генерирай документите".
4. Ще се появи страница с:
    - Линкове за сваляне на PDF проформи и PNG изображения за всеки клиент
    - transfer.log файл за импорт в Microinvest
    - Обновена таблица с номера и дата на проформа (за проследяване на плащания)
    - Готов текст за имейл и Viber съобщение (copy/paste)

## Файлове/папки:
- app.py – основният код на приложението
- utils.py – помощни функции (генериране на документи)
- config.yaml – конфиг файл с текстове и шаблони
- templates/ – HTML шаблони (интерфейс, проформа, лог)
- static/ – генерираните документи (PDF/PNG)
- requirements.txt – Python зависимости

## Конфигуриране:
- Промени фирмените и банкови данни, шаблоните за имейл и инструкции в config.yaml.
- Ако имаш специфични инструкции за определени модели/производители, добави ги към секцията `instructions:`.
- При липса на `object.id` или `partner_id` в конфигурацията се използва стойност `0`.

## Често срещани проблеми:
- Ако WeasyPrint не работи, инсталирай системните зависимости, както е описано горе.
- Ако при upload получаваш грешка за липсваща колона – увери се, че таблицата има всички задължителни полета (виж примерната структура).

## Примерен workflow:
1. Качваш таблица, въвеждаш начален номер, генерираш документи.
2. Изпращаш проформа PDF/PNG + копираш имейл/Viber текст към клиента.
3. Импортираш transfer.log в Microinvest.
4. Следиш плащания по обновената таблица с проформа №.

---

**За въпроси или помощ:**
Моля, използвайте GitHub issue tracker или се свържете с екипа по поддръжка на проекта.

---

**Успешна автоматизация!**

