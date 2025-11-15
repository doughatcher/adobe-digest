# Adobe Digest - Justfile
# Run tasks with: just <recipe-name>

# Default recipe - show available commands
default:
    @just --list

# Install Python dependencies
install:
    pip3 install -r content/requirements.txt

# Run the scraper to fetch new security bulletins
scrape:
    cd content && python3 scraper.py

# Clean scraped posts tracking file (will re-scrape all bulletins)
clean-posts:
    rm -f content/scraped_posts.json
    @echo "Cleared scraped posts tracking file"

# Build the Hugo site
build:
    hugo

# Run Hugo development server
serve:
    hugo serve --disableFastRender

# Run Hugo development server on all interfaces (for dev containers)
serve-all:
    hugo server -D --bind 0.0.0.0

# Clean Hugo build artifacts
clean-build:
    rm -rf public

# Full clean (build artifacts and scraper tracking)
clean-all: clean-build clean-posts
    @echo "Cleaned all generated files"

# Scrape and build in one command
refresh: scrape build
    @echo "Scraped new content and rebuilt site"

deps:
    pip3 install pyyaml
