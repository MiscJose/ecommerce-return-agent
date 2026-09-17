-- Customers: 2 VIP (assuming a $300 lifetime spend threshold), 1 Standard
INSERT INTO users (email_id, address, total_spend, VIP_status) VALUES
('emma.clarke@email.com', '12 Maple St, Austin, TX', 845.50, true),
('james.tran@email.com', '88 Birch Ave, Denver, CO', 120.00, false),
('sofia.reyes@email.com', '4 Cedar Ln, Miami, FL', 312.75, true);

-- Orders: mix of recent (within a 30-day return window) and older orders
INSERT INTO orders (user_id, total_amount, order_date) VALUES
(1, 156.00, NOW() - INTERVAL '5 days'),   -- order_id 1, Emma, recent
(1, 89.50,  NOW() - INTERVAL '60 days'),  -- order_id 2, Emma, old
(2, 120.00, NOW() - INTERVAL '10 days'),  -- order_id 3, James, recent
(3, 210.00, NOW() - INTERVAL '3 days'),   -- order_id 4, Sofia, recent
(3, 102.75, NOW() - INTERVAL '90 days');  -- order_id 5, Sofia, old

-- Order items: a few clothing items per order
INSERT INTO order_items (order_id, item_price, item_quantity, item_total_price) VALUES
(1, 78.00, 2, 156.00),   -- item_id 1, denim jacket x2
(2, 44.75, 2, 89.50),    -- item_id 2, graphic tee x2
(3, 60.00, 2, 120.00),   -- item_id 3, sneakers x2
(4, 70.00, 3, 210.00),   -- item_id 4, sweaters x3
(5, 34.25, 3, 102.75);   -- item_id 5, socks pack x3

-- Returns: one of each status
INSERT INTO returns (order_id, return_amount, return_status, return_reason) VALUES
(3, 60.00,  'accepted', 'Wrong size shipped'),
(5, 34.25,  'denied',   'Changed mind, outside return window');
