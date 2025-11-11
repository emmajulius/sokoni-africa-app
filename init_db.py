"""
Database initialization script
Run this to create tables and seed initial data
"""
from database import engine, SessionLocal
from models import Base, Category
from sqlalchemy.orm import Session


def init_db():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    print("[SUCCESS] Database tables created")


def seed_categories(db: Session):
    """Seed initial categories"""
    categories_data = [
        {"name": "Electronics", "slug": "electronics", "description": "Electronic devices and gadgets"},
        {"name": "Fashion", "slug": "fashion", "description": "Clothing and accessories"},
        {"name": "Food", "slug": "food", "description": "Food and beverages"},
        {"name": "Beauty", "slug": "beauty", "description": "Beauty and personal care products"},
        {"name": "Home/Kitchen", "slug": "home_kitchen", "description": "Home and kitchen items"},
        {"name": "Sports", "slug": "sports", "description": "Sports and fitness equipment"},
        {"name": "Automotives", "slug": "automotives", "description": "Automotive parts and accessories"},
        {"name": "Books", "slug": "books", "description": "Books and literature"},
        {"name": "Kids", "slug": "kids", "description": "Kids products and toys"},
        {"name": "Agriculture", "slug": "agriculture", "description": "Agricultural products and equipment"},
        {"name": "Art/Craft", "slug": "art_craft", "description": "Art and craft supplies"},
        {"name": "Computer/Software", "slug": "computer_software", "description": "Computers and software"},
        {"name": "Health/Wellness", "slug": "health_wellness", "description": "Health and wellness products"},
    ]
    
    for cat_data in categories_data:
        existing = db.query(Category).filter(Category.slug == cat_data["slug"]).first()
        if not existing:
            category = Category(**cat_data)
            db.add(category)
    
    db.commit()
    print("[SUCCESS] Categories seeded")


if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    
    print("Seeding initial data...")
    db = SessionLocal()
    try:
        seed_categories(db)
    finally:
        db.close()
    
    print("[SUCCESS] Database initialization complete!")

