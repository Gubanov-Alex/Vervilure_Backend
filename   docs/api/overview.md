
# API Overview
## Introduction
This API provides programmatic access to the e-commerce platform's functionality, allowing third-party applications, mobile apps, and other services to interact with our system.
## API Design Principles
- **RESTful**: Resources are represented as URLs with appropriate HTTP methods
- **Consistent**: Uniform response structure and error handling
- **Secure**: Authentication required for protected endpoints
- **Versioned**: API versioning to ensure compatibility
## Base URL
https://api.example.com/v1/

## Authentication

The API supports the following authentication methods:
- Token Authentication
- Session Authentication (for browser-based clients)
- OAuth2 (for third-party applications)

See the [Authentication documentation](authentication.md) for details.

## Response Format

All API responses are in JSON format with the following structure:

```json
{
  "data": { ... },  // The requested data (may be an object or array)
  "meta": {  // Metadata about the request/response
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 100,
      "pages": 5
    }
  }
}
```
Error Handling
Errors return appropriate HTTP status codes with JSON responses:

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input provided",
    "details": {
      "field_name": ["Specific error message"]
    }
  }
}
Rate Limiting
API requests are limited to:
    • 100 requests per minute for authenticated users
    • 20 requests per minute for unauthenticated users
Rate limit headers are included in all responses.

### 8. docs/api/endpoints.md

```markdown
# API Endpoints

## Products

### List Products

```
GET /api/v1/products/

Query parameters:
- `category_id`: Filter by category
- `search`: Search in title and description
- `min_price` / `max_price`: Price range filtering
- `page` / `per_page`: Pagination controls

Response:
json { "data": [ { "id": 1, "title": "Product Name", "description": "Product description", "price": 19.99, "category": { "id": 5, "name": "Category Name" }, "images": [ {"id": 1, "url": "https://example.com/image1.jpg"} ] } ], "meta": { "pagination": { "page": 1, "per_page": 20, "total": 100, "pages": 5 } } }

### Get Product Detail
GET /api/v1/products/{id}/

Response:
```json
{
  "data": {
    "id": 1,
    "title": "Product Name",
    "description": "Detailed product description",
    "price": 19.99,
    "category": {
      "id": 5,
      "name": "Category Name"
    },
    "images": [
      {"id": 1, "url": "https://example.com/image1.jpg"},
      {"id": 2, "url": "https://example.com/image2.jpg"}
    ],
    "attributes": [
      {"name": "Color", "value": "Blue"},
      {"name": "Size", "value": "Medium"}
    ]
  }
}
```
### Cart
Get Cart

GET /api/v1/cart/
Response:

{
  "data": {
    "id": "cart_uuid",
    "items": [
      {
        "id": 1,
        "product": {
          "id": 1,
          "title": "Product Name",
          "price": 19.99,
          "image_url": "https://example.com/image.jpg"
        },
        "quantity": 2,
        "total_price": 39.98
      }
    ],
    "total_items": 2,
    "subtotal": 39.98
  }
}

### Add Item to Cart

POST /api/v1/cart/items/
Request body:

{
  "product_id": 1,
  "quantity": 2
}

Orders
List Orders

GET /api/v1/orders/
Create Order

POST /api/v1/orders/
Request body:

{
  "shipping_address_id": 1,
  "payment_method_id": 1
}


### Users
Register User

POST /api/v1/users/
Request body:

{
  "email": "user@example.com",
  "password": "securepassword",
  "first_name": "John",
  "last_name": "Doe"
}
Get User Profile

GET /api/v1/users/me/
Requires authentication.

### 9. docs/api/authentication.md
markdown