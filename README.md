# Sokoni Africa Backend API

A RESTful API backend for the Sokoni Africa e-commerce platform built with FastAPI, PostgreSQL, and JWT authentication.

## Features

- **User Authentication**: JWT-based authentication with support for phone/email login and Google Sign-In
- **User Management**: User registration, profile management, guest mode
- **Product Management**: CRUD operations for products with categories
- **Category Management**: Product categories with filtering
- **Shopping Cart**: Add, update, and remove items from cart
- **Orders**: Order creation and management
- **Stories**: 24-hour expiring stories feature
- **Role-Based Access**: Client, Supplier, and Retailer roles with different permissions

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT (JSON Web Tokens)
- **Password Hashing**: bcrypt
- **API Documentation**: Automatic Swagger/OpenAPI docs

## Project Structure

```
africa_sokoni_app_backend/
├── app/
│   └── routers/
│       ├── auth.py          # Authentication endpoints
│       ├── users.py         # User management endpoints
│       ├── products.py       # Product endpoints
│       ├── categories.py     # Category endpoints
│       ├── stories.py        # Story endpoints
│       ├── cart.py          # Cart endpoints
│       └── orders.py        # Order endpoints
├── main.py                  # FastAPI application entry point
├── config.py                # Configuration settings
├── database.py              # Database connection and session
├── models.py                # SQLAlchemy database models
├── schemas.py               # Pydantic schemas for request/response
├── auth.py                  # Authentication utilities
├── init_db.py               # Database initialization script
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository** (if not already done):
   ```bash
   cd africa_sokoni_app_backend
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL database**:
   ```bash
   # Create database
   createdb sokoni_africa_db
   
   # Or using psql:
   psql -U postgres
   CREATE DATABASE sokoni_africa_db;
   ```

5. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env file with your database credentials and secret key
   ```

   Update `.env` with your settings:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/sokoni_africa_db
   SECRET_KEY=your-secret-key-change-this-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   DEBUG=True
   ENVIRONMENT=development
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
   ```

6. **Initialize database**:
   ```bash
   python init_db.py
   ```

7. **Run the application**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

8. **Access API documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication (`/api/auth`)
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/guest` - Login as guest
- `GET /api/auth/me` - Get current user info

### Users (`/api/users`)
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/me` - Update current user profile
- `GET /api/users/{user_id}` - Get user by ID

### Products (`/api/products`)
- `GET /api/products` - Get all products (with filters)
- `GET /api/products/{product_id}` - Get product by ID
- `POST /api/products` - Create product (suppliers/retailers only)
- `PUT /api/products/{product_id}` - Update product (owner only)
- `DELETE /api/products/{product_id}` - Delete product (owner only)

### Categories (`/api/categories`)
- `GET /api/categories` - Get all categories
- `GET /api/categories/{category_slug}` - Get category by slug
- `POST /api/categories` - Create category

### Stories (`/api/stories`)
- `GET /api/stories` - Get all active stories
- `GET /api/stories/user/{user_id}` - Get user stories
- `POST /api/stories` - Create story
- `POST /api/stories/{story_id}/view` - View story (increment views)
- `DELETE /api/stories/{story_id}` - Delete story (owner only)

### Cart (`/api/cart`)
- `GET /api/cart` - Get cart items
- `POST /api/cart` - Add item to cart (clients/retailers only)
- `PUT /api/cart/{item_id}` - Update cart item quantity
- `DELETE /api/cart/{item_id}` - Remove item from cart
- `DELETE /api/cart` - Clear cart

### Orders (`/api/orders`)
- `GET /api/orders` - Get user orders
- `GET /api/orders/sales` - Get seller orders (suppliers/retailers only)
- `GET /api/orders/{order_id}` - Get order by ID
- `POST /api/orders` - Create order from cart
- `PUT /api/orders/{order_id}/status` - Update order status (seller only)

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-token>
```

## User Roles

- **Client**: Can buy products only
- **Supplier**: Can sell products only
- **Retailer**: Can both buy and sell products

## Database Models

- **Users**: User accounts with roles and authentication
- **Products**: Product listings with categories
- **Categories**: Product categories
- **Stories**: 24-hour expiring stories
- **CartItems**: Shopping cart items
- **Orders**: Order records
- **OrderItems**: Order line items

## Development

### Running Tests
```bash
# Add tests here when implemented
pytest
```

### Database Migrations (using Alembic)
```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

## Production Deployment

1. Set `DEBUG=False` and `ENVIRONMENT=production` in `.env`
2. Use a strong `SECRET_KEY`
3. Configure proper CORS origins
4. Use a production-grade PostgreSQL database
5. Set up proper logging and monitoring
6. Use HTTPS
7. Configure rate limiting
8. Set up database backups

## License

This project is part of the Sokoni Africa e-commerce platform.

