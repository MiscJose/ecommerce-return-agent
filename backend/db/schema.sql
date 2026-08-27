CREATE TABLE users (

	user_id serial primary key not null,
	email_id text unique not null,
	address text not null,
	total_spend decimal (12,2),
	VIP_status bool
);

CREATE Table orders (
	order_id serial primary key not null,
	user_id int references users(user_id) not null,
	total_amount decimal (12,2) not null,
	order_date timestamp not null
);

CREATE Table order_items (
	item_id serial primary key not null,
	order_id int references orders(order_id) not null,
	item_price decimal (12,2) not null,
	item_quantity int not null,
	item_total_price decimal (12,2) not null
);

CREATE Table returns (
	return_id serial primary key not null,
	order_id int references orders(order_id) not null,
	item_id int references order_items(item_id) not null,
	return_quantity int not null,
	return_amount decimal (12,2) not null,
	return_status text CHECK (return_status IN ('pending', 'accepted', 'denied')) not null,
	return_reason text not null
);