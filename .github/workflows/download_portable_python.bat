@echo off
REM Make a portable python environment in ./python

REM Version info
set PYTHON_VERSION=3.10.11
set PYTHON_VER_SHORT=310

REM Delete ./python if exist
if exist python rmdir /s python

REM Download embeddable python
curl -OL https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
powershell Expand-Archive -Force -Path python-%PYTHON_VERSION%-embed-amd64.zip
del python-%PYTHON_VERSION%-embed-amd64.zip
cd python-%PYTHON_VERSION%-embed-amd64

REM Remove unnecessary files
del pythonw.exe python.cat python%PYTHON_VER_SHORT%._pth
del python3.dll libcrypto-*.dll libssl-*.dll sqlite*.dll
del _asyncio.pyd _bz2.pyd _decimal.pyd _elementtree.pyd _hashlib.pyd
del _lzma.pyd _msi.pyd _overlapped.pyd _queue.pyd
del _sqlite3.pyd _ssl.pyd _uuid.pyd _zoneinfo.pyd
del pyexpat.pyd unicodedata.pyd winsound.pyd

REM Remove unnecessary files from pythonXXX.zip
powershell Expand-Archive -Force -Path python%PYTHON_VER_SHORT%.zip
cd python%PYTHON_VER_SHORT%
rmdir /s /q asyncio curses dbm distutils email html http lib2to3 msilib
rmdir /s /q pydoc_data site-packages sqlite3 tomllib unittest urllib
rmdir /s /q wsgiref xml xmlrpc zoneinfo
del _aix_support.pyc _compression.pyc _markupbase.pyc _osx_support.pyc _pydecimal.pyc _strptime.pyc
del aifc.pyc ast.pyc asynchat.pyc asyncore.pyc base64.pyc bz2.pyc
del calendar.pyc cgi.pyc cgitb.pyc configparser.pyc cProfile.pyc csv.pyc
del datetime.pyc difflib.pyc dis.pyc doctest.pyc fileinput.pyc fractions.pyc ftplib.pyc gzip.pyc
del getopt.pyc graphlib.pyc hashlib.pyc hmac.pyc imaplib.pyc imghdr.pyc ipaddress.pyc lzma.pyc
del mailbox.pyc mailcap.pyc netrc.pyc nntplib.pyc nturl2path.pyc
del opcode.pyc optparse.pyc pdb.pyc pickletools.pyc plistlib.pyc poplib.pyc pprint.pyc profile.pyc pstats.pyc pydoc.pyc quopri.pyc
del rlcompleter.pyc sched.pyc shelve.pyc shlex.pyc smtpd.pyc smtplib.pyc sndhdr.pyc socketserver.pyc ssl.pyc statistics.pyc sunau.pyc symtable.pyc
del tarfile.pyc telnetlib.pyc timeit.pyc tty.pyc
del uuid.pyc wave.pyc webbrowser.pyc xdrlib.pyc zipapp.pyc zipfile.pyc zipimport.pyc
powershell Compress-Archive -Force -Path * -Destination ../python%PYTHON_VER_SHORT%.zip
cd ..
rmdir /s /q python%PYTHON_VER_SHORT%
cd ..

REM Rename folder
rename python-%PYTHON_VERSION%-embed-amd64 python

pause
