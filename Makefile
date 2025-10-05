serve:
	python manage.py runserver

2serve:
	python manage.py runserver 10.216.153.102:8000

sserve:
	python manage.py runserver 192.168.1.61:8000

flush:
	python manage.py flush

fake:
	python manage.py populate_db

migrate:
	python manage.py migrate