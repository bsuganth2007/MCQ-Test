# Quick Start: Fix Database Reset on Render

**Problem**: Your history.db resets after every redeploy on Render.

**Solution**: Switch to PostgreSQL (5 minutes setup)

## Steps

### 1. Create PostgreSQL Database
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **PostgreSQL**
3. Name: `mcq-test-db`
4. Click **Create Database**
5. Copy the **Internal Database URL**

### 2. Add to Your Web Service
1. Go to your web service on Render
2. Click **Environment** tab
3. Add new environment variable:
   - **Key**: `DATABASE_URL`
   - **Value**: (paste the database URL)
4. Click **Save Changes**

### 3. Redeploy
- Render will automatically redeploy
- Your database will now persist! ✅

## Verify It Works
1. Take a test on your Render URL
2. Check test history
3. Click **Manual Deploy** → redeploy your app
4. Go back and verify test history is still there! 🎉

## Need More Help?
- See detailed guide: [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md)
- Verify your setup locally: `python verify_setup.py`
- Migrate existing data: `python backend/migrate_sqlite_to_postgres.py`

---
**That's it!** Your database will now persist across all future deployments.
