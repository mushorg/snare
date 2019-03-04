SNARE
=====

Super Next generation Advanced Reactive honEypot

Snare is a web application honeypot and is the successor of Glastopf, which has many of the same
features as Glastopf as well as ability to convert existing Web pages into attack surfaces with TANNER.
SNARE is an abbreviation for Super Next generation Advanced Reactive HonEypot. Every event sent from
SNARE to TANNER is evaluated, and TANNER decides how SNARE should respond to the client. This allows
the honeypot to produce dynamic responses which improves its camouflage.

Basic Concepts
""""""""""""""

* Surface first. Focus on the attack surface generation.
* Sensors and masters. Lightweight collectors (SNARE) and central decision maker (tanner).

SNARE provides a basic Web interface that displays the number of attack sessions, total duration,
and the frequencies of types of attacks. SNARE also provides further information such as IPs,
ports, user agents, start and end times, paths and attack types on each individual session.

SNARE when fingerprinted by attackers shows that it is a Nginx Web application server.  It requires
Web contents to serve as a website. It comes with a Python program clone.py that allows the cloning
of a website.

Getting started
"""""""""""""""

 You need Python3. We tested primarily with >=3.4
 
 This was tested with a recent Ubuntu based Linux.

**Steps to setup:**

1. Get SNARE: ``git clone https://github.com/mushorg/snare.git`` and ``cd snare``

2. Install requirements: ``pip3 install -r requirements.txt``

3. Setup snare: ``sudo python3 setup.py install``

4. Clone a page: ``sudo clone --target http://example.com``

5. Run SNARE: ``sudo snare --port 8080 --page-dir example.com`` (See :doc:`parameters` description for more info)

6. Test: Visit http://localhost:8080/index.html

7. (Optionally) Have your own tanner_ service running.

.. _tanner: https://github.com/mushorg/tanner

[Note : Cloner clones the whole website, to restrict to a desired depth of cloning add ``--max-depth`` parameter]

You obviously want to bind to 0.0.0.0 and port 80 when running in *production*.
