from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
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

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
client = MongoClient(MONGODB_URL)
db = client.ecommerce

# Collections
products_collection = db.products
orders_collection = db.orders

# Pydantic models
class Size(BaseModel):
    size: str
    quantity: int

class Product(BaseModel):
    name: str
    price: float
    sizes: List[Size]

class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    sizes: List[Size] = []

class OrderItem(BaseModel):
    productId: str
    qty: int

class Order(BaseModel):
    userId: str
    items: List[OrderItem]

class OrderResponse(BaseModel):
    id: str

class ProductInOrder(BaseModel):
    productDetails: Dict[str, Any] = {}
    name: str
    qty: int

class OrderListItem(BaseModel):
    id: str
    items: List[ProductInOrder]
    total: float

class OrderListResponse(BaseModel):
    data: List[OrderListItem]
    page: Dict[str, Any]

class ProductListResponse(BaseModel):
    data: List[ProductResponse]
    page: Dict[str, Any]

# Helper functions
def product_helper(product) -> dict:
    return {
        "id": str(product["_id"]),
        "name": product["name"],
        "price": product["price"],
        "sizes": product.get("sizes", [])
    }

def order_helper(order) -> dict:
    return {
        "id": str(order["_id"]),
        "userId": order["userId"],
        "items": order["items"],
        "total": order.get("total", 0),
        "createdAt": order.get("createdAt")
    }

# API Endpoints

@app.post("/products", status_code=201)
async def create_product(product: Product):
    """Create a new product"""
    try:
        product_dict = product.dict()
        result = products_collection.insert_one(product_dict)
        return {"id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products", status_code=200)
async def list_products(
    name: Optional[str] = Query(None, description="Filter by product name (supports regex)"),
    size: Optional[str] = Query(None, description="Filter by size"),
    limit: Optional[int] = Query(10, description="Number of documents to return"),
    offset: Optional[int] = Query(0, description="Number of documents to skip")
):
    """List products with optional filters"""
    try:
        # Build filter query
        filter_query = {}
        
        if name:
            filter_query["name"] = {"$regex": name, "$options": "i"}
        
        if size:
            filter_query["sizes.size"] = size
        
        # Get total count for pagination
        total_count = products_collection.count_documents(filter_query)
        
        # Get products with pagination
        cursor = products_collection.find(filter_query).skip(offset).limit(limit)
        products = [product_helper(product) for product in cursor]
        
        # Calculate pagination info
        next_offset = offset + limit if offset + limit < total_count else None
        prev_offset = max(0, offset - limit) if offset > 0 else None
        
        response = {
            "data": products,
            "page": {
                "next": str(next_offset) if next_offset is not None else None,
                "limit": len(products),
                "previous": str(prev_offset) if prev_offset is not None else None
            }
        }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders", status_code=201)
async def create_order(order: Order):
    """Create a new order"""
    try:
        order_dict = order.dict()
        
        # Calculate total price
        total = 0
        for item in order_dict["items"]:
            product = products_collection.find_one({"_id": ObjectId(item["productId"])})
            if product:
                total += product["price"] * item["qty"]
        
        order_dict["total"] = total
        order_dict["createdAt"] = datetime.utcnow()
        
        result = orders_collection.insert_one(order_dict)
        return {"id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/orders/{user_id}", status_code=200)
async def get_user_orders(
    user_id: str,
    limit: Optional[int] = Query(10, description="Number of documents to return"),
    offset: Optional[int] = Query(0, description="Number of documents to skip")
):
    """Get orders for a specific user"""
    try:
        # Build filter query
        filter_query = {"userId": user_id}
        
        # Get total count for pagination
        total_count = orders_collection.count_documents(filter_query)
        
        # Get orders with pagination
        cursor = orders_collection.find(filter_query).skip(offset).limit(limit)
        orders = []
        
        for order in cursor:
            order_items = []
            for item in order["items"]:
                # Get product details
                product = products_collection.find_one({"_id": ObjectId(item["productId"])})
                product_item = {
                    "productDetails": product_helper(product) if product else {},
                    "name": product["name"] if product else "Unknown Product",
                    "qty": item["qty"]
                }
                order_items.append(product_item)
            
            order_data = {
                "id": str(order["_id"]),
                "items": order_items,
                "total": order.get("total", 0)
            }
            orders.append(order_data)
        
        # Calculate pagination info
        next_offset = offset + limit if offset + limit < total_count else None
        prev_offset = max(0, offset - limit) if offset > 0 else None
        
        response = {
            "data": orders,
            "page": {
                "next": str(next_offset) if next_offset is not None else None,
                "limit": len(orders),
                "previous": str(prev_offset) if prev_offset is not None else None
            }
        }
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Ecommerce API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)