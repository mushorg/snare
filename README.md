SNARE
=====
[![Documentation Status](https://readthedocs.org/projects/snare/badge/?version=latest)](http://snare.readthedocs.io/en/latest/?badge=latest)
[![Build Status](https://travis-ci.org/mushorg/snare.svg?branch=master)](https://travis-ci.org/mushorg/snare)
[![Coverage Status](https://coveralls.io/repos/github/mushorg/snare/badge.svg?branch=master)](https://coveralls.io/github/mushorg/snare?branch=master)

_**Super Next generation Advanced Reactive honEypot**_

About
---------
SNARE is a web application honeypot sensor attracting all sort of maliciousness from the Internet.

Documentation
--------------
The documentation can be found [here](http://snare.readthedocs.io).

Basic Concepts
--------------

- Surface first. Focus on the attack surface generation.
- Sensors and masters. Lightweight collectors (SNARE) and central decision maker (tanner).

Getting started
---------------

- You need Python3.6 to run SNARE
- This was tested with a recent Ubuntu based Linux.

#### Steps to setup

1. Get SNARE: `git clone https://github.com/mushorg/snare.git` and `cd snare`
2. Make virtual environment: `python3 -m venv venv`
3. Activate virtual environment: `. venv/bin/activate`
4. Install requirements: `pip3 install -r requirements.txt`
5. Setup snare: `python3 setup.py install`
6. Clone a page: `clone --target http://example.com --path <path to base dir>`
7. Run SNARE: `snare --port 8080 --page-dir example.com --path <path to base dir> --log-dir <path to log dir>`
8. Test: Visit http://localhost:8080/index.html
9. (Optionally) Have your own [tanner](https://github.com/mushorg/tanner) service running.

#### Docker build instructions

1. Change current directory to `snare` project directory
2. `docker-compose build`
3. `docker-compose up`

More information about running `docker-compose` can be found [here.](https://docs.docker.com/compose/gettingstarted/)

[Note : Cloner clones the whole website, to restrict to a desired depth of cloning add `--max-depth` parameter]

You obviously want to bind to 0.0.0.0 and port 80 when running in _production_.

## Testing

In order to run the tests and receive a test coverage report, we recommend running `pytest`:

    pip install pytest pytest-cov
    sudo pytest --cov-report term-missing --cov=snare snare/tests/

## Sample Output

```shell

    # sudo snare --port 8080 --page-dir example.com

       _____ _   _____    ____  ______
      / ___// | / /   |  / __ \/ ____/
      \__ \/  |/ / /| | / /_/ / __/
     ___/ / /|  / ___ |/ _, _/ /___
    /____/_/ |_/_/  |_/_/ |_/_____/


    privileges dropped, running as "nobody:nogroup"
    serving with uuid 9c10172f-7ce2-4fb4-b1c6-abc70141db56
    Debug logs will be stored in /opt/snare/snare.log
    Error logs will be stored in /opt/snare/snare.err
    ======== Running on http://127.0.0.1:8080 ========
    (Press CTRL+C to quit)
    you are running the latest version

```
