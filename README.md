# Personal Finance Management System

A comprehensive Django-based personal finance management application that helps users track their income, expenses, and budgets.

## Features

- **User Authentication**: Register, login, and logout functionality
- **Transaction Management**: Add, view, and categorize income and expenses
- **Budget Planning**: Set monthly budgets for different categories
- **Financial Dashboard**: Overview of income, expenses, and balance
- **Responsive Design**: Mobile-friendly interface using Bootstrap
- **Media Support**: Upload and store profile pictures

## Project Structure

```
personal_finance_management/
├── manage.py
├── requirements.txt
├── README.md
├── personal_finance_management/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── user/                          # Main app
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── tests.py
├── templates/                     # HTML templates
│   ├── base.html
│   └── user/
│       ├── home.html
│       ├── dashboard.html
│       ├── login.html
│       ├── register.html
│       ├── add_transaction.html
│       ├── transaction_list.html
│       └── budget_management.html
├── static/                        # Static files (CSS, JS)
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── media/                         # User uploads
    └── profile_pictures/
```

## Installation

1. **Clone the repository** (if using version control):
   ```bash
   git clone <repository-url>
   cd personal_finance_management
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a superuser** (optional):
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

7. **Access the application**:
   - Open your browser and go to `http://127.0.0.1:8000/`
   - Admin panel: `http://127.0.0.1:8000/admin/`

## Usage

### Getting Started
1. Register a new account or login with existing credentials
2. Access the dashboard to see your financial overview
3. Add transactions to track your income and expenses
4. Set budgets for different categories
5. Monitor your spending patterns

### Key Features

#### Dashboard
- View total income, expenses, and balance
- Recent transactions overview
- Budget progress tracking
- Quick action buttons

#### Transaction Management
- Add new income or expense transactions
- Categorize transactions (Food, Transportation, Entertainment, etc.)
- View and filter transaction history
- Search and filter capabilities

#### Budget Management
- Set monthly budgets for different categories
- Track budget progress
- Edit existing budgets

## Models

### UserProfile
- Extends Django's User model
- Stores additional user information (phone, address, profile picture)

### Transaction
- Records income and expense transactions
- Categories: Food, Transportation, Entertainment, Shopping, Bills, Healthcare, Education, Salary, Freelance, Investment, Other
- Amount, date, description, and type tracking

### Budget
- Monthly budget planning
- Category-based budget allocation
- Progress tracking

## Technologies Used

- **Backend**: Django 5.0.2
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Database**: SQLite (default)
- **Icons**: Font Awesome
- **Image Processing**: Pillow

## Development

### Running Tests
```bash
python manage.py test
```

### Database Management
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Static Files
```bash
# Collect static files (for production)
python manage.py collectstatic
```

## Configuration

### Settings
Key settings in `personal_finance_management/settings.py`:
- `DEBUG = True` (set to False in production)
- `SECRET_KEY` (change in production)
- `ALLOWED_HOSTS` (configure for production)
- Static and media file configurations

### Media Files
- Profile pictures: `media/profile_pictures/`
- Configure `MEDIA_URL` and `MEDIA_ROOT` in settings

## Production Deployment

1. Set `DEBUG = False`
2. Configure `ALLOWED_HOSTS`
3. Use a production database (PostgreSQL, MySQL)
4. Set up static file serving
5. Configure media file serving
6. Use environment variables for sensitive settings

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For support and questions, please create an issue in the repository or contact the development team.
