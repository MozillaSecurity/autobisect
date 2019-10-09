[![Build Status](https://travis-ci.org/MozillaSecurity/autobisect.svg?branch=master)](https://travis-ci.org/MozillaSecurity/autobisect)

Autobisect
==========
Autobisect is a python module that automates bisection of Mozilla Firefox and SpiderMonkey bugs.

Installation
------------

##### To install after cloning the repository

    pip install --user -e <autobisect_repo>

Usage
-----

Firefox bug biesction supports the following arguments:

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
  --esr                 Download from mozilla-esr

boundary arguments (YYYY-MM-DD or SHA1 revision:
  --start START         Start revision (default: earliest available TC build)
  --end END             End revision (default: latest available TC build)

bisection arguments:
  --count COUNT         Number of times to evaluate testcase (per build)
  --find-fix            Indentify fix date
  --verify              Verify boundaries
  --config CONFIG       Path to optional config file

build arguments:
  --asan                Test asan builds
  --debug               Test debug builds
  --fuzzing             Test --enable-fuzzing builds
  --coverage            Test --coverage builds
  --32                  Test 32 bit version of browser on 64 bit system.

launcher arguments:
  --timeout TIMEOUT     Maximum iteration time in seconds (default: 60)
  --launch-timeout LAUNCH_TIMEOUT
                        Maximum launch time in seconds (default: 300)
  --abort-token ABORT_TOKEN
                        Scan the log for the given value and close browser on
                        detection. For example '-a ###!!! ASSERTION:' would be
                        used to detect soft assertions.
  --ext EXT             Path to fuzzPriv extension
  --prefs PREFS         Path to preference file
  --profile PROFILE     Path to profile directory
  --memory MEMORY       Process memory limit in MBs
  --gdb                 Use GDB
  --valgrind            Use valgrind
  --xvfb                Use xvfb (Linux only)
```

Bisecting a Firefox bug:
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
