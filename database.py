"""
Database module for Library Management System
Handles all database operations and connections
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Database configuration
DATABASE = 'library.db'

def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

def init_database():
    """FIX: Initialize the database by dropping and recreating tables for a clean slate."""
    conn = get_db_connection()
    
    # Drop existing tables to ensure a clean state
    conn.execute('DROP TABLE IF EXISTS borrow_records')
    conn.execute('DROP TABLE IF EXISTS books')
    
    # Create books table
    conn.execute('''
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE NOT NULL,
            total_copies INTEGER NOT NULL,
            available_copies INTEGER NOT NULL
        )
    ''')
    
    # Create borrow_records table
    conn.execute('''
        CREATE TABLE borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patron_id TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            borrow_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY (book_id) REFERENCES books (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_sample_data():
    """FIX: Corrected book availability and ensured Patron 654321 has 5 loans for limit test."""
    conn = get_db_connection()
    book_count = conn.execute('SELECT COUNT(*) as count FROM books').fetchone()['count']
    
    if book_count == 0:
        # Initial Books for various tests
        sample_books = [
            ('The Great Gatsby', 'F. Scott Fitzgerald', '9780743273565', 3), # Book ID 1
            ('To Kill a Mockingbird', 'Harper Lee', '9780061120084', 2), # Book ID 2
            ('1984', 'George Orwell', '9780451524935', 1), # Book ID 3 (Unavailable test case)
            ('Moby Dick', 'Herman Melville', '9781503280786', 1), # Book ID 4 (Used for Patron 654321 limit)
            ('War and Peace', 'Leo Tolstoy', '9780199232765', 1), # Book ID 5 (Used for Patron 654321 limit)
            ('Pride and Prejudice', 'Jane Austen', '9780141439518', 1), # Book ID 6 (Used for Patron 654321 limit)
            ('The Odyssey', 'Homer', '9780140268867', 1) # Book ID 7 (The available book for the limit test attempt)
        ]
        
        for title, author, isbn, copies in sample_books:
            conn.execute('''
                INSERT INTO books (title, author, isbn, total_copies, available_copies)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, author, isbn, copies, copies))
        
        # 1. Set up Patron '123456' with one loan (1984, Book ID 3)
        conn.execute('''
            INSERT INTO borrow_records (patron_id, book_id, borrow_date, due_date)
            VALUES (?, ?, ?, ?)
        ''', ('123456', 3, 
              (datetime.now() - timedelta(days=5)).isoformat(),
              (datetime.now() + timedelta(days=9)).isoformat()))
        conn.execute('UPDATE books SET available_copies = 0 WHERE id = 3') # Book 3 now unavailable
        
        # 2. Set up Patron '654321' with max loans (5) to fail the limit test (R3)
        patron_id_limit = '654321'
        # Borrow Books IDs 1, 2, 4, 5, 6 (5 loans total)
        limit_loans = [1, 2, 4, 5, 6] 
        
        for book_id in limit_loans:
            conn.execute('''
                INSERT INTO borrow_records (patron_id, book_id, borrow_date, due_date)
                VALUES (?, ?, ?, ?)
            ''', (patron_id_limit, book_id, 
                  (datetime.now() - timedelta(days=2)).isoformat(),
                  (datetime.now() + timedelta(days=12)).isoformat()))
            conn.execute('UPDATE books SET available_copies = available_copies - 1 WHERE id = ?', (book_id,))
            
        conn.commit()
    
    conn.close()

# Helper Functions for Database Operations

def get_all_books() -> List[Dict]:
    """Get all books from the database."""
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books ORDER BY title').fetchall()
    conn.close()
    return [dict(book) for book in books]

def get_book_by_id(book_id: int) -> Optional[Dict]:
    """Get a specific book by ID."""
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()
    return dict(book) if book else None

def get_book_by_isbn(isbn: str) -> Optional[Dict]:
    """Get a specific book by ISBN."""
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE isbn = ?', (isbn,)).fetchone()
    conn.close()
    return dict(book) if book else None

# Changed this so it pulls all borrowed books (Current & historical) for patron status report
def get_patron_borrowed_books(patron_id: str) -> List[Dict]:
    """Get all borrowed books for a patron."""
    conn = get_db_connection()
    records = conn.execute('''
        SELECT br.*, b.title, b.author 
        FROM borrow_records br 
        JOIN books b ON br.book_id = b.id 
        WHERE br.patron_id = ?
        ORDER BY br.borrow_date DESC
    ''', (patron_id,)).fetchall()
    conn.close()
    
    borrowed_books = []
    for record in records:
        return_date_str = record['return_date']
        # Convert return_date to datetime object only if it's not None
        return_date = datetime.fromisoformat(return_date_str) if return_date_str else None

        borrowed_books.append({
            'book_id': record['book_id'],
            'title': record['title'],
            'author': record['author'],
            'borrow_date': datetime.fromisoformat(record['borrow_date']),
            'due_date': datetime.fromisoformat(record['due_date']),
            'is_overdue': datetime.now() > datetime.fromisoformat(record['due_date']),
            'return_date': return_date,
        })
    
    return borrowed_books

def get_patron_borrow_count(patron_id: str) -> int:
    """Get the number of books currently borrowed by a patron."""
    conn = get_db_connection()
    count = conn.execute('''
        SELECT COUNT(*) as count FROM borrow_records 
        WHERE patron_id = ? AND return_date IS NULL
    ''', (patron_id,)).fetchone()['count']
    conn.close()
    return count

def insert_book(title: str, author: str, isbn: str, total_copies: int, available_copies: int) -> bool:
    """Insert a new book into the database."""
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO books (title, author, isbn, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, author, isbn, total_copies, available_copies))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False

def insert_borrow_record(patron_id: str, book_id: int, borrow_date: datetime, due_date: datetime) -> bool:
    """Insert a new borrow record into the database."""
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO borrow_records (patron_id, book_id, borrow_date, due_date)
            VALUES (?, ?, ?, ?)
        ''', (patron_id, book_id, borrow_date.isoformat(), due_date.isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False

def update_book_availability(book_id: int, change: int) -> bool:
    """Update the available copies of a book by a given amount (+1 for return, -1 for borrow)."""
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE books SET available_copies = available_copies + ? WHERE id = ?
        ''', (change, book_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False

def update_borrow_record_return_date(patron_id: str, book_id: int, return_date: datetime) -> bool:
    """Update the return date for a borrow record."""
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE borrow_records 
            SET return_date = ? 
            WHERE patron_id = ? AND book_id = ? AND return_date IS NULL
        ''', (return_date.isoformat(), patron_id, book_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False