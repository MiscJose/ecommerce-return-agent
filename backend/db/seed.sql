-- Customers: 2 VIP (assuming a $300 lifetime spend threshold), 1 Standard
INSERT INTO users (email_id, address, total_spend, VIP_status) VALUES
('emma.clarke@email.com', '12 Maple St, Austin, TX', 845.50, true),
('james.tran@email.com', '88 Birch Ave, Denver, CO', 120.00, false),
('sofia.reyes@email.com', '4 Cedar Ln, Miami, FL', 312.75, true);

-- Orders: each one exercises a different path through the graph
INSERT INTO orders (user_id, total_amount, order_date) VALUES
(1, 156.00, NOW() - INTERVAL '5 days'),   -- order 1: Emma (VIP), >= $150 -> reason, then manager approval
(1, 89.50,  NOW() - INTERVAL '40 days'),  -- order 2: Emma (VIP), inside 60-day window -> reason, auto-approve
(2, 120.00, NOW() - INTERVAL '10 days'),  -- order 3: James (standard), inside 30-day window -> reason, auto-approve
(3, 210.00, NOW() - INTERVAL '3 days'),   -- order 4: Sofia (VIP), >= $150 -> reason, then manager approval
(3, 102.75, NOW() - INTERVAL '90 days'),  -- order 5: Sofia (VIP), past 60-day window -> auto-deny
(2, 75.00,  NOW() - INTERVAL '40 days');  -- order 6: James (standard), past 30-day window -> auto-deny

INSERT INTO order_items (order_id, item_price, item_quantity, item_total_price) VALUES
(1, 78.00, 2, 156.00),
(2, 44.75, 2, 89.50),
(3, 60.00, 2, 120.00),
(4, 70.00, 3, 210.00),
(5, 34.25, 3, 102.75),
(6, 25.00, 3, 75.00);

INSERT INTO returns (order_id, return_amount, return_status, return_reason, return_reason_category) VALUES
(4, 210.00, 'accepted', 'I received the wrong size', 'Incorrect Items Delivered');
