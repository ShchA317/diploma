SELECT u.email, o.amount
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.amount > 400
ORDER BY o.amount, u.id;