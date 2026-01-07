from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this-to-something-secure'

# Database configuration
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'expenses.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# Database Model
# =========================
class Expense(db.Model):
    """Expense model for storing expense records"""
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert expense object to dictionary"""
        return {
            'id': self.id,
            'amount': self.amount,
            'category': self.category,
            'date': self.date,
            'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

# =========================
# Initialize Database
# =========================
with app.app_context():
    db.create_all()
    print(f"✓ Database initialized at: {DB_PATH}")

# =========================
# Helper Functions
# =========================
def get_filtered_expenses(filter_type='all'):
    """
    Get expenses filtered by time period
    
    Args:
        filter_type (str): 'all', 'week', or 'month'
    
    Returns:
        list: List of expense dictionaries
    """
    query = Expense.query

    if filter_type == 'week':
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        query = query.filter(Expense.date >= week_ago)

    elif filter_type == 'month':
        current_month = datetime.now().strftime('%Y-%m')
        query = query.filter(Expense.date.like(f'{current_month}%'))

    expenses = query.order_by(Expense.date.desc()).all()
    return [exp.to_dict() for exp in expenses]


def get_custom_range_expenses(start_date, end_date):
    """
    Get expenses filtered by custom date range
    
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
    
    Returns:
        list: List of expense dictionaries
    """
    try:
        # Validate dates
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
        
        # Query expenses within date range
        query = Expense.query.filter(
            Expense.date >= start_date,
            Expense.date <= end_date
        )
        
        expenses = query.order_by(Expense.date.desc()).all()
        return [exp.to_dict() for exp in expenses]
    
    except ValueError:
        # Invalid date format, return empty list
        return []


def get_summary(expenses):
    """
    Calculate summary statistics for expenses
    
    Args:
        expenses (list): List of expense dictionaries
    
    Returns:
        dict: Summary statistics including total, count, categories, and breakdown
    """
    if not expenses:
        return {
            'total': 0.0,
            'count': 0,
            'categories': 0,
            'category_breakdown': {}
        }

    total = sum(float(exp['amount']) for exp in expenses)
    categories = set(exp['category'] for exp in expenses)

    # Calculate category-wise totals
    category_totals = {}
    for exp in expenses:
        cat = exp['category']
        category_totals[cat] = category_totals.get(cat, 0) + float(exp['amount'])

    # Sort categories by amount (highest first)
    category_totals = dict(sorted(category_totals.items(), key=lambda x: x[1], reverse=True))

    return {
        'total': round(total, 2),
        'count': len(expenses),
        'categories': len(categories),
        'category_breakdown': category_totals
    }


def validate_expense_data(amount, category, date, description):
    """
    Validate expense input data
    
    Args:
        amount (str): Amount value
        category (str): Category name
        date (str): Date string
        description (str): Description text
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check if all fields are provided
    if not all([amount, category, date, description]):
        return False, "All fields are required!"

    # Validate amount
    try:
        amount_float = float(amount)
        if amount_float <= 0:
            return False, "Amount must be greater than 0!"
        if amount_float > 1000000:
            return False, "Amount is too large!"
    except ValueError:
        return False, "Invalid amount format!"

    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        return False, "Invalid date format!"

    # Validate description length
    if len(description) > 255:
        return False, "Description is too long (max 255 characters)!"

    if len(description.strip()) == 0:
        return False, "Description cannot be empty!"

    # Validate category
    valid_categories = ['Food', 'Transport', 'Utilities', 'Entertainment', 'Healthcare', 'Shopping', 'Other']
    if category not in valid_categories:
        return False, "Invalid category!"

    return True, None


# =========================
# Context Processor
# =========================
@app.context_processor
def inject_today():
    """Inject today's date into all templates"""
    return {'today': datetime.now().strftime('%Y-%m-%d')}


