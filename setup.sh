#!/bin/bash
# Setup script for PostgreSQL connection

echo "=== Sokoni Africa Backend Setup ==="
echo ""

# Create .env file
cat > .env << 'EOF'
DATABASE_URL=postgresql://postgres:julius1999$@192.168.1.185:5432/sokoni_app_db
SECRET_KEY=your-secret-key-change-this-in-production-min-32-characters-long-please-use-a-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
EOF

echo "✓ Created .env file"
echo ""
echo "Configuration:"
echo "  Database: sokoni_app_db"
echo "  Host: 192.168.1.185"
echo "  Port: 5432"
echo "  Username: postgres"
echo ""
echo "Next steps:"
echo "1. Install dependencies: pip install -r requirements.txt"
echo "2. Test connection: python3 -c 'from config import settings; import psycopg2; conn = psycopg2.connect(settings.DATABASE_URL); print(\"✓ Connected!\"); conn.close()'"
echo "3. Initialize database: python3 init_db.py"
echo "4. Run server: uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""

