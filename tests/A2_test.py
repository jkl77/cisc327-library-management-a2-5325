# Unit Tests

import pytest
import sys
import os
from uuid import uuid4 
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.library_service import (
    add_book_to_catalog,
    borrow_book_by_patron,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report
)

from database import (
    get_all_books,
    get_book_by_id,
    init_database, 
    add_sample_data 
)

@pytest.fixture(autouse=True, scope="function")
def setup_db_for_test():
    """Clears and reloads sample data before EVERY test to ensure tables exist and state is consistent."""
    init_database()
    add_sample_data()

# R1 Tests: Add a Book to the Catalog

def test_add_book_valid_input():
    """Add a book with all valid inputs."""
    unique_isbn = str(uuid4().int)[:13]
    success, message = add_book_to_catalog("Test Book A", "Test Author A", unique_isbn, 5)
    assert success is True
    assert "successfully" in message.lower()

def test_add_book_missing_title():
    """Add book with missing title should fail."""
    success, message = add_book_to_catalog("", "Author", "1234567890123", 2)
    assert success is False
    assert "title" in message.lower()

def test_add_book_author_too_long():
    """Add book with author name longer than 100 chars should fail."""
    success, message = add_book_to_catalog("Book1", "A" * 101, "1234567890123", 2)
    assert success is False
    assert "author" in message.lower()

def test_add_book_invalid_isbn():
    """Add book with invalid ISBN length should fail."""
    success, message = add_book_to_catalog("Book2", "Author", "123", 2)
    assert success is False
    assert "13 digits" in message

def test_add_book_invalid_copies():
    """Add book with negative copies should fail."""
    success, message = add_book_to_catalog("Book3", "Author", "1234567890123", -1)
    assert success is False
    assert "positive" in message.lower()

# New R1 Tests

def test_add_book_title_too_long():
    """Test adding a book with title longer than 200 chars should fail."""
    long_title = "A" * 201
    unique_isbn = str(uuid4().int)[:13]
    success, message = add_book_to_catalog(long_title, "Author A", unique_isbn, 1)
    assert success == False
    assert "200 characters" in message

def test_add_book_duplicate_isbn():
    """Test adding a book with an existing ISBN should fail."""
    duplicate_isbn = str(uuid4().int)[:13]
    add_book_to_catalog("Original Book", "Author B", duplicate_isbn, 1) 
    success, message = add_book_to_catalog("Duplicate Book", "Author C", duplicate_isbn, 1)
    assert success == False
    assert "already exists" in message

# R2 Tests: Checking the Book Catalog Display

def test_catalog_fetch_returns_list(): 
    """Catalog fetch should return a list (using get_all_books).""" 
    catalog = get_all_books() 
    assert isinstance(catalog, list) 

def test_catalog_contains_required_fields(): 
    """Catalog entries should contain all required database fields.""" 
    catalog = get_all_books()
    required_fields = ["id", "title", "author", "isbn", "total_copies", "available_copies"]
    if catalog: 
        book = catalog[0] 
        assert all(k in book for k in required_fields) 

def test_catalog_shows_available_vs_total(): 
    """Available copies should never exceed total copies. Relies on clean sample data setup.""" 
    catalog = get_all_books() 
    for book in catalog: 
        assert 0 <= book["available_copies"] <= book["total_copies"] 

def test_catalog_empty_case(): 
    """Tests empty state.""" 
    init_database() # Clears tables but does not load sample data
    catalog = get_all_books() 
    assert catalog == [] 

def test_catalog_includes_id_field(): 
    """Each catalog row must include the 'id' field for UI actions like 'borrow'.""" 
    catalog = get_all_books() 
    if catalog: 
        assert "id" in catalog[0] 

# R3 Tests: Checking the Book Borrowing Functionality

def test_borrow_valid_case():
    """Borrow book successfully with valid patron and available book."""
    success, message = borrow_book_by_patron("123456", 1) 
    assert success is True

def test_borrow_invalid_patron_id():
    """Borrow with invalid patron ID (not 6 digits)."""
    success, message = borrow_book_by_patron("12", 1)
    assert success is False

def test_borrow_book_not_found():
    """Borrow with non-existent book ID should fail."""
    success, message = borrow_book_by_patron("123456", 9999)
    assert success is False

def test_borrow_unavailable_book():
    """Borrow unavailable book should fail."""
    success, message = borrow_book_by_patron("123456", 3) 
    assert success is False

def test_borrow_exceeds_limit():
    """FIX: Borrow when patron already has 5 books should fail."""
    # Patron 654321 is set up with 5 active loans by the autouse fixture
    success, message = borrow_book_by_patron("654321", 7) 
    assert success is False
    assert "maximum borrowing limit" in message

# New R3 Test

def test_borrow_invalid_patron_id_non_digit():
    """Test borrowing with invalid patron ID (contains non-digits)."""
    success, message = borrow_book_by_patron("12345A", 1)
    assert success == False
    assert "digits" in message

# R4 Tests: Validating the Book Return Processes

def test_return_book_success():
    """Return a borrowed book successfully."""
    # Note: Using Book 3 loan from sample data (Patron 123456)
    success, message = return_book_by_patron("123456", 3)
    assert success is True

def test_return_book_not_borrowed():
    """Return a book not borrowed by patron should fail."""
    success, message = return_book_by_patron("123456", 99)
    assert success is False

