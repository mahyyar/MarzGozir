import logging
import os
from .db_adapter import db_adapter
from bot_config import DB_TYPE, DB_PATH

logger = logging.getLogger(__name__)

def init_db():
    """Initialize the database and create necessary tables."""
    try:
        conn = db_adapter.get_connection()
        c = conn.cursor()
        
        if DB_TYPE == "sqlite":
            # SQLite syntax
            c.execute('''
                CREATE TABLE IF NOT EXISTS panels (
                    chat_id INTEGER,
                    alias TEXT,
                    panel_url TEXT,
                    token TEXT,
                    username TEXT,
                    password TEXT,
                    PRIMARY KEY (chat_id, alias)
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    chat_id INTEGER PRIMARY KEY
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS log_channel (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER UNIQUE
                )
            ''')
        elif DB_TYPE == "mysql":
            # MySQL syntax
            c.execute('''
                CREATE TABLE IF NOT EXISTS panels (
                    chat_id BIGINT,
                    alias VARCHAR(255),
                    panel_url VARCHAR(255),
                    token VARCHAR(255),
                    username VARCHAR(255),
                    password VARCHAR(255),
                    PRIMARY KEY (chat_id, alias)
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    chat_id BIGINT PRIMARY KEY
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS log_channel (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    channel_id BIGINT UNIQUE
                )
            ''')
        
        conn.commit()
        logger.info(f"Database initialized successfully. Type: {DB_TYPE}")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

def save_panel(chat_id: int, alias: str, panel_url: str, token: str, username: str, password: str):
    """Save or update a panel in the database."""
    try:
        conn = db_adapter.get_connection()
        c = conn.cursor()
        
        if DB_TYPE == "sqlite":
            c.execute('''
                INSERT OR REPLACE INTO panels (chat_id, alias, panel_url, token, username, password)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (chat_id, alias, panel_url, token, username, password))
        elif DB_TYPE == "mysql":
            c.execute('''
                INSERT INTO panels (chat_id, alias, panel_url, token, username, password)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                panel_url=%s, token=%s, username=%s, password=%s
            ''', (chat_id, alias, panel_url, token, username, password, panel_url, token, username, password))
            
        conn.commit()
        logger.info(f"Panel saved for chat_id {chat_id}, alias {alias}")
    except Exception as e:
        logger.error(f"Error saving panel for chat_id {chat_id}, alias {alias}: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def get_panels(chat_id: int) -> list:
    """Retrieve all panels for a given chat_id."""
    try:
        conn = db_adapter.get_connection()
        c = conn.cursor()
        
        c.execute('SELECT alias, panel_url, token, username, password FROM panels WHERE chat_id = %s' % ('?' if DB_TYPE == "sqlite" else '%s'), (chat_id,))
        
        if DB_TYPE == "sqlite":
            panels = c.fetchall()
        else:
            # MySQL connector returns a different cursor object
            panels = [row for row in c]
            
        logger.info(f"Fetched {len(panels)} panels for chat_id {chat_id}")
        return panels
    except Exception as e:
        logger.error(f"Error fetching panels for chat_id {chat_id}: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def delete_panel(chat_id: int, alias: str):
    """Delete a panel from the database."""
    try:
        conn = db_adapter.get_connection()
        c = conn.cursor()
        
        c.execute('DELETE FROM panels WHERE chat_id = %s AND alias = %s' % ('?' if DB_TYPE == "sqlite" else '%s'), (chat_id, alias))
        conn.commit()
        logger.info(f"Panel deleted for chat_id {chat_id}, alias {alias}")
    except Exception as e:
        logger.error(f"Error deleting panel for chat_id {chat_id}, alias {alias}: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def add_admin(chat_id: int):
    """Add a chat_id to the admins table."""
    try:
        conn = db_adapter.get_connection()
        c = conn.cursor()
        
        if DB_TYPE == "sqlite":
            c.execute('INSERT OR IGNORE INTO admins (chat_id) VALUES (?)', (chat_id,))
        elif DB_TYPE == "mysql":
            c.execute('INSERT IGNORE INTO admins (chat_id) VALUES (%s)', (chat_id,))
            
        conn.commit()
        logger.info(f"Admin added: chat_id {chat_id}")
    except Exception as e:
        logger.error(f"Error adding admin chat_id {chat_id}: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def remove_admin(chat_id: int):
    """Remove a chat_id from the admins table."""
    try:
        conn = db_adapter.get_connection()
        c = conn.cursor()
        
        c.execute('DELETE FROM admins WHERE chat_id = %s' % ('?' if DB_TYPE == "sqlite" else '%s'), (chat_id,))
        conn.commit()
        logger.info(f"Admin removed: chat_id {chat_id}")
    except Exception as e:
        logger.error(f"Error removing admin chat_id {chat_id}: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def get_admins() -> list:
    """Retrieve all admin chat_ids."""
    try:
        conn = db_adapter.get_connection()
        c = conn.cursor()
        
        c.execute('SELECT chat_id FROM admins')
        
        if DB_TYPE == "sqlite":
            admins = [row[0] for row in c.fetchall()]
        else:
            # MySQL connector returns a different cursor object
            admins = [row[0] for row in c]
            
        logger.info(f"Fetched {len(admins)} admins")
        return admins
    except Exception as e:
        logger.error(f"Error fetching admins: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def set_log_channel(channel_id: int):
    """Set the log channel ID."""
    try:
        conn = db_adapter.get_connection()
        c = conn.cursor()
        
        if DB_TYPE == "sqlite":
            c.execute('INSERT OR REPLACE INTO log_channel (id, channel_id) VALUES (1, ?)', (channel_id,))
        elif DB_TYPE == "mysql":
            c.execute('''
                INSERT INTO log_channel (id, channel_id) VALUES (1, %s)
                ON DUPLICATE KEY UPDATE channel_id=%s
            ''', (channel_id, channel_id))
            
        conn.commit()
        logger.info(f"Log channel set to {channel_id}")
    except Exception as e:
        logger.error(f"Error setting log channel {channel_id}: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def get_log_channel() -> int:
    """Retrieve the log channel ID."""
    try:
        conn = db_adapter.get_connection()
        c = conn.cursor()
        
        c.execute('SELECT channel_id FROM log_channel WHERE id = 1')
        
        if DB_TYPE == "sqlite":
            result = c.fetchone()
        else:
            # MySQL connector returns a different cursor object
            result = next(iter(c), None)
            
        channel_id = result[0] if result else None
        logger.info(f"Fetched log channel: {channel_id}")
        return channel_id
    except Exception as e:
        logger.error(f"Error fetching log channel: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

try:
    init_db()
except Exception as e:
    logger.error(f"Failed to initialize database on startup: {e}")
