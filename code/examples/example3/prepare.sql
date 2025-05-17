-- Удаляем таблицу, если существует
DROP TABLE IF EXISTS accounts;

-- Создание таблицы accounts
CREATE TABLE accounts (
  id SERIAL PRIMARY KEY,
  login TEXT UNIQUE,
  password_hash TEXT,
  email TEXT
);

-- Заполнение таблицы 200,000 строк
INSERT INTO accounts (login, password_hash, email)
SELECT
  'user_' || i,
  md5('password_' || i),  -- фейковый хеш пароля
  'user_' || i || '@example.com'
FROM generate_series(1, 200000) AS s(i);
