#!/bin/bash

YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m'

INSTALL_DIR="/opt/marzgozir"
CONFIG_FILE="$INSTALL_DIR/bot_config.py"
COMPOSE_FILE="$INSTALL_DIR/docker-compose.yml"
DATA_DIR="$INSTALL_DIR/data"
DB_FILE="$DATA_DIR/bot_data.db"
REPO_URL="https://github.com/mahyyar/MarzGozir.git"
PROJECT_NAME="marzgozir"

# Database variables
DB_TYPE="sqlite"
DB_HOST="localhost"
DB_PORT=3306
DB_USER="marzgozir_user"
DB_PASSWORD=""
DB_NAME="marzgozir_db"

check_prerequisites() {
    echo -e "${YELLOW}Checking system prerequisites...${NC}"
    if ! command -v git &> /dev/null; then
        echo -e "${YELLOW}Git not found. Installing Git...${NC}"
        sudo apt-get update
        sudo apt-get install -y git || { echo -e "${RED}Failed to install Git${NC}"; exit 1; }
    fi
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}Docker not found. Installing Docker...${NC}"
        sudo apt-get update
        sudo apt-get install -y docker.io || { echo -e "${RED}Failed to install Docker${NC}"; exit 1; }
        sudo systemctl start docker
        sudo systemctl enable docker
    fi
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${YELLOW}Docker Compose not found. Installing Docker Compose...${NC}"
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose || { echo -e "${RED}Failed to install Docker Compose${NC}"; exit 1; }
        sudo chmod +x /usr/local/bin/docker-compose
    fi
    if ! command -v curl &> /dev/null; then
        echo -e "${YELLOW}Curl not found. Installing Curl...${NC}"
        sudo apt-get update
        sudo apt-get install -y curl || { echo -e "${RED}Failed to install Curl${NC}"; exit 1; }
    fi
    echo -e "${GREEN}All prerequisites successfully installed${NC}"
}

