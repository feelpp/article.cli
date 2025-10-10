#!/bin/bash

# Article CLI Build and Test Script

set -e

echo "🔧 Article CLI Build and Test Script"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    echo -e "${RED}❌ Error: pyproject.toml not found. Please run from package root.${NC}"
    exit 1
fi

# Function to run commands with status
run_command() {
    echo -e "${BLUE}▶ $1${NC}"
    if $1; then
        echo -e "${GREEN}✅ Success${NC}\n"
    else
        echo -e "${RED}❌ Failed${NC}\n"
        exit 1
    fi
}

# Install development dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
run_command "pip install -e ."

# Check if optional dependencies are available
echo -e "${YELLOW}🧪 Checking optional dependencies...${NC}"
if python -c "import tomli" 2>/dev/null; then
    echo -e "${GREEN}✅ tomli available for Python < 3.11${NC}"
else
    echo -e "${YELLOW}⚠️  Installing tomli for TOML support${NC}"
    run_command "pip install tomli"
fi

# Build the package
echo -e "${YELLOW}🏗️  Building package...${NC}"
if ! command -v build &> /dev/null; then
    echo -e "${YELLOW}📦 Installing build tool${NC}"
    run_command "pip install build"
fi

run_command "python -m build"

# Test installation from wheel
echo -e "${YELLOW}🧪 Testing wheel installation...${NC}"
WHEEL_FILE=$(ls dist/*.whl | head -n 1)
if [[ -f "$WHEEL_FILE" ]]; then
    echo -e "${BLUE}📦 Found wheel: $WHEEL_FILE${NC}"
    
    # Create temporary virtual environment for testing
    echo -e "${BLUE}🔧 Creating test environment...${NC}"
    python -m venv test_env
    source test_env/bin/activate
    
    # Install from wheel
    run_command "pip install $WHEEL_FILE"
    
    # Test the CLI
    echo -e "${YELLOW}🧪 Testing CLI functionality...${NC}"
    run_command "article-cli --version"
    run_command "article-cli --help"
    run_command "article-cli config create --path test-config.toml"
    
    # Cleanup
    deactivate
    rm -rf test_env test-config.toml
    echo -e "${GREEN}✅ Wheel test completed${NC}\n"
else
    echo -e "${RED}❌ No wheel file found${NC}"
    exit 1
fi

# Show package contents
echo -e "${YELLOW}📋 Package contents:${NC}"
echo -e "${BLUE}Distribution files:${NC}"
ls -la dist/

echo -e "\n${GREEN}🎉 Build and test completed successfully!${NC}"
echo -e "${BLUE}📦 Package ready for distribution${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "  1. Test upload to TestPyPI:"
echo -e "     ${BLUE}twine upload --repository testpypi dist/*${NC}"
echo -e "  2. Install and test from TestPyPI:"
echo -e "     ${BLUE}pip install --index-url https://test.pypi.org/simple/ article-cli${NC}"
echo -e "  3. Upload to PyPI:"
echo -e "     ${BLUE}twine upload dist/*${NC}"