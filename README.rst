====================================
SSR_task |build-status| |codecov-io|
====================================

With git action

.. |build-status| image:: https://circleci.com/gh/abcsFrederick/SSR_task.svg?style=svg
    :target: https://circleci.com/gh/abcsFrederick/SSR_task
    :alt: Build Status

.. |codecov-io| image:: https://codecov.io/gh/abcsFrederick/SSR_task/branch/master/graphs/badge.svg?branch=master
    :target: https://codecov.io/gh/abcsFrederick/SSR_task/branch/master
    :alt: codecov.io

Girder plugin for SSR Task deploy.

Available Tasks:
 For Radiology
 
 1. Dicom Split
 
 2. Link
 
 For Pathology
 
 3. Aperio
 
 4. Halo
 
 5. Overlays
 
 6. CD4+
 
 7. RNAScope
 
 8. Download_Statistic

Make sure set up girder-worker worker.local.cfg(for fetching) and SSR_task.GIRDER_WORKER_TMP(for writing) setting to the same place you want(large storage prefer). Otherwise fetched input and written output will be saved in different place.
