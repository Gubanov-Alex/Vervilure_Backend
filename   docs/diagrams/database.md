# Database Schema
## Core Tables
Below is the entity relationship diagram for the core tables in our e-commerce platform:
┌────────────────┐ ┌────────────────┐ ┌────────────────┐ │ User │ │ Product │ │ Category │ ├────────────────┤ ├────────────────┤ ├────────────────┤ │ id │ │ id │ │ id │ │ email │ │ name │ │ name │ │ password │ │ description │ │ description │ │ first_name │ │ price │ │ slug │ │ last_name │ │ stock_quantity │ │ parent_id │ │ is_staff │ │ category_id │────┐ │ image │ │ date_joined │ │ created_at │ │ │ created_at │ │ last_login │ │ updated_at │ │ │ updated_at │ └────────────────┘ └────────────────┘ │ └────────────────┘ │ │ └─────────────┘ │ │ │ │ │ │ ┌───────▼────────┐ ┌───────▼────────┐ ┌────────────────┐ │ Order │ │ ProductImage │ │ CartItem │ ├────────────────┤ ├────────────────┤ ├────────────────┤ │ id │ │ id │ │ id │ │ user_id │──┐ │ product_id │───┐ │ cart_id │──┐ │ status │ │ │ image_url │ │ │ product_id │──┼─┐ │ total_amount │ │ │ is_primary │ │ │ quantity │ │ │ │ created_at │ │ │ created_at │ │ │ created_at │ │ │ │ updated_at │ │ └────────────────┘ │ └────────────────┘ │ │ └────────────────┘ │ │ │ │ │ │ │ │ │ │ │ │ │ │ ┌───────▼────────┐ │ ┌────────────────┐ │ ┌────────────────┐ │ │ │ OrderItem │ │ │ Review │ │ │ Cart │ │ │ ├────────────────┤ │ ├────────────────┤ │ ├────────────────┤ │ │ │ id │ │ │ id │ │ │ id │ │ │ │ order_id │──┘ │ product_id │───┘ │ user_id │──┘ │ │ product_id │──────│ user_id │───────│ created_at │ │ │ quantity │ │ rating │ │ updated_at │ │ │ price │ │ comment │ └────────────────┘ │ │ created_at │ │ created_at │ │ └────────────────┘ └────────────────┘ │ │ ┌────────────────┐ ┌────────────────┐ │ │ Address │ │ Payment │ │ ├────────────────┤ ├────────────────┤ │ │ id │ │ id │ │ │ user_id │──────│ order_id │─────────────────────────────┘ │ address_line1 │ │ amount │ │ address_line2 │ │ payment_method │ │ city │ │ status │ │ state │ │ transaction_id │ │ postal_code │ │ created_at │ │ country │ └────────────────┘ │ is_default │ └────────────────┘

## Table Descriptions

### Users and Authentication

- **User**: Stores user account information
- **Address**: Stores shipping and billing addresses for users

### Product Catalog

- **Category**: Product categories in a hierarchical structure
- **Product**: Core product information
- **ProductImage**: Images associated with products
- **Review**: Customer reviews and ratings for products

### Shopping and Orders

- **Cart**: User's shopping cart
- **CartItem**: Items in a user's shopping cart
- **Order**: Customer orders
- **OrderItem**: Individual items within an order
- **Payment**: Payment information for orders

## Key Relationships

- A **User** can have multiple **Orders** and **Addresses**
- A **Product** belongs to a **Category** and can have multiple **ProductImages**
- A **Cart** belongs to a **User** and contains multiple **CartItems**
- An **Order** contains multiple **OrderItems** and has one **Payment**
- A **Review** is associated with a **Product** and a **User**

## Indexes

The following indexes are implemented for performance optimization:

- User.email