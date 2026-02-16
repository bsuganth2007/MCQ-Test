#!/usr/bin/env python3
"""
Database Setup Verification Script

This script helps verify your database configuration and checks
if the application will use SQLite or PostgreSQL.
"""

import os
import sys

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_section(text):
    print(f"\n{text}")
    print("-" * 60)

def check_environment():
    """Check environment variables"""
    print_header("DATABASE CONFIGURATION CHECK")
    
    database_url = os.environ.get('DATABASE_URL')
    
    print_section("Environment Variables")
    if database_url:
        print(f"✓ DATABASE_URL is Set")
        print(f"  Value: {database_url[:50]}{'...' if len(database_url) > 50 else ''}")
    else:
        print(f"ℹ DATABASE_URL is Not Set")
    
    print_section("Database Mode")
    if database_url:
        print("📊 Mode: PostgreSQL (Production/Cloud)")
        print("   - Database persists across deployments")
        print("   - Suitable for cloud platforms (Render, Heroku, etc.)")
    else:
        print("📊 Mode: SQLite (Local Development)")
        print("   - Database stored in: backend/data/history.db")
        print("   - Good for local development only")
        print("   - ⚠️  WARNING: Will be reset on cloud deployments!")

def check_dependencies():
    """Check if required dependencies are installed"""
    print_section("Dependencies Check")
    
    required = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'pandas': 'Pandas',
        'sqlite3': 'SQLite3 (built-in)',
    }
    
    if os.environ.get('DATABASE_URL'):
        required['psycopg2'] = 'psycopg2-binary'
    
    missing = []
    for module, name in required.items():
        try:
            if module == 'sqlite3':
                import sqlite3
            else:
                __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} - NOT INSTALLED")
            missing.append(name)
    
    if missing:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing)}")
        print(f"   Run: pip install -r requirements.txt")
        return False
    else:
        print("\n✓ All required dependencies are installed")
        return True

def check_database_connection():
    """Check if database is accessible"""
    print_section("Database Connection Test")
    
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # Test PostgreSQL connection
        try:
            import psycopg2
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            cursor.execute('SELECT version();')
            version = cursor.fetchone()[0]
            conn.close()
            print(f"✓ PostgreSQL connection successful")
            print(f"  Version: {version[:60]}...")
            return True
        except ImportError:
            print("✗ psycopg2 not installed")
            print("  Run: pip install psycopg2-binary")
            return False
        except Exception as e:
            print(f"✗ PostgreSQL connection failed")
            print(f"  Error: {str(e)[:200]}")
            return False
    else:
        # Test SQLite
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), 'backend', 'data', 'history.db')
        db_dir = os.path.dirname(db_path)
        
        if not os.path.exists(db_dir):
            print(f"ℹ Database directory doesn't exist yet: {db_dir}")
            print(f"  Will be created on first run")
            return True
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            conn.close()
            
            if tables:
                print(f"✓ SQLite database exists: {db_path}")
                print(f"  Tables: {len(tables)} found")
            else:
                print(f"ℹ SQLite database file exists but has no tables yet")
                print(f"  Tables will be created on first run")
            return True
        except Exception as e:
            print(f"✗ SQLite check failed")
            print(f"  Error: {str(e)}")
            return False

def provide_recommendations():
    """Provide recommendations based on configuration"""
    print_section("Recommendations")
    
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        print("✓ You are using PostgreSQL - Good for production!")
        print("\nNext steps:")
        print("  1. Deploy your application")
        print("  2. Application will automatically create tables on first run")
        print("  3. To migrate existing SQLite data:")
        print("     python backend/migrate_sqlite_to_postgres.py")
    else:
        print("ℹ You are using SQLite - Good for local development!")
        print("\nFor production deployment:")
        print("  1. Create PostgreSQL database on your cloud platform")
        print("  2. Set DATABASE_URL environment variable")
        print("  3. See RENDER_DEPLOYMENT.md for detailed instructions")
        print("\n⚠️  IMPORTANT: SQLite data will be lost on cloud redeploys!")

def main():
    """Main verification routine"""
    print("\n🔍 MCQ Test Application - Database Setup Verification")
    
    check_environment()
    deps_ok = check_dependencies()
    
    if deps_ok:
        check_database_connection()
    
    provide_recommendations()
    
    print("\n" + "=" * 60)
    print("✓ Verification complete!")
    print("=" * 60 + "\n")

if __name__ == '__main__':
    main()
