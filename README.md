Autobisect
==========
[![Task Status](https://community-tc.services.mozilla.com/api/github/v1/repository/MozillaSecurity/autobisect/main/badge.svg)](https://community-tc.services.mozilla.com/api/github/v1/repository/MozillaSecurity/autobisect/main/latest)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![codecov](https://codecov.io/gh/MozillaSecurity/autobisect/branch/master/graph/badge.svg)](https://codecov.io/gh/MozillaSecurity/autobisect)

Autobisect is a python module that automates bisection of Mozilla Firefox and SpiderMonkey bugs.

Installation
------------

```bash
git clone git@github.com:MozillaSecurity/autobisect.git
cd autobisect
poetry install
```

Usage
-----
Firefox bug bisection supports the following arguments:

```
python -m autobisect firefox --help

positional arguments:
  testcase              Path to testcase

optional arguments:
  -h, --help            show this help message and exit

Launcher Arguments:
  -e EXTENSION, --extension EXTENSION
                        Install an extension. Specify the path to the xpi or
                        the directory containing the unpacked extension. To
                        install multiple extensions specify multiple times
  --launch-timeout LAUNCH_TIMEOUT
                        Number of seconds to wait before LaunchError is raised
                        (default: 300)
  --log-limit LOG_LIMIT
                        Log file size limit in MBs (default: 'no limit')
  -m MEMORY, --memory MEMORY
                        Browser process memory limit in MBs (default: 'no
                        limit')
  -p PREFS, --prefs PREFS
                        prefs.js file to use
  --soft-asserts        Detect soft assertions
  --xvfb                Use Xvfb (Linux only)

Reporter Arguments:
  --ignore IGNORE [IGNORE ...]
                        Space separated ignore list. ie: log-limit memory
                        timeout (default: nothing)

Replay Arguments:
  --any-crash           Any crash is interesting, not only crashes which match
                        the original signature.
  --idle-timeout IDLE_TIMEOUT
                        Number of seconds to wait before polling testcase for
                        idle (default: 60)
  --idle-threshold IDLE_THRESHOLD
                        CPU usage threshold to mark the process as idle
                        (default: 25)

Target:
  --target {firefox,js}
                        Specify the build target. (default: firefox)
  --os {Android,Darwin,Linux,Windows}
                        Specify the target system. (default: Linux)
  --cpu {AMD64,ARM64,aarch64,arm,arm64,i686,x64,x86,x86_64}
                        Specify the target CPU. (default: x86_64)

Build:
  --build DATE|REV|NS   Specify the build to download, (default: latest)
                        Accepts values in format YYYY-MM-DD (2017-01-01)
                        revision (57b37213d81150642f5139764e7044b07b9dccc3) or
                        TaskCluster namespace (gecko.v2....)

Branch:
  --inbound             Download from mozilla-inbound
  --central             Download from mozilla-central (default)
  --release             Download from mozilla-release
  --beta                Download from mozilla-beta
  --esr-stable          Download from esr-stable
  --esr-next            Download from esr-next
  --try                 Download from try

Build Arguments:
  -d, --debug           Get debug builds w/ symbols (default=optimized).
  -a, --asan            Download AddressSanitizer builds.
  -t, --tsan            Download ThreadSanitizer builds.
  --fuzzing             Download --enable-fuzzing builds.
  --coverage            Download --coverage builds. This also pulls down the
                        *.gcno files
  --valgrind            Download Valgrind builds.

Test Arguments:
  --tests  [ ...]       Download tests associated with this build. Acceptable
                        values are: gtest, common, reftests
  --full-symbols        Download the full crashreport-symbols.zip archive.

Misc. Arguments:
  -n NAME, --name NAME  Specify a name (default=auto)
  -o OUT, --out OUT     Specify output directory (default=.)
  --dry-run             Search for build and output metadata only, don't
                        download anything.

Near Arguments:
  If the specified build isn't found, iterate over builds in the specified
  direction

  --nearest-newer       Search from specified build in ascending order
  --nearest-older       Search from the specified build in descending order

Boundary Arguments (YYYY-MM-DD or SHA1 revision):
  --start START         Start build id (default: earliest available build)
  --end END             End build id (default: latest available build)

Bisection Arguments:
  --timeout TIMEOUT     Maximum iteration time in seconds (default: 60)
  --repeat REPEAT       Number of times to evaluate testcase (per build)
  --config CONFIG       Path to optional config file
  --find-fix            Identify fix date

```

Simple Bisection
----------------
```
python -m autobisect firefox trigger.html --prefs prefs.js --asan --end 2017-11-14
```

By default, Autobisect will cache downloaded builds (up to 30GBs) to reduce bisection time.  This behavior can be modified by supplying a custom configuration file in the following format:
```
[autobisect]
storage-path: /home/ubuntu/cached
persist: true
; size in MBs
persist-limit: 30000
```

Development
-----------
Autobisect includes a pre-commit hook for [black](https://github.com/psf/black) and [flake8](https://flake8.pycqa.org/en/latest/).  To install the pre-commit hook, run the following.  
```bash
pre-commit install
```

Furthermore, all tests should be executed via tox.
```bash
poetry run tox
```

