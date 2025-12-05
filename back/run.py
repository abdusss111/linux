# Этот скрипт является точкой входа для запуска веб-приложения.
# Он имитирует команду `CMD` из Dockerfile, запуская uvicorn
# с необходимыми параметрами.
#
# Ключевая особенность - он динамически добавляет директорию 'src'
# в PYTHONPATH, что позволяет uvicorn находить модуль приложения 'dapmeet'.

import subprocess
import sys
import os

def main():
    """
    Запускает uvicorn сервер так, как это определено в Dockerfile.
    """
    # Убедимся, что мы используем python из того же venv, где запущен этот скрипт
    python_executable = sys.executable
    uvicorn_path = os.path.join(os.path.dirname(python_executable), 'uvicorn')

    command = [
        uvicorn_path,
        "dapmeet.cmd.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]

    print(f"Running command: {' '.join(command)}")

    # Добавляем 'src' в PYTHONPATH, чтобы uvicorn нашел модуль dapmeet
    env = os.environ.copy()
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
    env['PYTHONPATH'] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}"
    
    try:
        # Запускаем uvicorn с обновленным окружением.
        # Используем Popen, чтобы не заменять текущий процесс и видеть вывод.
        proc = subprocess.Popen(command, env=env)
        proc.wait()
    except FileNotFoundError:
        print(f"Error: '{command[0]}' not found.")
        print("Please make sure uvicorn is installed in your virtual environment.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
