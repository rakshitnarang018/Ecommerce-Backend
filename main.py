from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from bson import ObjectId
import os
from datetime import datetime
import re

# Initialize FastAPI app
app = FastAPI(
    title="Ecommerce API",
    description="A sample ecommerce backend with products and orders",
    version="1.0.0"
)

# MongoDB connection with better error handling
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")

if not MONGODB_URL or MONGODB_URL == "mongodb://localhost:27017/":
    print("❌ MONGODB_URL environment variable not set!")
    print("Please set MONGODB_URL in your Render environment variables")
    raise Exception("MongoDB URL not configured")

try:
    print(f"🔗 Connecting to MongoDB...")
    print(f"🔗 URL: {MONGODB_URL[:50]}...") # Show first 50 chars for debugging
    
    client = MongoClient(MONGODB_URL, serverSelectionTimeoutMS=10000)
    # Test the connection
    client.admin.command('ping')
    db = client.ecommerce
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")
    print("Common fixes:")
    print("1. Check username/password in connection string")
    print("2. Ensure Network Access allows 0.0.0.0/0")
    print("3. Verify database user has proper permissions")
    raise e

# Collections
products_collection = db.products if db else None
orders_collection = db.orders if db else None

# Models
class Size(BaseModel):
    size: str
    quantity: int

class Product(BaseModel):
    name: str
    price: float
    sizes: List[Size]
    description: Optional[str] = None

class OrderItem(BaseModel):
    productId: str
    qty: int
    
    @validator('productId')
    def validate_product_id(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid product ID format')
        return v

class Order(BaseModel):
    userId: str
    items: List[OrderItem]
    status: str = "pending"

# Helper function to convert ObjectId to string
def serialize_doc(doc):
    if doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc

# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        if db is None:
            return {"status": "unhealthy", "database": "disconnected"}
        # Test MongoDB connection
        client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": f"error: {str(e)}"}

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to Ecommerce API", "status": "running"}

# Product endpoints
@app.post("/products", status_code=201)
async def create_product(product: Product):
    """Create a new product"""
    if not products_collection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Use model_dump() instead of dict() for Pydantic v2
        product_dict = product.model_dump()
        product_dict["created_at"] = datetime.utcnow()
        
        result = products_collection.insert_one(product_dict)
        
        # Return the created product with ID
        created_product = products_collection.find_one({"_id": result.inserted_id})
        return serialize_doc(created_product)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")

@app.get("/products", status_code=200)
async def get_products(
    limit: Optional[int] = Query(10, description="Number of products to return"),
    offset: Optional[int] = Query(0, description="Number of products to skip")
):
    """Get all products with pagination"""
    if not products_collection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = products_collection.find().skip(offset).limit(limit)
        products = [serialize_doc(product) for product in cursor]
        return {"products": products, "total": len(products)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch products: {str(e)}")

@app.get("/products/{product_id}", status_code=200)
async def get_product(product_id: str):
    """Get a specific product by ID"""
    if not products_collection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=400, detail="Invalid product ID format")
    
    try:
        product = products_collection.find_one({"_id": ObjectId(product_id)})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return serialize_doc(product)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch product: {str(e)}")

# Order endpoints
@app.post("/orders", status_code=201)
async def create_order(order: Order):
    """Create a new order"""
    if not orders_collection or not products_collection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Use model_dump() instead of dict() for Pydantic v2
        order_dict = order.model_dump()
        
        # Calculate total and validate products
        total_amount = 0
        for item in order.items:
            # Validate product exists
            product = products_collection.find_one({"_id": ObjectId(item.productId)})
            if not product:
                raise HTTPException(status_code=400, detail=f"Product {item.productId} not found")
            
            total_amount += product["price"] * item.qty
        
        order_dict["total_amount"] = total_amount
        order_dict["created_at"] = datetime.utcnow()
        
        result = orders_collection.insert_one(order_dict)
        
        # Return the created order with ID
        created_order = orders_collection.find_one({"_id": result.inserted_id})
        return serialize_doc(created_order)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

@app.get("/orders/{user_id}", status_code=200)
async def get_user_orders(
    user_id: str,
    limit: Optional[int] = Query(10, description="Number of orders to return"),
    offset: Optional[int] = Query(0, description="Number of orders to skip")
):
    """Get orders for a specific user"""
    if not orders_collection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = orders_collection.find({"userId": user_id}).skip(offset).limit(limit).sort("created_at", -1)
        orders = [serialize_doc(order) for order in cursor]
        return {"orders": orders, "total": len(orders)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")

@app.get("/orders", status_code=200)
async def get_all_orders(
    limit: Optional[int] = Query(10, description="Number of orders to return"),
    offset: Optional[int] = Query(0, description="Number of orders to skip")
):
    """Get all orders with pagination"""
    if not orders_collection:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = orders_collection.find().skip(offset).limit(limit).sort("created_at", -1)
        orders = [serialize_doc(order) for order in cursor]
        return {"orders": orders, "total": len(orders)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)