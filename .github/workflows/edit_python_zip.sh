# Remove unnecessary files from python310.zip
unzip -d python310 python310.zip
cd python310
rm -rf curses
rm -rf dbm
rm -rf distutils
rm -rf email
rm -rf html
rm -rf http
rm -rf lib2to3
rm -rf msilib
rm -rf pydoc_data
rm -rf site-packages
rm -rf sqlite3
rm -rf urllib
rm -rf wsgiref
rm -rf xml
rm -rf xmlrpc
rm -rf zoneinfo
rm ast.pyc
rm calendar.pyc
rm csv.pyc
rm doctest.pyc
rm ftplib.pyc
rm imaplib.pyc
rm ipaddress.pyc
rm mailbox.pyc
rm nntplib.pyc
rm optparse.pyc
rm pdb.pyc
rm pickletools.pyc
rm pydoc.pyc
rm smtpd.pyc
rm smtplib.pyc
rm ssl.pyc
rm tarfile.pyc
cd ..
