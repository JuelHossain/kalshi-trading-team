#!/usr/bin/env python3
"""
Supabase Schema Migration Script
Creates all necessary tables for the Sentient Alpha trading system.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()
load_dotenv('.env.local')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# SQL statements to create tables
MIGRATIONS = [
    {
        "name": "agent_heartbeats",
        "sql": """
        CREATE TABLE IF NOT EXISTS agent_heartbeats (
            agent_id INT PRIMARY KEY,
            agent_name TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            last_active TIMESTAMPTZ DEFAULT NOW()
        );
        """
    },
    {
        "name": "system_status",
        "sql": """
        CREATE TABLE IF NOT EXISTS system_status (
            id INT PRIMARY KEY DEFAULT 1,
            status TEXT DEFAULT 'ACTIVE',
            reason TEXT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    },
    {
        "name": "balance_history",
        "sql": """
        CREATE TABLE IF NOT EXISTS balance_history (
            id SERIAL PRIMARY KEY,
            balance_cents BIGINT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    },
    {
        "name": "trade_history",
        "sql": """
        CREATE TABLE IF NOT EXISTS trade_history (
            id SERIAL PRIMARY KEY,
            agent_id INT,
            ticker TEXT,
            action TEXT,
            contracts INT,
            price_cents INT,
            message TEXT,
            status TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    }
]

def run_migrations():
    """Execute all migration SQL statements."""
    print("🚀 Starting Supabase Schema Migration...")
    print(f"📍 Target: {SUPABASE_URL}\n")
    
    for migration in MIGRATIONS:
        table_name = migration['name']
        sql = migration['sql']
        
        try:
            print(f"⏳ Creating table: {table_name}...", end=" ")
            
            # Execute raw SQL via Supabase RPC or direct query
            # Note: Supabase Python client doesn't have direct SQL execution
            # We'll use the REST API to execute via a custom function or direct table operations
            
            # For now, we'll try to query the table to see if it exists
            try:
                supabase.table(table_name).select("*").limit(1).execute()
                print(f"✅ Already exists")
            except Exception as e:
                # Table doesn't exist, we need to create it
                # Unfortunately, the Python client doesn't support raw SQL execution
                # We need to use the SQL Editor in Supabase Dashboard or use psycopg2
                print(f"⚠️  Needs manual creation (Python client limitation)")
                print(f"   SQL: {sql.strip()}\n")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "="*60)
    print("⚠️  IMPORTANT: Supabase Python client doesn't support raw SQL execution.")
    print("Please run the following SQL in your Supabase SQL Editor:\n")
    
    for migration in MIGRATIONS:
        print(f"-- {migration['name']}")
        print(migration['sql'])
        print()

if __name__ == "__main__":
    run_migrations()
