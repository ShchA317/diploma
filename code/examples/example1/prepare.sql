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
  ARRAY[
    CASE (random() * 3)::int
      WHEN 0 THEN 'music'
      WHEN 1 THEN 'sports'
      ELSE 'tech'
    END
  ],
  jsonb_build_object(
    'age', 18 + (random() * 50)::int,
    'country', (ARRAY['US', 'CA', 'UK', 'DE', 'FR'])[floor(random() * 5)::int + 1]
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

INSERT INTO orders (user_id, amount, status)
SELECT
  (random() * 499999)::int + 1,
  round((random() * 1000)::numeric, 2),
  CASE (random() * 4)::int
    WHEN 0 THEN 'new'
    WHEN 1 THEN 'processing'
    WHEN 2 THEN 'shipped'
    ELSE 'cancelled'
  END
FROM generate_series(1, 1200000) AS s(i);
