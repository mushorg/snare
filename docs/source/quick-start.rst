SNARE
=====
Super Next generation Advanced Reactive honEypot

Basic concept
"""""""""""""
* Surface first: Focus on the attack surface generation.
* Sensors and masters. Lightweight collector (SNARE) and central decision maker/emulator (TANNER).

Getting started
"""""""""""""""

You need Python3. We tested primarily with >=3.4
This was tested with a recent Ubuntu based Linux.

* Get SNARE: ``git clone https://github.com/mushorg/snare.git``
* Install requirements: ``pip3 install -r requirements.txt``
* Clone a page: ``sudo python3 clone.py --target http://example.com``
* Run SNARE: ``sudo python3 snare.py --port 8080 --page-dir example.com`` (See :doc:`parameters` description for more info)
* Test: Visit ``http://localhost:8080/index.html``
* (Optionally) Have your own tanner service running.


You obviously want to bind to 0.0.0.0 and port 80 when running in production.
