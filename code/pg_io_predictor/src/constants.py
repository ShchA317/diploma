PAGE_SIZE = 8192  # размер страницы в байтах
TOAST_THRESHOLD = 2000  # порог, после которого данные хранятся в TOAST
FILL_FACTOR = 0.85  # fillfactor для таблиц по умолчанию
INDEX_TYPES = ['btree', 'hash', 'gin', 'gist', 'spgist', 'brin']

DEFAULT_FILL_FACTOR = 0.9

# fillfactor по умолчанию для индексов (может варьироваться по типу)
INDEX_FILL_FACTORS = {
    'btree': 0.90,
    'hash': 1.00,
    'gin': 0.80,
    'gist': 0.70,
    'spgist': 0.95,
    'brin': 0.95
}

# Free Space Map (FSM) — используется для отслеживания свободного места на страницах
# FSM примерно занимает 6 байт на каждую страницу
FSM_SIZE = lambda num_pages: int((num_pages * 6 + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE)

# Visibility Map (VM) — используется для ускорения операций vacuum и index-only scan
# VM занимает примерно 1 бит на каждую страницу (8 страниц на байт)
VM_SIZE = lambda num_pages: int(((num_pages + 7) // 8 + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE)
