import pytest
from unittest.mock import Mock
# Updated imports to include all functions needed for coverage >= 80%
from services.library_service import (
    pay_late_fees, 
    refund_late_fee_payment,
    add_book_to_catalog,
    borrow_book_by_patron,
    return_book_by_patron,
    calculate_late_fee_for_book,
    search_books_in_catalog,
    get_patron_status_report
)
from services.payment_service import PaymentGateway

# Part 2.1: Original Tests (Achieves coverage = 78%)

def test_pay_late_fees_success(mocker):
    # Stub the database functions we don't want to call
    # Use mocker.patch to replace them with fake return values.
    mocker.patch('services.library_service.calculate_late_fee_for_book', 
                 return_value={'fee_amount': 10.50})
    mocker.patch('services.library_service.get_book_by_id', 
                 return_value={'title': 'Hitchhiker\'s Guide', 'id': 1})
    
    # Mock the PaymentGateway
    # Create a mock object that looks like PaymentGateway
    mock_gateway = Mock(spec=PaymentGateway)
    # Configure it to return "success" tuple when process_payment is called
    # Tuple format = (success, transaction_id, message)
    mock_gateway.process_payment.return_value = (True, "txn_12345", "Payment successful")
    
    # Call the function under test & inject mock gateway
    success, message, transaction_id = pay_late_fees("123456", 1, mock_gateway)
    
    # Verify the return
    assert success is True
    assert transaction_id == "txn_12345"
    assert "Payment successful" in message
    
    # Verify the mock was used correctly
    mock_gateway.process_payment.assert_called_once()
    # Ensure it was called with the correct fee amount (10.50) & patron ID ("123456")
    mock_gateway.process_payment.assert_called_with(
        patron_id="123456",
        amount=10.50,
        description="Late fees for 'Hitchhiker's Guide'"
    )

def test_pay_late_fees_declined(mocker):
    # Stub db to return a valid fee
    mocker.patch('services.library_service.calculate_late_fee_for_book', 
                 return_value={'fee_amount': 10.50})
    mocker.patch('services.library_service.get_book_by_id', 
                 return_value={'title': 'Book Title', 'id': 1})
    
    # Mock Gateway to simulate declined payment
    mock_gateway = Mock(spec=PaymentGateway)
    # Tuple format = (success, transaction_id, message)
    mock_gateway.process_payment.return_value = (False, None, "Insufficient funds")
    
    success, message, transaction_id = pay_late_fees("123456", 1, mock_gateway)
    
    assert success is False
    assert transaction_id is None
    assert "Payment failed" in message
    assert "Insufficient funds" in message
    # Verify it was called
    mock_gateway.process_payment.assert_called_once()

def test_pay_late_fees_invalid_patron(mocker):
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Pass invalid ID (3 digits instead of required 6)
    success, message, transaction_id = pay_late_fees("123", 1, mock_gateway)
    
    assert success is False
    assert "Invalid patron ID" in message
    # Verify gateway was not called
    mock_gateway.process_payment.assert_not_called()

def test_pay_late_fees_zero_amount(mocker):
    # Stub calculate_late_fee to return $0.00
    mocker.patch('services.library_service.calculate_late_fee_for_book', 
                 return_value={'fee_amount': 0.00})
    
    mock_gateway = Mock(spec=PaymentGateway)
    
    success, message, transaction_id = pay_late_fees("123456", 1, mock_gateway)
    
    assert success is False
    assert "No late fees" in message
    # Verify gateway was not called
    mock_gateway.process_payment.assert_not_called()

def test_pay_late_fees_exception(mocker):
    mocker.patch('services.library_service.calculate_late_fee_for_book', 
                 return_value={'fee_amount': 5.00})
    mocker.patch('services.library_service.get_book_by_id', 
                 return_value={'title': 'Book', 'id': 1})
    
    mock_gateway = Mock(spec=PaymentGateway)
    # Configure mock to raise an exception when called
    mock_gateway.process_payment.side_effect = Exception("Network connection lost")
    
    success, message, transaction_id = pay_late_fees("123456", 1, mock_gateway)
    
    assert success is False
    assert transaction_id is None
    assert "Payment processing error" in message
    assert "Network connection lost" in message
    
