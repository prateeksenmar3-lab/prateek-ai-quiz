from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI(title="PW Clone Backend", version="1.0")

# Database Simulation
courses_db = [
    {"id": 1, "title": "JEE Physics Lakshya", "price": 3999, "category": "JEE"},
    {"id": 2, "title": "NEET Biology Yakeen", "price": 3999, "category": "NEET"},
    {"id": 3, "title": "UPSC Foundation", "price": 4999, "category": "UPSC"}
]

class Course(BaseModel):
    id: int
    title: str
    price: int
    category: str

@app.get("/api/v1/courses", response_model=List[Course])
def get_all_courses():
    return courses_db

@app.get("/api/v1/courses/{category}")
def get_courses_by_category(category: str):
    filtered = [c for c in courses_db if c["category"].lower() == category.lower()]
    if not filtered:
        raise HTTPException(status_code=404, detail="No courses found in this category")
    return filtered
    from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./pw_clone.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# User Table Model
class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

# Course Table Model
class CourseModel(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    price = Column(Integer)

# Database Tables Create karna
def init_db():
    Base.metadata.create_all(bind=engine)
    from datetime import datetime, timedelta
import jwt

SECRET_KEY = "apna_super_secret_key_yahan_likhein"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Example Usage:
# token = create_access_token({"sub": "student@pw.live"})
# print("Generated Token:", token)
