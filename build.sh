#!/usr/bin/env bash
# Render runs this script on every deploy, before starting the app.
# exit immediately if any command fails, so a broken deploy doesn't
# silently go live.
set -o errexit

pip install -r requirements.txt

# Build the Tailwind CSS / JS bundle so collectstatic below has
# something to actually collect from static/dist/.
cd frontend
npm install

# Some CI/build environments (Render's included) don't reliably
# preserve the executable bit on npm's locally-installed binaries,
# which causes "vite: Permission denied" even though npm install
# itself succeeded. Force it explicitly before running the build.
chmod +x node_modules/.bin/*

npm run build
cd ..

python manage.py collectstatic --no-input

python manage.py migrate