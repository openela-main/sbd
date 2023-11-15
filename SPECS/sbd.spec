#
# spec file for package sbd
#
# Copyright (c) 2014 SUSE LINUX Products GmbH, Nuernberg, Germany.
# Copyright (c) 2013 Lars Marowsky-Bree
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via http://bugs.opensuse.org/
#
%global longcommit cf5c2208bad2db2dff9b09624b89b05415c3bc11
%global shortcommit %(echo %{longcommit}|cut -c1-8)
%global modified %(echo %{longcommit}-|cut -f2 -d-)
%global github_owner Clusterlabs
%global buildnum 2

%ifarch s390x s390
# minimum timeout on LPAR diag288 watchdog is 15s
%global watchdog_timeout_default 15
%else
%global watchdog_timeout_default 5
%endif

# Be careful with sync_resource_startup_default
# being enabled. This configuration has
# to be in sync with configuration in pacemaker
# where it is called sbd_sync - assure by e.g.
# mutual rpm dependencies.
%bcond_without sync_resource_startup_default
# Syncing enabled per default will lead to
# syncing enabled on upgrade without adaption
# of the config.
# Setting can still be overruled via sysconfig.
# The setting in the config-template packaged
# will follow the default if below is is left
# empty. But it is possible to have the setting
# in the config-template deviate from the default
# by setting below to an explicit 'yes' or 'no'.
%global sync_resource_startup_sysconfig ""

Name:           sbd
Summary:        Storage-based death
License:        GPL-2.0-or-later
Version:        1.5.2
Release:        %{buildnum}%{?dist}
Url:            https://github.com/%{github_owner}/%{name}
Source0:        https://github.com/%{github_owner}/%{name}/archive/%{longcommit}/%{name}-%{longcommit}.tar.gz
Patch0:         0001-Fix-query-watchdog-avoid-issues-on-heap-allocation-f.patch
Patch1:         0002-Refactor-sbd-md-alloc-de-alloc-reverse-order.patch
Patch2:         0003-spec-convert-license-naming-to-SPDX.patch
BuildRequires:  autoconf
BuildRequires:  automake
BuildRequires:  libuuid-devel
BuildRequires:  glib2-devel
BuildRequires:  libaio-devel
BuildRequires:  corosync-devel
BuildRequires:  pacemaker-libs-devel > 1.1.12
BuildRequires:  libtool
BuildRequires:  libuuid-devel
BuildRequires:  libxml2-devel
BuildRequires:  pkgconfig
BuildRequires:  systemd
BuildRequires:  make
Conflicts:      fence-agents-sbd < 4.2.1-38
Conflicts:      pacemaker-libs < 2.0.5-4

%if 0%{?rhel} > 0
ExclusiveArch: i686 x86_64 s390x ppc64le aarch64
%endif

%if %{defined systemd_requires}
%systemd_requires
%endif

%description

This package contains the storage-based death functionality.

Available rpmbuild rebuild options:
  --with(out) : sync_resource_startup_default

%package tests
Summary:        Storage-based death environment for regression tests
License:        GPL-2.0-or-later

%description tests
This package provides an environment + testscripts for
regression-testing sbd.

###########################################################

%prep
%autosetup -n %{name}-%{longcommit} -p1

###########################################################

%build
./autogen.sh
export CFLAGS="$RPM_OPT_FLAGS -Wall -Werror"
%configure --with-watchdog-timeout-default=%{watchdog_timeout_default} \
           --with-sync-resource-startup-default=%{?with_sync_resource_startup_default:yes}%{!?with_sync_resource_startup_default:no} \
           --with-sync-resource-startup-sysconfig=%{sync_resource_startup_sysconfig} \
           --with-runstatedir=%{_rundir}
make %{?_smp_mflags}

###########################################################

%install

make DESTDIR=$RPM_BUILD_ROOT LIBDIR=%{_libdir} install
rm -rf ${RPM_BUILD_ROOT}%{_libdir}/stonith

install -D -m 0755 tests/regressions.sh $RPM_BUILD_ROOT/usr/share/sbd/regressions.sh
%if %{defined _unitdir}
install -D -m 0644 src/sbd.service $RPM_BUILD_ROOT/%{_unitdir}/sbd.service
install -D -m 0644 src/sbd_remote.service $RPM_BUILD_ROOT/%{_unitdir}/sbd_remote.service
%endif

mkdir -p ${RPM_BUILD_ROOT}%{_sysconfdir}/sysconfig
install -m 644 src/sbd.sysconfig ${RPM_BUILD_ROOT}%{_sysconfdir}/sysconfig/sbd

