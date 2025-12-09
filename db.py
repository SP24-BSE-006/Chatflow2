import mysql.connector
from mysql.connector import Error, pooling
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("Loading database configuration...")

class Database:
    def __init__(self):
        self.pool = None
        self.connection = None
        self.cursor = None
        self._create_pool()
    
    def _create_pool(self):
        """Create connection pool"""
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="mypool",
                pool_size=5,
                pool_reset_session=True,
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME', 'messaging_app_db'),
                autocommit=True
            )
            print("✓ Database connection pool created")
        except Error as e:
            print(f"✗ Error creating pool: {e}")
    
    def get_connection(self):
        """Get connection from pool"""
        try:
            if self.pool:
                return self.pool.get_connection()
        except Error as e:
            print(f"✗ Error getting connection: {e}")
            return None
    
    def connect(self):
        """Connect to MySQL database"""
        try:
            self.connection = self.get_connection()
            
            if self.connection and self.connection.is_connected():
                self.cursor = self.connection.cursor(dictionary=True)
                print("✓ Connected to MySQL database successfully")
                return True
        
        except Error as e:
            print(f"✗ Error connecting to MySQL: {e}")
            return False
    
    def ensure_connection(self):
        """Ensure database connection is active, reconnect if needed"""
        try:
            if not self.connection or not self.connection.is_connected():
                print("⚠ Connection lost, reconnecting...")
                return self.connect()
            return True
        except Exception as e:
            print(f"⚠ Connection check error: {e}")
            return self.connect()
    
    def disconnect(self):
        """Disconnect from database"""
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.connection:
                self.connection.close()
                self.connection = None
            print("✓ Disconnected from MySQL database")
        except Exception as e:
            print(f"⚠ Disconnect warning: {e}")
    
    def execute_query(self, query, params=None):
        """Execute a SELECT query and return results"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            if not conn:
                print("✗ Failed to get connection")
                return None
            
            cursor = conn.cursor(dictionary=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            result = cursor.fetchall()
            return result
        
        except Error as e:
            print(f"✗ Error executing query: {e}")
            return None
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def execute_update(self, query, params=None):
        """Execute INSERT, UPDATE, or DELETE query"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            if not conn:
                print("✗ Failed to get connection")
                return None
            
            cursor = conn.cursor(dictionary=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            conn.commit()
            rowcount = cursor.rowcount
            lastrowid = cursor.lastrowid
            
            print(f"✓ Query executed. Rows affected: {rowcount}")
            
            # Store lastrowid for get_insert_id
            self._last_insert_id = lastrowid
            
            return rowcount
        
        except Error as e:
            if conn:
                conn.rollback()
            print(f"✗ Error executing update: {e}")
            return None
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_insert_id(self):
        """Get the ID of the last inserted row"""
        return getattr(self, '_last_insert_id', None)

# Create a global database instance
db = Database()