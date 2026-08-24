#!/usr/bin/env bash
# Render runs this script on every deploy, before starting the app.
# exit immediately if any command fails, so a broken deploy doesn't
# silently go live.
set -o errexit

# Temporary diagnostic: confirms whether Render's build environment
# actually has DATABASE_URL set, without printing the real value.
# Remove this block once the database connection is confirmed working.
python3 -c "import os; print('DEBUG: DATABASE_URL is set:', 'DATABASE_URL' in os.environ)"

pip install -r requirements.txt

# Build the Tailwind CSS / JS bundle so collectstatic below has
# something to actually collect from static/dist/.
cd frontend

# npm ci (not npm install) deletes node_modules first and installs
# strictly from package-lock.json. This guarantees a clean install
# every build -- npm install alone can leave a corrupted, half-built
# node_modules in place if a previous build died partway through,
# which is exactly what caused the "Cannot find module .../vite/dist
# /node/cli.js" error on the last attempt.
npm ci

chmod +x node_modules/.bin/*

npm run build
cd ..

python manage.py collectstatic --no-input

python manage.py migrate