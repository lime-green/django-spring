# Django Spring

### Installing
```bash
pip install git+git://github.com/lime-green/django-spring.git#egg=django-spring --upgrade
```


### Usage

```bash
# First start the server:
spring start

# Then run a manage.py command (eg. test)
spring test --keepdb

# Optionally, specify a settings module:
DJANGO_SETTINGS_MODULE="base.settings" spring test --keepdb
```


### Comparison
For a large project I tested against, it reduced the test time from 27.8s to 14.5s! Most of the time savings are from app startup, so the largest difference will be felt for running small test suites for large projects.


#### manage.py
```
# time ./manage.py test --keepdb billing_service/tests/test_user.py
..........
----------------------------------------------------------------------
Ran 10 tests in 5.090s

OK
Preserving test database for alias 'default'...

real    0m27.773s
user    0m9.490s
sys     0m2.510s
```

#### spring
```
# time spring test --keepdb billing_service/tests/test_user.py
[APP] running command `test --keepdb billing_service/tests/test_user.py`
..........
----------------------------------------------------------------------
Ran 10 tests in 4.714s

OK
Preserving test database for alias 'default'...

real    0m14.457s
user    0m0.180s
sys     0m0.100s
```
