# Deploying MCQ Test Application on Render

## The Problem

When deploying on Render (or any cloud platform), the SQLite database (`data/history.db`) is stored in the **ephemeral filesystem** of the container. This means:
- ❌ Database gets **reset on every redeploy**
- ❌ User history and test data are **lost**
- ❌ Previous user details accessed through the Render URL are **not persisted**

## The Solution: Use PostgreSQL

The application already supports PostgreSQL! When the `DATABASE_URL` environment variable is set, it automatically switches from SQLite to PostgreSQL, which provides persistent storage in the cloud.

---

## Step-by-Step Deployment Guide

### Step 1: Create PostgreSQL Database on Render

1. Log in to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"PostgreSQL"**
3. Configure your database:
   - **Name**: `mcq-test-database` (or any name you prefer)
   - **Database**: `mcq_test` (default is fine)
   - **User**: `mcq_user` (default is fine)
   - **Region**: Choose closest to your users
   - **Plan**: Free (or paid for production)
4. Click **"Create Database"**
5. Wait for database to be created (takes 1-2 minutes)
6. Once created, click on your database and find the **Internal Database URL** or **External Database URL**
   - Copy the **Internal Database URL** (starts with `postgres://...`)

### Step 2: Deploy Your Flask Application on Render

1. In Render Dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository: `bsuganth2007/MCQ-Test`
3. Configure your web service:
   - **Name**: `mcq-test-app` (or any name you prefer)
   - **Region**: Same as your database
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty (or use `backend` if needed)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT main:app`
4. Click **"Advanced"** to add environment variables

### Step 3: Configure Environment Variables

Add the following environment variable:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Paste the Internal Database URL from Step 1 |
| `PORT` | `5001` (optional, Render sets this automatically) |

**Important**: The `DATABASE_URL` should look like:
```
postgresql://mcq_user:your_password@dpg-xxxxx-a.region.render.com/mcq_test
```

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Install dependencies from `requirements.txt`
   - Initialize the database schema (via `init_db()` in `app.py`)
   - Start your application with gunicorn

### Step 5: Verify Deployment

1. Once deployed, click on your web service URL (e.g., `https://mcq-test-app.onrender.com`)
2. Test the application:
   - Take a test
   - Submit and view results
   - Check test history
3. **Redeploy** the application (click "Manual Deploy" → "Deploy latest commit")
4. Verify that your test history is **still there** after redeploy! ✅

---

## Migrating Existing SQLite Data to PostgreSQL

If you already have test history in your local SQLite database and want to migrate it:

### Option 1: Using the Migration Script

1. Set the `DATABASE_URL` environment variable locally:
   ```bash
   export DATABASE_URL="your_postgresql_url_here"
   ```

2. Run the migration script:
   ```bash
   cd backend
   python migrate_sqlite_to_postgres.py
   ```

3. The script will:
   - Copy all data from `data/history.db` to PostgreSQL
   - Migrate all tables: test_history, question_history, user_sessions, etc.
   - Reset sequences to ensure new records get correct IDs

### Option 2: Manual Migration

1. Export data from SQLite:
   ```bash
   sqlite3 backend/data/history.db .dump > backup.sql
   ```

2. Import into PostgreSQL (requires manual SQL conversion)

---

## Troubleshooting

### Database Connection Errors

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solution**: 
- Verify `DATABASE_URL` is correctly set in Render environment variables
- Check that the database is in the same region as your web service
- Use **Internal Database URL** (not External) for better performance and security

### Application Won't Start

**Error**: `ImportError: No module named 'psycopg2'`

**Solution**: 
- Ensure `psycopg2-binary==2.9.9` is in `requirements.txt` ✅ (already included)
- Check build logs to confirm dependencies were installed

### Database Not Initializing

**Error**: Tables not being created

**Solution**:
- The `init_db()` function runs automatically when `app.py` is imported
- Check application logs for any database initialization errors
- Verify PostgreSQL user has CREATE TABLE permissions

### Old Data Not Appearing

**Problem**: History shows data locally but not on Render

**Explanation**:
- Local environment uses SQLite (`data/history.db`)
- Render environment uses PostgreSQL (via `DATABASE_URL`)
- These are **separate databases**!

**Solution**: Use the migration script (see above) to copy data

---

## How It Works: Database Selection Logic

The application automatically detects which database to use:

```python
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)

def get_db_connection():
    if USE_POSTGRES:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_FILE)  # SQLite fallback
```

- If `DATABASE_URL` is set → **PostgreSQL** (cloud deployment)
- If `DATABASE_URL` is NOT set → **SQLite** (local development)

---

## Environment-Specific Behavior

### Local Development
```bash
# No DATABASE_URL set
python main.py
# Uses: data/history.db (SQLite)
```

### Render Deployment
```bash
# DATABASE_URL is set in Render environment
gunicorn main:app
# Uses: PostgreSQL database (persistent)
```

---

## Additional Notes

### Why PostgreSQL Instead of SQLite?

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| **Persistence** | ❌ Lost on redeploy | ✅ Persistent storage |
| **Concurrent Users** | ❌ Limited | ✅ Excellent |
| **Scalability** | ❌ Single file | ✅ Scales horizontally |
| **Backups** | Manual | ✅ Automatic on Render |
| **Cost** | Free | Free tier available |

### Database Backups

Render automatically creates backups of PostgreSQL databases:
- **Free Plan**: 7 days of backups
- **Paid Plans**: Configurable backup retention

To create a manual backup:
1. Go to your database in Render Dashboard
2. Click "Backups" tab
3. Click "Create Backup"

### Monitoring Database

In Render Dashboard:
- View connection count
- Monitor database size
- Check query performance
- View logs

---

## Summary

✅ **Before**: SQLite database → Lost on redeploy  
✅ **After**: PostgreSQL database → Persists forever!

Your user history and test data will now be preserved across all redeployments! 🎉
