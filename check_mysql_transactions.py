#!/usr/bin/env python3
"""
Script to check and clean up MySQL transactions
"""

import os
from dotenv import load_dotenv
import pymysql

# Load environment variables
load_dotenv('config.env')

def check_transactions():
    """Check for active MySQL transactions"""
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_user = os.getenv('DB_USER', 'root')
    db_pass = os.getenv('DB_PASS', '')
    db_name = os.getenv('DB_NAME', 'scholarsphere')
    db_port = int(os.getenv('DB_PORT', 3306))
    
    try:
        # Connect to MySQL
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name,
            charset='utf8mb4'
        )
        
        cursor = conn.cursor()
        
        # Check for active transactions
        print("Checking for active transactions...")
        cursor.execute("""
            SELECT 
                trx_id,
                trx_state,
                trx_started,
                trx_requested_lock_id,
                trx_wait_started,
                trx_weight,
                trx_mysql_thread_id,
                trx_query
            FROM information_schema.innodb_trx
            ORDER BY trx_started
        """)
        
        transactions = cursor.fetchall()
        
        if transactions:
            print(f"\n⚠️  Found {len(transactions)} active transaction(s):")
            print("-" * 80)
            for trx in transactions:
                print(f"Transaction ID: {trx[0]}")
                print(f"State: {trx[1]}")
                print(f"Started: {trx[2]}")
                print(f"Thread ID: {trx[6]}")
                if trx[7]:
                    print(f"Query: {trx[7][:100]}...")
                print("-" * 80)
        else:
            print("✅ No active transactions found")
        
        # Check for locked tables
        cursor.execute("""
            SELECT 
                r.trx_id waiting_trx_id,
                r.trx_mysql_thread_id waiting_thread,
                r.trx_query waiting_query,
                b.trx_id blocking_trx_id,
                b.trx_mysql_thread_id blocking_thread,
                b.trx_query blocking_query
            FROM information_schema.innodb_lock_waits w
            INNER JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
            INNER JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id
        """)
        
        locks = cursor.fetchall()
        
        if locks:
            print(f"\n⚠️  Found {len(locks)} lock wait(s):")
            for lock in locks:
                print(f"Waiting Thread {lock[1]} blocked by Thread {lock[4]}")
        else:
            print("✅ No lock waits found")
        
        cursor.close()
        conn.close()
        
        return len(transactions), len(locks)
        
    except Exception as e:
        print(f"❌ Error checking transactions: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == '__main__':
    check_transactions()

