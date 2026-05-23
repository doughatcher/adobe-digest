# Experience Digest - Justfile
# Run tasks with: just <recipe-name>

# Load environment variables from .env file
set dotenv-load

# Bazzite /var/home fix (see devcontainer skill)
project := replace(justfile_directory(), "/var/home/", "/home/")

# devcontainer-ctl.sh lives in the skill
ctl := home_directory() / ".agents/skills/devcontainer/scripts/devcontainer-ctl.sh"

# Default recipe (list available recipes)
default:
    @just --list

# Start the devcontainer + tunnel, write state to vault
up port="1313":
    {{ctl}} up {{project}} {{port}}

# Stop the devcontainer + tunnel, remove state from vault
down:
    {{ctl}} down {{project}}

# Show all active devcontainers across machines
status:
    {{ctl}} status

# Get a shell inside the devcontainer
shell:
    devcontainer exec --workspace-folder {{project}} bash

# Rebuild the devcontainer from scratch
rebuild:
    {{ctl}} down {{project}} || true
    devcontainer up --workspace-folder {{project}} --remove-existing-container

# Install Python dependencies
install: git-config
    pip3 install --user requests python-dotenv
    pip3 install -r content/requirements.txt
    @echo "Installation complete."

# Build the Hugo site
build:
    hugo

# Run Hugo development server
serve:
    hugo server --disableFastRender --noHTTPCache

# Run Hugo development server on all interfaces (for dev containers)
serve-all:
    hugo server -D --bind 0.0.0.0

# Clean Hugo build artifacts
clean-build:
    rm -rf public

# Site-Specific: Scraper
# ======================

# Run the scraper to fetch new security bulletins
scrape:
    cd content && python3 scraper.py

# Clean scraped posts tracking file (will re-scrape all bulletins)
clean-posts:
    rm -f content/scraped_posts.json
    @echo "Cleared scraped posts tracking file"

# Full clean (build artifacts and scraper tracking)
clean-all: clean-build clean-posts
    @echo "Cleaned all generated files"

# Scrape and build in one command
refresh: scrape build
    @echo "Scraped new content and rebuilt site"

# Install scraper-specific dependencies
deps:
    pip3 install pyyaml

# Micro.blog Development Tasks
# =============================

# Authenticate to Micro.blog via email
auth:
    python3 .github/deploy/microblog_auth.py

# Deploy theme changes to Micro.blog
deploy:
    python3 .github/deploy/microblog_deploy.py --all

# Backup content from Micro.blog
backup:
    python3 .github/deploy/microblog_backup.py --all

# Backup and download only (no extraction)
backup-download:
    python3 .github/deploy/microblog_backup.py --export-only

# Extract content from existing backup ZIP
backup-extract ZIP_FILE:
    python3 .github/deploy/microblog_backup.py --extract-only {{ZIP_FILE}}

# Download the latest content export ZIP from the most recent GitHub release
release-download:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p backups
    echo "Fetching latest release from doughatcher/experience-digest..."
    gh release download --repo doughatcher/experience-digest --pattern "*.zip" --dir backups --clobber
    echo "Downloaded to backups/:"
    ls -lh backups/*.zip | tail -5

# Validate session cookie
validate:
    python3 .github/deploy/microblog_deploy.py --validate-only

# Configure git identity from .env file
git-config:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -f .env ]; then
        source .env
        if [ -n "${GIT_USER_NAME:-}" ] && [ -n "${GIT_USER_EMAIL:-}" ]; then
            git config user.name "$GIT_USER_NAME"
            git config user.email "$GIT_USER_EMAIL"
            echo "✅ Git identity configured:"
            echo "   Name:  $(git config user.name)"
            echo "   Email: $(git config user.email)"
        else
            echo "❌ GIT_USER_NAME and GIT_USER_EMAIL must be set in .env file"
            exit 1
        fi
    else
        echo "❌ .env file not found"
        exit 1
    fi

# Show available commands
help:
    just --list
