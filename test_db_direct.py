
import pymysql
import sys

def test():
    print("Testing connection to 127.0.0.1:3306...")
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='',
            charset='utf8mb4'
        )
        print("SUCCESS: Connected to MySQL on port 3306")
        conn.close()
        return True
    except Exception as e:
        print(f"FAILURE: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if test() else 1)
