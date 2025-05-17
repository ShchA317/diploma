-- Создание таблицы sensor_data
DROP TABLE IF EXISTS sensor_data;
CREATE TABLE sensor_data (
  id BIGSERIAL PRIMARY KEY,
  sensor_id INT,
  temperature FLOAT,
  reading_time TIMESTAMPTZ
);

-- Вставка данных пакетами по 1 миллиону строк
DO $$
DECLARE
  batch_size INTEGER := 1000000;
  total_rows BIGINT := 100000000;
  batches INTEGER := total_rows / batch_size;
  i INTEGER := 0;
BEGIN
  FOR i IN 0..batches - 1 LOOP
    INSERT INTO sensor_data (sensor_id, temperature, reading_time)
    SELECT
      (random() * 999)::int + 1,  -- sensor_id от 1 до 1000
      round(15 + random() * 10, 2),  -- температура от 15.00 до 25.00
      NOW() - (random() * interval '30 days')  -- последние 30 дней
    FROM generate_series(1, batch_size);
    
    RAISE NOTICE 'Inserted % rows', (i + 1) * batch_size;
  END LOOP;
END $$;