# =========================
# Routes
# =========================
@app.route('/')
def index():
    """Main page - displays expenses and summary"""
    filter_type = request.args.get('filter', 'all')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Validate filter type
    if filter_type not in ['all', 'week', 'month', 'custom']:
        filter_type = 'all'
    
    # Get filtered expenses
    if filter_type == 'custom' and start_date and end_date:
        expenses = get_custom_range_expenses(start_date, end_date)
    else:
        expenses = get_filtered_expenses(filter_type)
    
    summary = get_summary(expenses)

    return render_template(
        'index.html',
        expenses=expenses,
        summary=summary,
        current_filter=filter_type,
        start_date=start_date,
        end_date=end_date
    )


@app.route('/add', methods=['POST'])
def add_expense():
    """Add a new expense"""
    amount = request.form.get('amount')
    category = request.form.get('category')
    date = request.form.get('date')
    description = request.form.get('description')

    # Validate input
    is_valid, error_message = validate_expense_data(amount, category, date, description)
    if not is_valid:
        flash(error_message, 'error')
        return redirect(url_for('index'))

    try:
        expense = Expense(
            amount=float(amount),
            category=category,
            date=date,
            description=description.strip()
        )
        db.session.add(expense)
        db.session.commit()
        flash(f'💰 Expense of ${float(amount):.2f} added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error adding expense: {str(e)}', 'error')
        print(f"Error adding expense: {e}")

    return redirect(url_for('index'))


@app.route('/edit/<int:id>')
def edit_expense(id):
    """Display edit form for an expense"""
    expense = Expense.query.get_or_404(id)

    filter_type = request.args.get('filter', 'all')
    if filter_type not in ['all', 'week', 'month', 'custom']:
        filter_type = 'all'
    
    expenses = get_filtered_expenses(filter_type)
    summary = get_summary(expenses)

    return render_template(
        'index.html',
        expenses=expenses,
        summary=summary,
        current_filter=filter_type,
        editing=expense.to_dict()
    )


@app.route('/update/<int:id>', methods=['POST'])
def update_expense(id):
    """Update an existing expense"""
    amount = request.form.get('amount')
    category = request.form.get('category')
    date = request.form.get('date')
    description = request.form.get('description')

    # Validate input
    is_valid, error_message = validate_expense_data(amount, category, date, description)
    if not is_valid:
        flash(error_message, 'error')
        return redirect(url_for('edit_expense', id=id))

    try:
        expense = Expense.query.get_or_404(id)
        expense.amount = float(amount)
        expense.category = category
        expense.date = date
        expense.description = description.strip()

        db.session.commit()
        flash(f'✓ Expense updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error updating expense: {str(e)}', 'error')
        print(f"Error updating expense: {e}")

    return redirect(url_for('index'))


@app.route('/delete/<int:id>')
def delete_expense(id):
    """Delete an expense"""
    try:
        expense = Expense.query.get_or_404(id)
        amount = expense.amount
        db.session.delete(expense)
        db.session.commit()
        flash(f'🗑️ Expense of ${amount:.2f} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Error deleting expense: {str(e)}', 'error')
        print(f"Error deleting expense: {e}")

    return redirect(url_for('index'))


@app.route('/stats')
def stats():
    """Display statistics page (optional - for future enhancement)"""
    all_expenses = get_filtered_expenses('all')
    month_expenses = get_filtered_expenses('month')
    week_expenses = get_filtered_expenses('week')
    
    return {
        'all_time': get_summary(all_expenses),
        'this_month': get_summary(month_expenses),
        'this_week': get_summary(week_expenses)
    }


# =========================
# Error Handlers
# =========================
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    flash('⚠️ Page not found!', 'error')
    return redirect(url_for('index'))


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    flash('❌ An internal error occurred. Please try again.', 'error')
    return redirect(url_for('index'))


# =========================
# Run App
# =========================
if __name__ == '__main__':
    port = 3200
    print("=" * 60)
    print("💰 Personal Expense Tracker - Enhanced Edition")
    print("=" * 60)
    print("🚀 Starting server...")
    print(f"📁 Database: {DB_PATH}")
    print(f"🌐 Open your browser at: http://localhost:{port}")
    print("=" * 60)
    print("Press CTRL+C to quit")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=port)
