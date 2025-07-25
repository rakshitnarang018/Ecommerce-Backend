from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, field_validator
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

# Collections - Fixed the boolean issue
products_collection = db.products if db is not None else None
orders_collection = db.orders if db is not None else None

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
    
    @field_validator('productId')
    @classmethod
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
    if products_collection is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Use model_dump() instead of dict() for Pydantic v2
        product_dict = product.model_dump()
        product_dict["created_at"] = datetime.utcnow()
        
        result = products_collection.insert_one(product_dict)
        
        # Return only the ID as shown in the API doc
        return {"id": str(result.inserted_id)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")

@app.get("/products", status_code=200)
async def get_products(
    name: Optional[str] = Query(None, description="Filter by product name (regex/partial search)"),
    size: Optional[str] = Query(None, description="Filter by size (e.g., 'large')"),
    limit: Optional[int] = Query(10, description="Number of products to return"),
    offset: Optional[int] = Query(0, description="Number of products to skip")
):
    """Get all products with filtering and pagination"""
    if products_collection is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Build query filter
        query_filter = {}
        
        if name:
            # Case-insensitive regex search for name
            query_filter["name"] = {"$regex": name, "$options": "i"}
        
        if size:
            # Filter products that have the specified size
            query_filter["sizes.size"] = {"$regex": size, "$options": "i"}
        
        # Get total count for pagination
        total_count = products_collection.count_documents(query_filter)
        
        # Get products with pagination
        cursor = products_collection.find(query_filter).skip(offset).limit(limit)
        products = []
        
        for product in cursor:
            # Serialize and remove sizes from output as shown in API doc
            serialized_product = serialize_doc(product)
            # Remove sizes from response as indicated in the comment "# No sizes in output"
            if "sizes" in serialized_product:
                del serialized_product["sizes"]
            products.append(serialized_product)
        
        # Calculate pagination info
        next_offset = offset + limit if offset + limit < total_count else None
        prev_offset = max(0, offset - limit) if offset > 0 else None
        
        return {
            "data": products,
            "page": {
                "next": str(next_offset) if next_offset is not None else None,
                "limit": limit,
                "previous": prev_offset
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch products: {str(e)}")

@app.get("/products/{product_id}", status_code=200)
async def get_product(product_id: str):
    """Get a specific product by ID"""
    if products_collection is None:
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
    if orders_collection is None or products_collection is None:
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
        
        # Return only the ID as shown in the API doc
        return {"id": str(result.inserted_id)}
        
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
    if orders_collection is None or products_collection is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        # Get total count for pagination
        total_count = orders_collection.count_documents({"userId": user_id})
        
        # Get orders with pagination
        cursor = orders_collection.find({"userId": user_id}).skip(offset).limit(limit).sort("created_at", -1)
        orders = []
        
        for order in cursor:
            serialized_order = serialize_doc(order)
            
            # Enhance items with product details as shown in API doc
            enhanced_items = []
            for item in serialized_order.get("items", []):
                product = products_collection.find_one({"_id": ObjectId(item["productId"])})
                enhanced_item = {
                    "productDetails": {
                        "name": product["name"] if product else "Unknown Product",
                        "id": item["productId"]
                    },
                    "qty": item["qty"]
                }
                enhanced_items.append(enhanced_item)
            
            serialized_order["items"] = enhanced_items
            orders.append(serialized_order)
        
        # Calculate pagination info
        next_offset = offset + limit if offset + limit < total_count else None
        prev_offset = max(0, offset - limit) if offset > 0 else None
        
        return {
            "data": orders,
            "page": {
                "next": str(next_offset) if next_offset is not None else None,
                "limit": limit,
                "previous": prev_offset if prev_offset != offset else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")

@app.get("/orders", status_code=200)
async def get_all_orders(
    limit: Optional[int] = Query(10, description="Number of orders to return"),
    offset: Optional[int] = Query(0, description="Number of orders to skip")
):
    """Get all orders with pagination"""
    if orders_collection is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cursor = orders_collection.find().skip(offset).limit(limit).sort("created_at", -1)
        orders = [serialize_doc(order) for order in cursor]
        
        # Get actual total count
        total_count = orders_collection.count_documents({})
        
        return {"orders": orders, "total": total_count, "returned": len(orders)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)