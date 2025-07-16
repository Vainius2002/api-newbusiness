# Media Agency Lead Management System

A web-based lead management system for tracking advertiser spending data and managing business development activities.

## Features

- **Lead Management**: Track advertisers with configurable lead statuses (Hot, Warm, Cold, Ours, Non-qualified, Lost, Non-Market)
- **Spending Data Import**: Import advertiser spending data from CSV files with multi-encoding support
- **Net Spending Calculation**: Automatic calculation of net spending with industry-standard discounts or manual entry
- **Team Collaboration**: Role-based access control (Admin, Team Lead, Account Executive)
- **Activity Tracking**: Log calls, emails, meetings, and notes for each advertiser
- **Reporting**: Analytics dashboard with spending analysis and data export capabilities

## Setup

1. Clone the repository:
```bash
git clone https://github.com/credas/newbusiness.git
cd newbusiness/media_agency_leads
```

2. Create a virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and set your SECRET_KEY
```

5. Initialize the database:
```bash
python create_admin.py
```

6. Run the application:
```bash
python run.py
```

The application will be available at `http://localhost:5001`

## Default Login

- Username: admin
- Password: admin123

**Important**: Change the admin password after first login!

## CSV Import Format

The system supports CSV files with the following columns:
- Advertiser name
- Year
- Media spending by channel (Cinema, TV, Radio, Internet, etc.)
- Grand total

The import process automatically handles:
- Multiple encodings (UTF-8, UTF-16, Latin-1)
- Different separators (comma, tab, semicolon)
- Number formatting with spaces as thousands separators

## Lead Status Rules

- **Ours**: Automatically assigned to advertisers with IPG agencies
- **Non-Market**: Automatically assigned to public sector organizations
- **Non-Qualified**: Default status for new advertisers
- Other statuses are manually assigned based on business development progress