def test_refund_payment_success(mocker):
    mock_gateway = Mock(spec=PaymentGateway)
    mock_gateway.refund_payment.return_value = (True, "Refund processed successfully")
    
    success, message = refund_late_fee_payment("txn_123456", 10.50, mock_gateway)
    
    assert success is True
    assert "Refund processed" in message
    # Verify gateway called with exact parameters
    mock_gateway.refund_payment.assert_called_once_with("txn_123456", 10.50)

def test_refund_payment_invalid_txn_id(mocker):
    mock_gateway = Mock(spec=PaymentGateway)
    
    # Pass an ID that doesn't start with "txn_"
    success, message = refund_late_fee_payment("invalid_id", 10.50, mock_gateway)
    
    assert success is False
    assert "Invalid transaction ID" in message
    # Verify gateway was not called
    mock_gateway.refund_payment.assert_not_called()

@pytest.mark.parametrize("invalid_amount, expected_msg", [
    (-5.00, "Refund amount must be greater than 0"),
    (0.00, "Refund amount must be greater than 0"),
    (20.00, "Refund amount exceeds maximum late fee")
])
def test_refund_payment_invalid_amounts(mocker, invalid_amount, expected_msg):
    mock_gateway = Mock(spec=PaymentGateway)
    
    success, message = refund_late_fee_payment("txn_123456", invalid_amount, mock_gateway)
    
    assert success is False
    assert expected_msg in message
    # Verify gateway was not called for any invalid amounts
    mock_gateway.refund_payment.assert_not_called()

# Part 2.2: Added tests (To get coverage >= 80%)

def test_add_book_validations_coverage():
    """Cover remaining input validations not hit by A2_test."""
    # Empty author
    assert add_book_to_catalog("Title", "", "1234567890123", 5) == (False, "Author is required.")

def test_add_book_duplicate_mock(mocker):
    """Test adding duplicate ISBN by mocking the DB check."""
    mocker.patch('services.library_service.get_book_by_isbn', return_value={'title': 'Existing Book'})
    success, msg = add_book_to_catalog("New Title", "Author", "1234567890123", 5)
    assert success is False
    assert "already exists" in msg

def test_borrow_book_unavailable_mock(mocker):
    """Force a '0 copies available' state using a mock."""
    mocker.patch('services.library_service.get_book_by_id', return_value={'available_copies': 0})
    success, msg = borrow_book_by_patron("123456", 1)
    assert success is False
    assert "currently not available" in msg

def test_borrow_book_limit_reached_mock(mocker):
    """Force a 'borrow limit reached' state using a mock."""
    mocker.patch('services.library_service.get_book_by_id', return_value={'available_copies': 1})
    mocker.patch('services.library_service.get_patron_borrow_count', return_value=5)
    success, msg = borrow_book_by_patron("123456", 1)
    assert success is False
    assert "maximum borrowing limit" in msg

def test_return_book_no_active_loan_mock(mocker):
    """Test returning a book that isn't in the patron's borrowed list."""
    mocker.patch('services.library_service.get_patron_borrowed_books', return_value=[])
    success, msg = return_book_by_patron("123456", 1)
    assert success is False
    assert "No active borrowing record" in msg

def test_calculate_fee_not_borrowed_mock(mocker):
    """Test fee calc for a book that exists but isn't borrowed by this patron."""
    mocker.patch('services.library_service.get_patron_borrowed_books', return_value=[])
    mocker.patch('services.library_service.get_book_by_id', return_value={'title': 'Existing Book'})
    result = calculate_late_fee_for_book("123456", 1)
    assert result['status'] == 'Book is not currently borrowed by this patron.'

def test_calculate_fee_book_not_found_mock(mocker):
    """Test fee calc for a book ID that doesn't exist at all."""
    mocker.patch('services.library_service.get_patron_borrowed_books', return_value=[])
    mocker.patch('services.library_service.get_book_by_id', return_value=None)
    result = calculate_late_fee_for_book("123456", 999)
    assert result['status'] == 'Book not found.'

def test_search_invalid_type_coverage():
    """Hit the invalid search type branch."""
    assert search_books_in_catalog("term", "bad_type") == []

def test_patron_status_invalid_id_coverage():
    """Hit the invalid patron ID branch in status report."""
    assert get_patron_status_report("bad_id") == {'error': 'Invalid patron ID format.'}