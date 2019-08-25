# yandex-demo
Demo task for yandex backend school contest '19

sudo apt-get install python3-dev
sudo apt-get install libpq-dev

pg:
sudo -u postgres psql

create user test with password 'secret';
CREATE DATABASE test WITH OWNER=test;
grant all privileges on database test to test;

python -m pytest tests


random data:
