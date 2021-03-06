%define _topdir   .
%define buildroot ./builddir

Name:	tis-waptserver
Version:	1.4.3
Release:	1%{?dist}
Summary:	WAPT Server
BuildArch:	x86_64

Group:	        Development/Tools
License:	GPL
URL:		https://wapt.fr
Source0:	./waptserver/
Prefix:		/opt

Requires:  httpd mod_ssl dialog uwsgi-plugin-python uwsgi pytz m2crypto python-passlib python-netifaces python-urllib3 cabextract python-requests python-flask postgresql94-server python-psutil

# Turn off the brp-python-bytecompile script
%global __os_install_post %(echo '%{__os_install_post}' | sed -e 's!/usr/lib[^[:space:]]*/brp-python-bytecompile[[:space:]].*$!!g')

%description

%install
set -ex

mkdir -p %{buildroot}/opt/wapt
mkdir -p %{buildroot}/opt/wapt/log
mkdir -p %{buildroot}/opt/wapt/conf

mkdir -p %{buildroot}/opt/wapt/waptserver
mkdir -p %{buildroot}/opt/wapt/waptserver/scripts
ln -sf ../conf/waptserver.ini %{buildroot}/opt/wapt/waptserver/waptserver.ini

mkdir -p %{buildroot}/etc/init.d/

#rsync -aP --exclude 'scripts/waptserver-init-centos' --exclude '*.pyc' --exclude '.svn' --exclude 'apache-win32' --exclude 'deb' --exclude 'rpm' --exclude '.git' --exclude '.gitignore' -aP ../../../waptserver/ %{buildroot}/opt/wapt/waptserver
#rsync -aP ../../../waptserver/scripts/waptserver-init-centos %{buildroot}/etc/init.d/waptserver
#rsync -aP ../../../waptserver/scripts/postconf.py %{buildroot}/opt/wapt/waptserver/scripts/

#for libname in  'requests iniparse dns pefile.py rocket bson flask werkzeug jinja2 itsdangerous.py markupsafe dialog.py babel flask_babel' ; do \
#    rsync ../../../lib/site-packages/${i} lib),'./builddir/opt/wapt/lib/site-packages/')

(cd .. && python ./createrpm.py)

%files
%defattr(644,root,root,755)

/opt/wapt/waptserver/*
/opt/wapt/lib/*
/etc/logrotate.d/waptserver
/usr/bin/*

%attr(755,root,root)/etc/init.d/waptserver
%attr(755,root,root)/opt/wapt/waptserver/scripts/postconf.py

%attr(755,wapt,root)/opt/wapt/conf
%attr(755,wapt,root)/opt/wapt/log

%pre
getent passwd wapt >/dev/null || \
    useradd -r -g apache -d /opt/wapt -s /sbin/nologin \
    -c "Non privileged account for waptserver" wapt
exit 0

%post
old_ini='/opt/wapt/waptserver/waptserver.ini'
new_ini='/opt/wapt/conf/waptserver.ini'
if [ -e "$old_ini" ] && ! [ -L "$old_ini" ]; then
    if mv -n "$old_ini" "$new_ini"; then
	ln -s "$new_ini" "$old_ini"
    fi
fi
