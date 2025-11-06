"""
Library Service Module - Business Logic Functions
Contains all the core business logic for the Library Management System
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database import (
    get_book_by_id, get_book_by_isbn, get_patron_borrow_count,
    insert_book, insert_borrow_record, update_book_availability,
    update_borrow_record_return_date, get_all_books, get_patron_borrowed_books
)
from .payment_service import PaymentGateway

def add_book_to_catalog(title: str, author: str, isbn: str, total_copies: int) -> Tuple[bool, str]:
    """
    Add a new book to the catalog.
    Implements R1: Book Catalog Management
    
    Args:
        title: Book title (max 200 chars)
        author: Book author (max 100 chars)
        isbn: 13-digit ISBN
        total_copies: Number of copies (positive integer)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    if not title or not title.strip():
        return False, "Title is required."
    
    if len(title.strip()) > 200:
        return False, "Title must be less than 200 characters."
    
    if not author or not author.strip():
        return False, "Author is required."
    
    if len(author.strip()) > 100:
        return False, "Author must be less than 100 characters."
    
    if len(isbn) != 13:
        return False, "ISBN must be exactly 13 digits."
    
    if not isinstance(total_copies, int) or total_copies <= 0:
        return False, "Total copies must be a positive integer."
    
    # Check for duplicate ISBN
    existing = get_book_by_isbn(isbn)
    if existing:
        return False, "A book with this ISBN already exists."
    
    # Insert new book
    success = insert_book(title.strip(), author.strip(), isbn, total_copies, total_copies)
    if success:
        return True, f'Book "{title.strip()}" has been successfully added to the catalog.'
    else:
        return False, "Database error occurred while adding the book."

