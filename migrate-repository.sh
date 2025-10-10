#!/bin/bash

# Migration Script for Existing Article Repositories
# Run this in each existing article repository to migrate from a.py/a.cli to article-cli

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📄 Article Repository Migration Script${NC}"
echo -e "${BLUE}=====================================${NC}\n"

# Check if we're in a git repository
if [[ ! -d ".git" ]]; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    exit 1
fi

echo -e "${YELLOW}🔍 Current repository: $(basename $(pwd))${NC}\n"

# Backup existing files
echo -e "${YELLOW}📋 Backing up existing files...${NC}"
if [[ -f "a.py" ]]; then
    cp a.py a.py.backup
    echo -e "${GREEN}✅ Backed up a.py to a.py.backup${NC}"
fi

if [[ -f "a.cli" ]]; then
    cp a.cli a.cli.backup
    echo -e "${GREEN}✅ Backed up a.cli to a.cli.backup${NC}"
fi

# Install article-cli
echo -e "\n${YELLOW}📦 Installing article-cli...${NC}"
if command -v pip &> /dev/null; then
    pip install article-cli
    echo -e "${GREEN}✅ article-cli installed${NC}"
else
    echo -e "${RED}❌ pip not found. Please install pip first${NC}"
    exit 1
fi

# Test installation
echo -e "\n${YELLOW}🧪 Testing installation...${NC}"
if article-cli --version; then
    echo -e "${GREEN}✅ article-cli working correctly${NC}"
else
    echo -e "${RED}❌ article-cli installation failed${NC}"
    exit 1
fi

# Create configuration file
echo -e "\n${YELLOW}⚙️  Creating configuration file...${NC}"
if [[ ! -f ".article-cli.toml" ]]; then
    article-cli config create
    echo -e "${GREEN}✅ Created .article-cli.toml${NC}"
    echo -e "${YELLOW}⚠️  Please edit .article-cli.toml with your Zotero credentials${NC}"
else
    echo -e "${BLUE}ℹ️  .article-cli.toml already exists${NC}"
fi

# Try to extract Zotero settings from old files
echo -e "\n${YELLOW}🔍 Looking for existing Zotero configuration...${NC}"

# Check for environment variables or config in old files
FOUND_GROUP_ID=""
FOUND_API_KEY=""

if [[ -f "a.cli" ]]; then
    # Extract from bash script
    GROUP_ID_LINE=$(grep "DEFAULT_ZOTERO_GROUP_ID=" a.cli 2>/dev/null || true)
    if [[ -n "$GROUP_ID_LINE" ]]; then
        FOUND_GROUP_ID=$(echo "$GROUP_ID_LINE" | cut -d'"' -f2)
        echo -e "${BLUE}ℹ️  Found GROUP_ID in a.cli: $FOUND_GROUP_ID${NC}"
    fi
fi

if [[ -f "a.py" ]]; then
    # Look for default group ID in Python script
    GROUP_ID_LINE=$(grep "group_id.*=" a.py | grep -v "self.group_id" | head -n1 2>/dev/null || true)
    if [[ -n "$GROUP_ID_LINE" ]]; then
        FOUND_GROUP_ID=$(echo "$GROUP_ID_LINE" | grep -o '"[0-9]*"' | tr -d '"' || true)
        if [[ -n "$FOUND_GROUP_ID" ]]; then
            echo -e "${BLUE}ℹ️  Found GROUP_ID in a.py: $FOUND_GROUP_ID${NC}"
        fi
    fi
fi

# Update configuration file with found values
if [[ -n "$FOUND_GROUP_ID" && -f ".article-cli.toml" ]]; then
    echo -e "${YELLOW}🔧 Updating configuration with found GROUP_ID...${NC}"
    sed -i.bak "s/group_id = \"[^\"]*\"/group_id = \"$FOUND_GROUP_ID\"/" .article-cli.toml
    echo -e "${GREEN}✅ Updated group_id in .article-cli.toml${NC}"
fi

# Check for Makefile updates needed
if [[ -f "Makefile" ]]; then
    echo -e "\n${YELLOW}🔍 Checking Makefile for updates needed...${NC}"
    if grep -q "python a.py\|./a.cli" Makefile; then
        echo -e "${YELLOW}⚠️  Makefile contains references to old scripts${NC}"
        echo -e "${BLUE}ℹ️  Consider updating Makefile to use 'article-cli' instead${NC}"
        
        # Create updated Makefile
        cp Makefile Makefile.backup
        sed 's/python a\.py/article-cli/g; s/\.\/a\.cli/article-cli/g' Makefile > Makefile.new
        echo -e "${GREEN}✅ Created Makefile.new with suggested updates${NC}"
        echo -e "${BLUE}ℹ️  Review and replace Makefile if the changes look correct${NC}"
    fi
fi

# Remove old files
echo -e "\n${YELLOW}🗑️  Cleaning up old files...${NC}"
if [[ -f "a.py" ]]; then
    rm a.py
    echo -e "${GREEN}✅ Removed a.py${NC}"
fi

if [[ -f "a.cli" ]]; then
    rm a.cli
    echo -e "${GREEN}✅ Removed a.cli${NC}"
fi

# Test the new setup
echo -e "\n${YELLOW}🧪 Testing new setup...${NC}"
if article-cli --help > /dev/null; then
    echo -e "${GREEN}✅ article-cli help working${NC}"
else
    echo -e "${RED}❌ article-cli help failed${NC}"
    exit 1
fi

# Add .article-cli.toml to git if not already tracked
if [[ -f ".article-cli.toml" ]]; then
    if ! git ls-files --error-unmatch .article-cli.toml > /dev/null 2>&1; then
        git add .article-cli.toml
        echo -e "${GREEN}✅ Added .article-cli.toml to git${NC}"
    fi
fi

# Create .gitignore entry for backup files
if [[ -f ".gitignore" ]]; then
    if ! grep -q "*.backup" .gitignore; then
        echo "*.backup" >> .gitignore
        echo -e "${GREEN}✅ Added *.backup to .gitignore${NC}"
    fi
fi

echo -e "\n${GREEN}🎉 Migration completed successfully!${NC}"
echo -e "\n${YELLOW}📋 Summary of changes:${NC}"
echo -e "  ✅ Installed article-cli package"
echo -e "  ✅ Created .article-cli.toml configuration"
echo -e "  ✅ Backed up old files (*.backup)"
echo -e "  ✅ Removed old a.py and a.cli files"

if [[ -n "$FOUND_GROUP_ID" ]]; then
    echo -e "  ✅ Migrated GROUP_ID: $FOUND_GROUP_ID"
fi

echo -e "\n${YELLOW}📝 Next steps:${NC}"
echo -e "  1. Edit .article-cli.toml with your Zotero API key"
echo -e "  2. Test: ${BLUE}article-cli update-bibtex${NC}"
echo -e "  3. Update any scripts/Makefiles to use ${BLUE}article-cli${NC}"
echo -e "  4. Commit changes: ${BLUE}git add . && git commit -m \"Migrate to article-cli package\"${NC}"

if [[ -f "Makefile.new" ]]; then
    echo -e "  5. Review and replace Makefile with Makefile.new if appropriate"
fi

echo -e "\n${BLUE}📖 For help: article-cli --help${NC}"