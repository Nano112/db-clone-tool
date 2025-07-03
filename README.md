# PostgreSQL Database Clone Tool

Clone PostgreSQL databases with automatic sequence reset. Built with [Textual](https://textual.textualize.io/) for terminal UI.

## Features

- Interactive terminal interface with progress tracking
- Auto-loads credentials from `.env` files  
- Connection testing before cloning
- Automatic sequence reset after restore
- SSL support for cloud databases
- Handles PostgreSQL version differences
- Temporary file cleanup

## Installation

```bash
git clone https://github.com/Nano112/db-clone-tool.git
cd db-clone-tool

# Install dependencies
uv add textual psycopg2-binary python-dotenv

# Setup environment
cp .env.example .env
# Edit .env with your database credentials

# Run
uv run python db_clone_tool.py
```

## Prerequisites

- Python 3.8+
- PostgreSQL client tools (`pg_dump`, `pg_restore`)
- Network access to both databases

### Installing PostgreSQL Tools

```bash
# macOS
brew install libpq

# Ubuntu/Debian  
sudo apt-get install postgresql-client

# Windows
# Download from https://www.postgresql.org/download/windows/
```

## Configuration

Create `.env` with your database settings:

```env
# Source Database
PROD_DB_HOST=your-production-host.com
PROD_DB_PORT=5432
PROD_DB_DATABASE=your_prod_database
PROD_DB_USERNAME=your_prod_username
PROD_DB_PASSWORD=your_prod_password
PROD_DB_SSL=true

# Target Database
DB_HOST=localhost
DB_PORT=5432
DB_DATABASE=your_local_database
DB_USERNAME=your_local_username
DB_PASSWORD=your_local_password
```

### Common Setups

**Laravel Cloud**
```env
PROD_DB_HOST=ep-something-something.aws-region.pg.laravel.cloud
PROD_DB_SSL=true
```

**Laravel Sail**
```env
DB_HOST=localhost
DB_USERNAME=sail
DB_PASSWORD=password
```

**Heroku Postgres**
```env
PROD_DB_HOST=your-app-name.herokuapp.com
PROD_DB_SSL=true
```

## Usage

1. Start the application:
   ```bash
   uv run python db_clone_tool.py
   ```

2. The tool will load your `.env` configuration automatically

3. Test connections to verify database access

4. Start the clone process

The tool will:
- Create a dump from the source database
- Restore to the target database  
- Reset sequences to prevent primary key conflicts
- Verify the clone completed successfully

## Use Cases

**Testing Migrations**
```bash
# Clone production to local
uv run python main.py

# Test migrations
sail artisan migrate
```

**Development Setup**
```bash
# New developer onboarding
cp .env.example .env
# Add credentials and clone
uv run python main.py
```

## Troubleshooting

**Connection Issues**
- Set `PROD_DB_SSL=true` for cloud databases requiring SSL
- Verify credentials and network connectivity
- Ensure target database exists

**Version Compatibility**
- Update PostgreSQL client tools if version mismatch occurs:
  ```bash
  brew upgrade postgresql  # macOS
  ```

**Permissions**
- Ensure database users have necessary dump/restore permissions
- Use read-only users for source databases when possible

## Security

- Never commit `.env` to version control
- Use `.env.example` for credential templates
- Rotate passwords regularly
- Limit database network access

## Development

```bash
git clone https://github.com/Nano112/db-clone-tool.git
cd db-clone-tool

# Install dependencies
uv add textual psycopg2-binary python-dotenv

# Run
uv run python main.py
```

## License

MIT License - see [LICENSE](LICENSE) file for details.