def borrow_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Allow a patron to borrow a book.
    Implements R3 as per requirements  
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
    
    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."
    
    if book['available_copies'] <= 0:
        return False, "This book is currently not available."
    
    # Check patron's current borrowed books count
    current_borrowed = get_patron_borrow_count(patron_id)
    
    if current_borrowed >= 5:
        return False, "You have reached the maximum borrowing limit of 5 books."
    
    # Create borrow record
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=14)
    
    # Insert borrow record and update availability
    borrow_success = insert_borrow_record(patron_id, book_id, borrow_date, due_date)
    if not borrow_success:
        return False, "Database error occurred while creating borrow record."
    
    availability_success = update_book_availability(book_id, -1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."
    
    return True, f'Successfully borrowed "{book["title"]}". Due date: {due_date.strftime("%Y-%m-%d")}.'

def return_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Process book return by a patron.
    Implements R4: Book Return Processing
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book being returned
        
    Returns:
        tuple: (success: bool, message: str)
    """

    # Input Validation (Patron ID)
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."
        
    # Verify loan status
    borrowed_books = get_patron_borrowed_books(patron_id)
    
    # Find the specific open record for this book ID
    borrow_record = next(
        (book for book in borrowed_books if book['book_id'] == book_id), 
        None
    )
    
    if not borrow_record:
        return False, "No active borrowing record found for this book and patron."

    # Update the borrow record with the return date
    update_success = update_borrow_record_return_date(patron_id, book_id, datetime.now())
    if not update_success:
        return False, "Database error occurred while recording the return date."
        
    # Update book availability (increase available copies by 1)
    availability_success = update_book_availability(book_id, 1)
    if not availability_success:
        return False, "Database error occurred while incrementing book availability."
    
    # Retrieve the necessary data for message
    book = get_book_by_id(book_id)
    book_title = book['title']

    # Calculate late fees
    fee_details = calculate_late_fee_for_book(patron_id, book_id)
    late_fee = fee_details['fee_amount']
    overdue_days = fee_details['days_overdue']
    fee_message = ""
    
    if late_fee > 0:
        fee_message = f" A late fee of ${late_fee:.2f} has been added to your account for {overdue_days} day(s) overdue."

    return True, f'Successfully returned "{book_title}".{fee_message}'

def calculate_late_fee_for_book(patron_id: str, book_id: int) -> Dict:
    """
    Calculates late fees for a specific book based on R5 tiered rules.
    Implements R5: Late Fee Calculation.

    Args:
        patron_id: 6-digit library card ID.
        book_id: ID of the book to check.

    Returns:
        Dict: {'fee_amount': float, 'days_overdue': int, 'status': str}
    """

    # Late Fee Constants
    FEE_RATE_TIER1 = 0.50  # $0.50/day for days 1-7 (Tier 1 fee)
    FEE_RATE_TIER2 = 1.00  # $1.00/day for days 8+ (Tier 2 fee)
    MAX_FEE_PER_BOOK = 15.00  # Maximum $15.00 fee per book

    # Input Validation (Patron ID)
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return {'fee_amount': 0.00, 'days_overdue': 0, 'status': 'Invalid patron ID format.'}

    # Find the specific borrowed book
    borrowed_books = get_patron_borrowed_books(patron_id)
    borrow_record = next(
        (book for book in borrowed_books if book['book_id'] == book_id),
        None
    )

    if not borrow_record:
        # Check if book exists
        book = get_book_by_id(book_id)

        if not book:
            return {'fee_amount': 0.00, 'days_overdue': 0, 'status': 'Book not found.'}

        return {'fee_amount': 0.00, 'days_overdue': 0, 'status': 'Book is not currently borrowed by this patron.'}

    due_date: datetime = borrow_record['due_date']

    if borrow_record['return_date'] is None:
        calculation_date: datetime = datetime.now() # Use current time
    else:
        calculation_date = borrow_record['return_date']

    # Calculate overdue days based on calendar dates
    overdue_days = (calculation_date.date() - due_date.date()).days

    if overdue_days <= 0:
        return {'fee_amount': 0.00, 'days_overdue': 0, 'status': 'Not overdue.'}

    late_fee_calc = 0.0

    # Tier 1 fees: Days 1 through 7
    tier1_days = min(overdue_days, 7)
    late_fee_calc += tier1_days * FEE_RATE_TIER1

    # Tier 2 fees: Days 8 and beyond
    if overdue_days > 7:
        tier2_days = overdue_days - 7
        late_fee_calc += tier2_days * FEE_RATE_TIER2

    # Apply maximum fee cap
    final_fee = round(min(late_fee_calc, MAX_FEE_PER_BOOK), 2)

    return {
        'fee_amount': final_fee,
        'days_overdue': overdue_days,
        'status': f'Book is {overdue_days} day(s) overdue.'
    }

def search_books_in_catalog(search_term: str, search_type: str) -> List[Dict]:
    """
    Search for books in the catalog.
    Implements R6: Book Search Functionality
    
    Args:
        search_term: The string to search for.
        search_type: The field to search in ('title', 'author', or 'isbn').
        
    Returns:
        List[Dict]: A list of book dictionaries matching the search criteria.
    """

    # Input Validation (Search Type)
    valid_types = ['title', 'author', 'isbn']
    if search_type.lower() not in valid_types:
        return []
    
    # If search term is empty, return the entire catalog
    if not search_term or not search_term.strip():
        return get_all_books() 
    
    # Normalize inputs
    term = search_term.strip().lower()
    search_by = search_type.lower()

    # Get ALL books
    all_books = get_all_books()
    
    results = []
    
    for book in all_books:
        # R6: Exact matching for ISBN (case-sensitive check against original input)
        if search_by == 'isbn':
            if book.get('isbn') == search_term.strip():
                results.append(book)
        # R6: Partial, case-insensitive matching for title/author
        elif search_by == 'title':
            if term in book.get('title', '').lower():
                results.append(book)
        elif search_by == 'author':
            if term in book.get('author', '').lower():
                results.append(book)
        
    return results

def get_patron_status_report(patron_id: str) -> Dict:
    """
    Get status report for a patron.
    Implements R7: Patron Status Report
    
    Args:
        patron_id: 6-digit library card ID
        
    Returns:
        Dict: A comprehensive status report
    """
    
    # Input Validation (Patron ID)
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return { 'error': 'Invalid patron ID format.' }
    
    # Get static data from DB
    num_borrowed = get_patron_borrow_count(patron_id)
    borrowed_records = get_patron_borrowed_books(patron_id)    
    
    # Calculate fees
    fee_total = 0.0
    currently_borrowed_books_report = []
    borrowing_history = []
    
    for record in borrowed_records:
        if record['return_date'] is None:
            fee_details = calculate_late_fee_for_book(patron_id, record['book_id'])
            fee_total += fee_details['fee_amount']

            currently_borrowed_books_report.append({
            'book_id': record['book_id'],
            'title': record['title'],
            'due_date': record['due_date'].strftime('%Y-%m-%d'),
            'current_fee_amount': fee_details['fee_amount']
            })
        else:
            fee_details = calculate_late_fee_for_book(patron_id, record['book_id'])
            fee_total += fee_details['fee_amount']

            borrowing_history.append({
            'book_id': record['book_id'],
            'title': record['title'],
            'due_date': record['due_date'].strftime('%Y-%m-%d'),
            'return_date': record['return_date'].strftime('%Y-%m-%d'),
            'days_overdue': fee_details['days_overdue'],
            'fee_amount': fee_details['fee_amount']
            })

    # Compile the comprehensive report
    report = {
        'patron_id': patron_id,
        'currently_borrowed_count': num_borrowed,
        'total_late_fees_owed': round(fee_total, 2),
        'currently_borrowed_books': currently_borrowed_books_report,
        'borrowing_history': borrowing_history
    }
    
    return report

def pay_late_fees(patron_id: str, book_id: int, payment_gateway: PaymentGateway = None) -> Tuple[bool, str, Optional[str]]:
    """
    Process payment for late fees using external payment gateway.
    
    NEW FEATURE FOR ASSIGNMENT 3: Demonstrates need for mocking/stubbing
    This function depends on an external payment service that should be mocked in tests.
    
    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book with late fees
        payment_gateway: Payment gateway instance (injectable for testing)
        
    Returns:
        tuple: (success: bool, message: str, transaction_id: Optional[str])
        
    Example for you to mock:
        # In tests, mock the payment gateway:
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.return_value = (True, "txn_123", "Success")
        success, msg, txn = pay_late_fees("123456", 1, mock_gateway)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits.", None
    
    # Calculate late fee first
    fee_info = calculate_late_fee_for_book(patron_id, book_id)
    
    # Check if there's a fee to pay
    if not fee_info or 'fee_amount' not in fee_info:
        return False, "Unable to calculate late fees.", None
    
    fee_amount = fee_info.get('fee_amount', 0.0)
    
    if fee_amount <= 0:
        return False, "No late fees to pay for this book.", None
    
    # Get book details for payment description
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found.", None
    
    # Use provided gateway or create new one
    if payment_gateway is None:
        payment_gateway = PaymentGateway()
    
    # Process payment through external gateway
    # THIS IS WHAT YOU SHOULD MOCK IN THEIR TESTS!
    try:
        success, transaction_id, message = payment_gateway.process_payment(
            patron_id=patron_id,
            amount=fee_amount,
            description=f"Late fees for '{book['title']}'"
        )
        
        if success:
            return True, f"Payment successful! {message}", transaction_id
        else:
            return False, f"Payment failed: {message}", None
            
    except Exception as e:
        # Handle payment gateway errors
        return False, f"Payment processing error: {str(e)}", None


def refund_late_fee_payment(transaction_id: str, amount: float, payment_gateway: PaymentGateway = None) -> Tuple[bool, str]:
    """
    Refund a late fee payment (e.g., if book was returned on time but fees were charged in error).
    
    NEW FEATURE FOR ASSIGNMENT 3: Another function requiring mocking
    
    Args:
        transaction_id: Original transaction ID to refund
        amount: Amount to refund
        payment_gateway: Payment gateway instance (injectable for testing)
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate inputs
    if not transaction_id or not transaction_id.startswith("txn_"):
        return False, "Invalid transaction ID."
    
    if amount <= 0:
        return False, "Refund amount must be greater than 0."
    
    if amount > 15.00:  # Maximum late fee per book
        return False, "Refund amount exceeds maximum late fee."
    
    # Use provided gateway or create new one
    if payment_gateway is None:
        payment_gateway = PaymentGateway()
    
    # Process refund through external gateway
    # THIS IS WHAT YOU SHOULD MOCK IN YOUR TESTS!
    try:
        success, message = payment_gateway.refund_payment(transaction_id, amount)
        
        if success:
            return True, message
        else:
            return False, f"Refund failed: {message}"
            
    except Exception as e:
        return False, f"Refund processing error: {str(e)}"