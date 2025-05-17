SELECT u.email, o.amount
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.interests @> ARRAY['tech'] AND o.status = 'paid';