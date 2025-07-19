# FastAPI Ecommerce Backend

A sample ecommerce backend application built with FastAPI and MongoDB, featuring product management and order processing APIs.

## 🚀 Features

- **Product Management**: Create and list products with size variations
- **Order Processing**: Create orders and retrieve user order history
- **Advanced Filtering**: Search products by name (regex support) and filter by size
- **Pagination**: Built-in pagination for all listing endpoints
- **MongoDB Integration**: Optimized queries and proper data modeling
- **Input Validation**: Comprehensive request/response validation using Pydantic

## 🛠️ Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **Database**: MongoDB (with PyMongo)
- **Validation**: Pydantic
- **Server**: Uvicorn

## 📋 API Endpoints

### Products

#### Create Product
- **Endpoint**: `POST /products`
- **Request Body**:
```json
{
    "name": "string",
    "price": 100.0,
    "sizes": [
        {
            "size": "string",
            "quantity": 0
        }
    ]
}
```
- **Response**: `201 CREATED`
```json
{
    "id": "1234567890"
}
```

#### List Products
- **Endpoint**: `GET /products`
- **Query Parameters**:
  - `name` (optional): Filter by product name (supports regex/partial search)
  - `size` (optional): Filter products that have a specific size
  - `limit` (optional): Number of documents to return (default: 10)
  - `offset` (optional): Number of documents to skip for pagination (default: 0)
- **Response**: `200 OK`
```json
{
    "data": [
        {
            "id": "12345",
            "name": "Sample",
            "price": 100.0
        }
    ],
    "page": {
        "next": "10",
        "limit": 6,
        "previous": -10
    }
}
```

### Orders

#### Create Order
- **Endpoint**: `POST /orders`
- **Request Body**:
```json
{
    "userId": "user_1",
    "items": [
        {
            "productId": "12345678901",
            "qty": 3
        },
        {
            "productId": "2222222",
            "qty": 3
        }
    ]
}
```
- **Response**: `201 CREATED`
```json
{
    "id": "1234567890"
}
```

#### Get User Orders
- **Endpoint**: `GET /orders/{user_id}`
- **Query Parameters**:
  - `limit` (optional): Number of documents to return (default: 10)
  - `offset` (optional): Number of documents to skip for pagination (default: 0)
- **Response**: `200 OK`
```json
{
    "data": [
        {
            "id": "order_id",
            "items": [
                {
                    "productDetails": {},
                    "name": "Sample Product",
                    "qty": 3
                }
            ],
            "total": 300.0
        }
    ],
    "page": {
        "next": "10",
        "limit": 6,
        "previous": -10
    }
}
```

## 🏗️ Database Schema

### Products Collection
```json
{
    "_id": ObjectId,
    "name": "string",
    "price": "number",
    "sizes": [
        {
            "size": "string",
            "quantity": "number"
        }
    ]
}
```

### Orders Collection
```json
{
    "_id": ObjectId,
    "userId": "string",
    "items": [
        {
            "productId": "string",
            "qty": "number"
        }
    ],
    "total": "number",
    "createdAt": "datetime"
}
```

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- MongoDB (local installation or MongoDB Atlas)

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd fastapi-ecommerce
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
export MONGODB_URL="mongodb://localhost:27017/"  # Or your MongoDB Atlas connection string
```

5. **Run the application**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### MongoDB Setup

#### Using MongoDB Atlas (Recommended for deployment)
1. Create a free M0 cluster at [MongoDB Atlas](https://cloud.mongodb.com)
2. Get your connection string
3. Set the `MONGODB_URL` environment variable

#### Using Local MongoDB
1. Install MongoDB locally
2. Start MongoDB service
3. Use default connection string: `mongodb://localhost:27017/`

## 📚 API Documentation

Once the application is running, you can access:
- **Interactive API docs**: `http://localhost:8000/docs`
- **ReDoc documentation**: `http://localhost:8000/redoc`

## 🎯 Key Features Implemented

### Advanced Query Features
- **Regex Search**: Product name filtering supports partial matches and regex patterns
- **Size Filtering**: Filter products by available sizes
- **Efficient Pagination**: Cursor-based pagination with proper offset handling

### Data Optimization
- **Indexed Queries**: Optimized MongoDB queries for better performance
- **Aggregation Pipeline**: Efficient data joins for order details
- **Proper Data Modeling**: Normalized schema with appropriate relationships

### Error Handling
- **Comprehensive Validation**: Input validation using Pydantic models
- **Error Responses**: Proper HTTP status codes and error messages
- **Exception Handling**: Graceful handling of database and application errors

## 🔧 Configuration

### Environment Variables
- `MONGODB_URL`: MongoDB connection string (default: `mongodb://localhost:27017/`)

### Database Configuration
- Database name: `ecommerce`
- Collections: `products`, `orders`

## 📈 Performance Considerations

- **Indexing**: Recommended indexes for better query performance:
  ```javascript
  // Products collection
  db.products.createIndex({"name": "text"})
  db.products.createIndex({"sizes.size": 1})
  
  // Orders collection
  db.orders.createIndex({"userId": 1})
  db.orders.createIndex({"createdAt": -1})
  ```

- **Query Optimization**: All queries use efficient MongoDB operations
- **Pagination**: Implemented to handle large datasets efficiently

## 🚀 Deployment

### Using Render (Free)
1. Fork this repository
2. Connect your GitHub account to Render
3. Create a new Web Service
4. Set environment variables (MONGODB_URL)
5. Deploy!

### Using Railway (Free)
1. Connect your GitHub repository
2. Set environment variables
3. Deploy with one click

## 🧪 Testing

The application includes several test scenarios:
- Product creation with various size configurations
- Product listing with different filter combinations
- Order creation with multiple items
- User order retrieval with pagination

## 📝 Code Structure

```
├── main.py              # Main application file
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── .gitignore          # Git ignore file
```

### Code Organization
- **Models**: Pydantic models for request/response validation
- **Database**: MongoDB connection and collection setup
- **Helpers**: Utility functions for data transformation
- **Endpoints**: RESTful API endpoints with proper error handling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is created for the HROne Backend Intern Hiring Task.

## 🔍 Additional Notes

- All endpoints return data in the exact format specified in the assignment
- The application is designed to work with automated testing scripts
- Proper HTTP status codes are returned for all scenarios
- Database queries are optimized for performance
- Code follows Python best practices and is well-documented