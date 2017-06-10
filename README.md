Py2FA
===============


A front-end program for Two-Factor Authentication written in Python and GTK.

![screenshot](https://i.imgur.com/YaJsXEx.png)
![Ubuntu 16.10](http://i.imgur.com/VAMwaKa.png)

Example
=======
Use this program to generate two-factor authentication codes for your secured accounts such as:
- Google
- Dropbox
- WordPress

and many other platforms that support two-factor authentication.

Secret keys must be supplied in valid base32 encoding (a 32-character subset of the twenty-six letters A–Z and six digits 2–7).

Dependencies
============

* [python2](http://www.python.org/ "python2")
* [PyGTK](http://www.pygtk.org/ "PyGTK")


To run the files, just create a link calling the script.

## Windows
For example on windows, right-click -> new -> shortcut, and write:

    C:\Python27\pythonw.exe C:\path_to\py2fa\main.py

## Linux
On Linux, download main.py and run it as follows:
`$ python main.py`
