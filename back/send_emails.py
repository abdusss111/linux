#!/usr/bin/env python3
"""
Скрипт для массовой отправки email-сообщений из CSV файла
"""
import csv
import asyncio
import sys
from pathlib import Path

# Добавляем src в PYTHONPATH для импорта модулей
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Загружаем переменные окружения из .env файла перед импортом сервисов
from dotenv import load_dotenv
load_dotenv()

from dapmeet.services.email_service import email_service

TEMPLATE_PATH = Path(__file__).parent / "dapmeet_reminder_email.html"
SUBJECT = "Завершите настройку dapmeet"


def load_email_template(template_path: Path) -> str:
    """Загружает HTML шаблон письма из файла."""
    try:
        return template_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Не найден HTML шаблон письма по пути: {template_path}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Не удалось прочитать HTML шаблон письма: {template_path}"
        ) from exc


def read_emails_from_csv(csv_path: str) -> list[str]:
    """
    Читает email-адреса из CSV файла
    
    Args:
        csv_path: Путь к CSV файлу
        
    Returns:
        Список email-адресов из колонки "Email"
    """
    emails = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Проверяем наличие колонки Email
            if 'Email' not in reader.fieldnames:
                raise ValueError(f"Колонка 'Email' не найдена в CSV файле. Доступные колонки: {reader.fieldnames}")
            
            for row_num, row in enumerate(reader, start=2):  # начинаем с 2, так как первая строка - заголовок
                email = row.get('Email', '').strip()
                
                if email:
                    # Простая валидация email
                    if '@' in email and '.' in email.split('@')[1]:
                        emails.append(email)
                    else:
                        print(f"⚠️  Строка {row_num}: пропущен невалидный email '{email}'")
                else:
                    print(f"⚠️  Строка {row_num}: пустой email, пропущена")
        
        return emails
    
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV файл не найден: {csv_path}")
    except Exception as e:
        raise Exception(f"Ошибка при чтении CSV файла: {str(e)}")


async def send_email_to_address(
    email: str,
    semaphore: asyncio.Semaphore,
    subject: str,
    content: str,
) -> tuple[str, bool]:
    """
    Отправляет email одному адресату с использованием семафора для контроля параллелизма
    
    Args:
        email: Email адрес получателя
        semaphore: Семафор для ограничения параллельных запросов
        
    Returns:
        Кортеж (email, success) где success - True если письмо отправлено успешно
    """
    async with semaphore:
        try:
            success = await email_service.send_simple_email(
                to_email=email,
                subject=subject,
                content=content,
                is_html=True,
            )
            return (email, success)
        except Exception as e:
            print(f"❌ Ошибка при отправке письма на {email}: {str(e)}")
            return (email, False)


async def send_emails_async(
    emails: list[str],
    *,
    subject: str,
    content: str,
    max_concurrent: int = 5,
    delay_between_batches: float = 1.0,
):
    """
    Асинхронно отправляет письма с контролем параллелизма через семафор
    
    Args:
        emails: Список email-адресов
        max_concurrent: Максимальное количество параллельных отправок
        delay_between_batches: Задержка между батчами в секундах
    """
    total = len(emails)
    successful = 0
    failed = 0
    
    print(f"📧 Найдено {total} email-адресов для отправки")
    print(f"⚙️  Максимальное количество параллельных отправок: {max_concurrent}\n")
    
    # Создаем семафор для ограничения параллельных запросов
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Разбиваем на батчи для вывода прогресса
    batch_size = max_concurrent
    total_batches = (total + batch_size - 1) // batch_size
    
    # Создаем все задачи сразу, но семафор ограничит параллельное выполнение
    tasks = [
        asyncio.create_task(
            send_email_to_address(email, semaphore, subject, content)
        )
        for email in emails
    ]
    
    # Обрабатываем результаты по мере завершения задач
    batch_num = 0
    completed = 0
    
    # Используем as_completed для обработки результатов по мере их готовности
    for task in asyncio.as_completed(tasks):
        try:
            email, success = await task
            completed += 1
            
            if success:
                print(f"✅ [{completed}/{total}] {email}: отправлено")
                successful += 1
            else:
                print(f"❌ [{completed}/{total}] {email}: не удалось отправить")
                failed += 1
            
            # Выводим информацию о батче при завершении каждого батча
            if completed % batch_size == 0 or completed == total:
                batch_num = (completed + batch_size - 1) // batch_size
                if completed < total:
                    print(f"📊 Прогресс: батч {batch_num}/{total_batches} завершен ({completed}/{total} писем)")
                    if delay_between_batches > 0:
                        print(f"⏳ Пауза {delay_between_batches} секунд...\n")
                        await asyncio.sleep(delay_between_batches)
        except Exception as e:
            completed += 1
            print(f"❌ [{completed}/{total}] Исключение при обработке: {str(e)}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"📊 Итоги:")
    print(f"✅ Успешно отправлено: {successful}")
    print(f"❌ Ошибок: {failed}")
    print(f"📧 Всего обработано: {total}")
    print(f"{'='*50}")


async def main():
    """
    Главная функция скрипта
    """
    # Определяем путь к CSV файлу
    default_csv = Path("users.csv")
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_csv
    
    print(f"📁 Чтение CSV файла: {csv_path}\n")
    
    try:
        # Читаем email-адреса из CSV
        emails = read_emails_from_csv(str(csv_path))
        
        if not emails:
            print("⚠️  Не найдено ни одного валидного email-адреса в CSV файле")
            return

        # Загружаем HTML шаблон письма
        template = load_email_template(TEMPLATE_PATH)
        
        # Отправляем письма асинхронно
        await send_emails_async(
            emails,
            subject=SUBJECT,
            content=template,
            max_concurrent=5,
            delay_between_batches=1.0,
        )
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(main())

