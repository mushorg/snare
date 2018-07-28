SNARE
=====

Super Next generation Advanced Reactive honEypot

Basic Concepts
""""""""""""""

* Surface first. Focus on the attack surface generation.
* Sensors and masters. Lightweight collectors (SNARE) and central decision maker (tanner).


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

7. (Optionally) Have your own [tanner](https://github.com/mushorg/tanner) service running.

[Note : Cloner clones the whole website, to restrict to a desired depth of cloning add ``--max-depth`` parameter]

You obviously want to bind to 0.0.0.0 and port 80 when running in *production*.
