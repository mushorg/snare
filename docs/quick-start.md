# Quick Start

SNARE is a web application honeypot and is the successor of [Glastopf](https://github.com/mushorg/glastopf), which has many of the same features as [Glastopf](https://github.com/mushorg/glastopf) as well as ability to convert existing Web pages into attack surfaces with [TANNER](https://github.com/mushorg/tanner). Every event sent from SNARE to [TANNER](https://github.com/mushorg/tanner) is evaluated, and [TANNER](https://github.com/mushorg/tanner) decides how SNARE should respond to the client. This allows the honeypot to produce dynamic responses which improves its camouflage. SNARE when fingerprinted by attackers shows that it is a Nginx Web application server.

## Basic Concepts

- Surface first. Focus on the attack surface generation. Clone with `Cloner`.
- Sensors and masters. Lightweight collectors (SNARE) and central decision maker (tanner).

## Getting started

> You need Python3. We tested primarily with \>=3.6
> This was tested with a recent Ubuntu based Linux.

### Steps to setup

1. Get SNARE: `git clone https://github.com/mushorg/snare.git` and `cd snare`
2. [Optional] Make virtual environment: `python3 -m venv venv`
3. [Optional] Activate virtual environment: `. venv/bin/activate`

> Do not use sudo with below commands if you're running snare in virtual environment.

1. Install requirements: `sudo pip3 install -r requirements.txt`
2. Setup snare: `sudo python3 setup.py install`
3. Clone a page: `sudo clone --target http://example.com --path <path to base dir>`
4. Run SNARE: `sudo snare --port 8080 --page-dir example.com --path <path to base dir>` (See parameters description for more info)
5. Test: Visit <http://localhost:8080/index.html>
6. (Optionally) Have your own [tanner](https://github.com/mushorg/tanner) service running.

> Cloner clones the whole website, to restrict to a desired depth of cloning add `--max-depth` parameter

You obviously want to bind to 0.0.0.0 and port 80 when running in *production*.

## Docker build instructions

1. Change current directory to `snare` project directory
2. `docker-compose build`
3. `docker-compose up`

More information about running `docker-compose` can be found [here](https://docs.docker.com/compose/gettingstarted/).