# Don't package static libs
find %{buildroot} -name '*.a' -type f -print0 | xargs -0 rm -f
find %{buildroot} -name '*.la' -type f -print0 | xargs -0 rm -f

###########################################################

%clean
rm -rf %{buildroot}

%if %{defined _unitdir}
%post
%systemd_post sbd.service
%systemd_post sbd_remote.service
if [ $1 -ne 1 ] ; then
	if systemctl --quiet is-enabled sbd.service 2>/dev/null
	then
		systemctl --quiet reenable sbd.service 2>/dev/null || :
	fi
	if systemctl --quiet is-enabled sbd_remote.service 2>/dev/null
	then
		systemctl --quiet reenable sbd_remote.service 2>/dev/null || :
	fi
fi

%preun
%systemd_preun sbd.service
%systemd_preun sbd_remote.service

%postun
%systemd_postun sbd.service
%systemd_postun sbd_remote.service
%endif

%files
###########################################################
%defattr(-,root,root)
%config(noreplace) %{_sysconfdir}/sysconfig/sbd
%{_sbindir}/sbd
%{_datadir}/sbd
%{_datadir}/pkgconfig/sbd.pc
%exclude %{_datadir}/sbd/regressions.sh
%doc %{_mandir}/man8/sbd*
%if %{defined _unitdir}
%{_unitdir}/sbd.service
%{_unitdir}/sbd_remote.service
%endif
%doc COPYING

%files tests
###########################################################
%defattr(-,root,root)
%dir %{_datadir}/sbd
%{_datadir}/sbd/regressions.sh
%{_libdir}/libsbdtestbed*

%changelog
* Wed May 24 2023 Klaus Wenninger <kwenning@redhat.com> - 1.5.2-2
- add required tests subdirectory in addition to gating.yaml
  that had already been brought over before

  Related: rhbz#2168567

* Wed May 24 2023 Klaus Wenninger <kwenning@redhat.com> - 1.5.2-1
- rebase to upstream v1.5.2
- convert license naming to SPDX
- make static analysis happy with a few checks & rearanges with
  dynamic-memory-management

  Resolves: rhbz#2168567

* Fri Jul 15 2022 Klaus Wenninger <kwenning@redhat.com> - 1.5.1-2
- Be a bit more descriptive on issues opening watchdog-devices

  Resolves: rhbz#1841402

* Wed Dec 1 2021 Klaus Wenninger <kwenning@redhat.com> - 1.5.1-1
- rebase to upstream v1.5.1

  Resolves: rhbz#2013256

* Wed Aug 18 2021 Klaus Wenninger <kwenning@redhat.com> - 1.5.0-2
- reverted watchdog_timeout_default to 5s
  (slipped in via an unreleased change on 8.4.0 branch)

  Resolves: rhbz#1980797

* Mon Jul 19 2021 Klaus Wenninger <kwenning@redhat.com> - 1.5.0-1
- rebase to upstream v1.5.0
- sync with c9s & fedora

  Resolves: rhbz#1980797

* Mon Feb 1 2021 Klaus Wenninger <kwenning@redhat.com> - 1.4.2-3
- change the default for SBD_WATCHDOG_TIMEOUT to 10s
  s390(x) stays at 15s as before

  Resolves: rhbz#1922143

* Thu Jan 28 2021 Klaus Wenninger <kwenning@redhat.com> - 1.4.2-2
- update SBD_SYNC_RESOURCE_STARTUP description for
  configurable default

  Resolves: rhbz#1915874

* Thu Dec 3 2020 Klaus Wenninger <kwenning@redhat.com> - 1.4.2-1
- rebase to upstream v1.4.2
- make sbd default to do pacemakerd-api handshake
- conflict with pacemaker-libs < 2.0.5-4 to assure pacemaker
  is defaulting to pacemakerd-api handshake

  Resolves: rhbz#1903730
  Resolves: rhbz#1873135

* Thu Jul 30 2020 Klaus Wenninger <kwenning@redhat.com> - 1.4.1-7
- conflict with pacemaker-libs < 2.0.4-5 instead of requiring
  a minimum pacemaker version

  Resolves: rhbz#1861713

* Mon Jul 27 2020 Klaus Wenninger <kwenning@redhat.com> - 1.4.1-6
- match qdevice-sync_timeout against wd-timeout
- sync startup/shutdown via pacemakerd-api

  Resolves: rhbz#1703128
  Resolves: rhbz#1743726