validate_token() {
    local token=$1
    echo -e "${YELLOW}Validating Telegram bot token...${NC}"
    response=$(curl -s "https://api.telegram.org/bot${token}/getMe")
    if [[ "$response" =~ \"ok\":true ]]; then
        echo -e "${GREEN}Bot token is valid${NC}"
        return 0
    else
        echo -e "${RED}Error: Invalid bot token! Response: $response${NC}"
        return 1
    fi
}

get_token_and_id() {
    while true; do
        echo -e "${YELLOW}Enter your Telegram bot token:${NC}"
        read -r TOKEN
        echo -e "${YELLOW}Enter the admin numeric ID (numbers only, no brackets):${NC}"
        read -r ADMIN_ID
        if [ -z "$TOKEN" ] || [ -z "$ADMIN_ID" ]; then
            echo -e "${RED}Error: Bot token and admin ID cannot be empty!${NC}"
            continue
        fi
        if ! [[ "$TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]]; then
            echo -e "${RED}Error: Invalid bot token format! It should look like '123456789:ABCDEF1234567890abcdef1234567890'${NC}"
            continue
        fi
        if ! [[ "$ADMIN_ID" =~ ^[0-9]+$ ]]; then
            echo -e "${RED}Error: Admin ID must contain only numbers!${NC}"
            continue
        fi
        if ! validate_token "$TOKEN"; then
            echo -e "${RED}Please try again with a valid token${NC}"
            continue
        fi
        echo -e "${GREEN}Bot token and admin ID successfully collected${NC}"
        echo -e "${YELLOW}Collected TOKEN: $TOKEN${NC}"
        echo -e "${YELLOW}Collected ADMIN_ID: $ADMIN_ID${NC}"
        export TOKEN ADMIN_ID
        return 0
    done
}

select_database_type() {
    echo -e "${YELLOW}Which database would you like to use?${NC}"
    echo "1) SQLite (simpler, file-based, default)"
    echo "2) MySQL (more powerful, requires MySQL server)"
    read -r db_choice
    
    case $db_choice in
        2)
            DB_TYPE="mysql"
            echo -e "${GREEN}MySQL selected. Now setting up MySQL configuration...${NC}"
            setup_mysql_config
            ;;
        *)
            DB_TYPE="sqlite"
            echo -e "${GREEN}SQLite selected.${NC}"
            ;;
    esac
    export DB_TYPE
}

setup_mysql_config() {
    echo -e "${YELLOW}Do you want to install MySQL server locally? (y/n)${NC}"
    read -r install_mysql
    if [[ $install_mysql == "y" || $install_mysql == "Y" ]]; then
        install_mysql_server
    else
        echo -e "${YELLOW}Skipping MySQL installation. Please make sure you have a MySQL server available.${NC}"
    fi
    
    echo -e "${YELLOW}Enter MySQL host (default: localhost):${NC}"
    read -r mysql_host
    DB_HOST=${mysql_host:-localhost}
    
    echo -e "${YELLOW}Enter MySQL port (default: 3306):${NC}"
    read -r mysql_port
    DB_PORT=${mysql_port:-3306}
    
    echo -e "${YELLOW}Enter MySQL username (default: marzgozir_user):${NC}"
    read -r mysql_user
    DB_USER=${mysql_user:-marzgozir_user}
    
    echo -e "${YELLOW}Enter MySQL password:${NC}"
    read -r mysql_password
    if [ -z "$mysql_password" ]; then
        echo -e "${RED}Error: MySQL password cannot be empty!${NC}"
        setup_mysql_config
        return
    fi
    DB_PASSWORD=$mysql_password
    
    echo -e "${YELLOW}Enter MySQL database name (default: marzgozir_db):${NC}"
    read -r mysql_db
    DB_NAME=${mysql_db:-marzgozir_db}
    
    # Test connection
    if ! test_mysql_connection; then
        echo -e "${RED}Failed to connect to MySQL database. Please check your credentials and try again.${NC}"
        setup_mysql_config
        return
    fi
    
    echo -e "${GREEN}MySQL configuration completed successfully.${NC}"
    export DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME
}

install_mysql_server() {
    echo -e "${YELLOW}Installing MySQL server...${NC}"
    sudo apt-get update
    sudo apt-get install -y mysql-server
    
    # Secure MySQL installation
    echo -e "${YELLOW}Securing MySQL installation...${NC}"
    
    # Generate a random password for MySQL root user
    ROOT_PASSWORD=$(openssl rand -base64 12)
    
    # Set root password
    sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${ROOT_PASSWORD}';"
    
    # Create database and user
    echo -e "${YELLOW}Creating database and user for MarzGozir...${NC}"
    
    # Generate a secure password for the application user if none was provided
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD=$(openssl rand -base64 12)
    fi
    
    sudo mysql -uroot -p${ROOT_PASSWORD} -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME};"
    sudo mysql -uroot -p${ROOT_PASSWORD} -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';"
    sudo mysql -uroot -p${ROOT_PASSWORD} -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';"
    sudo mysql -uroot -p${ROOT_PASSWORD} -e "FLUSH PRIVILEGES;"
    
    echo -e "${GREEN}MySQL server installed and configured successfully.${NC}"
    echo -e "${YELLOW}Root Password (please save this): ${ROOT_PASSWORD}${NC}"
    echo -e "${YELLOW}Application User: ${DB_USER}${NC}"
    echo -e "${YELLOW}Application Password: ${DB_PASSWORD}${NC}"
    echo -e "${YELLOW}Database Name: ${DB_NAME}${NC}"
}

test_mysql_connection() {
    # Install mysql-client if not present
    if ! command -v mysql &> /dev/null; then
        echo -e "${YELLOW}MySQL client not found. Installing...${NC}"
        sudo apt-get update
        sudo apt-get install -y mysql-client
    fi
    
    echo -e "${YELLOW}Testing MySQL connection...${NC}"
    if mysql -h${DB_HOST} -P${DB_PORT} -u${DB_USER} -p${DB_PASSWORD} -e "SELECT 1" ${DB_NAME} &>/dev/null; then
        echo -e "${GREEN}MySQL connection successful.${NC}"
        return 0
    else
        echo -e "${RED}MySQL connection failed.${NC}"
        return 1
    fi
}

extract_token_and_id() {
    echo -e "${YELLOW}Extracting token and admin ID from bot_config.py...${NC}"
    if [ -f "$CONFIG_FILE" ]; then
        echo -e "${YELLOW}Current bot_config.py content:${NC}"
        cat "$CONFIG_FILE"
        TOKEN=$(grep -E "^TOKEN\s*=" "$CONFIG_FILE" | sed -E "s/TOKEN\s*=\s*['\"]?([^'\"]+)['\"]?/\1/" | tr -d ' ')
        ADMIN_ID=$(grep -E "^ADMIN_IDS\s*=" "$CONFIG_FILE" | sed -E "s/ADMIN_IDS\s*=\s*\[(.*)\]/\1/" | tr -d ' ')
        if [ -n "$TOKEN" ] && [ -n "$ADMIN_ID" ] && [[ "$TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]+$ ]] && [[ "$ADMIN_ID" =~ ^[0-9]+$ ]]; then
            echo -e "${YELLOW}Extracted TOKEN: $TOKEN${NC}"
            echo -e "${YELLOW}Extracted ADMIN_ID: $ADMIN_ID${NC}"
            if validate_token "$TOKEN"; then
                echo -e "${GREEN}Valid token and admin ID extracted${NC}"
                export TOKEN ADMIN_ID
                return 0
            fi
        fi
        echo -e "${RED}Invalid or missing token/admin ID in bot_config.py${NC}"
    else
        echo -e "${RED}bot_config.py not found${NC}"
    fi
    get_token_and_id
}

extract_db_config() {
    echo -e "${YELLOW}Extracting database configuration from bot_config.py...${NC}"
    if [ -f "$CONFIG_FILE" ]; then
        DB_TYPE=$(grep -E "^DB_TYPE\s*=" "$CONFIG_FILE" | sed -E "s/DB_TYPE\s*=\s*['\"]?([^'\"]+)['\"]?/\1/" | tr -d ' ')
        if [ "$DB_TYPE" == "mysql" ]; then
            DB_HOST=$(grep -E "^DB_HOST\s*=" "$CONFIG_FILE" | sed -E "s/DB_HOST\s*=\s*['\"]?([^'\"]+)['\"]?/\1/" | tr -d ' ')
            DB_PORT=$(grep -E "^DB_PORT\s*=" "$CONFIG_FILE" | sed -E "s/DB_PORT\s*=\s*([0-9]+)/\1/" | tr -d ' ')
            DB_USER=$(grep -E "^DB_USER\s*=" "$CONFIG_FILE" | sed -E "s/DB_USER\s*=\s*['\"]?([^'\"]+)['\"]?/\1/" | tr -d ' ')
            DB_PASSWORD=$(grep -E "^DB_PASSWORD\s*=" "$CONFIG_FILE" | sed -E "s/DB_PASSWORD\s*=\s*['\"]?([^'\"]+)['\"]?/\1/" | tr -d ' ')
            DB_NAME=$(grep -E "^DB_NAME\s*=" "$CONFIG_FILE" | sed -E "s/DB_NAME\s*=\s*['\"]?([^'\"]+)['\"]?/\1/" | tr -d ' ')
            
            echo -e "${YELLOW}Extracted DB_TYPE: $DB_TYPE${NC}"
            echo -e "${YELLOW}Extracted DB_HOST: $DB_HOST${NC}"
            echo -e "${YELLOW}Extracted DB_PORT: $DB_PORT${NC}"
            echo -e "${YELLOW}Extracted DB_USER: $DB_USER${NC}"
            echo -e "${YELLOW}Extracted DB_NAME: $DB_NAME${NC}"
            
            export DB_TYPE DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME
            return 0
        else
            echo -e "${YELLOW}Extracted DB_TYPE: $DB_TYPE (SQLite)${NC}"
            export DB_TYPE
            return 0
        fi
    else
        echo -e "${RED}bot_config.py not found${NC}"
    fi
    select_database_type
}

edit_bot_config() {
    echo -e "${YELLOW}Editing bot_config.py...${NC}"
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${YELLOW}bot_config.py not found in repository, creating default...${NC}"
        cat > "$CONFIG_FILE" << EOF
TOKEN = "SET_YOUR_TOKEN"
ADMIN_IDS = [123456789]

# Database configuration
DB_TYPE = "sqlite"  # "sqlite" or "mysql"
DB_PATH = "data/bot_data.db"  # For SQLite

# MySQL configuration (used only if DB_TYPE is "mysql")
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "marzgozir_user"
DB_PASSWORD = "marzgozir_password"
DB_NAME = "marzgozir_db"

CACHE_DURATION = 30
VERSION = "V1.1.3"
EOF
    fi
    
    # Fix malformed TOKEN line
    sed -i 's|^TOKEN\s*=\s*SET_YOUR_TOKEN.*|TOKEN = "SET_YOUR_TOKEN"|' "$CONFIG_FILE"
    
    echo -e "${YELLOW}Before edit - bot_config.py content:${NC}"
    cat "$CONFIG_FILE"
    
    echo -e "${YELLOW}Using TOKEN: $TOKEN${NC}"
    echo -e "${YELLOW}Using ADMIN_ID: $ADMIN_ID${NC}"
    echo -e "${YELLOW}Using DB_TYPE: $DB_TYPE${NC}"
    
    sed -i "s|^TOKEN\s*=\s*['\"].*['\"]|TOKEN = \"$TOKEN\"|" "$CONFIG_FILE"
    sed -i "s|^ADMIN_IDS\s*=\s*\[.*\]|ADMIN_IDS = [$ADMIN_ID]|" "$CONFIG_FILE"
    sed -i "s|^DB_TYPE\s*=\s*['\"].*['\"]|DB_TYPE = \"$DB_TYPE\"|" "$CONFIG_FILE"
    
    if [ "$DB_TYPE" == "mysql" ]; then
        echo -e "${YELLOW}Updating MySQL configuration...${NC}"
        sed -i "s|^DB_HOST\s*=\s*['\"].*['\"]|DB_HOST = \"$DB_HOST\"|" "$CONFIG_FILE"
        sed -i "s|^DB_PORT\s*=\s*[0-9]*|DB_PORT = $DB_PORT|" "$CONFIG_FILE"
        sed -i "s|^DB_USER\s*=\s*['\"].*['\"]|DB_USER = \"$DB_USER\"|" "$CONFIG_FILE"
        sed -i "s|^DB_PASSWORD\s*=\s*['\"].*['\"]|DB_PASSWORD = \"$DB_PASSWORD\"|" "$CONFIG_FILE"
        sed -i "s|^DB_NAME\s*=\s*['\"].*['\"]|DB_NAME = \"$DB_NAME\"|" "$CONFIG_FILE"
    fi
    
    chmod 644 "$CONFIG_FILE"
    
    echo -e "${YELLOW}After edit - bot_config.py content:${NC}"
    cat "$CONFIG_FILE"
    
    # Verify the changes
    if grep -q "TOKEN = \"$TOKEN\"" "$CONFIG_FILE" && grep -q "ADMIN_IDS = \[$ADMIN_ID\]" "$CONFIG_FILE" && grep -q "DB_TYPE = \"$DB_TYPE\"" "$CONFIG_FILE"; then
        echo -e "${GREEN}bot_config.py updated successfully${NC}"
    else
        echo -e "${RED}Error: Failed to update bot_config.py${NC}"
        echo -e "${YELLOW}Expected TOKEN: $TOKEN${NC}"
        echo -e "${YELLOW}Expected ADMIN_ID: $ADMIN_ID${NC}"
        echo -e "${YELLOW}Expected DB_TYPE: $DB_TYPE${NC}"
        exit 1
    fi
}

setup_data_directory() {
    echo -e "${YELLOW}Setting up database directory and permissions...${NC}"
    mkdir -p "$DATA_DIR"
    chmod 777 "$DATA_DIR"
    if [ "$DB_TYPE" == "sqlite" ]; then
        rm -f "$DB_FILE"
    fi
    echo -e "${GREEN}Database directory configured successfully${NC}"
}

update_requirements() {
    echo -e "${YELLOW}Updating requirements.txt with database dependencies...${NC}"
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        if [ "$DB_TYPE" == "mysql" ] && ! grep -q "mysql-connector-python" "$INSTALL_DIR/requirements.txt"; then
            echo "mysql-connector-python==8.0.32" >> "$INSTALL_DIR/requirements.txt"
            echo -e "${GREEN}Added MySQL connector to requirements.txt${NC}"
        fi
    else
        echo -e "${RED}requirements.txt not found${NC}"
    fi
}

check_required_files() {
    echo -e "${YELLOW}Verifying required files...${NC}"
    for file in Dockerfile docker-compose.yml requirements.txt main.py bot/handlers.py bot/menus.py bot/states.py database/db.py utils/message_utils.py utils/activity_logger.py; do
        if [ ! -f "$INSTALL_DIR/$file" ]; then
            echo -e "${RED}Error: File $file not found!${NC}"
            return 1
        fi
    done
    echo -e "${GREEN}All required files are present${NC}"
    return 0
}

cleanup_docker() {
    echo -e "${YELLOW}Cleaning up existing Docker containers, images, and volumes...${NC}"
    if [ -f "$COMPOSE_FILE" ]; then
        sudo docker-compose -f "$COMPOSE_FILE" down --volumes --rmi all 2>/dev/null || true
    fi
    sudo docker images -q -f "reference=$PROJECT_NAME" | sort -u | xargs -r sudo docker rmi 2>/dev/null || true
    sudo docker ps -a -q -f "name=$PROJECT_NAME" | xargs -r sudo docker rm 2>/dev/null || true
    echo -e "${GREEN}Docker cleanup completed${NC}"
}

check_container_status() {
    echo -e "${YELLOW}Checking container status...${NC}"
    sleep 5
    container_status=$(sudo docker ps -q -f "name=$PROJECT_NAME")
    if [ -n "$container_status" ]; then
        echo -e "${GREEN}Container is running successfully${NC}"
        return 0
    else
        echo -e "${RED}Error: Container failed to start${NC}"
        sudo docker-compose logs
        return 1
    fi
}

create_db_docs() {
    echo -e "${YELLOW}Creating database documentation...${NC}"
    cat > "$INSTALL_DIR/db_mysql.md" << EOF
# راهنمای دیتابیس MarzGozir

## نوع‌های دیتابیس پشتیبانی شده
MarzGozir از دو نوع دیتابیس پشتیبانی می‌کند:

### SQLite
- **استفاده آسان**: نیازی به نصب سرور دیتابیس ندارد
- **فایل-محور**: تمام داده‌ها در یک فایل ذخیره می‌شوند
- **پیکربندی ساده**: نیازی به تنظیمات پیچیده ندارد
- **مناسب برای**: استفاده‌های شخصی و پروژه‌های کوچک با تعداد کاربران محدود

### MySQL
- **قدرتمندتر**: امکانات پیشرفته و کارایی بالاتر برای مقیاس بزرگ
- **چند-کاربره**: امکان دسترسی همزمان چندین کاربر
- **مقیاس‌پذیری**: مناسب برای پروژه‌های با تعداد کاربران زیاد
- **پیکربندی پیچیده‌تر**: نیاز به نصب و تنظیم سرور MySQL دارد

## نحوه تغییر نوع دیتابیس
برای تغییر نوع دیتابیس، فایل `bot_config.py` را ویرایش کنید:

\`\`\`python
# برای استفاده از SQLite
DB_TYPE = "sqlite"

# برای استفاده از MySQL
DB_TYPE = "mysql"
DB_HOST = "localhost"  # آدرس سرور MySQL
DB_PORT = 3306         # پورت MySQL
DB_USER = "username"   # نام کاربری
DB_PASSWORD = "pass"   # رمز عبور
DB_NAME = "marzgozir_db"  # نام دیتابیس
\`\`\`

## تفاوت‌های اصلی

| ویژگی | SQLite | MySQL |
|-------|--------|-------|
| سرعت | مناسب برای حجم کم داده | سریع‌تر برای حجم زیاد داده |
| نصب | نیاز به نصب ندارد | نیاز به نصب سرور دارد |
| مقیاس‌پذیری | محدود | بالا |
| همزمانی | محدود | پیشرفته |
| پشتیبان‌گیری | کپی فایل | ابزارهای پیشرفته |

# MarzGozir Database Guide

## Supported Database Types
MarzGozir supports two types of databases:

### SQLite
- **Easy to use**: No database server installation required
- **File-based**: All data stored in a single file
- **Simple configuration**: No complex setup needed
- **Suitable for**: Personal use and small projects with limited users

### MySQL
- **More powerful**: Advanced features and better performance for large scale
- **Multi-user**: Allows simultaneous access from multiple users
- **Scalability**: Suitable for projects with many users
- **More complex setup**: Requires MySQL server installation and configuration

## How to Change Database Type
To change the database type, edit the `bot_config.py` file:

\`\`\`python
# For SQLite
DB_TYPE = "sqlite"

# For MySQL
DB_TYPE = "mysql"
DB_HOST = "localhost"  # MySQL server address
DB_PORT = 3306         # MySQL port
DB_USER = "username"   # Username
DB_PASSWORD = "pass"   # Password
DB_NAME = "marzgozir_db"  # Database name
\`\`\`

## Key Differences

| Feature | SQLite | MySQL |
|---------|--------|-------|
| Speed | Good for small data | Faster for large data |
| Installation | No installation needed | Server installation required |
| Scalability | Limited | High |
| Concurrency | Limited | Advanced |
| Backup | File copy | Advanced tools |
EOF
    echo -e "${GREEN}Database documentation created successfully${NC}"
}

install_bot() {
    echo -e "${YELLOW}Starting bot installation...${NC}"
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}Existing directory detected. Removing old installation...${NC}"
        cd /tmp || { echo -e "${RED}Failed to change to /tmp${NC}"; exit 1; }
        cleanup_docker
        sudo rm -rf "$INSTALL_DIR" || { echo -e "${RED}Failed to remove $INSTALL_DIR${NC}"; exit 1; }
        if [ -d "$INSTALL_DIR" ]; then
            echo -e "${RED}Error: Directory $INSTALL_DIR still exists after removal attempt${NC}"
            exit 1
        fi
    fi
    check_prerequisites
    echo -e "${YELLOW}Cloning repository from $REPO_URL into $INSTALL_DIR...${NC}"
    cd /tmp || { echo -e "${RED}Failed to change to /tmp${NC}"; exit 1; }
    git clone "$REPO_URL" "$INSTALL_DIR" 2>&1 || { echo -e "${RED}Failed to clone repository${NC}"; exit 1; }
    cd "$INSTALL_DIR" || { echo -e "${RED}Failed to change to $INSTALL_DIR${NC}"; exit 1; }
    check_required_files || { echo -e "${RED}Required files are missing${NC}"; exit 1; }
    get_token_and_id || { echo -e "${RED}Failed to collect token and ID${NC}"; exit 1; }
    select_database_type || { echo -e "${RED}Failed to select database type${NC}"; exit 1; }
    edit_bot_config
    setup_data_directory
    update_requirements
    create_db_docs
    echo -e "${YELLOW}Building and starting bot with Docker Compose...${NC}"
    sudo docker-compose build --no-cache || { echo -e "${RED}Failed to build Docker image${NC}"; exit 1; }
    sudo docker-compose up -d || { echo -e "${RED}Failed to start Docker Compose${NC}"; sudo docker-compose logs; exit 1; }
    check_container_status || exit 1
    echo -e "${GREEN}Bot installed and running successfully!${NC}"
    if [ "$DB_TYPE" == "mysql" ]; then
        echo -e "${YELLOW}MySQL configuration: ${NC}"
        echo -e "${YELLOW}Host: $DB_HOST${NC}"
        echo -e "${YELLOW}Port: $DB_PORT${NC}"
        echo -e "${YELLOW}User: $DB_USER${NC}"
        echo -e "${YELLOW}Database: $DB_NAME${NC}"
    fi
}

uninstall_bot() {
    echo -e "${YELLOW}Uninstalling bot...${NC}"
    if [ -d "$INSTALL_DIR" ]; then
        cd "$INSTALL_DIR" || exit 1
        cleanup_docker
        cd /tmp || { echo -e "${RED}Failed to change to /tmp${NC}"; exit 1; }
        sudo rm -rf "$INSTALL_DIR" || { echo -e "${RED}Failed to remove $INSTALL_DIR${NC}"; exit 1; }
        echo -e "${GREEN}Bot uninstalled successfully${NC}"
    else
        echo -e "${RED}Bot is not installed!${NC}"
    fi
}

update_bot() {
    echo -e "${YELLOW}Updating bot...${NC}"
    if [ -d "$INSTALL_DIR" ]; then
        cd "$INSTALL_DIR" || exit 1
        # Backup database
        if [ "$DB_TYPE" == "sqlite" ] && [ -f "$DB_FILE" ]; then
            cp "$DB_FILE" "/tmp/bot_data.db.bak" || { echo -e "${RED}Failed to backup database${NC}"; exit 1; }
        fi
        # Extract token, admin ID and database config
        extract_token_and_id
        extract_db_config
        # Clean up Docker and remove project directory
        cleanup_docker
        cd /tmp || { echo -e "${RED}Failed to change to /tmp${NC}"; exit 1; }
        sudo rm -rf "$INSTALL_DIR" || { echo -e "${RED}Failed to remove $INSTALL_DIR${NC}"; exit 1; }
        if [ -d "$INSTALL_DIR" ]; then
            echo -e "${RED}Error: Directory $INSTALL_DIR still exists after removal attempt${NC}"
            exit 1
        fi
        # Re-clone repository
        echo -e "${YELLOW}Cloning repository from $REPO_URL into $INSTALL_DIR...${NC}"
        git clone "$REPO_URL" "$INSTALL_DIR" 2>&1 || { echo -e "${RED}Failed to clone repository${NC}"; exit 1; }
        cd "$INSTALL_DIR" || { echo -e "${RED}Failed to change to $INSTALL_DIR${NC}"; exit 1; }
        check_required_files || { echo -e "${RED}Required files are missing${NC}"; exit 1; }
        # Restore database for SQLite
        if [ "$DB_TYPE" == "sqlite" ] && [ -f "/tmp/bot_data.db.bak" ]; then
            mkdir -p "$DATA_DIR"
            mv "/tmp/bot_data.db.bak" "$DB_FILE" || { echo -e "${RED}Failed to restore database${NC}"; exit 1; }
            chmod 777 "$DATA_DIR"
        fi
        # Edit config with stored token, admin ID and database config
        edit_bot_config
        setup_data_directory
        update_requirements
        create_db_docs
        echo -e "${YELLOW}Building and starting bot with Docker Compose...${NC}"
        sudo docker-compose build --no-cache || { echo -e "${RED}Failed to build Docker image${NC}"; exit 1; }
        sudo docker-compose up -d || { echo -e "${RED}Failed to start Docker Compose${NC}"; sudo docker-compose logs; exit 1; }
        check_container_status || exit 1
        echo -e "${GREEN}Bot updated and running successfully!${NC}"
    else
        echo -e "${RED}Bot is not installed!${NC}"
    fi
}

restart_bot() {
    echo -e "${YELLOW}Restarting bot...${NC}"
    if [ -d "$INSTALL_DIR" ]; then
        cd "$INSTALL_DIR" || exit 1
        sudo docker-compose restart || { echo -e "${RED}Failed to restart bot${NC}"; exit 1; }
        check_container_status || exit 1
        echo -e "${GREEN}Bot restarted successfully${NC}"
    else
        echo -e "${RED}Bot is not installed!${NC}"
    fi
}

reset_token_and_id() {
    echo -e "${YELLOW}Resetting bot token and admin ID...${NC}"
    if [ -d "$INSTALL_DIR" ]; then
        cd "$INSTALL_DIR" || exit 1
        get_token_and_id || { echo -e "${RED}Failed to collect token and ID${NC}"; exit 1; }
        edit_bot_config
        restart_bot
    else
        echo -e "${RED}Bot is not installed!${NC}"
    fi
}

change_database_config() {
    echo -e "${YELLOW}Changing database configuration...${NC}"
    if [ -d "$INSTALL_DIR" ]; then
        cd "$INSTALL_DIR" || exit 1
        select_database_type || { echo -e "${RED}Failed to select database type${NC}"; exit 1; }
        edit_bot_config
        update_requirements
        sudo docker-compose build --no-cache || { echo -e "${RED}Failed to build Docker image${NC}"; exit 1; }
        sudo docker-compose up -d || { echo -e "${RED}Failed to start Docker Compose${NC}"; sudo docker-compose logs; exit 1; }
        check_container_status || exit 1
        echo -e "${GREEN}Database configuration changed successfully!${NC}"
    else
        echo -e "${RED}Bot is not installed!${NC}"
    fi
}

show_menu() {
    clear
    echo -e "${YELLOW}===== MarzGozir Bot Management Menu =====${NC}"
    echo "1) Install Bot"
    echo "2) Update Bot"
    echo "3) Uninstall Bot"
    echo "4) Change Bot Token and Admin ID"
    echo "5) Change Database Configuration"
    echo "6) Restart Bot"
    echo "7) Exit"
    echo -e "${YELLOW}Please select an option (1-7):${NC}"
}

while true; do
    show_menu
    read -r choice
    case $choice in
        1) install_bot ;;
        2) update_bot ;;
        3) uninstall_bot ;;
        4) reset_token_and_id ;;
        5) change_database_config ;;
        6) restart_bot ;;
        7) echo -e "${GREEN}Exiting program...${NC}"; exit 0 ;;
        *) echo -e "${RED}Invalid option! Please select a number between 1 and 7.${NC}" ;;
    esac
    echo -e "${YELLOW}Press any key to return to the menu...${NC}"
    read -n 1
done
