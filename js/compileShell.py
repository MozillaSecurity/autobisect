#!/usr/bin/env python
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import ctypes
import multiprocessing
import os
import shutil
import subprocess
import sys
import traceback

from optparse import OptionParser

import buildOptions
import inspectShell

path0 = os.path.dirname(os.path.abspath(__file__))
path1 = os.path.abspath(os.path.join(path0, os.pardir, 'util'))
sys.path.append(path1)
import hgCmds
import subprocesses as sps
from LockDir import LockDir

# If one wants to bisect between 97464:e077c138cd5d to 150877:c62ad7dd57cd on Windows with
# MSVC 2010, change "mozmake" in the line below back to "make".
if sps.isWin:
    MAKE_BINARY = 'mozmake'
else:
    MAKE_BINARY = 'make'
    CLANG_PARAMS = ' -Qunused-arguments'
    CLANG_ASAN_PARAMS = ' -fsanitize=address -Dxmalloc=myxmalloc'
    SSE2_FLAGS = ' -msse2 -mfpmath=sse'  # See bug 948321
    CLANG_X86_FLAG = ' -arch i386'

if multiprocessing.cpu_count() > 2:
    COMPILATION_JOBS = ((multiprocessing.cpu_count() * 5) // 4)
elif sps.isARMv7l:
    COMPILATION_JOBS = 3  # An ARM board
else:
    COMPILATION_JOBS = 3  # Other single/dual core computers


class CompiledShell(object):
    def __init__(self, buildOpts, hgHash):
        self.shellNameWithoutExt = buildOptions.computeShellName(buildOpts, hgHash)
        self.shellNameWithExt = self.shellNameWithoutExt + ('.exe' if sps.isWin else '')
        self.hgHash = hgHash
        self.buildOptions = buildOpts

        self.jsObjdir = ''
        self.nsprObjdir = ''
    def setDestDir(self, tDir):
        self.destDir = tDir

        if os.name == 'nt':  # adapted from http://stackoverflow.com/a/3931799
            winTmpDir = unicode(self.destDir)
            GetLongPathName = ctypes.windll.kernel32.GetLongPathNameW
            unicodeBuffer = ctypes.create_unicode_buffer(GetLongPathName(winTmpDir, 0, 0))
            GetLongPathName(winTmpDir, unicodeBuffer, len(unicodeBuffer))
            self.destDir = sps.normExpUserPath(str(unicodeBuffer.value)) # convert back to a str

        assert '~' not in self.destDir
        assert os.path.isdir(self.destDir)
    def getDestDir(self):
        return self.destDir
    def setCfgCmdExclEnv(self, cfg):
        self.cfg = cfg
    def getCfgCmdExclEnv(self):
        return self.cfg
    def getJsCfgPath(self):
        self.jsCfgFile = sps.normExpUserPath(os.path.join(self.getRepoDirJsSrc(), 'configure'))
        assert os.path.isfile(self.jsCfgFile)
        return self.jsCfgFile
    def getNsprCfgPath(self):
        self.nsprCfgFile = sps.normExpUserPath(os.path.join(self.getRepoDirNsprSrc(), 'configure'))
        assert os.path.isfile(self.nsprCfgFile)
        return self.nsprCfgFile
    def setEnvAdded(self, addedEnv):
        self.addedEnv = addedEnv
    def getEnvAdded(self):
        return self.addedEnv
    def setEnvFull(self, fullEnv):
        self.fullEnv = fullEnv
    def getEnvFull(self):
        return self.fullEnv
    def getHgHash(self):
        return self.hgHash
    def getJsBuildSystemConsidersNspr(self):
        return self.jsBuildSystemConsidersNspr
    def setJsBuildSystemConsidersNspr(self):
        # This rev is when js build system compiles NSPR together when compiling threadsafe builds
        # Landed in m-c rev ID 194734 (from TBPL) and in mid-July 2014, when Fx33 was nightly.
        self.jsBuildSystemConsidersNspr = hgCmds.existsAndIsAncestor(
            self.getRepoDir(), 'a459b02a9ca472fa10299b5cb6c0456fe492c78a', '.')
    def getJsUsesNoThreadsFlag(self):
        return self.jsUsesNoThreadsFlag
    def setJsUsesNoThreadsFlag(self):
        # This rev is when --enable/disable-threadsafe was replaced by the --no-threads flag.
        # Landed in m-c rev ID 195996 (from TBPL) and in end-July 2014, when Fx34 was nightly.
        self.jsUsesNoThreadsFlag = hgCmds.existsAndIsAncestor(
            self.getRepoDir(), '35038c3324ee08b29924059da9b117940e740bd7', '.')
    def getJsObjdir(self):
        return self.jsObjdir
    def setJsObjdir(self, oDir):
        self.jsObjdir = oDir
    def getNsprObjdir(self):
        return self.nsprObjdir
    def setNsprObjdir(self, oDir):
        self.nsprObjdir = oDir
    def getRepoDir(self):
        return self.buildOptions.repoDir
    def getRepoDirJsSrc(self):
        return sps.normExpUserPath(os.path.join(self.getRepoDir(), 'js', 'src'))
    def getRepoDirNsprSrc(self):
        return sps.normExpUserPath(os.path.join(self.getRepoDir(), 'nsprpub'))
    def getRepoName(self):
        return hgCmds.getRepoNameFromHgrc(self.buildOptions.repoDir)
    def getShellCacheDir(self):
        return sps.normExpUserPath(os.path.join(ensureCacheDir(), self.shellNameWithoutExt))
    def getShellCacheFullPath(self):
        return sps.normExpUserPath(os.path.join(self.getShellCacheDir(), self.shellNameWithExt))
    def getShellCompiledPath(self):
        return sps.normExpUserPath(
            os.path.join(self.getJsObjdir(), 'dist', 'bin', 'js' + ('.exe' if sps.isWin else '')))
    def getShellCompiledRunLibsPath(self):
        lDir = self.getJsObjdir() if self.getJsBuildSystemConsidersNspr() else self.getNsprObjdir()
        libsList = [
            sps.normExpUserPath(os.path.join(lDir, 'dist', 'lib', runLib)) \
                for runLib in inspectShell.ALL_RUN_LIBS
        ]
        return libsList
    def getShellBaseTempDirWithName(self):
        return sps.normExpUserPath(os.path.join(self.getDestDir(), self.shellNameWithExt))
    def getShellNameWithExt(self):
        return self.shellNameWithExt


def ensureCacheDir():
    '''Returns a cache directory for compiled shells to live in, creating one if needed'''
    cacheDir = os.path.join(sps.normExpUserPath('~'), 'shell-cache')
    ensureDir(cacheDir)
    return cacheDir


def ensureDir(directory):
    '''Creates a directory, if it does not already exist'''
    if not os.path.exists(directory):
        os.mkdir(directory)
    assert os.path.isdir(directory)


def autoconfRun(cwDir):
    '''Run autoconf binaries corresponding to the platform.'''
    if sps.isMac:
        autoconf213MacBin = '/usr/local/Cellar/autoconf213/2.13/bin/autoconf213' \
                                if sps.isProgramInstalled('brew') else 'autoconf213'
        subprocess.check_call([autoconf213MacBin], cwd=cwDir)
    elif sps.isLinux:
        subprocess.check_call(['autoconf2.13'], cwd=cwDir)
    elif sps.isWin:
        # Windows needs to call sh to be able to find autoconf.
        subprocess.check_call(['sh', 'autoconf-2.13'], cwd=cwDir)


def cfgJsCompile(shell):
    '''Configures, compiles and copies a js shell according to required parameters.'''
    if shell.buildOptions.enableNsprBuild and not shell.getJsBuildSystemConsidersNspr():
        compileNspr(shell)
    autoconfRun(shell.getRepoDirJsSrc())
    configureTryCount = 0
    while True:
        try:
            cfgBin(shell, 'js')
            break
        except Exception as e:
            configureTryCount += 1
            if configureTryCount > 3:
                print 'Configuration of the js binary failed 3 times.'
                raise
            # This exception message is returned from sps.captureStdout via cfgBin.
            # No idea why this is sps.isLinux as well..
            if sps.isLinux or (sps.isWin and 'Windows conftest.exe configuration permission' in repr(e)):
                print 'Trying once more...'
                continue
    compileJs(shell)
    inspectShell.verifyBinary(shell)
    envDump(shell, sps.normExpUserPath(os.path.join(shell.getDestDir(), 'compilation-parameters.txt')))


def cfgBin(shell, binToBeCompiled):
    '''This function configures a binary according to required parameters.'''
    cfgCmdList = []
    cfgEnvDt = copy.deepcopy(os.environ)
    origCfgEnvDt = copy.deepcopy(os.environ)
    cfgEnvDt['AR'] = 'ar'
    if shell.buildOptions.buildWithAsan:
        llvmPath = sps.findLlvmBinPath()
        CLANG_PATH = sps.normExpUserPath(os.path.join(llvmPath, 'clang'))
        CLANGPP_PATH = sps.normExpUserPath(os.path.join(llvmPath, 'clang++'))

    if sps.isARMv7l:
        # 32-bit shell on ARM boards, e.g. odroid boards.
        # This is tested on Ubuntu 14.04 with necessary armel libraries (force)-installed.
        assert shell.buildOptions.enable32, 'arm7vl boards are only 32-bit, armv8 boards will be 64-bit.'
        if not shell.buildOptions.enableHardFp:
            cfgEnvDt['CC'] = 'gcc-4.7 -mfloat-abi=softfp -B/usr/lib/gcc/arm-linux-gnueabi/4.7'
            cfgEnvDt['CXX'] = 'g++-4.7 -mfloat-abi=softfp -B/usr/lib/gcc/arm-linux-gnueabi/4.7'
        cfgCmdList.append('sh')
        if binToBeCompiled == 'nspr':
            cfgCmdList.append(os.path.normpath(shell.getNsprCfgPath()))
        else:
            cfgCmdList.append(os.path.normpath(shell.getJsCfgPath()))
            # From mjrosenb: things might go wrong if these three lines are not present for
            # compiling ARM on a 64-bit host machine. Not needed if compiling on the board itself.
            #cfgCmdList.append('--target=arm-linux-gnueabi')
            #cfgCmdList.append('--with-arch=armv7-a')
            #cfgCmdList.append('--with-thumb')
        if not shell.buildOptions.enableHardFp:
            cfgCmdList.append('--target=arm-linux-gnueabi')
    elif shell.buildOptions.enable32 and os.name == 'posix':
        # 32-bit shell on Mac OS X 10.7 Lion and greater
        if sps.isMac:
            assert sps.macVer() >= [10, 7]  # We no longer support Snow Leopard 10.6 and prior.
            if shell.buildOptions.buildWithAsan:  # Uses custom compiled clang
                cfgEnvDt['CC'] = cfgEnvDt['HOST_CC'] = CLANG_PATH + CLANG_PARAMS + \
                    CLANG_ASAN_PARAMS + SSE2_FLAGS
                cfgEnvDt['CXX'] = cfgEnvDt['HOST_CXX'] = CLANGPP_PATH + CLANG_PARAMS + \
                    CLANG_ASAN_PARAMS + SSE2_FLAGS
            else:  # Uses system clang
                cfgEnvDt['CC'] = cfgEnvDt['HOST_CC'] = 'clang' + CLANG_PARAMS + SSE2_FLAGS
                cfgEnvDt['CXX'] = cfgEnvDt['HOST_CXX'] = 'clang++' + CLANG_PARAMS + SSE2_FLAGS
            cfgEnvDt['CC'] = cfgEnvDt['CC'] + CLANG_X86_FLAG  # only needed for CC, not HOST_CC
            cfgEnvDt['CXX'] = cfgEnvDt['CXX'] + CLANG_X86_FLAG  # only needed for CXX, not HOST_CXX
            cfgEnvDt['RANLIB'] = 'ranlib'
            cfgEnvDt['AS'] = '$CC'
            cfgEnvDt['LD'] = 'ld'
            cfgEnvDt['STRIP'] = 'strip -x -S'
            cfgEnvDt['CROSS_COMPILE'] = '1'
            if sps.isProgramInstalled('brew'):
                cfgEnvDt['AUTOCONF'] = '/usr/local/Cellar/autoconf213/2.13/bin/autoconf213'
            cfgCmdList.append('sh')
            if binToBeCompiled == 'nspr':
                cfgCmdList.append(os.path.normpath(shell.getNsprCfgPath()))
            else:
                cfgCmdList.append(os.path.normpath(shell.getJsCfgPath()))
            cfgCmdList.append('--target=i386-apple-darwin9.2.0')  # Leopard 10.5.2
            cfgCmdList.append('--enable-macos-target=10.5')
            if shell.buildOptions.buildWithAsan:
                cfgCmdList.append('--enable-address-sanitizer')
            if shell.buildOptions.enableArmSimulator:
                cfgCmdList.append('--enable-arm-simulator')
        # 32-bit shell on 32/64-bit x86 Linux
        elif sps.isLinux and not sps.isARMv7l:
            cfgEnvDt['PKG_CONFIG_LIBDIR'] = '/usr/lib/pkgconfig'
            if shell.buildOptions.buildWithAsan:  # Uses custom compiled clang
                cfgEnvDt['CC'] = cfgEnvDt['HOST_CC'] = CLANG_PATH + CLANG_PARAMS + \
                    CLANG_ASAN_PARAMS + SSE2_FLAGS + CLANG_X86_FLAG
                cfgEnvDt['CXX'] = cfgEnvDt['HOST_CXX'] = CLANGPP_PATH + CLANG_PARAMS + \
                    CLANG_ASAN_PARAMS + SSE2_FLAGS + CLANG_X86_FLAG
            else:  # Uses system clang
                # We might still be using GCC on Linux 32-bit, use clang only if we specify ASan
                # apt-get `lib32z1 gcc-multilib g++-multilib` first, if on 64-bit Linux.
                cfgEnvDt['CC'] = 'gcc -m32' + SSE2_FLAGS
                cfgEnvDt['CXX'] = 'g++ -m32' + SSE2_FLAGS
            cfgCmdList.append('sh')
            if binToBeCompiled == 'nspr':
                cfgCmdList.append(os.path.normpath(shell.getNsprCfgPath()))
            else:
                cfgCmdList.append(os.path.normpath(shell.getJsCfgPath()))
            cfgCmdList.append('--target=i686-pc-linux')
            if shell.buildOptions.buildWithAsan:
                cfgCmdList.append('--enable-address-sanitizer')
            if shell.buildOptions.enableArmSimulator:
                cfgCmdList.append('--enable-arm-simulator')
        else:
            cfgCmdList.append('sh')
            if binToBeCompiled == 'nspr':
                cfgCmdList.append(os.path.normpath(shell.getNsprCfgPath()))
            else:
                cfgCmdList.append(os.path.normpath(shell.getJsCfgPath()))
    # 64-bit shell on Mac OS X 10.7 Lion and greater
    elif sps.isMac and sps.macVer() >= [10, 7] and not shell.buildOptions.enable32:
        if shell.buildOptions.buildWithAsan:  # Uses custom compiled clang
            cfgEnvDt['CC'] = CLANG_PATH + CLANG_PARAMS + CLANG_ASAN_PARAMS
            cfgEnvDt['CXX'] = CLANGPP_PATH + CLANG_PARAMS + CLANG_ASAN_PARAMS
        else:  # Uses system clang
            cfgEnvDt['CC'] = 'clang' + CLANG_PARAMS
            cfgEnvDt['CXX'] = 'clang++' + CLANG_PARAMS
        if sps.isProgramInstalled('brew'):
            cfgEnvDt['AUTOCONF'] = '/usr/local/Cellar/autoconf213/2.13/bin/autoconf213'
        cfgCmdList.append('sh')
        if binToBeCompiled == 'nspr':
            cfgCmdList.append(os.path.normpath(shell.getNsprCfgPath()))
            cfgCmdList.append('--enable-64bit')
        else:
            cfgCmdList.append(os.path.normpath(shell.getJsCfgPath()))
        cfgCmdList.append('--target=x86_64-apple-darwin12.5.0')  # Mountain Lion 10.8.5
        if shell.buildOptions.buildWithAsan:
            cfgCmdList.append('--enable-address-sanitizer')

    elif sps.isWin:
        cfgEnvDt['MAKE'] = 'mozmake'  # Workaround for bug 948534
        cfgCmdList.append('sh')
        if binToBeCompiled == 'nspr':
            cfgCmdList.append(os.path.normpath(shell.getNsprCfgPath()))
            if shell.buildOptions.enable32:
                cfgCmdList.append('--enable-win32-target=WIN95')
            else:
                cfgCmdList.append('--enable-64bit')
        else:
            cfgCmdList.append(os.path.normpath(shell.getJsCfgPath()))
        if shell.buildOptions.enable32:
            if shell.buildOptions.enableArmSimulator:
                cfgCmdList.append('--enable-arm-simulator')
        else:
            cfgCmdList.append('--host=x86_64-pc-mingw32')
            cfgCmdList.append('--target=x86_64-pc-mingw32')
    else:
        # We might still be using GCC on Linux 64-bit, so do not use clang unless Asan is specified
        if shell.buildOptions.buildWithAsan:  # Uses custom compiled clang
            cfgEnvDt['CC'] = CLANG_PATH + CLANG_PARAMS + CLANG_ASAN_PARAMS
            cfgEnvDt['CXX'] = CLANGPP_PATH + CLANG_PARAMS + CLANG_ASAN_PARAMS
        cfgCmdList.append('sh')
        if binToBeCompiled == 'nspr':
            cfgCmdList.append(os.path.normpath(shell.getNsprCfgPath()))
            cfgCmdList.append('--enable-64bit')
        else:
            cfgCmdList.append(os.path.normpath(shell.getJsCfgPath()))
        if shell.buildOptions.buildWithAsan:
            cfgCmdList.append('--enable-address-sanitizer')

    if shell.buildOptions.buildWithAsan:
        assert 'clang' in cfgEnvDt['CC']
        assert 'clang++' in cfgEnvDt['CXX']

    # For NSPR, specify "--disable-debug --enable-optimize" to generate an opt build.
    # They can actually be used independently, but it's not recommended.
    # https://developer.mozilla.org/en-US/docs/NSPR_build_instructions#Configure_options
    if shell.buildOptions.enableDbg:
        # NSPR configure without options compiles debug by default
        if binToBeCompiled == 'js':
            cfgCmdList.append('--enable-debug')
    elif shell.buildOptions.disableDbg or binToBeCompiled == 'nspr':
        cfgCmdList.append('--disable-debug')

    if shell.buildOptions.enableOpt:
        cfgCmdList.append('--enable-optimize' + ('=-O1' if shell.buildOptions.buildWithVg else ''))
    elif binToBeCompiled == 'js' and shell.buildOptions.disableOpt:
        # NSPR configure without options compiles debug by default
        cfgCmdList.append('--disable-optimize')

    if binToBeCompiled == 'nspr':
        cfgCmdList.append('--prefix=' + \
            sps.normExpUserPath(os.path.join(shell.getNsprObjdir(), 'dist')))
    else:
        if shell.buildOptions.enableProfiling:
            cfgCmdList.append('--enable-profiling')
        if shell.getJsUsesNoThreadsFlag() and shell.buildOptions.enableNsprBuild:
                cfgCmdList.append('--enable-nspr-build')
        else:
            if shell.buildOptions.enableNsprBuild:
                cfgCmdList.append('--enable-threadsafe')
                if not shell.getJsBuildSystemConsidersNspr():
                    cfgCmdList.append('--with-nspr-prefix=' + \
                        sps.normExpUserPath(os.path.join(shell.getNsprObjdir(), 'dist')))
                    cfgCmdList.append('--with-nspr-cflags=-I' + \
                        sps.normExpUserPath(os.path.join(shell.getNsprObjdir(), 'dist', 'include',
                                                         'nspr')))
                    cfgCmdList.append('--with-nspr-libs=' + ' '.join([
                        sps.normExpUserPath(os.path.join(shell.getNsprObjdir(), 'dist', 'lib',
                                                         compileLib))\
                            for compileLib in inspectShell.ALL_COMPILE_LIBS
                        ]))
            else:
                cfgCmdList.append('--disable-threadsafe')

        if shell.buildOptions.enableMoreDeterministic:
            # Fuzzing tweaks for more useful output, implemented in bug 706433
            cfgCmdList.append('--enable-more-deterministic')
        # GGC requires exact rooting to be enabled
        if shell.buildOptions.disableGcGenerational or shell.buildOptions.disableExactRooting:
            cfgCmdList.append('--disable-gcgenerational')
            if shell.buildOptions.disableExactRooting:
                cfgCmdList.append('--disable-exact-rooting')

        if shell.buildOptions.buildWithVg:
            cfgCmdList.append('--enable-valgrind')

        # We add the following flags by default.
        if os.name == 'posix':
            cfgCmdList.append('--with-ccache')
        cfgCmdList.append('--enable-gczeal')
        cfgCmdList.append('--enable-debug-symbols')  # gets debug symbols on opt shells
        cfgCmdList.append('--disable-tests')

    if os.name == 'nt':
        # FIXME: Replace this with sps.shellify.
        counter = 0
        for entry in cfgCmdList:
            if os.sep in entry:
                assert sps.isWin  # MozillaBuild on Windows sometimes confuses "/" and "\".
                cfgCmdList[counter] = cfgCmdList[counter].replace(os.sep, '//')
            counter = counter + 1

    # Print whatever we added to the environment
    envVarList = []
    for envVar in set(cfgEnvDt.keys()) - set(origCfgEnvDt.keys()):
        strToBeAppended = envVar + '="' + cfgEnvDt[envVar] + '"' \
            if ' ' in cfgEnvDt[envVar] else envVar + '=' + cfgEnvDt[envVar]
        envVarList.append(strToBeAppended)
    sps.vdump('Command to be run is: ' + sps.shellify(envVarList) + ' ' + sps.shellify(cfgCmdList))

    wDir = shell.getNsprObjdir() if binToBeCompiled == 'nspr' else shell.getJsObjdir()
    assert os.path.isdir(wDir)

    if sps.isWin:
        changedCfgCmdList = []
        for entry in cfgCmdList:
            # See bug 986715 comment 6 as to why we need forward slashes for NSPR
            # For JS, quoted from :glandium: "the way icu subconfigure is called is what changed.
            #   but really, the whole thing likes forward slashes way better"
            # See bug 1038590 comment 9.
            if '\\' in entry:
                entry = entry.replace('\\', '/')
            changedCfgCmdList.append(entry)
        sps.captureStdout(changedCfgCmdList, ignoreStderr=True, currWorkingDir=wDir, env=cfgEnvDt)
    else:
        sps.captureStdout(cfgCmdList, ignoreStderr=True, currWorkingDir=wDir, env=cfgEnvDt)

    shell.setEnvAdded(envVarList)
    shell.setEnvFull(cfgEnvDt)
    shell.setCfgCmdExclEnv(cfgCmdList)


def compileJs(shell):
    '''This function compiles and copies a binary.'''
    try:
        cmdList = [MAKE_BINARY, '-C', shell.getJsObjdir(), '-j' + str(COMPILATION_JOBS), '-s']
        out = sps.captureStdout(cmdList, combineStderr=True, ignoreExitCode=True,
                            currWorkingDir=shell.getJsObjdir(), env=shell.getEnvFull())[0]
    except Exception as e:
        # This exception message is returned from sps.captureStdout via cmdList.
        if (sps.isLinux or sps.isMac) and \
            ('GCC running out of memory' in repr(e) or 'Clang running out of memory' in repr(e)):
            # FIXME: Absolute hack to retry after hitting OOM.
            print 'Trying once more due to the compiler running out of memory...'
            out = sps.captureStdout(cmdList, combineStderr=True, ignoreExitCode=True,
                                currWorkingDir=shell.getJsObjdir(), env=shell.getEnvFull())[0]
        # A non-zero error can be returned during make, but eventually a shell still gets compiled.
        if os.path.exists(shell.getShellCompiledPath()):
            print 'A shell was compiled even though there was a non-zero exit code. Continuing...'
        else:
            print MAKE_BINARY + " did not result in a js shell:"
            raise

    if os.path.exists(shell.getShellCompiledPath()):
        shutil.copy2(shell.getShellCompiledPath(), shell.getShellBaseTempDirWithName())
        for runLib in shell.getShellCompiledRunLibsPath():
            if os.path.isfile(runLib):
                shutil.copy2(runLib, shell.getDestDir())
    else:
        print out
        raise Exception(MAKE_BINARY + " did not result in a js shell, no exception thrown.")


def compileNspr(shell):
    '''Compile a NSPR binary.'''
    cfgBin(shell, 'nspr')
    # Continue to use -j1 because NSPR does not yet seem to support parallel compilation very well.
    # Even if we move to parallel compile NSPR in the future, we must beware of breaking old
    # build during bisection. Maybe find the changeset that fixes this, and if before that, use -j1,
    # and after that, use -jX ?
    nsprCmdList = [MAKE_BINARY, '-C', shell.getNsprObjdir(), '-j1', '-s']
    out = sps.captureStdout(nsprCmdList, combineStderr=True, ignoreExitCode=True,
                        currWorkingDir=shell.getNsprObjdir(), env=shell.getEnvFull())[0]
    for compileLib in inspectShell.ALL_COMPILE_LIBS:
        if not sps.normExpUserPath(os.path.join(shell.getNsprObjdir(), 'dist', 'lib', compileLib)):
            print out
            raise Exception(MAKE_BINARY + " did not result in a NSPR binary.")

    assert os.path.isdir(sps.normExpUserPath(
        os.path.join(shell.getNsprObjdir(), 'dist', 'include', 'nspr')))


def compileStandalone(shell, updateToRev=None, isTboxBins=False):
    '''Compile a standalone shell. Keep the objdir for now, especially .a files, for symbols.'''
    compileStandaloneCreatedCacheDir = False
    if not os.path.exists(shell.getShellCacheDir()):
        try:
            os.mkdir(shell.getShellCacheDir())
        except OSError:
            raise Exception('Unable to create shell cache directory.')
        compileStandaloneCreatedCacheDir = True
    shell.setDestDir(shell.getShellCacheDir())

    cachedNoShell = shell.getShellCacheFullPath() + ".busted"

    if os.path.exists(shell.getShellCacheFullPath()):
        # Don't remove the comma at the end of this line, and thus remove the newline printed.
        # We would break JSBugMon.
        print 'Found cached shell...'
        # Assuming that since the binary is present, everything else (e.g. symbols) is also present
        return
    elif os.path.exists(cachedNoShell):
        raise Exception("Found a cached shell that failed compilation...")
    elif not compileStandaloneCreatedCacheDir and os.path.exists(shell.getShellCacheDir()):
        print 'Found a cache dir without a successful/failed shell, so recompiling...'
        sps.rmTreeIncludingReadOnly(shell.getShellCacheDir())

    assert os.path.isdir(getLockDirPath(shell.buildOptions.repoDir))

    if updateToRev:
        # We should not print here without a trailing newline to avoid breaking other stuff:
        print "Updating..."
        sps.captureStdout(["hg", "-R", shell.buildOptions.repoDir] + \
            ['update', '-C', '-r', updateToRev], ignoreStderr=True)
        # We should not print here without a trailing newline to avoid breaking other stuff:
        print "Compiling..."
    hgCmds.destroyPyc(shell.buildOptions.repoDir)
    shell.setJsBuildSystemConsidersNspr()
    shell.setJsUsesNoThreadsFlag()

    try:
        if shell.buildOptions.patchFile:
            hgCmds.patchHgRepoUsingMq(shell.buildOptions.patchFile, shell.getRepoDir())

        if not os.path.exists(shell.getShellCacheDir()):
            try:
                os.mkdir(shell.getShellCacheDir())
            except OSError:
                raise Exception('Unable to create shell cache directory.')
        shell.setDestDir(shell.getShellCacheDir())

        if shell.buildOptions.enableNsprBuild and not shell.getJsBuildSystemConsidersNspr():
            try:
                os.mkdir(sps.normExpUserPath(os.path.join(shell.getShellCacheDir(), 'objdir-nspr')))
            except OSError:
                raise Exception('Unable to create nspr objdir directory.')
            shell.setNsprObjdir(sps.normExpUserPath(os.path.join(shell.getShellCacheDir(),
                                                             'objdir-nspr')))

        try:
            os.mkdir(sps.normExpUserPath(os.path.join(shell.getShellCacheDir(), 'objdir-js')))
        except OSError:
            raise Exception('Unable to create js objdir directory.')
        shell.setJsObjdir(sps.normExpUserPath(os.path.join(shell.getShellCacheDir(), 'objdir-js')))
        cfgJsCompile(shell)

    except KeyboardInterrupt:
        sps.rmTreeIncludingReadOnly(shell.getShellCacheDir())
        raise
    except Exception as e:
        sps.rmTreeIncludingReadOnly(shell.getShellCacheDir())

        # Remove the cache dir, but recreate it with only the .busted file.
        try:
            os.mkdir(shell.getShellCacheDir())
        except OSError:
            raise Exception('Unable to create shell cache directory.')

        with open(cachedNoShell, 'wb') as f:
            f.write("Caught exception %s (%s)\n" % (repr(e), str(e)))
            f.write("Backtrace:\n")
            f.write(traceback.format_exc() + "\n")
        if os.path.exists(shell.getShellCacheFullPath()):
            print 'Stop autoBisect - a .busted file should not be generated ' + \
                            'with a shell that has been compiled successfully.'
        print 'Compilation failed (' + str(e) + ') (details in ' + cachedNoShell + ')'
        raise
    finally:
        if shell.buildOptions.patchFile:
            hgCmds.hgQpopQrmAppliedPatch(shell.buildOptions.patchFile, shell.getRepoDir())


def envDump(shell, log):
    '''Dumps environment to file.'''
    with open(log, 'ab') as f:
        f.write('Information about shell:\n\n')

        f.write('Create another shell in shell-cache like this one:\n')
        f.write(sps.shellify(["python", "-u", os.path.join(path0, "compileShell.py"),
            "-b", shell.buildOptions.buildOptionsStr]) + "\n\n")

        f.write('Full environment is: ' + str(shell.getEnvFull()) + '\n')
        f.write('Environment variables added are:\n')
        f.write(sps.shellify(shell.getEnvAdded()) + '\n\n')

        f.write('Configuration command was:\n')
        f.write(sps.shellify(shell.getCfgCmdExclEnv()) + '\n\n')

        f.write('Full configuration command with needed environment variables is:\n')
        f.write(sps.shellify(shell.getEnvAdded()) + ' ' + sps.shellify(shell.getCfgCmdExclEnv()) + '\n\n')


def getLockDirPath(repoDir, tboxIdentifier=''):
    '''Returns the name of the lock directory, located in the cache directory by default.'''
    lockDirNameList = ['shell', os.path.basename(repoDir), 'lock']
    if tboxIdentifier:
        lockDirNameList.append(tboxIdentifier)
    return os.path.join(ensureCacheDir(), '-'.join(lockDirNameList))


def makeTestRev(options):
    def testRev(rev):
        shell = CompiledShell(options.buildOptions, rev)
        print "Rev " + rev + ":",

        try:
            compileStandalone(shell, updateToRev=rev, isTboxBins=options.useTinderboxBinaries)
        except Exception:
            return (options.compilationFailedLabel, 'compilation failed')

        print "Testing...",
        return options.testAndLabel(shell.getShellCacheFullPath(), rev)
    return testRev


def main():
    """Build a shell and place it in the autoBisect cache."""

    usage = 'Usage: %prog [options]'
    parser = OptionParser(usage)
    parser.disable_interspersed_args()

    parser.set_defaults(
        buildOptions = "",
    )

    # Specify how the shell will be built.
    # See buildOptions.py for details.
    parser.add_option('-b', '--build',
                      dest='buildOptions',
                      help='Specify build options, e.g. -b "--disable-debug --enable-optimize" ' + \
                           '(python buildOptions.py --help)')

    parser.add_option('-r', '--rev',
                      dest='revision',
                      help='Specify revision to build')

    (options, args) = parser.parse_args()
    options.buildOptions = buildOptions.parseShellOptions(options.buildOptions)

    with LockDir(getLockDirPath(options.buildOptions.repoDir)):
        if options.revision:
            shell = CompiledShell(options.buildOptions, options.revision)
        else:
            localOrigHgHash, localOrigHgNum, isOnDefault = \
                hgCmds.getRepoHashAndId(options.buildOptions.repoDir)
            shell = CompiledShell(options.buildOptions, localOrigHgHash)

        compileStandalone(shell, updateToRev=options.revision)
        print shell.getShellCacheFullPath()

if __name__ == '__main__':
    main()
