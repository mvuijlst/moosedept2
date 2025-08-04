#!/bin/bash

set -e

# === CONFIGURATION ===
VPS_ALIAS=yusupov
VPS_PATH=/home/django/moosedept

UGENT_USER=mvuijlst
UGENT_HOST=users.ugent.be
UGENT_PATH=public_html

echo "=============================="
echo "      HUGO DEPLOY SCRIPT"
echo "=============================="
echo ""

# === CHOOSE TARGET ===
echo "Where do you want to deploy?"
echo "  1) Hetzner VPS (moosedept.org)"
echo "  2) UGent webspace (users.ugent.be/~mvuijlst/)"
echo "  3) Both"
read -p "Enter your choice (1/2/3): " TARGET_CHOICE

# === ASK FOR DRY RUN ===
read -p "Do a dry run? (y/N): " DRY_CHOICE

RSYNC_FLAGS="-avz --delete"
if [[ "$DRY_CHOICE" == "y" || "$DRY_CHOICE" == "Y" ]]; then
    echo "🧪 Dry run enabled — no files will actually be uploaded."
    RSYNC_FLAGS="$RSYNC_FLAGS --dry-run"
fi

# === DEPLOY TO VPS ===
if [[ "$TARGET_CHOICE" == "1" || "$TARGET_CHOICE" == "3" ]]; then
    echo ""
    echo "🏗️  Building Hugo site for Hetzner VPS (moosedept.org)..."
    hugo --baseURL "https://moosedept.org"
    echo "🚀 Deploying to Hetzner VPS ($VPS_ALIAS)..."
    rsync $RSYNC_FLAGS public/ $VPS_ALIAS:$VPS_PATH
fi

# === DEPLOY TO UGENT ===
if [[ "$TARGET_CHOICE" == "2" || "$TARGET_CHOICE" == "3" ]]; then
    echo ""
    echo "🏗️  Building Hugo site for UGent webspace..."
    hugo --baseURL "http://users.ugent.be/~mvuijlst/"
    echo "🚀 Deploying to UGent webspace ($UGENT_USER@$UGENT_HOST)..."
    rsync $RSYNC_FLAGS public/ $UGENT_USER@$UGENT_HOST:$UGENT_PATH
fi

echo ""
echo "✅ Done."
