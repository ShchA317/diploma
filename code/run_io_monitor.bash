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

# 🔍 Сбор доступных example-директорий (включая подкаталоги examples/)
echo "📁 Доступные примеры:"
mapfile -t EXAMPLES < <(find ./examples -maxdepth 1 -type d -name "example*" | sort)

if [ ${#EXAMPLES[@]} -eq 0 ]; then
    echo "❌ Не найдены директории вида examples/example*/"
    exit 1
fi

# Вывод списка директорий
for i in "${!EXAMPLES[@]}"; do
    echo "[$i] ${EXAMPLES[$i]}"
done

# 🔢 Запрос номера примера
while true; do
    read -p "Введите номер примера [0..$((${#EXAMPLES[@]} - 1))]: " EX_INDEX
    if [[ "$EX_INDEX" =~ ^[0-9]+$ ]] && [ "$EX_INDEX" -ge 0 ] && [ "$EX_INDEX" -lt "${#EXAMPLES[@]}" ]; then
        break
    fi
    echo "❌ Неверный ввод. Попробуйте снова."
done

SELECTED_DIR="${EXAMPLES[$EX_INDEX]}"
echo "✅ Выбранный пример: $SELECTED_DIR"

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
PG_PID=$(pgrep -u postgres -x postgres | head -n 1)
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

collect_pg_io_stats() {
    local OUTPUT_FILE="$1"
    local WHEN="$2"  # "pre" или "post"

    echo "📥 [$WHEN] Сбор статистики PostgreSQL..." 

    if [ "$PG_VERSION" -ge 160000 ]; then
        echo "👉 pg_stat_io:" >> "$OUTPUT_FILE"
        psql -U "$DB_USER" -d "$DB_NAME" -Atc "
            SELECT backend_type || '|' || object || '|' || context AS key,
                   reads,
                   writes
            FROM pg_stat_io
            ORDER BY 1;" >> "$OUTPUT_FILE"

        echo "👉 pg_statio_user_tables:" >> "$OUTPUT_FILE"
        psql -U "$DB_USER" -d "$DB_NAME" -Atc "
            SELECT relname,
                   heap_blks_read,
                   heap_blks_hit
            FROM pg_statio_user_tables
            ORDER BY 1;" >> "$OUTPUT_FILE"
    else
        echo "👉 pg_statio_user_tables:" >> "$OUTPUT_FILE"
        psql -U "$DB_USER" -d "$DB_NAME" -Atc "
            SELECT relname,
                   heap_blks_read,
                   heap_blks_hit
            FROM pg_statio_user_tables
            ORDER BY 1;" >> "$OUTPUT_FILE"
    fi
}

collect_pg_io_stats "$PRE_IO" "pre"

# --- 2. Сбор системной статистики ---
echo "📥 Сбор исходной системной статистики..."
iostat -dx 1 1 > "$PRE_SYS"
sudo grep -E '^rchar|^wchar|^syscr|^syscw' /proc/$PG_PID/io > "$PRE_PROC"

# --- 3. Запуск запроса ---
RPS=5      # Количество запросов в секунду
DURATION=10  # Продолжительность нагрузки в секундах

# ----------------------------
# Функция запроса
# ----------------------------
run_query() {
    psql -U "$DB_USER" -d "$DB_NAME" -f "$QUERY_FILE" > /dev/null 2>&1
}

export -f run_query
export DB_USER DB_NAME QUERY_FILE

echo "Принудительно сбрасываем кэш"
psql -U "$DB_USER" -d "$DB_NAME" -c "DISCARD ALL;"

# ----------------------------
# Основной цикл нагрузки
# ----------------------------
echo "🚀 Запуск нагрузки: $RPS RPS, $DURATION секунд..."
LOAD_START=$(date +%s)
echo "🚀 Запуск запроса из $QUERY_FILE..."
for ((i=1; i<=DURATION; i++)); do
    seq $RPS | parallel -j $RPS run_query
    sleep 1
done

echo "✅ Нагрузка завершена."
LOAD_END=$(date +%s)
echo "⏱️ Время нагрузки: $((LOAD_END - LOAD_START)) секунд"

# --- 4. Сбор статистики после выполнения запроса ---
collect_pg_io_stats "$POST_IO" "post"

echo "📤 Сбор финальной системной статистики..."
iostat -dx 1 1 > "$POST_SYS"
sudo grep -E '^rchar|^wchar|^syscr|^syscw' /proc/$PG_PID/io > "$POST_PROC"

# --- 5. Анализ PostgreSQL I/O ---

echo
echo "📊 Δ PostgreSQL I/O:" | tee -a "$RESULT_FILE"

if [ "$PG_VERSION" -ge 160000 ]; then
    echo "📌 pg_stat_io (Δ чтений/записей):" | tee -a "$RESULT_FILE"
    awk '
    BEGIN { in_pre = 1 }
    /^👉/ {
        if ($0 ~ /post/) in_pre = 0
        next
    }
    in_pre && $0 !~ /^👉/ {
        split($0, a, "|")
        key = a[1] "|" a[2] "|" a[3]
        pre_reads[key] = a[4]
        pre_writes[key] = a[5]
        next
    }
    !in_pre && $0 !~ /^👉/ {
        split($0, a, "|")
        key = a[1] "|" a[2] "|" a[3]
        dr = a[4] - pre_reads[key]
        dw = a[5] - pre_writes[key]
        if (dr != 0 || dw != 0) {
            printf "  %-20s | Δread: %-6d Δwrite: %-6d\n", key, dr, dw
        }
    }' <(sed -n '/pg_stat_io:/,/pg_statio_user_tables:/p' "$PRE_IO") <(sed -n '/pg_stat_io:/,/pg_statio_user_tables:/p' "$POST_IO") | tee -a "$RESULT_FILE"

    echo
    echo "📌 pg_statio_user_tables (Δ disk read/cache hit):" | tee -a "$RESULT_FILE"
    join -t $'\t' \
        <(sed -n '/pg_statio_user_tables:/,$p' "$PRE_IO" | tail -n +2 | sort) \
        <(sed -n '/pg_statio_user_tables:/,$p' "$POST_IO" | tail -n +2 | sort) | \
    awk -F'\t' '
    {
        rel=$1
        r1=$2; h1=$3; r2=$4; h2=$5
        dr = r2 - r1
        dh = h2 - h1
        if (dr != 0 || dh != 0) {
            printf "  %-30s | Δdisk read: %-6d Δcache hit: %-6d\n", rel, dr, dh
        }
    }' | tee -a "$RESULT_FILE"
else
    echo "📌 pg_statio_user_tables (Δ disk read/cache hit):" | tee -a "$RESULT_FILE"
    join -t $'\t' <(cat "$PRE_IO" | sort) <(cat "$POST_IO" | sort) | awk -F'\t' '
    {
        rel=$1
        r1=$2; h1=$3; r2=$4; h2=$5
        dr = r2 - r1
        dh = h2 - h1
        if (dr != 0 || dh != 0) {
            printf "  %-30s | Δdisk read: %-6d Δcache hit: %-6d\n", rel, dr, dh
        }
    }' | tee -a "$RESULT_FILE"
fi

# --- 6. Анализ системной статистики ---
echo
echo "📊 Δ Системная статистика (/proc/$PG_PID/io): (за время теста выполнялось)" | tee -a "$RESULT_FILE"
awk -v duration="$DURATION" '
    function human(x) {
        if (x > 1024*1024) return sprintf("%.2f MB", x / (1024*1024));
        else if (x > 1024) return sprintf("%.2f KB", x / 1024);
        else return sprintf("%d B", x);
    }

    FNR==NR { pre[$1]=$2; next }

    {
        delta = $2 - pre[$1];
        per_sec = delta / duration;

        printf "%-10s : %10d (%s total, %.2f/sec)\n",
               $1, delta, human(delta), per_sec;

        if ($1 == "rchar") rchar = delta;
        if ($1 == "wchar") wchar = delta;
        if ($1 == "syscr") syscr = delta;
        if ($1 == "syscw") syscw = delta;
    }

    END {
        total_bytes = rchar + wchar;
        total_ops = syscr + syscw;
        printf "\n%-20s: %s (%.2f KB/s)\n", "📦 Пропускная способность", human(total_bytes), total_bytes / 1024 / duration;
        printf "%-20s: %d (%.2f IOPS)\n", "⚙️  Всего операций ввода/вывода", total_ops, total_ops / duration;
    }
' "$PRE_PROC" "$POST_PROC" | tee -a "$RESULT_FILE"

echo "--- Содержимое PRE_PROC ---"; cat "$PRE_PROC"
echo "--- Содержимое POST_PROC ---"; cat "$POST_PROC"

echo


DISK=$(iostat -dx | awk '/^Device:/ {getline; print $1; exit}')
if [ -z "$DISK" ]; then
    echo "Не удалось определить диск для анализа iostat!" | tee -a "$RESULT_FILE"
else
    echo "Устройство: $DISK" | tee -a "$RESULT_FILE"
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
