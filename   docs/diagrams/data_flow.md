# Data Flow Diagrams
## Order Processing Flow
This diagram illustrates the data flow during the order creation and processing:
┌──────────────┐ (1) Add to cart ┌──────────────┐ │ User │─────────────────────────▶ Shopping │ │ │ │ Cart │ └──────────────┘ └──────────────┘ │ │ │ (6) Order │ │ confirmation │ (2) Checkout │ │ ▼ ▼ ┌──────────────┐ (5) Update order ┌──────────────┐ │ Email │◀────────────────────────│ Order │ │ Notification│ │ Processing │ └──────────────┘ └──────────────┘ │ │ (3) Process │ payment ▼ ┌──────────────┐ │ Payment │ │ Gateway │ │ (Stripe) │ └──────────────┘ │ │ (4) Payment │ result ▼ ┌──────────────┐ │ Payment │ │ Processing │ └──────────────┘

1. User adds products to their shopping cart
2. User proceeds to checkout, providing shipping and payment information
3. Order processing system communicates with payment gateway
4. Payment gateway returns success or failure
5. Order status is updated based on payment result
6. User receives order confirmation

## User Authentication Flow
┌──────────────┐ (1) Login attempt ┌──────────────┐ │ User │─────────────────────────▶│ Authentication│ │ │ │ Service │ └──────────────┘ └──────────────┘ ▲ │ │ │ (2) Validate │ │ credentials │ ▼ │ ┌──────────────┐ │ (5) Return token │ Database │ │ or error │ │ │ └──────────────┘ │ │ │ │ (3) User found │ ▼ ┌──────────────┐ (4) Generate token ┌──────────────┐ │ Client │◀────────────────────────│ Token │ │ Application │ │ Generator │ └──────────────┘ └──────────────┘

1. User attempts to log in with credentials
2. Authentication service validates credentials against database
3. If user is found, proceed to token generation
4. Generate authentication token
5. Return token to client application for subsequent requests

## Product Search Flow
┌──────────────┐ (1) Search query ┌──────────────┐ │ User │─────────────────────────▶│ Search │ │ │ │ Controller │ └──────────────┘ └──────────────┘ ▲ │ │ │ (2) Query │ │ database │ ▼ │ ┌──────────────┐ │ (5) Display results │ Database │ │ │ │ │ └──────────────┘ │ │ │ │ (3) Raw results │ ▼ ┌──────────────┐ (4) Format results ┌──────────────┐ │ Product │◀────────────────────────│ Result │ │ List │ │ Processor │ └──────────────┘ └──────────────┘

1. User submits search query
2. Search controller queries the database with filters
3. Database returns raw results
4. Result processor formats and sorts results
5. Formatted results are displayed to the user