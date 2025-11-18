import os
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Novel as NovelSchema, Chapter as ChapterSchema, Progress as ProgressSchema

app = FastAPI(title="Futuristic Novel Reader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Helpers --------------------

def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID format")

def serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    out = {**doc}
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    # Convert any ObjectIds inside document
    for k, v in list(out.items()):
        if isinstance(v, ObjectId):
            out[k] = str(v)
    return out

# -------------------- Health --------------------

@app.get("/")
def read_root():
    return {"message": "Futuristic Novel Reader Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response

# -------------------- Schemas (Requests) --------------------

class NovelCreate(BaseModel):
    title: str
    author: str
    description: str
    cover_url: Optional[str] = None
    genres: Optional[List[str]] = None

class ChapterCreate(BaseModel):
    index: int
    title: str
    content: str

class ProgressUpsert(BaseModel):
    user_id: str
    novel_id: str
    chapter_id: str
    position: float

# -------------------- Novels --------------------

@app.get("/api/novels")
def list_novels():
    docs = db.novel.find({}).sort("title", 1)
    return [serialize(d) for d in docs]

@app.post("/api/novels")
def create_novel(novel: NovelCreate):
    data = NovelSchema(**novel.model_dump())
    new_id = create_document("novel", data)
    return {"id": new_id}

@app.get("/api/novels/{novel_id}")
def get_novel(novel_id: str):
    doc = db.novel.find_one({"_id": oid(novel_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Novel not found")
    return serialize(doc)

# -------------------- Chapters --------------------

@app.get("/api/novels/{novel_id}/chapters")
def list_chapters(novel_id: str):
    docs = db.chapter.find({"novel_id": novel_id}).sort("index", 1)
    return [serialize(d) for d in docs]

@app.post("/api/novels/{novel_id}/chapters")
def create_chapter(novel_id: str, chapter: ChapterCreate):
    data = ChapterSchema(novel_id=novel_id, **chapter.model_dump())
    new_id = create_document("chapter", data)
    return {"id": new_id}

@app.get("/api/chapters/{chapter_id}")
def get_chapter(chapter_id: str):
    doc = db.chapter.find_one({"_id": oid(chapter_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return serialize(doc)

# -------------------- Progress --------------------

@app.get("/api/progress/{user_id}/{novel_id}")
def get_progress(user_id: str, novel_id: str):
    doc = db.progress.find_one({"user_id": user_id, "novel_id": novel_id})
    return serialize(doc) if doc else None

@app.post("/api/progress")
def upsert_progress(p: ProgressUpsert):
    # Upsert based on user+novel
    res = db.progress.update_one(
        {"user_id": p.user_id, "novel_id": p.novel_id},
        {"$set": {
            "user_id": p.user_id,
            "novel_id": p.novel_id,
            "chapter_id": p.chapter_id,
            "position": p.position,
        }},
        upsert=True
    )
    # Return the updated doc
    doc = db.progress.find_one({"user_id": p.user_id, "novel_id": p.novel_id})
    return serialize(doc)

# -------------------- Seed (Demo Data) --------------------

@app.post("/api/seed")
def seed_demo_data():
    # If novels already exist, skip
    if db.novel.count_documents({}) > 0:
        novels = [serialize(n) for n in db.novel.find({}).limit(5)]
        return {"status": "exists", "novels": novels}

    n1 = NovelSchema(
        title="Neon Skies of Andromeda",
        author="Ava Kestrel",
        description="A rogue pilot and a sentient starship uncover a conspiracy spanning galaxies.",
        cover_url="https://images.unsplash.com/photo-1520975980471-4f0f2c56b05c?q=80&w=1200&auto=format&fit=crop",
        genres=["Sci-Fi", "Space Opera", "Adventure"],
    )
    n2 = NovelSchema(
        title="Quantum Garden",
        author="Jun Park",
        description="In a city where time blossoms like petals, a gardener tends to timelines.",
        cover_url="https://images.unsplash.com/photo-1526318472351-c75fcf070305?q=80&w=1200&auto=format&fit=crop",
        genres=["Speculative", "Time", "Mystery"],
    )

    n1_id = create_document("novel", n1)
    n2_id = create_document("novel", n2)

    ch1 = ChapterSchema(novel_id=n1_id, index=1, title="Docking Under Neon", content=("""
The city-orbit glowed like a halo around the dead moon. As Kestrel aligned the ship with Dock 47, the hull hummed—anxious, aware.
"You sure about this?" the ship asked, voice like rain on glass.
"No," she said, and smiled.
""".strip()))
    ch2 = ChapterSchema(novel_id=n1_id, index=2, title="Ghost Frequencies", content=("""
The transmission carried a heartbeat buried in static. Every station they passed began to blink in unison.
The pattern spelled a name Kestrel swore she'd forgotten.
""".strip()))

    ch3 = ChapterSchema(novel_id=n2_id, index=1, title="Pruning the Dawn", content=("""
Morning arrived in layers, like rings inside a tree. Jae clipped the excess day and folded it into the compost of yesterday.
""".strip()))

    create_document("chapter", ch1)
    create_document("chapter", ch2)
    create_document("chapter", ch3)

    novels = [serialize(n) for n in db.novel.find({})]
    return {"status": "seeded", "novels": novels}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
