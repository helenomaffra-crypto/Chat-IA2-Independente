
try:
    import psycopg2
    print(f"✅ psycopg2 version: {psycopg2.__version__}")
    print("✅ psycopg2 is installed and working!")
except ImportError:
    print("❌ psycopg2 is NOT installed!")
except Exception as e:
    print(f"❌ Error importing psycopg2: {e}")
