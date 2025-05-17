#!/bin/bash

# -------------------------------
# Настройки подключения
DB_NAME="test1db"
DB_USER="neegroom"
DB_HOST="localhost"
QUERY_FILE="query.sql"
PREPARE_FILE="prepare.sql"
PGDATA_DIR="/var/lib/postgresql/17/main"
PG_SERVICE_NAME="postgresql"
# -------------------------------

# Временные файлы
PRE_IO="/tmp/io_pre.txt"
POST_IO="/tmp/io_post.txt"
PRE_SYS="/tmp/sys_pre.txt"
POST_SYS="/tmp/sys_post.txt"
PRE_PROC="/tmp/sys_pre_proc.txt"
POST_PROC="/tmp/sys_post_proc.txt"

# Сбор доступных example-директорий
echo "📁 Доступные примеры:"
mapfile -t EXAMPLES < <(find . -maxdepth 1 -type d -name "example*" | sort)
if [ ${#EXAMPLES[@]} -eq 0 ]; then
    echo "❌ Нет директорий вида example*/"
    exit 1
fi

for i in "${!EXAMPLES[@]}"; do
    echo "[$i] ${EXAMPLES[$i]}"
done

# Запрос выбора пользователя
read -p "Выберите номер примера: " EX_INDEX
SELECTED_DIR="${EXAMPLES[$EX_INDEX]}"
if [ -z "$SELECTED_DIR" ]; then
    echo "❌ Неверный выбор."
    exit 1
fi

QUERY_FILE="$SELECTED_DIR/query.sql"
PREPARE_FILE="$SELECTED_DIR/prepare.sql"
echo "📂 Выбранный пример: $SELECTED_DIR"
echo "📄 prepare.sql: $PREPARE_FILE"
echo "📄 query.sql:   $QUERY_FILE"
echo

# Временные файлы
PRE_IO="/tmp/io_pre.txt"
POST_IO="/tmp/io_post.txt"
PRE_SYS="/tmp/sys_pre.txt"
POST_SYS="/tmp/sys_post.txt"
PRE_PROC="/tmp/sys_pre_proc.txt"
POST_PROC="/tmp/sys_post_proc.txt"

# Время запуска
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
LOG_DIR="logs"
RESULT_DIR="results"
LOG_FILE="$LOG_DIR/run_$TIMESTAMP.log"
RESULT_FILE="$RESULT_DIR/result_$TIMESTAMP.txt"

# Создание директорий
mkdir -p "$LOG_DIR" "$RESULT_DIR"

# Перенаправление вывода в лог-файл
exec > >(tee -a "$LOG_FILE") 2>&1

# Получаем PID PostgreSQL
PG_PID=$(pidof postgres | awk '{print $1}')
if [ -z "$PG_PID" ]; then
    echo "❌ PostgreSQL не запущен или PID не найден."
    exit 1
fi

# Получение версии PostgreSQL
PG_VERSION=$(psql -U "$DB_USER" -d "$DB_NAME" -tAc "SHOW server_version_num;")
echo "🕒 Запуск теста: $TIMESTAMP"
echo "PostgreSQL version: $PG_VERSION"
echo "PostgreSQL PID: $PG_PID"
echo

# --- ⏱️ Подготовка DDL и данных ---
if [ -f "$PREPARE_FILE" ]; then
    echo "📦 Подготовка данных (выполняется $PREPARE_FILE)..."
    psql -U "$DB_USER" -d "$DB_NAME" -f "$PREPARE_FILE"
    echo "✅ Подготовка завершена."
else
    echo "⚠️ Файл подготовки ($PREPARE_FILE) не найден, пропускаем."
fi
echo

# --- 1. Сбор PostgreSQL-IO статистики ---
echo "📥 Сбор исходной PostgreSQL-статистики..."
if [ "$PG_VERSION" -ge 160000 ]; then
    psql -U "$DB_USER" -d "$DB_NAME" -Atc "
        SELECT obj_type, io_object, io_context,
               sum(reads_direct) as reads_direct,
               sum(writes_direct) as writes_direct
        FROM pg_stat_io
        GROUP BY obj_type, io_object, io_context
        ORDER BY 1,2,3;" > "$PRE_IO"
else
    psql -U "$DB_USER" -d "$DB_NAME" -Atc "
        SELECT relname, heap_blks_read, heap_blks_hit
        FROM pg_statio_user_tables
        ORDER BY 2 DESC;" > "$PRE_IO"
fi

# --- 2. Сбор системной статистики ---
echo "📥 Сбор исходной системной статистики..."
iostat -dx 1 1 > "$PRE_SYS"
grep -E '^rchar|^wchar|^syscr|^syscw' /proc/$PG_PID/io > "$PRE_PROC"

# --- 3. Запуск запроса ---
if [ -f "$QUERY_FILE" ]; then
    echo "🚀 Запуск запроса из $QUERY_FILE..."
    psql -U "$DB_USER" -d "$DB_NAME" -f "$QUERY_FILE" > /dev/null
else
    echo "⚠️ Файл запроса ($QUERY_FILE) не найден. Прерывание."
    exit 1
fi

# --- 4. Сбор статистики после выполнения запроса ---
echo "📤 Сбор финальной PostgreSQL-статистики..."
if [ "$PG_VERSION" -ge 160000 ]; then
    psql -U "$DB_USER" -d "$DB_NAME" -Atc "
        SELECT obj_type, io_object, io_context,
               sum(reads_direct) as reads_direct,
               sum(writes_direct) as writes_direct
        FROM pg_stat_io
        GROUP BY obj_type, io_object, io_context
        ORDER BY 1,2,3;" > "$POST_IO"
else
    psql -U "$DB_USER" -d "$DB_NAME" -Atc "
        SELECT relname, heap_blks_read, heap_blks_hit
        FROM pg_statio_user_tables
        ORDER BY 2 DESC;" > "$POST_IO"
fi

echo "📤 Сбор финальной системной статистики..."
iostat -dx 1 1 > "$POST_SYS"
grep -E '^rchar|^wchar|^syscr|^syscw' /proc/$PG_PID/io > "$POST_PROC"

# --- 5. Анализ PostgreSQL I/O ---
echo
echo "📊 Δ PostgreSQL I/O:" | tee -a "$RESULT_FILE"
if [ "$PG_VERSION" -ge 160000 ]; then
    join -t $'\t' "$PRE_IO" "$POST_IO" | awk -F'\t' '
    {
        obj=$1; io_obj=$2; ctx=$3;
        r1=$4; w1=$5; r2=$6; w2=$7;
        dr=r2 - r1;
        dw=w2 - w1;
        if (dr != 0 || dw != 0) {
            printf "%-10s %-12s %-10s | Δread: %-6d Δwrite: %-6d\n", obj, io_obj, ctx, dr, dw;
        }
    }' | tee -a "$RESULT_FILE"
else
    join -t $'\t' "$PRE_IO" "$POST_IO" | awk -F'\t' '
    {
        rel=$1; r1=$2; h1=$3; r2=$4; h2=$5;
        dr=r2 - r1;
        dh=h2 - h1;
        if (dr != 0 || dh != 0) {
            printf "%-30s | Δdisk read: %-6d Δcache hit: %-6d\n", rel, dr, dh;
        }
    }' | tee -a "$RESULT_FILE"
fi

# --- 6. Анализ системной статистики ---
echo
echo "📊 Δ Системная статистика (/proc/$PG_PID/io):" | tee -a "$RESULT_FILE"
awk '
    FNR==NR { pre[$1]=$2; next }
    {
        delta = $2 - pre[$1];
        printf "%-10s : %d\n", $1, delta;
    }
' "$PRE_PROC" "$POST_PROC" | tee -a "$RESULT_FILE"

echo
echo "📊 Общая диск-нагрузка (iostat):" | tee -a "$RESULT_FILE"
DISK=$(iostat -dx | awk '/^Device:/ {getline; print $1; exit}')
echo "Устройство: $DISK" | tee -a "$RESULT_FILE"
echo
paste <(grep "^$DISK" "$PRE_SYS") <(grep "^$DISK" "$POST_SYS") | awk '
{
    print "Δ iostat поля:"
    printf "r/s:    %.2f -> %.2f\n", $2, $15;
    printf "w/s:    %.2f -> %.2f\n", $3, $16;
    printf "rKB/s:  %.2f -> %.2f\n", $4, $17;
    printf "wKB/s:  %.2f -> %.2f\n", $5, $18;
    printf "await:  %.2f -> %.2f\n", $10, $23;
}' | tee -a "$RESULT_FILE"

echo
echo "✅ Тест завершён. Лог: $LOG_FILE | Результаты: $RESULT_FILE"
