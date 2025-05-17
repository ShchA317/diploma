#!/bin/bash

VENV_DIR="venv"
REQUIREMENTS="requirements.txt"

if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Создаем виртуальное окружение..."
    python3 -m venv "$VENV_DIR"
    
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при создании venv"
        exit 1
    fi
fi

echo "🚀 Активируем виртуальное окружение..."
source "$VENV_DIR/bin/activate"

if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Не удалось активировать venv"
    exit 1
fi

echo "🔄 Обновляем pip..."
pip3 install --upgrade pip

if [ -f "$REQUIREMENTS" ]; then
    echo "📦 Устанавливаем зависимости из $REQUIREMENTS..."
    pip3 install -r "$REQUIREMENTS"
    
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при установке зависимостей"
        exit 1
    fi
else
    echo "⚠️ Файл $REQUIREMENTS не найден, зависимости не установлены"
fi

echo "🟢 Виртуальное окружение готово к работе"
echo "----------------------------------------"

for file in examples/example*/*.yaml; do
    echo "🔍 Running analyzer on $file"
    python3 analyze_postgres_files.py "$file"
    echo
done

deactivate