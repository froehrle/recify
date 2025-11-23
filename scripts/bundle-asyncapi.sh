#!/bin/bash

# Script to find and bundle all AsyncAPI files from services directory
# This script will:
# 1. Find all asyncapi.yaml/yml files in services/*/
# 2. Bundle them together into a single file at project root

set -e

echo "🔍 Finding AsyncAPI files in services directory..."

# Find all asyncapi files
ASYNCAPI_FILES=$(find services -type f \( -name "asyncapi.yaml" -o -name "asyncapi.yml" \) 2>/dev/null || true)

if [ -z "$ASYNCAPI_FILES" ]; then
  echo "❌ No AsyncAPI files found in services directory"
  exit 1
fi

echo "📁 Found AsyncAPI files:"
echo "$ASYNCAPI_FILES" | while read file; do
  echo "  - $file"
done

# Count files
FILE_COUNT=$(echo "$ASYNCAPI_FILES" | wc -l | tr -d ' ')

if [ "$FILE_COUNT" -eq 1 ]; then
  # Single file - just bundle it
  echo "📦 Bundling single AsyncAPI file..."
  asyncapi bundle $ASYNCAPI_FILES -o asyncapi-bundled.yaml
else
  # Multiple files - bundle them together
  echo "📦 Bundling $FILE_COUNT AsyncAPI files..."
  asyncapi bundle $ASYNCAPI_FILES -o asyncapi-bundled.yaml
fi

echo "✅ AsyncAPI bundle created at: asyncapi-bundled.yaml"