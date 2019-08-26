# yandex-demo
Demo task for Yandex Backend School Contest '19.

Пробное задание для [школы бэкенд-разработчиков](https://yandex.ru/promo/academy/backend-school/) Яндекса.
  
## Что сделано
- [x] JSON-API на Flask, выполненное согласно [ТЗ](./TASK.pdf)
- [x] фильтрация запросов к API через fastjsonschema
- [x] бэкенд в postgres c psycopg2, без ORM.
- [x] генератор фейковых данных c Fake
- [x] некоторые тесты с Pytest

Все инструменты использовались мною впервые (кроме Flask и Postgres), так что реализацию не следует принимать за эталонную ;) замечания и комментарии приветствуются.

### Особенности реализации
* Часть полей экземпляров `Citizens` хранятся в базе данных в формате JSON. Такое решение позволит добавлять в выгрузку дополнительные поля без изменения схемы БД, а также деперсонализировать выгрузки в соответствии с № 152-ФЗ «О персональных данных» не затрагивая функциональность API... на самом деле мне просто очень хотелось опробовать хранение json в Postgres.
* Неориентированные связи экземпляров `Citizens` хранятся в отдельной таблице `Relatives`, по одной строке на связь. Целостность связей обеспечивается на уровне БД по внешнему ключу.
* Запросы к БД преимущественно реализованы через views, что упростило программный код.
* Возраст с поправкой на временную зону UTC считается SQL-функцией `utc_age` в СУБД.
  
- [] psycopg2 connection pool
- [] flask blueprints


## Оглавление

   * [Развертывание](#развертывание)
      * [Установка Postgres](#установка-postgres)
      * [Запуск тестов](#запуск-тестов)
   * [Запуск в качестве сервиса](#запуск-в-качестве-сервиса)
      * [Автоматический запуск](#автоматический-запуск)
   * [Масштабирование бэкенда](#масштабирование-бэкенда)
   * [Тестовые данные](#тестовые-данные)


## Развертывание
В Ubuntu: `apt install git virtualenv`

Чтобы опробовать приложение достаточно склонировать репозиторий в домашнюю директорию: 
```bash
git clone --depth=1 https://github.com/sergey-inform/yandex-demo.git -b dev
```
... и выполнить в ней несколько команд:
```
cd yandex-demo
virtualenv --python python3 .env
source .env/bin/activate
pip3 install -r requirements.txt 
```
### Установка Postgres
```bash
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql  
```
Для запуска тестов создаем пользователя `test` с отдельной базой данных:
```SQL
create user test with password 'secret';
CREATE DATABASE test WITH OWNER=test;
grant all privileges on database test to test;
```
Перед запуском тестов база данных автоматически очищается. 

### Запуск тестов
```
cd yandex-demo/
source .env/bin/activate
python3 -m pytest tests/
```

## Запуск в качестве сервиса
Самый простой способ -- запустить приложение с WSGI HTTP-сервером Gunicorn или аналогичным.
```
sudo apt-get install gunicorn3
```
Для запуска сервиса следует создать отдельного пользователя и постоянную базу данных:
```SQL
create user demo with password 'secret';
CREATE DATABASE demo WITH OWNER=demo;
grant all privileges on database demo to demo;
```
Параметры подключения к базе нужно прописать в файле `yandex-demo/app/app/config.py`:
```python
DB_CONF = {
    "host": "localhost",
    "port": 5432,
    "user": "demo",
    "password": "secret",
    "dbname": "demo",
    }
```
После чего создать в базе необхоимые таблицы:
```
cd yandex-demo/
source .env/bin/activate
flask init-db
```
Скрипт `yandex-demo/debug.sh` предназначен для запуска приложения в отладочном режиме на компьютере разработчика.

Для запуска на сервере выполните команду:
```
gunicorn --bind 0.0.0.0:5000 --workers 7 wsgi:app
```
### Автоматический запуск 
Чтобы приложение автоматически запускалось после перезагрузки, в системах с `systemd` создайте файл `/etc/systemd/system/yandex-demo.service` с таким содержимым:
```
[Unit]
Description=Gunicorn instance to serve yandex-demo
After=network.target

[Service]
User=nobody
Group=nogroup
WorkingDirectory=/home/entrant/yandex-demo
Environment="PATH=/home/entrant/yandex-demo/.env/bin"
ExecStart=/home/entrant/yandex-demo/.env/bin/gunicorn --workers 7 --bind 0.0.0.0:5000 wsgi:app

[Install]
WantedBy=multi-user.target
```
Путь `home/entrant/yandex-demo/` следует заменить на актуальный для вашей системы. Вместо пользователя `nobody` можно использовать вашу учетную запись, если папка yandex-demo не доступна на чтение другим пользователям.

После этого выполните команды для добавления сервиса в автозапуск и для запуска:
```
systemctl enable yandex-demo.service
systemctl start yandex-demo.service
```

Также не забудьте включить автозапуск `postgres` при старте системы. 

## Масштабирование бэкенда
Бэкенд, теоретически, довольно легко масштабируется через:
* многопоточный запуск Flask 
* in-app sharding по таблице `Imports` в разные таблицы или на разные серверы БД в сочетании с postgres_fdw.

## Тестовые данные
Для генерации тестовых данных был написан скрипт `tests/fake_citizens.py`:
```
usage: fake_citizens.py [-h] [-n N] [-k K]

Generates a large set of valid citizens data. Useful for testing.

optional arguments:
  -h, --help        show this help message and exit
  -n N, --number N  number of citizens
  -k K, --links K   number of relatives
```
Пример данных:
```json
{
  "citizens": [
    {
      "citizen_id": 1,
      "town": "Москва",
      "street": "Тополиная",
      "building": "71",
      "apartment": 134,
      "name": "Константинов Дорофей Геннадиевич",
      "birth_date": "24.02.1980",
      "gender": "male",
      "relatives": [
        1
      ]
    },
    {
      "citizen_id": 2,
      "town": "Санкт-Петербург",
      "street": "Горняцкая",
      "building": "33к4",
      "apartment": 369,
      "name": "Королева Октябрина Робертовна",
      "birth_date": "30.03.1914",
      "gender": "female",
      "relatives": [
        3
      ]
    },
    {
      "citizen_id": 3,
      "town": "Краснодар",
      "street": "Рыбацкая",
      "building": "32",
      "apartment": 147,
      "name": "Лебедев Еремей Юлианович",
      "birth_date": "11.03.1917",
      "gender": "male",
      "relatives": [
        2,
        3
      ]
    }
  ]
}
```


