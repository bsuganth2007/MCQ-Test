# Database Files Cleanup

## Issue
Several SQLite database files are currently tracked in git and will be committed. This is not ideal because:
- Database files can be large
- They contain user data that shouldn't be in version control
- They cause merge conflicts
- They're environment-specific (different for each developer/deployment)

## Files to Untrack

The following database files are currently tracked:
- `backend/data/history.db`
- `backend/data/history-backup.db`
- `backend/data/history-backup1.db`
- `data/history.db`
- `mcq_backup/backend/data/history.db`

## Solution

Run these commands to untrack database files while keeping them locally:

```bash
# Remove from git tracking but keep local files
git rm --cached backend/data/*.db
git rm --cached data/*.db
git rm --cached mcq_backup/backend/data/*.db

# Commit the removal
git commit -m "Untrack database files from version control"

# Push the changes
git push
```

## Verification

After running these commands:
1. Database files will remain on your local machine
2. They will no longer be tracked by git
3. `.gitignore` will prevent them from being added again
4. Future commits won't include database changes

## Note

The `.gitignore` file already has patterns to ignore `.db` files:
```
*.db
*.sqlite
*.sqlite3
data/*.db
backend/data/*.db
mcq_backup/backend/data/*.db
```

These patterns will prevent accidentally re-adding database files in the future.
