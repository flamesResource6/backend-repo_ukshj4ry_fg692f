"""
Database Schemas for the Futuristic Novel Reading App

Each Pydantic model represents a MongoDB collection.
Class name lowercased is used as the collection name by convention:
- Novel -> "novel"
- Chapter -> "chapter"
- Progress -> "progress"
"""

from typing import Optional, List
from pydantic import BaseModel, Field

class Novel(BaseModel):
    title: str = Field(..., description="Novel title")
    author: str = Field(..., description="Author name")
    description: str = Field(..., description="Short description of the novel")
    cover_url: Optional[str] = Field(None, description="Cover image URL")
    genres: List[str] = Field(default_factory=list, description="List of genres/tags")

class Chapter(BaseModel):
    novel_id: str = Field(..., description="Reference to the parent novel _id as string")
    index: int = Field(..., ge=1, description="Chapter number (1-based)")
    title: str = Field(..., description="Chapter title")
    content: str = Field(..., description="Chapter content as markdown or plain text")

class Progress(BaseModel):
    user_id: str = Field(..., description="Anonymous or authenticated user id")
    novel_id: str = Field(..., description="Novel id as string")
    chapter_id: str = Field(..., description="Chapter id as string")
    position: float = Field(0.0, ge=0.0, le=1.0, description="Scroll progress between 0 and 1")
