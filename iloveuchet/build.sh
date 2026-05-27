#!/usr/bin/env bash

set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput

#python manage.py migrate

echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'adminpass123')" | python manage.py shell