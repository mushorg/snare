SNARE
=====

<b><i>Super Next generation Advanced Reactive honEypot</b></i>


Basic Concepts
--------------

- Surface first. Focus on the attack surface generation.
- Sensors and masters. Lightweight collectors (SNARE) and central decision maker (tanner).


Getting started
---------------

- You need Python3. We tested primarily with >=3.4
- This was tested with a recent Ubuntu based Linux.


1. Get SNARE: `git clone https://github.com/mushorg/snare.git`
2. Install requirements: `pip3 install -r requirements.txt`
3. Clone a page: `sudo python3 clone.py --target http://example.com`
4. Run SNARE: `sudo python3 snare.py --port 8080 --page-dir example.com`
5. Test: Visit http://localhost:8080/index.html
6. (Optionally) Have your own [tanner](https://github.com/mushorg/tanner) service running.
[Note : Cloner clones the whole website, to restrict to a desired depth of cloning add `--maxdepth` parameter]

You obviously want to bind to 0.0.0.0 and port 80 when running in <i>production</i>.
