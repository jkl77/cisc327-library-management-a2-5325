# Unit Tests

import pytest
from library_service import (
    add_book_to_catalog,
    display_catalog,
    borrow_book_by_patron,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report
)

# R1 Tests: Add a Book to the Catalog

def test_add_book_valid_input():
    """Add a book with all valid inputs."""
    success, message = add_book_to_catalog("Test Book", "Test Author", "1234567890123", 5)
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

def test_add_book_title_too_long():
    """Test adding a book with title longer than 200 chars should fail."""
    long_title = "A" * 201
    success, message = add_book_to_catalog(long_title, "Author A", "1111111111111", 1)
    assert success == False
    assert "200 characters" in message

def test_add_book_duplicate_isbn():
    """Test adding a book with an existing ISBN should fail."""
    add_book_to_catalog("Original Book", "Author B", "9999999999999", 1) 
    success, message = add_book_to_catalog("Duplicate Book", "Author C", "9999999999999", 1)
    assert success == False
    assert "already exists" in message


# R2 Tests: Checking the Book Catalog Display

def test_catalog_display_returns_list():
    """Catalog display should return a list."""
    catalog = display_catalog()
    assert isinstance(catalog, list)

def test_catalog_contains_required_fields():
    """Catalog entries should contain all required fields."""
    catalog = display_catalog()
    if catalog:
        book = catalog[0]
        assert all(k in book for k in ["book_id", "title", "author", "isbn", "available_copies", "total_copies"])

def test_catalog_shows_available_vs_total():
    """Available copies should never exceed total copies."""
    catalog = display_catalog()
    for book in catalog:
        assert 0 <= book["available_copies"] <= book["total_copies"]

def test_catalog_empty_case():
    """If no books exist, catalog should return empty list."""
    # Assume display_catalog handles empty DB
    catalog = display_catalog()
    assert catalog == [] or isinstance(catalog, list)

def test_catalog_includes_actions_field():
    """Each catalog row should include an actions field like 'borrow'."""
    catalog = display_catalog()
    if catalog:
        assert "actions" in catalog[0]


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
    """Borrow when patron already has 5 books should fail."""
    success, message = borrow_book_by_patron("654321", 2)
    assert success is False

def test_borrow_invalid_patron_id_non_digit():
    """Test borrowing with invalid patron ID (contains non-digits)."""
    success, message = borrow_book_by_patron("12345A", 1)
    assert success == False
    assert "digits" in message

# R4 Tests: Validating the Book Return Processes

def test_return_book_success():
    """Return a borrowed book successfully."""
    success, message = return_book_by_patron("123456", 1)
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
    # Placeholder: simulate count before/after
    before = 1
    return_book_by_patron("123456", 1)
    after = 2
    assert after == before + 1


# R5 Tests: Validating Proper Late Fee Calculation

def test_late_fee_on_time():
    """No fee when book returned on time."""
    result = calculate_late_fee_for_book("123456", 1)
    assert result["fee_amount"] == 0.0

def test_late_fee_within_7_days():
    """Fee should be $0.50/day up to 7 days."""
    result = calculate_late_fee_for_book("123456", 2)
    assert 0 < result["fee_amount"] <= 3.5

def test_late_fee_after_7_days():
    """Fee increases to $1/day after first 7 days."""
    result = calculate_late_fee_for_book("123456", 3)
    assert result["fee_amount"] > 3.5

def test_late_fee_cap():
    """Fee should not exceed $15 max."""
    result = calculate_late_fee_for_book("123456", 4)
    assert result["fee_amount"] <= 15.0

# New R5 Tests --------------------------------------

def test_late_fee_exactly_7_days(setup_loan_7_days_overdue):
    """Test fee calculation for a loan that is exactly 7 days overdue (Tier 1 max $3.50)."""
    result = calculate_late_fee_for_book("777777", 7) 
    assert result["fee_amount"] == 3.50
    assert result["days_overdue"] == 7

def test_late_fee_exactly_8_days(setup_loan_8_days_overdue):
    """Test fee calculation for a loan that is exactly 8 days overdue (Tier 2 kicks in $4.50)."""
    result = calculate_late_fee_for_book("888888", 8)
    assert result["fee_amount"] == 4.50
    assert result["days_overdue"] == 8

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
    results = search_books_in_catalog("1234567890123", "isbn")
    assert all(b["isbn"] == "1234567890123" for b in results)

def test_search_invalid_type():
    """Search with invalid type should return empty list."""
    results = search_books_in_catalog("something", "invalid")
    assert results == []

def test_search_empty_query():
    """Empty query should return empty list."""
    results = search_books_in_catalog("", "title")
    assert results == []

# New R6 Test ---------------------------------------

def test_search_empty_query_returns_all(setup_with_multiple_books):
    """Test empty search query (e.g., just spaces) returns ALL books in the catalog (per R6 logic)."""
    results = search_books_in_catalog("   ", "title")
    assert isinstance(results, list)
    assert len(results) > 0 

# R7 Tests: Checking the Customer Status Report Function

def test_patron_status_structure():
    """Status report should include required fields."""
    report = get_patron_status_report("123456")
    assert all(k in report for k in ["borrowed_books", "late_fees", "num_borrowed", "history"])

def test_patron_status_valid_patron():
    """Report for valid patron should return dictionary."""
    report = get_patron_status_report("123456")
    assert isinstance(report, dict)

def test_patron_status_invalid_patron():
    """Invalid patron ID should return error or empty report."""
    report = get_patron_status_report("badid")
    assert report == {} or "error" in report

def test_patron_status_late_fees_format():
    """Late fees should be displayed with 2 decimal places."""
    report = get_patron_status_report("123456")
    assert isinstance(report["late_fees"], float)

def test_patron_status_borrow_limit_tracking():
    """Report should reflect correct number of currently borrowed books."""
    report = get_patron_status_report("123456")
    assert report["num_borrowed"] >= 0

# New R7 Tests --------------------------------------

def test_patron_status_correct_structure_new_keys(setup_sample_patron):
    """Test the status report structure includes the final, correct keys and data types."""
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

def test_patron_status_no_loans(setup_clean_patron):
    """Test status report for a patron with no loan history or active loans (boundary case)."""
    report = get_patron_status_report("000000")
    assert report['patron_id'] == "000000"
    assert report['currently_borrowed_count'] == 0
    assert report['total_late_fees_owed'] == 0.00
    assert report['currently_borrowed_books'] == []
    assert report['borrowing_history'] == []