* Wed Jun 24 2020 Klaus Wenninger <kwenning@redhat.com> - 1.4.1-5
- rebuild against pacemaker having new no_quorum_demote

  Resolves: rhbz#1850078

* Wed Jun 24 2020 Klaus Wenninger <kwenning@redhat.com> - 1.4.1-4
- handle new no_quorum_demote in pacemaker

  Resolves: rhbz#1850078

* Mon Feb 17 2020 Klaus Wenninger <kwenning@redhat.com> - 1.4.1-3
- append the man-page by a section auto-generated from
  sbd.sysconfig

  Resolves: rhbz#1803826

* Wed Nov 20 2019 Klaus Wenninger <kwenning@redhat.com> - 1.4.1-2
- silence coverity regarding inconsistent parameter passing
- adapt fence-agents-dependency from upstream to distribution

  Resolves: rhbz#1769305

* Tue Nov 19 2019 Klaus Wenninger <kwenning@redhat.com> - 1.4.1-1
- rebase to upstream v1.4.0

  Resolves: rhbz#1769305
  Resolves: rhbz#1768906

* Fri Aug 16 2019 Klaus Wenninger <kwenning@redhat.com> - 1.4.0-15
- check for shutdown attribute on every cib-diff

  Resolves: rhbz#1718296

* Wed Jun 12 2019 Klaus Wenninger <kwenning@redhat.com> - 1.4.0-10
- added missing patches to git

  Resolves: rhbz#1702727
  Resolves: rhbz#1718296

* Tue Jun 11 2019 Klaus Wenninger <kwenning@redhat.com> - 1.4.0-9
- assume graceful pacemaker exit if leftovers are unmanaged
- query corosync liveness via votequorum-api

  Resolves: rhbz#1702727
  Resolves: rhbz#1718296

* Mon Jun 3 2019 Klaus Wenninger <kwenning@redhat.com> - 1.4.0-8
- check for rt-budget > 0 and move to root-slice otherwise

  Resolves: rhbz#1713021

* Wed Apr 10 2019 Klaus Wenninger <kwenning@redhat.com> - 1.4.0-7
- add some minor fixes from upstream found by coverity

  Resolves: rhbz#1698056

* Wed Apr 10 2019 Klaus Wenninger <kwenning@redhat.com> - 1.4.0-6
- add decision-context to gating.yaml

  Resolves: rhbz#1682137

* Mon Jan 14 2019 Klaus Wenninger <kwenning@redhat.com> - 1.4.0-5
- rebase to upstream v1.4.0
- finalize cmap connection if disconnected from cluster
- make handling of cib-connection loss more robust
- add ci test files
- use generic term cluster-services in doc
- stress in doc that on-disk metadata watchdog-timeout
  takes precedence
- fail earlier on invalid servants to make gcc 9 happy

  Resolves: rhbz#1698056
  Resolves: rhbz#1682137

* Mon Dec 17 2018 Klaus Wenninger <kwenning@redhat.com> - 1.3.1-18
- make timeout-action executed by sbd configurable

  Resolves: rhbz#1660147

* Mon Dec 3 2018 Klaus Wenninger <kwenning@redhat.com> - 1.3.1-17
- use pacemaker's new pe api with constructors/destructors

  Resolves: rhbz#1650663

* Wed Sep 19 2018 Klaus Wenninger <kwenning@redhat.com> - 1.3.1-16
- avoid statting potential symlink-targets in /dev

  Resolves: rhbz#1629020

* Wed Sep 19 2018 Klaus Wenninger <kwenning@redhat.com> - 1.3.1-15
- rebuild against new versions of libqb (1.0.3-7.el8),
  corosync (2.99.3-4.el8) and pacemaker (2.0.0-9.el8)

  Related: rhbz#1615945

* Fri Sep 14 2018 Klaus Wenninger <kwenning@redhat.com> - 1.3.1-14
- skip symlinks pointing to dev-nodes outside of /dev

  Resolves: rhbz#1629020

* Wed Sep 5 2018 Klaus Wenninger <kwenning@redhat.com> - 1.3.1-13
- Require systemd-package during build to have the macros

  Resolves: rhbz#1625553

* Mon Jul 30 2018 Florian Weimer <fweimer@redhat.com> - 1.3.1-12
- Rebuild with fixed binutils

* Tue Jul 3 2018 <kwenning@redhat.com> - 1.3.1-11
- replaced tarball by version downloaded from github

* Mon Jul 2 2018 <kwenning@redhat.com> - 1.3.1-10
- removed unneeded python build-dependency
- updated legacy corosync-devel to corosynclib-devel

  Resolves: rhbz#1595856

