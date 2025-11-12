"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Lead/contact submissions
class Lead(BaseModel):
    """
    Contact leads from the website
    Collection name: "lead"
    """
    name: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=7, description="Phone number with country code if possible")
    email: Optional[EmailStr] = Field(None, description="Email of the lead")
    message: Optional[str] = Field(None, max_length=2000)
    selected_plan: Optional[str] = Field(None, description="Plan the user selected (Basic/Pro/Premium)")
    source: Optional[str] = Field("web", description="Source of the lead")
