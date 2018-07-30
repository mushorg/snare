Snare command line parameters
=============================
snare [**--page-dir** *folder* ] [**--list-pages**]
[**--host-ip**]
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
* **host--ip** -- host ip to bind to, default: localhost
* **index--page** -- file name of the index page, default: index.html
* **port** -- port to listen on, default: 8080
* **interface** -- interface to bind to
* **debug** -- run web server in debug mode, default: False
* **tanner** -- ip of the tanner service, default: tanner.mushmush.org
* **skip--check-version** -- skip check for update
* **slurp--enabled** -- enable nsq logging
* **slurp--host** -- nsq logging host, default: slurp.mushmush.org
* **slurp--auth** -- nsq logging auth, default: slurp
* **config** -- snare config file, default: snare.cfg
* **auto--update** -- auto update SNARE if new version available, default: True
* **update--timeout** -- update SNARE every timeout (possible labels are: **D** -- day, **H** -- hours, **M** -- minutes), default: 24H
* **server--header** -- set server header, default: nginx
