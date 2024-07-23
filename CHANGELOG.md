# Changelog

<!--next-version-placeholder-->

## v7.7.0 (2024-07-23)

### Feature

* Replace deprecated pytest-freezegun with pytest-freezer ([`b0c57f9`](https://github.com/MozillaSecurity/autobisect/commit/b0c57f94116e12765998d70321a1a63fe0b67806))
* Update grizzly-framework and lithium deps ([`8689ce7`](https://github.com/MozillaSecurity/autobisect/commit/8689ce7bdde6e3eb3e2b13c45bd875475c3d40d8))
* Update lithium-reducer and platformdirs ([`75f313c`](https://github.com/MozillaSecurity/autobisect/commit/75f313c5ecfbe329593b100b910ffd6633e09b8f))
* Update grizzly to 0.18.0 ([`948a921`](https://github.com/MozillaSecurity/autobisect/commit/948a921bebd8ba98385d1ca06e426897dede7266))
* Update fuzzfetch to 7.0.0 ([`520b503`](https://github.com/MozillaSecurity/autobisect/commit/520b50338a0922078e1ecac1441482d7c538ba9c))

### Fix

* Replace deprecated grizzly logs arg with output ([`d322603`](https://github.com/MozillaSecurity/autobisect/commit/d322603c28651911f859baaf4a52eef57c86bc99))
* Allow setting launch attempts ([`63aeed6`](https://github.com/MozillaSecurity/autobisect/commit/63aeed6a190b953ac0edcbff7a5449077491f04f))
* Remove unnecessary exception handling around extract_build ([`99c6c65`](https://github.com/MozillaSecurity/autobisect/commit/99c6c65fba75203d43b9b71e8e4f0c5c83dbf04f))

### Documentation

* Unify docstring format ([`89cabf3`](https://github.com/MozillaSecurity/autobisect/commit/89cabf36e0c429458363ad95cfa65a7d12c542b1))

## v7.6.0 (2024-05-30)

### Feature

* Set default grizzly logging level to info ([`a1703b0`](https://github.com/MozillaSecurity/autobisect/commit/a1703b0a2d4dbfa58b51360ee5837dc998e6fa05))
* Set relaunch to 1 by default ([`1b0143c`](https://github.com/MozillaSecurity/autobisect/commit/1b0143c76cde6e739a88ed566109beeecc5d01e8))

### Fix

* Disable headless mode by default ([`6ea6b88`](https://github.com/MozillaSecurity/autobisect/commit/6ea6b887dd15b2fa70b2f4f7eeaf4a8e427ea6ae))
* Use module name as logger name ([`e9a1240`](https://github.com/MozillaSecurity/autobisect/commit/e9a12402919aec29563b09e01bd9063a6f1e0452))

### Documentation

* Normalize reST docstrings ([`7e46cb4`](https://github.com/MozillaSecurity/autobisect/commit/7e46cb4df0b472697b8a88a63fa6793b762f31b6))

## v7.5.0 (2024-01-02)

### Feature

* Update lithium to 1.1.1 ([`a715044`](https://github.com/MozillaSecurity/autobisect/commit/a715044d157a0e8fcb8d1918eaf0e285f13b9efe))

### Fix

* Js builds are limited to 90 days ([`5844aaf`](https://github.com/MozillaSecurity/autobisect/commit/5844aaf6b1e58da2ac291e93ed227155f4443ad0))
* Add file extension to binary for windows builds ([`826e0da`](https://github.com/MozillaSecurity/autobisect/commit/826e0dab8ff8d37a313798c23ee6bfb46dfe3d0f))

## v7.4.3 (2023-12-08)

### Fix

* Add correct binary extension based on platform ([`651168d`](https://github.com/MozillaSecurity/autobisect/commit/651168da145ac9d26a9f24718595e5539ff9f528))
* Close test file so that windows can access it ([`9e1f0bd`](https://github.com/MozillaSecurity/autobisect/commit/9e1f0bd07e4a86faf8a250617c506b659d60d31e))

## v7.4.2 (2023-12-05)

### Fix

* Update fuzzfetch ([`7127301`](https://github.com/MozillaSecurity/autobisect/commit/71273013be2f354941f1afb8b691de83de9d04d1))

## v7.4.1 (2023-11-28)

### Fix

* Lock grizzly to 0.17.0 ([`e2b1a41`](https://github.com/MozillaSecurity/autobisect/commit/e2b1a4166657cff39189901817093e2579f787d3))

## v7.4.0 (2023-10-16)

### Feature

* Update prefpicker to 1.15.0 ([`ace16fe`](https://github.com/MozillaSecurity/autobisect/commit/ace16fe84a7cc6f2c0f7e01189e69b69e0fdc396))
* Update grizzly-framework to 0.17.0 ([`f25b1c2`](https://github.com/MozillaSecurity/autobisect/commit/f25b1c29b5d7dc9bf1c46968446850ea53661e4a))

### Documentation

* Add MPL ([`7f55fdf`](https://github.com/MozillaSecurity/autobisect/commit/7f55fdf52959a0664816562c5e5b4574fb8ea366))

## v7.3.0 (2023-10-05)

### Feature

* Update prefpicker ([`4b16def`](https://github.com/MozillaSecurity/autobisect/commit/4b16deffc1632ed35520c011367bd971db44e05e))

## v7.2.1 (2023-10-04)

### Fix

* Update fuzzfetch to 2.4.2 ([`d677d92`](https://github.com/MozillaSecurity/autobisect/commit/d677d9260cda1881218ff4e46d6e673dc365ad9f))

### Documentation

* Add missing mpl license header ([`b7bece5`](https://github.com/MozillaSecurity/autobisect/commit/b7bece5215f6a9a9d8d6343287fe529b6bb728d5))
* Minor formatting change to docstring ([`e0975ab`](https://github.com/MozillaSecurity/autobisect/commit/e0975ab7f84d964a485acdabc691e2d29642a9e2))
* Minor docstring format change ([`f99b418`](https://github.com/MozillaSecurity/autobisect/commit/f99b4180599fae0f74d176053f50171ed266a975))
* Add mpl header where missing ([`8320e2f`](https://github.com/MozillaSecurity/autobisect/commit/8320e2f94c3c76ec8e3ca33ed8315090dc1dfb68))

## v7.2.0 (2023-09-13)

### Feature

* Add support for platform dependent browser features ([`767e7e2`](https://github.com/MozillaSecurity/autobisect/commit/767e7e27980a334e056b009419f7854e44a8aa8a))

### Fix

* Remove duplicate valgrind args ([`daa2c8d`](https://github.com/MozillaSecurity/autobisect/commit/daa2c8d7dd5149416c4acc5f24b64f34105efe62))

## v7.1.0 (2023-09-07)

### Feature

* Use platformdirs for configuration and downloaded builds ([`d82ebfc`](https://github.com/MozillaSecurity/autobisect/commit/d82ebfca0d2844732c90ee88e991e1d44ebe8b52))

### Fix

* Use user_cache_dir instead of user_data_dir ([`3c271ba`](https://github.com/MozillaSecurity/autobisect/commit/3c271baadadfa9fd84fd5e0a21f5f02473ec6cb3))
* Update black in an attempt to fix ci intermittent failure ([`eeceded`](https://github.com/MozillaSecurity/autobisect/commit/eecededfe62a34abaec561ad43cbf68a9a46a2a7))

## v7.0.5 (2023-09-06)

### Fix

* Update black in an attempt to fix ci intermittent failure ([`f96c15e`](https://github.com/MozillaSecurity/autobisect/commit/f96c15ef78e64f1e068fa8879949f66a877fa628))
* Add required pylint fixes ([`d2d1f3e`](https://github.com/MozillaSecurity/autobisect/commit/d2d1f3e63b69a92725674636aa568c5428428ef4))

## v7.0.4 (2023-08-16)

### Fix

* Return empty string if LD_LIBRARY_PATH doesn't exist ([`2b4b294`](https://github.com/MozillaSecurity/autobisect/commit/2b4b294c9bc7c723c373bc934e6168c62d43b25c))

## v7.0.3 (2023-08-15)

### Fix

* Set LD_LIBRARY_PATH to build dir for js shell ([`19773df`](https://github.com/MozillaSecurity/autobisect/commit/19773df96056ea14dd316e1312d94724d40cda6b))

## v7.0.2 (2023-06-08)

### Fix

* Fuzzfetch update includes fix for recent taskcluster build changes ([`329af45`](https://github.com/MozillaSecurity/autobisect/commit/329af45747ddf02c0db934e3a6f8c925357f7a6f))

## v7.0.1 (2023-05-03)
### Fix
* Set minimum prefpicker version to 1.10.0 ([`7c7c895`](https://github.com/MozillaSecurity/autobisect/commit/7c7c895ca26fcd505135e07f318c888a5606e92c))

## v7.0.0 (2023-04-25)
### Feature
* Update grizzly-framework to 0.16.5 ([`4d9a39c`](https://github.com/MozillaSecurity/autobisect/commit/4d9a39cf0aee31493c7d61fba7c8d05c59c5d834))

### Fix
* Newer versions of tox use allowlist_externals ([`8ede068`](https://github.com/MozillaSecurity/autobisect/commit/8ede068630b7a4cd3c954f6d17a7aeae36b33c32))

### Breaking
* drops support for python 3.7 ([`d43020c`](https://github.com/MozillaSecurity/autobisect/commit/d43020cf551ed77e45cd7a274e38b465976f42dc))

## v6.1.1 (2022-12-21)
### Fix
* Raise if supplied binary doesn't exist ([`661fc2e`](https://github.com/MozillaSecurity/autobisect/commit/661fc2e68e8088fade38225b632c8c2b2130a6c1))
* Update grizzly-framework ([`6a5e55d`](https://github.com/MozillaSecurity/autobisect/commit/6a5e55d5cc441bbe314c8cb7384ad8d1b30ed257))

## v6.1.0 (2022-10-27)
### Feature
* Add support for grizzly --time-limit ([`9487282`](https://github.com/MozillaSecurity/autobisect/commit/94872824a09c9ed907c28d6f5ce8adf8ec3b5049))

## v6.0.2 (2022-10-20)
### Fix
* Don't treat launch failures as crashes ([`a5911ab`](https://github.com/MozillaSecurity/autobisect/commit/a5911ab9970f5e6c1b5899937dd4cff39e729b9f))

## v6.0.1 (2022-10-20)
### Fix
* Launch method no longer accepts a repeat argument ([`8fc21e0`](https://github.com/MozillaSecurity/autobisect/commit/8fc21e0f9fdd6a472f16cb601b75dd7606886c1b))

## v6.0.0 (2022-09-29)
### Feature
* Add support for passing --pernosco to grizzly ([`6e2be3c`](https://github.com/MozillaSecurity/autobisect/commit/6e2be3c2d6e4693d06b58c1b2588d77374f99f32))

### Breaking
* Modifies the BrowserEvaluator.launch method parameters.  ([`6e2be3c`](https://github.com/MozillaSecurity/autobisect/commit/6e2be3c2d6e4693d06b58c1b2588d77374f99f32))

## v5.0.4 (2022-09-27)
### Fix
* Only explicitly set ignore if options were provided ([`c1b49b9`](https://github.com/MozillaSecurity/autobisect/commit/c1b49b9a7b84055f1dc5525defd46dee59d1dae4))
* Always set relaunch to 1 ([`f9c17fe`](https://github.com/MozillaSecurity/autobisect/commit/f9c17fe96441568e4e058c1c23aa558edd40baaf))

## v5.0.3 (2022-09-27)
### Fix
* Ignore warnings when trying to close an inactive db ([`83530b2`](https://github.com/MozillaSecurity/autobisect/commit/83530b26c67a2dcb7a2f731bbf657e11bea52a25))
* Update poetry dev dependencies to use new toml key ([`f9be7d8`](https://github.com/MozillaSecurity/autobisect/commit/f9be7d8b883ad92b75b5e479bf52ea9eccd52663))

## v5.0.2 (2022-06-01)
### Fix
* Simpify success check ([`518cba3`](https://github.com/MozillaSecurity/autobisect/commit/518cba3c2451f1307e4919d3d91cba85f7fcd0e9))
* Update fuzzfetch ([`ec3861f`](https://github.com/MozillaSecurity/autobisect/commit/ec3861f4809e47f49939f6090bfb80b7d3ad7191))

## v5.0.1 (2022-04-26)
### Fix
* Update ffpuppet to v0.9.0 ([`322046c`](https://github.com/MozillaSecurity/autobisect/commit/322046ce7e58acdf4d48b31c532622d27fa74cdb))

## v5.0.0 (2022-04-04)
### Breaking
* Sets minimum version to 3.7  ([`3a3092e`](https://github.com/MozillaSecurity/autobisect/commit/3a3092eaa4ebdb4af2647f5253020c6610419c53))

## v4.0.0 (2022-04-04)
### Feature
* Add --no-harness argument to disable harness ([`20a6aba`](https://github.com/MozillaSecurity/autobisect/commit/20a6aba7f9dd4933a0c1b8e1aab7d6c0ce08c232))
* Explicitly link evaluators to a fuzzfetch target ([`c341e33`](https://github.com/MozillaSecurity/autobisect/commit/c341e334eaa4d0303e431a36a345e4ea58f1143f))
* Enable mypy type checking ([#44](https://github.com/MozillaSecurity/autobisect/issues/44)) ([`bb3ed92`](https://github.com/MozillaSecurity/autobisect/commit/bb3ed92d54ae46467a6e7285b9358f9143a47c92))
* Add type annotations throughout ([`23b5d9a`](https://github.com/MozillaSecurity/autobisect/commit/23b5d9a3ac3ff7b15dfacbfdcfed8f174e649772))
* Update fuzzfetch, grizzly-framework and lithium-reducer ([#41](https://github.com/MozillaSecurity/autobisect/issues/41)) ([`6170fee`](https://github.com/MozillaSecurity/autobisect/commit/6170fee77fc5dd64851c6c22d1b75e60e94e18e8))

### Fix
* Ensure task.url exists and is a string before checking substring ([`5e36adb`](https://github.com/MozillaSecurity/autobisect/commit/5e36adb368040f36d28330cc669b85d6e9e2446d))
* Only include autoland strategy when bisecting on central ([`1b755b4`](https://github.com/MozillaSecurity/autobisect/commit/1b755b47ee06863301c47027c20877611b321e80))
* Filter out pushdates that match the start/end revs ([`017aef4`](https://github.com/MozillaSecurity/autobisect/commit/017aef4473908b9e5a3dfeee5194e0a64a771218))
* Ignore latest pushdate aliases ([`25c87b5`](https://github.com/MozillaSecurity/autobisect/commit/25c87b578b880d92b48a3b7c1c50d01929e9b6f5))
* Don't use mozilla-unified when mismatch between autoland and central ([`6859755`](https://github.com/MozillaSecurity/autobisect/commit/685975553f320cd19e9ecb2f5d6bbb3f86f2fde3))
* Return build failure status if build_manager raises ([`c73032d`](https://github.com/MozillaSecurity/autobisect/commit/c73032dbb9668d3702b309a87c976bb848f92f6f))
* Catch and raise when build fails to extract ([`9a5eed7`](https://github.com/MozillaSecurity/autobisect/commit/9a5eed7ef89ea2e0845e0034c2873ab7bc1bb372))
* Remove explicit type cast for branch ([`6660448`](https://github.com/MozillaSecurity/autobisect/commit/66604480b20cb1299652f2c68fb49361a3652bce))
* Update type to allow None for start and end values ([`0028e88`](https://github.com/MozillaSecurity/autobisect/commit/0028e884347c43ee959a6d8f9b2fb5a9eb7c97cb))
* Update lithium ([`4d04887`](https://github.com/MozillaSecurity/autobisect/commit/4d04887b199a941f596bf4853b8cb15ad737f620))
* Autoland ranges may include multiple pushes ([`00821ea`](https://github.com/MozillaSecurity/autobisect/commit/00821ea7de71342cea96235128c99a25585164de))
* Add correct Testcase.load_single parameters ([`47b202e`](https://github.com/MozillaSecurity/autobisect/commit/47b202ef0aff037f1715b535e571f55456a03a86))
* Ignore pylint unsubscriptable-object false positive ([`c4cd456`](https://github.com/MozillaSecurity/autobisect/commit/c4cd456ce1035bcafadb191a70d3b27c4a413302))
* Update grizzly to v0.14.0 ([`2264a4d`](https://github.com/MozillaSecurity/autobisect/commit/2264a4d436b31660472c0bec75546ae7d5fb1a1d))
* Address lithium mypy type violations ([`6dd9ef8`](https://github.com/MozillaSecurity/autobisect/commit/6dd9ef8ce06e5f82534b5f238cb5d013793ef9c8))
* Use correct dep name for requests-mock ([`e0481a5`](https://github.com/MozillaSecurity/autobisect/commit/e0481a5621b84a3960d5ee46fcb49cf3821981f5))
* Use corrected types in fuzzfetch==^2.0.0 ([`0fe7f63`](https://github.com/MozillaSecurity/autobisect/commit/0fe7f638e63f072870ec72292ede89d19e925462))
* Update args to timed_run ([`d8ef7a2`](https://github.com/MozillaSecurity/autobisect/commit/d8ef7a2d560a05384054158bcbf605b94678a006))
* Ignore js runs that report unhandleable oom ([`22bed58`](https://github.com/MozillaSecurity/autobisect/commit/22bed58b065340f16473cf052bcac68d9f6bb4cb))
* Manually bump project version ([`3bcb59b`](https://github.com/MozillaSecurity/autobisect/commit/3bcb59b375d703b0f34b7b80cd05c36a653e92cd))
* Correct the broken query used to detect in_use builds ([`2324e6f`](https://github.com/MozillaSecurity/autobisect/commit/2324e6fcb698f2aca0e0ed8217a87effbc461d31))
* Sort builds by st_atime_ns for increased precision ([`cf4ea25`](https://github.com/MozillaSecurity/autobisect/commit/cf4ea255175634f1b4b418a404fd71dedd2faa91))
* Set build_path column type to TEXT ([`060d26b`](https://github.com/MozillaSecurity/autobisect/commit/060d26b473ef8ccaa5c0effa1115d27cb27052ed))
* Properly check enum value when generating message ([`c8b157d`](https://github.com/MozillaSecurity/autobisect/commit/c8b157d52b17dcf9fcaa09e9aee0abe2d43f7863))
* Set JSEvaluator target to 'js' ([`a870af3`](https://github.com/MozillaSecurity/autobisect/commit/a870af34d6ded412fa89838ce083d03cf49bfb26))
* Apply black formatting: ([`5339e24`](https://github.com/MozillaSecurity/autobisect/commit/5339e24a4faeb48e38da4819c4fa2c43361e45fa))
* Convert path args to str before passing to lithium ([`ca8ec8a`](https://github.com/MozillaSecurity/autobisect/commit/ca8ec8a5545be0ba4b5d89997d10c8b6e55f73af))
* Correct type hint issues ([`a0026a8`](https://github.com/MozillaSecurity/autobisect/commit/a0026a8545d7d0d65b469610845f388d2d907b05))
* Additional fixes required by fuzzfetch update ([`3fd730a`](https://github.com/MozillaSecurity/autobisect/commit/3fd730add36abcaaacc5cdf5d79a9d778121530f))
* Update grizzly-framework to 1.13.2 ([`bcdcf15`](https://github.com/MozillaSecurity/autobisect/commit/bcdcf1563301e3716bf165556b6ae3b6aa0c8461))
* **ci:** Multi-command requires bash to be called first ([`acf9e5f`](https://github.com/MozillaSecurity/autobisect/commit/acf9e5fc57b1d2b497d465583c7df085240b6bf7))
* **ci:** Add deploy key to scope ([`069e6f1`](https://github.com/MozillaSecurity/autobisect/commit/069e6f1f42f21253227fd854da9ae7d55b5fc1e3))
* **ci:** Ensure master exists before running release ([`68778c2`](https://github.com/MozillaSecurity/autobisect/commit/68778c2595823c58eda7d2770c221830ce98eb3d))
* **docs:** Update usage info ([`12f6fa0`](https://github.com/MozillaSecurity/autobisect/commit/12f6fa07c0d375459000149608ea347c11392c62))

### Breaking
* Modifies the bisector constructor args  ([`c341e33`](https://github.com/MozillaSecurity/autobisect/commit/c341e334eaa4d0303e431a36a345e4ea58f1143f))
* Adds target arg to BuildManager init  ([`3fd730a`](https://github.com/MozillaSecurity/autobisect/commit/3fd730add36abcaaacc5cdf5d79a9d778121530f))

### Documentation
* Remove entries caused by semantic-release error ([`0412bf5`](https://github.com/MozillaSecurity/autobisect/commit/0412bf5a723034039ec2416f3d602381fc6901fe))

## v3.1.10 (2022-04-04)
### Fix
* Ensure task.url exists and is a string before checking substring ([`5e36adb`](https://github.com/MozillaSecurity/autobisect/commit/5e36adb368040f36d28330cc669b85d6e9e2446d))
* Only include autoland strategy when bisecting on central ([`1b755b4`](https://github.com/MozillaSecurity/autobisect/commit/1b755b47ee06863301c47027c20877611b321e80))
* Filter out pushdates that match the start/end revs ([`017aef4`](https://github.com/MozillaSecurity/autobisect/commit/017aef4473908b9e5a3dfeee5194e0a64a771218))
* Ignore latest pushdate aliases ([`25c87b5`](https://github.com/MozillaSecurity/autobisect/commit/25c87b578b880d92b48a3b7c1c50d01929e9b6f5))
* Don't use mozilla-unified when mismatch between autoland and central ([`6859755`](https://github.com/MozillaSecurity/autobisect/commit/685975553f320cd19e9ecb2f5d6bbb3f86f2fde3))
* Return build failure status if build_manager raises ([`c73032d`](https://github.com/MozillaSecurity/autobisect/commit/c73032dbb9668d3702b309a87c976bb848f92f6f))

## v3.1.9 (2022-03-30)
### Fix
* Catch and raise when build fails to extract ([`9a5eed7`](https://github.com/MozillaSecurity/autobisect/commit/9a5eed7ef89ea2e0845e0034c2873ab7bc1bb372))

## v3.1.8 (2022-02-17)
### Fix
* Remove explicit type cast for branch ([`6660448`](https://github.com/MozillaSecurity/autobisect/commit/66604480b20cb1299652f2c68fb49361a3652bce))
* Update type to allow None for start and end values ([`0028e88`](https://github.com/MozillaSecurity/autobisect/commit/0028e884347c43ee959a6d8f9b2fb5a9eb7c97cb))

## v3.1.7 (2022-02-01)
### Fix
* Update lithium ([`4d04887`](https://github.com/MozillaSecurity/autobisect/commit/4d04887b199a941f596bf4853b8cb15ad737f620))

## v3.1.6 (2022-01-31)
### Fix
* Autoland ranges may include multiple pushes ([`00821ea`](https://github.com/MozillaSecurity/autobisect/commit/00821ea7de71342cea96235128c99a25585164de))

## v3.1.5 (2022-01-28)
### Fix
* Add correct Testcase.load_single parameters ([`47b202e`](https://github.com/MozillaSecurity/autobisect/commit/47b202ef0aff037f1715b535e571f55456a03a86))

## v3.1.4 (2022-01-28)
### Fix
* Ignore pylint unsubscriptable-object false positive ([`c4cd456`](https://github.com/MozillaSecurity/autobisect/commit/c4cd456ce1035bcafadb191a70d3b27c4a413302))
* Update grizzly to v0.14.0 ([`2264a4d`](https://github.com/MozillaSecurity/autobisect/commit/2264a4d436b31660472c0bec75546ae7d5fb1a1d))
* Address lithium mypy type violations ([`6dd9ef8`](https://github.com/MozillaSecurity/autobisect/commit/6dd9ef8ce06e5f82534b5f238cb5d013793ef9c8))
* Use correct dep name for requests-mock ([`e0481a5`](https://github.com/MozillaSecurity/autobisect/commit/e0481a5621b84a3960d5ee46fcb49cf3821981f5))
* Use corrected types in fuzzfetch==^2.0.0 ([`0fe7f63`](https://github.com/MozillaSecurity/autobisect/commit/0fe7f638e63f072870ec72292ede89d19e925462))

## v3.1.3 (2021-09-21)
### Fix
* Update args to timed_run ([`d8ef7a2`](https://github.com/MozillaSecurity/autobisect/commit/d8ef7a2d560a05384054158bcbf605b94678a006))

## v3.1.2 (2021-09-20)
### Fix
* Ignore js runs that report unhandleable oom ([`22bed58`](https://github.com/MozillaSecurity/autobisect/commit/22bed58b065340f16473cf052bcac68d9f6bb4cb))

## v3.1.1 (2021-08-11)
### Fix
* Manually bump project version ([`3bcb59b`](https://github.com/MozillaSecurity/autobisect/commit/3bcb59b375d703b0f34b7b80cd05c36a653e92cd))
* Correct the broken query used to detect in_use builds ([`2324e6f`](https://github.com/MozillaSecurity/autobisect/commit/2324e6fcb698f2aca0e0ed8217a87effbc461d31))
* Sort builds by st_atime_ns for increased precision ([`cf4ea25`](https://github.com/MozillaSecurity/autobisect/commit/cf4ea255175634f1b4b418a404fd71dedd2faa91))
* Set build_path column type to TEXT ([`060d26b`](https://github.com/MozillaSecurity/autobisect/commit/060d26b473ef8ccaa5c0effa1115d27cb27052ed))

## v3.1.0 (2021-08-06)
### Feature
* Add --no-harness argument to disable harness ([`20a6aba`](https://github.com/MozillaSecurity/autobisect/commit/20a6aba7f9dd4933a0c1b8e1aab7d6c0ce08c232))

## v3.0.3 (2021-07-08)
### Fix
* Properly check enum value when generating message ([`c8b157d`](https://github.com/MozillaSecurity/autobisect/commit/c8b157d52b17dcf9fcaa09e9aee0abe2d43f7863))

## v3.0.2 (2021-07-07)
### Fix
* Set JSEvaluator target to 'js' ([`a870af3`](https://github.com/MozillaSecurity/autobisect/commit/a870af34d6ded412fa89838ce083d03cf49bfb26))

## v3.0.1 (2021-07-06)
### Fix
* Apply black formatting: ([`5339e24`](https://github.com/MozillaSecurity/autobisect/commit/5339e24a4faeb48e38da4819c4fa2c43361e45fa))
* Convert path args to str before passing to lithium ([`ca8ec8a`](https://github.com/MozillaSecurity/autobisect/commit/ca8ec8a5545be0ba4b5d89997d10c8b6e55f73af))

## v3.0.0 (2021-07-06)
### Feature
* Explicitly link evaluators to a fuzzfetch target ([`c341e33`](https://github.com/MozillaSecurity/autobisect/commit/c341e334eaa4d0303e431a36a345e4ea58f1143f))

### Breaking
* Modifies the bisector constructor args  ([`c341e33`](https://github.com/MozillaSecurity/autobisect/commit/c341e334eaa4d0303e431a36a345e4ea58f1143f))

## v2.1.0 (2021-06-24)
### Feature
* Enable mypy type checking ([#44](https://github.com/MozillaSecurity/autobisect/issues/44)) ([`bb3ed92`](https://github.com/MozillaSecurity/autobisect/commit/bb3ed92d54ae46467a6e7285b9358f9143a47c92))

## v2.0.0 (2021-06-21)


## v1.0.1 (2021-06-21)
### Fix
* Correct type hint issues ([`a0026a8`](https://github.com/MozillaSecurity/autobisect/commit/a0026a8545d7d0d65b469610845f388d2d907b05))

## v1.0.0 (2021-06-17)
### Feature
* Add type annotations throughout ([`23b5d9a`](https://github.com/MozillaSecurity/autobisect/commit/23b5d9a3ac3ff7b15dfacbfdcfed8f174e649772))

### Fix
* Additional fixes required by fuzzfetch update ([`3fd730a`](https://github.com/MozillaSecurity/autobisect/commit/3fd730add36abcaaacc5cdf5d79a9d778121530f))

### Breaking
* Adds target arg to BuildManager init  ([`3fd730a`](https://github.com/MozillaSecurity/autobisect/commit/3fd730add36abcaaacc5cdf5d79a9d778121530f))

### Documentation
* Remove entries caused by semantic-release error ([`0412bf5`](https://github.com/MozillaSecurity/autobisect/commit/0412bf5a723034039ec2416f3d602381fc6901fe))

## v0.14.1 (2021-06-15)
### Fix
* Update grizzly-framework to 1.13.2 ([`bcdcf15`](https://github.com/MozillaSecurity/autobisect/commit/bcdcf1563301e3716bf165556b6ae3b6aa0c8461))

## v0.10.0 (2021-06-15)
### Fix
* **ci:** Multi-command requires bash to be called first ([`acf9e5f`](https://github.com/MozillaSecurity/autobisect/commit/acf9e5fc57b1d2b497d465583c7df085240b6bf7))
* **ci:** Add deploy key to scope ([`069e6f1`](https://github.com/MozillaSecurity/autobisect/commit/069e6f1f42f21253227fd854da9ae7d55b5fc1e3))
* **ci:** Ensure master exists before running release ([`68778c2`](https://github.com/MozillaSecurity/autobisect/commit/68778c2595823c58eda7d2770c221830ce98eb3d))
* **docs:** Update usage info ([`12f6fa0`](https://github.com/MozillaSecurity/autobisect/commit/12f6fa07c0d375459000149608ea347c11392c62))

## v0.9.0 (2021-06-14)
### Feature
* Update fuzzfetch, grizzly-framework and lithium-reducer ([#41](https://github.com/MozillaSecurity/autobisect/issues/41)) ([`6170fee`](https://github.com/MozillaSecurity/autobisect/commit/6170fee77fc5dd64851c6c22d1b75e60e94e18e8))
