#!/bin/bash
# Manual PyPI upload script
# Usage: ./upload-to-pypi.sh

set -e

echo "🏗️  Building package..."
python -m build

echo "🔍 Checking package..."
python -m twine check dist/*

echo ""
echo "📦 Package built successfully!"
echo ""
echo "To upload to PyPI:"
echo "1. Make sure you have PyPI credentials configured"
echo "2. Run: python -m twine upload dist/*"
echo ""
echo "Or with token:"
echo "export TWINE_USERNAME=__token__"
echo "export TWINE_PASSWORD=pypi-your_token_here"
echo "python -m twine upload dist/*"
echo ""
echo "For TestPyPI (recommended for testing):"
echo "python -m twine upload --repository testpypi dist/*"