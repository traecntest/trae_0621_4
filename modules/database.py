import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH, CATEGORIES


class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        self.db_path = DB_PATH
        self._create_tables()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                location TEXT DEFAULT '',
                category TEXT DEFAULT '其他',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                notified INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_expiry_date ON inventory(expiry_date)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_category ON inventory(category)
        ''')
        conn.commit()
        conn.close()

    def add_item(self, name: str, expiry_date: str, location: str = '', category: str = '') -> int:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not category:
            category = self._auto_categorize(name)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO inventory (name, expiry_date, location, category, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, expiry_date, location, category, now, now))
        item_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return item_id

    def update_item(self, item_id: int, name: str = None, expiry_date: str = None,
                    location: str = None, category: str = None) -> bool:
        updates = []
        params = []
        if name is not None:
            updates.append('name = ?')
            params.append(name)
            if category is None:
                category = self._auto_categorize(name)
        if expiry_date is not None:
            updates.append('expiry_date = ?')
            params.append(expiry_date)
        if location is not None:
            updates.append('location = ?')
            params.append(location)
        if category is not None:
            updates.append('category = ?')
            params.append(category)
        if not updates:
            return False
        updates.append('updated_at = ?')
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        params.append(item_id)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            UPDATE inventory SET {', '.join(updates)} WHERE id = ?
        ''', params)
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0

    def delete_item(self, item_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0

    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM inventory WHERE id = ?', (item_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_all_items(self, category: str = None, sort_by: str = 'expiry_date',
                      ascending: bool = True) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        query = 'SELECT * FROM inventory'
        params = []
        if category and category != '全部':
            query += ' WHERE category = ?'
            params.append(category)
        order = 'ASC' if ascending else 'DESC'
        if sort_by == 'expiry_date':
            query += f' ORDER BY DATE(expiry_date) {order}'
        elif sort_by == 'name':
            query += f' ORDER BY name {order}'
        elif sort_by == 'created_at':
            query += f' ORDER BY created_at {order}'
        else:
            query += f' ORDER BY DATE(expiry_date) ASC'
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_expiring_items(self, within_days: int = 3) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM inventory
            WHERE DATE(expiry_date) <= DATE('now', '+' || ? || ' days')
            ORDER BY DATE(expiry_date) ASC
        ''', (within_days,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_expired_items(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM inventory
            WHERE DATE(expiry_date) < DATE('now')
            ORDER BY DATE(expiry_date) DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def mark_as_notified(self, item_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE inventory SET notified = 1 WHERE id = ?', (item_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0

    def reset_notified(self, item_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE inventory SET notified = 0 WHERE id = ?', (item_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        return rows_affected > 0

    def get_stats(self) -> Dict[str, int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM inventory')
        total = cursor.fetchone()[0]
        cursor.execute('''
            SELECT COUNT(*) FROM inventory
            WHERE DATE(expiry_date) < DATE('now')
        ''')
        expired = cursor.fetchone()[0]
        cursor.execute('''
            SELECT COUNT(*) FROM inventory
            WHERE DATE(expiry_date) BETWEEN DATE('now') AND DATE('now', '+3 days')
        ''')
        expiring_3d = cursor.fetchone()[0]
        cursor.execute('''
            SELECT COUNT(*) FROM inventory
            WHERE DATE(expiry_date) BETWEEN DATE('now') AND DATE('now', '+7 days')
        ''')
        expiring_7d = cursor.fetchone()[0]
        conn.close()
        return {
            'total': total,
            'expired': expired,
            'expiring_3d': expiring_3d,
            'expiring_7d': expiring_7d
        }

    def _auto_categorize(self, name: str) -> str:
        for category, info in CATEGORIES.items():
            if category == '全部' or category == '其他':
                continue
            for keyword in info['keywords']:
                if keyword in name:
                    return category
        return '其他'

    def search_items(self, keyword: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM inventory
            WHERE name LIKE ? OR location LIKE ?
            ORDER BY DATE(expiry_date) ASC
        ''', (f'%{keyword}%', f'%{keyword}%'))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
