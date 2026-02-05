# Backend Utility Scripts

This folder contains utility scripts for database management and system administration.

## Available Scripts

### 1. check_admin.py
**Purpose**: Verify existing admin accounts in the database  
**Usage**: 
```bash
python scripts/check_admin.py
```
**When to use**: To check if admin account exists and view credentials

---

### 2. create_superadmin.py
**Purpose**: Create a new superadmin account  
**Usage**:
```bash
python scripts/create_superadmin.py
```
**Default Credentials**:
- Email: admin@autocare.com
- Password: Admin@123
- Phone: 9800000000

**When to use**: Initial setup or creating new admin accounts

---

### 3. reset_admin_password.py
**Purpose**: Reset admin account password  
**Usage**:
```bash
python scripts/reset_admin_password.py
```
**When to use**: When admin forgets password or password needs to be reset

---

### 4. run_migration.py
**Purpose**: Run database migrations to add missing columns  
**Usage**:
```bash
python scripts/run_migration.py
```
**What it does**:
- Adds municipality column
- Adds ward_no column
- Checks if columns exist before adding

**When to use**: After model updates that require new database columns

---

## Important Notes

⚠️ **All scripts require**:
- Active virtual environment (`venv/Scripts/Activate`)
- Correct database credentials in `app/core/config.py`
- PostgreSQL server running

⚠️ **Run from backend directory**:
```bash
cd backend
python scripts/<script_name>.py
```

## Database Configuration

Scripts use the database configuration from `app/core/config.py`:
- Host: localhost
- Port: 5432
- Database: autocare_db
- User: postgres
- Password: root123

To change credentials, update the `.env` file or `config.py`.
