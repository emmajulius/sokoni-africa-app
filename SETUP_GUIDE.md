# PostgreSQL Connection Setup Guide

## Connection Details (Configured)
- **IP Address**: 192.168.1.185
- **Port**: 5432
- **Database Name**: sokoni_app_db
- **Username**: postgres
- **Password**: julius1999$

## Step 1: Create .env File

Create a file named `.env` in the `africa_sokoni_app_backend` directory with the following content:

```env
DATABASE_URL=postgresql://postgres:julius1999$@192.168.1.185:5432/sokoni_app_db
SECRET_KEY=your-secret-key-change-this-in-production-min-32-characters-long-please-use-a-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

**Important**: 
- The password contains special characters (`$`), so URL encoding might be needed. If connection fails, try `julius1999%24` instead of `julius1999$`
- Change the `SECRET_KEY` to a secure random string (at least 32 characters)

## Step 2: Install Python Dependencies

```bash
cd africa_sokoni_app_backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 3: Test Database Connection

Before initializing the database, test the connection:

```bash
python3 -c "
from config import settings
import psycopg2
try:
    conn = psycopg2.connect(settings.DATABASE_URL)
    print('✓ Database connection successful!')
    conn.close()
except Exception as e:
    print(f'✗ Connection failed: {e}')
"
```

## Step 4: Initialize Database

Once connection is successful, initialize the database:

```bash
python3 init_db.py
```

This will:
- Create all database tables
- Seed initial categories

## Step 5: Run the API Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Troubleshooting

### If connection fails:

1. **Check Windows PC Firewall**: Ensure port 5432 is open
   - Windows Firewall → Advanced Settings → Inbound Rules → Allow port 5432

2. **Check PostgreSQL Configuration on Windows PC**:
   
   Edit `postgresql.conf` (usually in `C:\Program Files\PostgreSQL\*\data\`):
   ```conf
   listen_addresses = '*'  # or '0.0.0.0'
   ```
   
   Edit `pg_hba.conf` (same directory):
   ```conf
   # Add this line to allow connections from your Mac's IP
   host    all             all             192.168.1.0/24         md5
   ```
   
   Restart PostgreSQL service after changes.

3. **URL Encode Password**: If password has special characters, try:
   ```env
   DATABASE_URL=postgresql://postgres:julius1999%24@192.168.1.185:5432/sokoni_app_db
   ```

4. **Check Network Connectivity**:
   ```bash
   ping 192.168.1.185
   telnet 192.168.1.185 5432
   ```

5. **Verify Database Exists**:
   Connect to PostgreSQL on Windows PC and create database if needed:
   ```sql
   CREATE DATABASE sokoni_app_db;
   ```

## Connection String Format

The DATABASE_URL format is:
```
postgresql://username:password@host:port/database_name
```

For your setup:
```
postgresql://postgres:julius1999$@192.168.1.185:5432/sokoni_app_db
```

If special characters in password cause issues, use URL encoding:
- `$` → `%24`
- `@` → `%40`
- `#` → `%23`
- `%` → `%25`
- `&` → `%26`

## Next Steps After Setup

1. Verify connection works
2. Run `init_db.py` to create tables
3. Start the API server
4. Test endpoints at http://localhost:8000/docs

