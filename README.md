Autobisect
==========
[![Task Status](https://community-tc.services.mozilla.com/api/github/v1/repository/MozillaSecurity/autobisect/master/badge.svg)](https://community-tc.services.mozilla.com/api/github/v1/repository/MozillaSecurity/autobisect/master/latest)
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
usage: __main__.py firefox [-h] [--log-level LOG_LEVEL] [--start START] [--end END] [--timeout TIMEOUT] [--repeat REPEAT] [--config CONFIG] [--find-fix] [--os {Android,Darwin,Linux,Windows}]
                           [--cpu {AMD64,ARM64,aarch64,arm,arm64,i686,x64,x86,x86_64}] [--central | --release | --beta | --esr-stable | --esr-next | --try | --autoland] [-d] [-a] [-t] [--fuzzing]
                           [--fuzzilli] [--coverage] [--valgrind] [--no-opt] [--launch-timeout LAUNCH_TIMEOUT] [-p PREFS] [--xvfb] [--ignore [IGNORE [IGNORE ...]]]
                           testcase

positional arguments:
  testcase              Path to testcase

optional arguments:
  -h, --help            show this help message and exit
  --log-level LOG_LEVEL
                        Configure console logging. Options: DEBUG, INFO, WARN, ERROR, CRIT (default: INFO)

Boundary Arguments:
  Accepts revision or build date in YYYY-MM-DD format)

  --start START         Start build id (default: earliest available build)
  --end END             End build id (default: latest available build)

Bisection Arguments:
  --timeout TIMEOUT     Maximum iteration time in seconds (default: 60)
  --repeat REPEAT       Number of times to evaluate testcase (per build)
  --config CONFIG       Path to optional config file
  --find-fix            Identify fix date

Target Arguments:
  --os {Android,Darwin,Linux,Windows}
                        Specify the target system. (default: Linux)
  --cpu {AMD64,ARM64,aarch64,arm,arm64,i686,x64,x86,x86_64}
                        Specify the target CPU. (default: x86_64)

Branch Arguments:
  --central             Download from mozilla-central (default)
  --release             Download from mozilla-release
  --beta                Download from mozilla-beta
  --esr-stable          Download from esr-stable
  --esr-next            Download from esr-next
  --try                 Download from try
  --autoland            Download from autoland

Build Arguments:
  -d, --debug           Get debug builds w/ symbols (default=optimized).
  -a, --asan            Download AddressSanitizer builds.
  -t, --tsan            Download ThreadSanitizer builds.
  --fuzzing             Download --enable-fuzzing builds.
  --fuzzilli            Download --enable-js-fuzzilli builds.
  --coverage            Download --coverage builds.
  --valgrind            Download Valgrind builds.
  --no-opt              Download non-optimized builds.

Launcher Arguments:
  --launch-timeout LAUNCH_TIMEOUT
                        Number of seconds to wait before LaunchError is raised (default: 300)
  -p PREFS, --prefs PREFS
                        Optional prefs.js file to use
  --xvfb                Use Xvfb (Linux only)

Reporter Arguments:
  --ignore [IGNORE [IGNORE ...]]
                        Space separated list of issue types to ignore. Valid options: log-limit memory timeout (default: log-limit memory timeout)
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

