import pytest
import sqlite3
import os
from playwright.sync_api import Page, expect

@pytest.fixture(autouse=True)
def db_setup():
    # Connect to the database file
    db_path = os.path.join(os.getcwd(), 'library.db')
    
    if os.path.exists(db_path):
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        
        # Turn off foreign keys to allow deletion
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        try:
            # Clear the books table so we don't get duplicate ISBN errors
            cursor.execute("DELETE FROM books;")
            cursor.execute("DELETE FROM borrow_records;") 
            connection.commit()
        except Exception as e:
            print(f"Warning: Could not clear database: {e}")
        finally:
            connection.close()

def test_add_and_verify_book(page: Page):
    # Navigate to the Home (Catalog) page
    page.goto("http://127.0.0.1:5000/")

    # Click add new book button
    page.click("text=Add New Book")

    # Fill the form
    page.fill("input[name='title']", "E2E Test Book")
    page.fill("input[name='author']", "E2E Tester")
    page.fill("input[name='isbn']", "9999999999999")
    page.fill("input[name='total_copies']", "5")

    # Submit the form
    page.click("button[type='submit']")

    # Verify redirect
    expect(page).to_have_url("http://127.0.0.1:5000/catalog")
    
    expect(page.locator("td", has_text="E2E Test Book")).to_be_visible()

def test_borrow_book_flow(page: Page):
    # We must add the book again because db_setup cleared it
    page.goto("http://127.0.0.1:5000/add_book")
    page.fill("input[name='title']", "Borrowable Book")
    page.fill("input[name='author']", "Robot")
    page.fill("input[name='isbn']", "1111111111111")
    page.fill("input[name='total_copies']", "2")
    page.click("button[type='submit']")

    # Now navigate to catalog to borrow it
    page.goto("http://127.0.0.1:5000/")
    
    # Find the specific row for our new book
    book_row = page.locator("tr", has_text="Borrowable Book")

    # Fill the Patron ID inside that row
    book_row.locator("input[name='patron_id']").fill("123456")

    # Click the Borrow button
    book_row.locator("button:text('Borrow')").click()

    # Assert success message
    success_message = page.locator(".flash-success")
    expect(success_message).to_be_visible()
    expect(success_message).to_contain_text("Successfully borrowed")