# Jackson Louws - 20295325

## Project Implementation Status

| Requirement | Function(s) | Status | What’s Missing |
|-------------|-------------|--------|----------------|
| **R1: Add Book To Catalog** | `add_book_to_catalog` | Complete | Everything for adding a book seems to be there, the fields are validated properly and it updates the catalog. I tested some edge cases like really long titles for books and everything seemed to work okay. |
| **R2: Book Catalog Display** | `get_all_books`, `catalog_routes.py` | Partial | The catalog shows the list of books but how it looks and how the “Borrow” button actually works depends on the routes and templates. I’d want to double-check that the available number of copies are showing up properly in the UI. |
| **R3: Book Borrowing Interface** | `borrow_book_by_patron` | Partial | The borrowing logic is mostly there but there’s a small bug with the book borrow limit. Right now the program checks `> 5` for the limit, but it should stop at 5 books, not let them go over, so that needs to be changed. |
| **R4: Book Return Processing** | `return_book_by_patron` | Not Implemented | This function is essentially empty. It should be handling the return process, checking if the patron actually borrowed the book, updating the copies, adding the return date, and then also dealing with any late fees. |
| **R5: Late Fee Calculation API** | `calculate_late_fee_for_book` | Not Implemented | This function is also empty. It needs to be able to calculate late fees based on the rules (14-day window with pricing at $0.50/day for the first week overdue and $1/day after the first week, capped at $15 total). |
| **R6: Book Search Functionality** | `search_books_in_catalog` | Not Implemented | THis function is also empty. It should let you search by title, author, or ISBN. Title and author searches are supposed to be partial and case-insensitive, while ISBN has to be an exact match. |
| **R7: Patron Status Report** | `get_patron_status_report` | Not Implemented | This function is also not implemented. It should give a proper overview of a customer, what books they’ve got right now (with due dates), how much in late fees they owe, how many books they currently have, and their full borrowing history. |

## Unit Test Summaries

Here are the summaries of the unit tests for all seven functional requirements (R1–R7) from the requirements specification.

### R1 Tests: Add a Book to the Catalog
I wrote tests that check if valid books with proper fields are added correctly and that error cases like missing required fields, an ISBN that isn’t exactly 13 digits, negative or zero copies of books, and overly long titles and author names are handled properly. These tests make sure that the book catalog only accepts clean and valid book data. 

### R2 Tests: Checking the Book Catalog Display
My tests focus on whether the book catalog display shows all of the fields properly (ID, title, author, ISBN, available/total copies), correctly formats the available vs total copies of books, and handles both normal catalogs and edge cases like when there are no books or when available copies of books are somehow greater than the total amount of copies.

### R3 Tests: Checking the Book Borrowing Functionality
I tested cases where a customer borrows a book properly as well as error cases where customer ID is invalid, a customer tries to borrow more than the maximum of five books, a customer tries to borrow a book that has no copies available, or a customer tries to borrow a book that doesn’t exist.

### R4 Tests: Validating the Book Return Processes
My tests include confirming a normal successful book return, catching errors that occur when a customer ID is invalid, making sure customers can’t return books that they never borrowed, and verifying that available copies of books increase after a return.

### R5 Tests: Validating Proper Late Fee Calculation
I tested different cases like when books are returned on time (no fee), when books are a few days overdue (validate $0.50/day fee for the first week), and when books are overdue for longer than 7 days (validate the $1.00/day fee). I also wrote a test to confirm that the maximum fee of $15 per book is enforced properly.

### R6 Tests: Ensuring the Book Search Function Works Properly
I wrote tests that checked for partial matches on book title and author inputs, exact matches on ISBN inputs, as well as testing empty searches and invalid search types.

### R7 Tests: Checking the Customer Status Report Function
I tested that the customer report displays the correct structure with borrowed books, due dates, fees, and history for valid customers, while also catching invalid customer IDs. I also checked that customer late fees are shown properly with two decimal places, that the number of currently borrowed books is accurate, and that the customer borrowing history is included in the report.

## New Unit Test Summaries

### New R5 Test Summaries
New boundary condition tests were added to precisely validate the tiered late fee calculation. These tests confirm the exact fee amount when a loan is exactly 7 days overdue (the maximum for the Tier 1 rate of $3.50) and when a loan is exactly 8 days overdue, accurately validating the transition to the higher Tier 2 rate.

### New R6 Test Summaries
A critical test was added to align the search functionality with requirements for an empty query. This test verifies that if the search input consists only of whitespace or an empty string, the function correctly returns a list of all books in the catalog.

### New R7 Test Summaries
New tests were developed specifically to validate the corrected `get_patron_status_report` function. These cases verify that the report uses the final, correct data structure (including `currently_borrowed_books` and `borrowing_history` as lists) and successfully handles the edge case of a patron with no loan records at all, returning zero counts and empty lists for fees and loans.