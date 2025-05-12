API Authentication
Authentication Methods
The API supports several authentication methods to accommodate different client types and use cases.
Token Authentication
This is the recommended authentication method for most API clients.
    1. Obtain a token:

POST /api/v1/auth/token/
Request body:

{
  "username": "user@example.com",
  "password": "securepassword"
}
Response:

{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
    2. Use the token in subsequent requests:

Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Tokens expire after 24 hours of inactivity.
Session Authentication
For browser-based clients, session authentication is supported. After logging in through the web interface, API requests will be authenticated automatically using cookies.
OAuth2 Authentication
For third-party applications, OAuth2 authentication is supported.
    1. Register your application:

POST /api/v1/oauth/applications/
    2. Implement the OAuth2 authorization flow appropriate for your application type:
        ◦ Authorization Code (for web applications)
        ◦ Implicit (for browser-based applications)
        ◦ Resource Owner Password Credentials (for trusted applications)
        ◦ Client Credentials (for server-to-server applications)
Permissions
API endpoints have different permission requirements:
    • Public: Accessible without authentication
    • Authenticated: Requires a valid authentication token
    • Owner: Requires authentication and ownership of the resource
    • Admin: Requires administrative privileges
Security Recommendations
    • Always use HTTPS for API requests
    • Securely store authentication tokens
    • Implement token refresh strategies for long-running applications
    • Avoid embedding tokens in client-side code

### 10. docs/api/examples.md
markdown
API Usage Examples
This document provides practical examples of common API operations.
Authentication
Logging In and Obtaining a Token

import requests
response = requests.post(
    "https://api.example.com/v1/auth/token/",
    json={
        "username": "user@example.com",
        "password": "securepassword"
    }
)
token = response.json()["token"]
headers = {"Authorization": f"Token {token}"}
Products
Listing Products with Filtering

import requests
# Get products in a specific category, sorted by price
response = requests.get(
    "https://api.example.com/v1/products/",
    params={
        "category_id": 5,
        "ordering": "price",
        "per_page": 50
    }
)
products = response.json()["data"]
Searching Products

import requests
# Search for products containing "smartphone"
response = requests.get(
    "https://api.example.com/v1/products/",
    params={"search": "smartphone"}
)
products = response.json()["data"]
Shopping Cart
Adding an Item to Cart

import requests
# Assuming you have a token from authentication
headers = {"Authorization": f"Token {token}"}
response = requests.post(
    "https://api.example.com/v1/cart/items/",
    headers=headers,
    json={
        "product_id": 42,
        "quantity": 2
    }
)
cart = response.json()["data"]
Checkout Process

import requests
# Step 1: Get the current cart
headers = {"Authorization": f"Token {token}"}
cart_response = requests.get(
    "https://api.example.com/v1/cart/",
    headers=headers
)
# Step 2: Create an order from the cart
order_response = requests.post(
    "https://api.example.com/v1/orders/",
    headers=headers,
    json={
        "shipping_address_id": 1,
        "payment_method_id": 2
    }
)
order = order_response.json()["data"]
order_id = order["id"]
# Step 3: Process payment
payment_response = requests.post(
    f"https://api.example.com/v1/orders/{order_id}/payments/",
    headers=headers,
    json={
        "payment_method_id": 2,
        "return_url": "https://yourapp.com/payment-success"
    }
)
# Get payment URL for redirect or client-side processing
payment_info = payment_response.json()["data"]

```

┌─────────────────────────────────────────────────────────────────┐
│                       Client Applications                        │
│                                                                 │
│  ┌───────────────┐   ┌────────────────┐   ┌────────────────┐   │
│  │  Web Browser  │   │  Mobile App    │   │  Third-party   │   │
│  │               │   │                │   │  Integrations  │   │
│  └───────┬───────┘   └────────┬───────┘   └────────┬───────┘   │
└──────────┼────────────────────┼────────────────────┼────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                             API Layer                             │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐  │
│  │ Authentication │  │    REST API    │  │  API Documentation │  │
│  │  (django-      │  │  (Django REST  │  │     (drf-yasg)     │  │
│  │   allauth)     │  │   Framework)   │  │                    │  │
│  └────────────────┘  └────────────────┘  └────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                         Application Layer                         │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │   Product  │  │    User    │  │   Order    │  │  Payment   │  │
│  │  Management│  │ Management │  │ Processing │  │ Processing │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
└──────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Infrastructure Layer                       │
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ PostgreSQL │  │    Redis   │  │   Celery   │  │   Stripe   │  │
│  │  Database  │  │   Cache    │  │   Tasks    │  │  Payment   │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
└──────────────────────────────────────────────────────────────────┘

## System Interactions

The diagram below shows the primary interactions between system components:

1. **Client Applications** communicate with the system via the API Layer
2. **API Layer** handles authentication and routes requests to the Application Layer
3. **Application Layer** contains the business logic and communicates with the Infrastructure Layer
4. **Infrastructure Layer** provides data persistence, caching, and external service integration

## Key Components

- **Web Browser**: Server-rendered Django templates and JavaScript
- **Mobile App**: Native mobile application using the REST API
- **Third-party Integrations**: External systems consuming our API
- **Authentication**: User authentication and authorization via django-allauth
- **REST API**: Django REST Framework endpoints
- **API Documentation**: Interactive API documentation via drf-yasg
- **Product Management**: Catalog, inventory, and pricing management
- **User Management**: User accounts, profiles, and permissions
- **Order Processing**: Shopping cart, checkout, and order fulfillment
- **Payment Processing**: Integration with Stripe for payment handling
- **PostgreSQL Database**: Primary data store
- **Redis Cache**: Caching and message broker
- **Celery Tasks**: Asynchronous and scheduled task processing
- **Stripe Payment**: External payment processing service