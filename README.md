Autobisect
==========
[![Build Status](https://travis-ci.org/MozillaSecurity/autobisect.svg?branch=master)](https://travis-ci.org/MozillaSecurity/autobisect)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

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
  --inbound             Download from mozilla-inbound
  --central             Download from mozilla-central (default)
  --release             Download from mozilla-release
  --beta                Download from mozilla-beta
  --esr-stable          Download from esr-stable
  --esr-next            Download from esr-next

boundary arguments (YYYY-MM-DD or SHA1 revision):
  --start START         Start revision (default: earliest available TC build)
  --end END             End revision (default: latest available TC build)

bisection arguments:
  --timeout TIMEOUT     Maximum iteration time in seconds (default: 60)
  --repeat REPEAT       Number of times to evaluate testcase (per build)
  --config CONFIG       Path to optional config file
  --find-fix            Identify fix date

build arguments:
  --asan                Test ASAN builds
  --tsan                Test TSAN builds
  --debug               Test debug builds
  --fuzzing             Test --enable-fuzzing builds
  --coverage            Test --coverage builds
  --valgrind            Download Valgrind builds.
  --32                  Test 32 bit version of browser on 64 bit system.

launcher arguments:
  --asserts             Detect soft assertions
  --detect {crash,memory,log,timeout}
                        Type of failure to detect (default: crash)
  --launch-timeout LAUNCH_TIMEOUT
                        Maximum launch time in seconds (default: 300)
  --ext EXT             Path to fuzzPriv extension
  --prefs PREFS         Path to preference file
  --memory MEMORY       Process memory limit in MBs (default: no limit)
  --log-limit LOG_LIMIT
                        Log file size limit in MBs (default: no limit)
  --gdb                 Use GDB
  --xvfb                Use xvfb (Linux only)
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

Furthermore, all tests should be executed via tox
```bash
poetry run tox
```

