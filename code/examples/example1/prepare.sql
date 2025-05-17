-- Создание таблицы users
DROP TABLE IF EXISTS users;
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email TEXT,
  interests TEXT[],
  profile JSONB
);

-- Заполнение таблицы users 500000 строк
INSERT INTO users (email, interests, profile)
SELECT
  'user' || i || '@example.com',
  ARRAY['music', 'sports', 'tech'][1 + (random() * 2)::int : 3],
  jsonb_build_object(
    'age', 18 + (random() * 50)::int,
    'country', ARRAY['US', 'CA', 'UK', 'DE', 'FR'][(random() * 4)::int + 1]
  )
FROM generate_series(1, 500000) AS s(i);


-- Создание таблицы orders
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  user_id INT,
  amount NUMERIC,
  status TEXT
);

-- Заполнение таблицы orders 1200000 строк
INSERT INTO orders (user_id, amount, status)
SELECT
  (random() * 499999)::int + 1,
  round((random() * 1000)::numeric, 2),
  ARRAY['new', 'processing', 'shipped', 'cancelled'][(random() * 3)::int + 1]
FROM generate_series(1, 1200000) AS s(i);
