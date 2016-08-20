Snare command line parameters
=============================
snare.py [**--page-dir** *folder* ] [**--list-pages**]
[**--index-page** *filename*] [**--port** *port*]
[**--interface** *ip_addr*] [**--debug** ]
[**--tanner** *tanner_ip**] [**--skip-check-version**]
[**--slurp-enabled**] [**--slurp-host** *host_ip*]
[**--slurp-auth**] [**--config** *filename*]
[**--auto-update**] [**--update-timeout** *timeout*]

Description
~~~~~~~~~~~

* **page--dir** -- name of the folder to be served
* **list--pages** -- list available pages
* **index--page** -- file name of the index page
* **port** -- port to listen on
* **interface** -- interface to bind to
* **debug** -- run web server in debug mode
* **tanner** -- ip of the tanner service
* **skip--check-version** -- skip check for update
* **slurp--enabled** -- enable nsq logging
* **slurp--host** -- nsq logging host
* **slurp--auth** -- nsq logging auth
* **config** -- snare config file
* **auto--update** -- auto update SNARE if new version available
* **update--timeout** -- update SNARE every timeout (possible labels are: **D** -- day, **H** -- hours, **M** -- minutes)
