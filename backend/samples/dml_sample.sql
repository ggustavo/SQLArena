-- DML Sample: Seed data for customers and orders
INSERT INTO customers (id, name) VALUES 
    (1, 'Alice'),
    (2, 'Bob'),
    (3, 'Charlie');

INSERT INTO orders (customer_id, amount) VALUES 
    (1, 150.00),
    (1, 200.00),
    (2, 50.00),
    (3, 300.00);
