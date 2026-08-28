#!/usr/bin/env bash
# Render runs this script on every deploy, before starting the app.
# exit immediately if any command fails, so a broken deploy doesn't
# silently go live.
set -o errexit


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
python manage.py migrate

python manage.py shell -c "
from pages.models import Location
import time
print('DEBUG: total locations:', Location.objects.count())
print('DEBUG: missing coords BEFORE:', Location.objects.filter(latitude__isnull=True).count())
for loc in Location.objects.filter(latitude__isnull=True):
    loc.save()
    time.sleep(1)
print('DEBUG: missing coords AFTER:', Location.objects.filter(latitude__isnull=True).count())
"
python manage.py createsuperuser --noinput || true