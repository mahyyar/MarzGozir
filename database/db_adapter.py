import sqlite3
import logging
import os
from bot_config import DB_PATH, DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger(__name__)

class DatabaseAdapter:
    """Database adapter for both SQLite and MySQL"""
    
    def __init__(self):
        self.db_type = DB_TYPE
        
    def get_connection(self):
        """Get database connection based on configured type"""
        try:
            if self.db_type == "sqlite":
                ensure_db_directory()
                return sqlite3.connect(DB_PATH)
            elif self.db_type == "mysql":
                import mysql.connector
                return mysql.connector.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME
                )
            else:
                logger.error(f"Unknown database type: {self.db_type}")
                raise ValueError(f"Unknown database type: {self.db_type}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.db_type} database: {e}")
            raise

def ensure_db_directory():
    """Ensure the directory for the SQLite database file exists."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:  
        try:
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Database directory ensured: {db_dir}")
        except OSError as e:
            logger.error(f"Failed to create database directory {db_dir}: {e}")
            raise

db_adapter = DatabaseAdapter()