* Fri May 4 2018 <kwenning@redhat.com> - 1.3.1-9
- use cib-api directly as get_cib_copy gone with
  pacemaker 2.0.0
- add sys/sysmacros.h to build with glibc-2.25
- enlarge string buffer to satisfy newer gcc
- no corosync 1 support with pacemaker 2.0.0
- set default to LOG_NOTICE + overhaul levels
- refactor proc-parsing
- adaptions for daemon-names changed with
  pacemaker 2.0.0 rc3
- added .do-not-sync-with-fedora
  Resolves: rhbz#1571797

* Mon Apr 16 2018 <kwenning@redhat.com> - 1.3.1-8
- Added aarch64 target

  Resolves: rhbz#1568029

* Mon Jan 15 2018 <kwenning@redhat.com> - 1.3.1-7
- reenable sbd on upgrade so that additional
  links to make pacemaker properly depend on
  sbd are created

  Resolves: rhbz#1525981

* Wed Jan 10 2018 <kwenning@redhat.com> - 1.3.1-5
- add man sections for query- & test-watchdog

  Resolves: rhbz#1462002

* Wed Dec 20 2017 <kwenning@redhat.com> - 1.3.1-3
- mention timeout caveat with SBD_DELAY_START
  in configuration template
- make systemd wait for sbd-start to finish
  before starting pacemaker or dlm

  Resolves: rhbz#1525981

* Fri Nov 3 2017 <kwenning@redhat.com> - 1.3.1-2
- rebase to upstream v1.3.1

  Resolves: rhbz#1499864
            rhbz#1468580
            rhbz#1462002

* Wed Jun 7 2017 <kwenning@redhat.com> - 1.3.0-3
- prevent creation of duplicate servants
- check 2Node flag in corosync to support
  2-node-clusters with shared disk fencing
- move disk-triggered reboot/off/crashdump
  to inquisitor to have sysrq observed by watchdog

  Resolves: rhbz#1413951

* Sun Mar 26 2017 <kwenning@redhat.com> - 1.3.0-1
- rebase to upstream v1.3.0
- remove watchdog-limitation from description
  Resolves: rhbz#1413951

* Mon Feb 27 2017 <kwenning@redhat.com> - 1.2.1-23
- if shared-storage enabled check for node-name <= 63 chars
  Resolves: rhbz#1413951

* Tue Jan 31 2017 <kwenning@redhat.com> - 1.2.1-22
- Rebuild with shared-storage enabled
- Package original manpage
- Added ppc64le target
  Resolves: rhbz#1413951

* Fri Apr 15 2016 <kwenning@redhat.com> - 1.2.1-21
- Rebuild for new pacemaker
  Resolves: rhbz#1320400

* Fri Apr 15 2016 <kwenning@redhat.com> - 1.2.1-20
- tarball updated to c511b0692784a7085df4b1ae35748fb318fa79ee
  from https://github.com/Clusterlabs/sbd
  Resolves: rhbz#1324240

* Thu Jul 23 2015 <abeekhof@redhat.com> - 1.2.1-5
- Rebuild for pacemaker

* Tue Jun 02 2015 <abeekhof@redhat.com> - 1.2.1-4
- Include the dist tag in the release string
- Rebuild for new pacemaker

* Mon Jan 12 2015 <abeekhof@redhat.com> - 1.2.1-3
- Correctly parse SBD_WATCHDOG_TIMEOUT into seconds (not milliseconds)

* Mon Oct 27 2014 <abeekhof@redhat.com> - 1.2.1-2
- Correctly enable /proc/pid validation for sbd_lock_running()

* Fri Oct 24 2014 <abeekhof@redhat.com> - 1.2.1-1
- Further improve integration with the el7 environment

* Thu Oct 16 2014 <abeekhof@redhat.com> - 1.2.1-0.5.872e82f3.git
- Disable unsupported functionality (for now)

* Wed Oct 15 2014 <abeekhof@redhat.com> - 1.2.1-0.4.872e82f3.git
- Improved integration with the el7 environment

* Tue Sep 30 2014 <abeekhof@redhat.com> - 1.2.1-0.3.8f912945.git
- Only build on archs supported by the HA Add-on

* Fri Aug 29 2014 <abeekhof@redhat.com> - 1.2.1-0.2.8f912945.git
- Remove some additional SUSE-isms

* Fri Aug 29 2014 <abeekhof@redhat.com> - 1.2.1-0.1.8f912945.git
- Prepare for package review
