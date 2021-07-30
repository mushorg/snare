Cloner
======
.. _cloner:

Cloner clones the website that we require to be served by snare.

Command line parameters
~~~~~~~~~~~~~~~~~~~~~~~

clone [**--target** *website_url* ] [**--max-depth** *clone_depth*] [**--log_path** *LOG_PATH*] [**--css-validate**] [**--path** *PATH*] [**--headless**]

Description
~~~~~~~~~~~

* **target** -- url of website to be cloned
* **max--depth** -- maximum depth of the web-pages desired to be cloned (optional), default: full depth of the site
* **log_path** -- path to the log file (optional)
* **css-validate** -- enable css validation (optional)
* **path** -- path to save the page to be cloned (optional)
* **headless** -- enable headless cloning using pyppeteer (optional)

Headless cloning
""""""""""""""""

* Headless cloning in cloner is done with the help of `Pyppeteer <https://pyppeteer.github.io/pyppeteer/>`_ which requires Chromium.
* Chromium is automatically downloaded during the first run.
* Alternatively, you can run `pyppeteer-install` to manually download it.
* In case normal cloning does not provide satisfactory results - for example, missing content - headless cloning is a viable alternative.
* Headless cloning provides a more intelligent way of cloning websites by spawning a (headless) browser instance.
