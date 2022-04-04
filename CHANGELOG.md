# Changelog

<!--next-version-placeholder-->

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
