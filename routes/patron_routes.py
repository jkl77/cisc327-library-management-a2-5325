"""
Patron Routes - Patron status and management endpoints (R7)
"""

from flask import Blueprint, render_template, request, flash
from library_service import get_patron_status_report # Import the R7 business logic

patron_bp = Blueprint('patron', __name__)

@patron_bp.route('/patron/status', methods=['GET'])
def status_report():
    """
    Displays the Patron Status Report.
    Implements R7: Patron Status Report.
    """
    # Get the patron ID from the URL query parameters (e.g., ?patron_id=123456)
    patron_id = request.args.get('patron_id', '').strip()
    report = None
    
    # Only run the report if a 6-digit patron ID is provided
    if patron_id and patron_id.isdigit() and len(patron_id) == 6:
        # Use business logic function (R7)
        report = get_patron_status_report(patron_id)
        
        if 'error' in report:
            flash(f"Error generating report: {report['error']}", 'error')
            report = None # Clear report data on error

    elif patron_id:
        # Handle case where text is entered but not 6 digits
        flash("Patron ID must be exactly 6 digits.", 'error')

    # Render the HTML template, passing the ID and the report data (if available)
    return render_template('patron_status.html', patron_id=patron_id, report=report)