def test_return_invalid_patron_id():
    """Return with invalid patron ID should fail."""
    success, message = return_book_by_patron("abc", 1)
    assert success is False

def test_return_updates_available_copies():
    """Returning book should increase available copies."""
    borrow_book_by_patron("123456", 1)
    book = get_book_by_id(1)
    before = book["available_copies"]
    return_book_by_patron("123456", 1)
    book = get_book_by_id(1)
    after = book["available_copies"]
    assert after == before + 1

# R5 Tests: Validating Proper Late Fee Calculation

def test_late_fee_on_time():
    """No fee when book returned on time."""
    result = calculate_late_fee_for_book("123456", 1)
    assert result["fee_amount"] == 0.0

def test_late_fee_within_7_days():
    """FIX: Fee should be $0.50/day up to 7 days (Patron 777777 is 2 days overdue)."""
    # Patron 777777 loan is 2 days overdue in sample data: 2 * $0.50 = $1.00
    result = calculate_late_fee_for_book("777777", 1) 
    assert result["fee_amount"] == 1.00

def test_late_fee_after_7_days():
    """FIX: Fee increases to $1/day after first 7 days (Patron 888888 is 8 days overdue)."""
    # Patron 888888 loan is 8 days overdue: (7 * $0.50) + (1 * $1.00) = $4.50
    result = calculate_late_fee_for_book("888888", 1)
    assert result["fee_amount"] == 4.50

def test_late_fee_cap():
    """FIX: Fee should not exceed $15 max (Patron 999999 is 22 days overdue)."""
    # Patron 999999 loan is 22 days overdue, calculation yields $18.50, capped at $15.00
    result = calculate_late_fee_for_book("999999", 1)
    assert result["fee_amount"] == 15.00

# New R5 Test

def test_late_fee_book_not_in_catalog():
    """Tests calculate_late_fee_for_book when the book ID does not exist in the catalog."""
    result = calculate_late_fee_for_book("123456", 9999) 
    assert result['fee_amount'] == 0.00
    assert result['days_overdue'] == 0
    assert "Book not found" in result['status']

# R6 Tests: Ensuring the Book Search Function Works Properly

def test_search_by_title_partial():
    """Search should return partial match on title."""
    results = search_books_in_catalog("gatsby", "title")
    assert any("gatsby" in b["title"].lower() for b in results)

def test_search_by_author_partial():
    """Search should return partial match on author."""
    results = search_books_in_catalog("orwell", "author")
    assert any("orwell" in b["author"].lower() for b in results)

def test_search_by_isbn_exact():
    """Search should only match exact ISBN."""
    results = search_books_in_catalog("9780743273565", "isbn")
    assert all(b["isbn"] == "9780743273565" for b in results)

def test_search_invalid_type():
    """Search with invalid type should return empty list."""
    results = search_books_in_catalog("something", "invalid")
    assert results == []

def test_search_empty_query_returns_all():
    """Test empty search query returns ALL books."""
    results = search_books_in_catalog("   ", "title")
    assert isinstance(results, list)
    assert len(results) > 0 

# R7 Tests: Checking the Customer Status Report Function

def test_patron_status_structure():
    """Status report should include correct required fields."""
    report = get_patron_status_report("123456")
    expected_keys = [
        "patron_id", 
        "currently_borrowed_count", 
        "total_late_fees_owed", 
        "currently_borrowed_books", 
        "borrowing_history"
    ]
    assert all(k in report for k in expected_keys)

def test_patron_status_valid_patron():
    """Report for valid patron should return dictionary."""
    report = get_patron_status_report("123456")
    assert isinstance(report, dict)

def test_patron_status_invalid_patron():
    """Invalid patron ID should return error structure."""
    report = get_patron_status_report("badid")
    assert "error" in report

def test_patron_status_late_fees_format():
    """Use corrected key 'total_late_fees_owed'."""
    report = get_patron_status_report("123456")
    assert isinstance(report["total_late_fees_owed"], float)

def test_patron_status_borrow_limit_tracking():
    """Use corrected key 'currently_borrowed_count'."""
    report = get_patron_status_report("123456")
    assert report["currently_borrowed_count"] >= 0

# New R7 Tests

def test_patron_status_correct_structure_new_keys():
    """Test the final, correct report structure and types."""
    report = get_patron_status_report("123456") 
    expected_keys = {
        'patron_id', 
        'currently_borrowed_count', 
        'total_late_fees_owed', 
        'currently_borrowed_books', 
        'borrowing_history'
    }
    assert expected_keys.issubset(report.keys())
    assert isinstance(report['currently_borrowed_count'], int)
    assert isinstance(report['total_late_fees_owed'], float)
    assert isinstance(report['currently_borrowed_books'], list)
    assert isinstance(report['borrowing_history'], list)

def test_patron_status_no_loans():
    """Test status report for a patron with no loan history."""
    PATRON_ID = "000000" # Patron not set up in sample data
    report = get_patron_status_report(PATRON_ID)
    
    assert report['patron_id'] == PATRON_ID
    assert report['currently_borrowed_count'] == 0
    assert report['total_late_fees_owed'] == 0.00
    assert report['currently_borrowed_books'] == []
    assert report['borrowing_history'] == []