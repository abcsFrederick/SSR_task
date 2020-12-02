====================================
SSR_task |build-status| |codecov-io|
====================================

.. |build-status| image:: https://travis-ci.org/abcsFrederick/SSR_task.svg?branch=master
    :target: https://travis-ci.org/abcsFrederick/SSR_task?branch=master
    :alt: Build Status

.. |codecov-io| image:: https://codecov.io/gh/abcsFrederick/SSR_task/branch/master/graphs/badge.svg?branch=master
    :target: https://codecov.io/gh/abcsFrederick/SSR_task/branch/master
    :alt: codecov.io

Girder plugin for SSR Task deploy.

Available Tasks:
 1. Dicom Split
 2. Link

Make sure set up girder-worker worker.local.cfg(for fetching) and SSR_task.GIRDER_WORKER_TMP(for writing) setting to the same place you want(large storage prefer). Otherwise fetched input and written output will be saved in different place.
