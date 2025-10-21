#!/bin/bash

# eBay Reseller Manager - Push to GitHub Script
# Run this script to push all changes to your GitHub repository

echo "=========================================="
echo "eBay Reseller Manager - GitHub Push"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

echo "📊 Current Status:"
git status
echo ""

echo "📝 Recent Commit:"
git log -1 --oneline
echo ""

echo "🚀 Pushing to GitHub..."
echo ""

# Push to GitHub
git push origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Successfully pushed to GitHub!"
    echo "=========================================="
    echo ""
    echo "Your repository is now updated at:"
    echo "https://github.com/phoneman1224/ebay-reseller-manager"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ Push failed!"
    echo "=========================================="
    echo ""
    echo "You may need to:"
    echo "1. Set up GitHub authentication"
    echo "2. Check your internet connection"
    echo "3. Verify repository permissions"
    echo ""
    echo "To push manually, run:"
    echo "  cd $(pwd)"
    echo "  git push origin main"
    echo ""
fi
