girderTest.importPlugin('jobs', 'worker', 'large_image', 'large_image_annotation', 'slicer_cli_web', 'histomicsui', 'archive', 'ssrtask');

girderTest.startApp();

describe('Test on SSR Task configuration', function () { 
    it('login', function () {
    	var tmpDir = '/tmp/test_girder_worker'
        girderTest.login('admin', 'Admin', 'Admin', 'password')();
        waitsFor(function () {
            return $('a.g-nav-link[g-target="admin"]').length > 0;
        }, 'admin console link to load');
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });
        waitsFor(function () {
            return $('.g-plugins-config').length > 0;
        }, 'the admin console to load');
        runs(function () {
            $('.g-plugins-config').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-plugin-config-link').length > 0;
        }, 'the plugins page to load');
        runs(function () {
            expect($('.g-plugin-config-link[g-route="plugins/ssrtask/config"]').length > 0);
            $('.g-plugin-config-link[g-route="plugins/ssrtask/config"]').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('#g-SSR-task-settings-form').length > 0;
        }, 'settings to be shown');
        runs(function () {
            $('#g-SSR-task-settings-TMP').val(tmpDir);
            $('.btn-primary').click();
            $('.g-SSR-task-list input[task="RNAScope"]').click();
        });
        waitsFor(function () {
            var resp = girder.rest.restRequest({
                url: 'system/setting',
                method: 'GET',
                data: {
                    list: JSON.stringify([
                        'SSR_task.TASKS',
                        'SSR_task.GIRDER_WORKER_TMP'
                    ])
                },
                async: false
            });
            var settings = resp.responseJSON;
            var settingsTMP = settings['SSR_task.GIRDER_WORKER_TMP'];
            var settingsTasks = settings['SSR_task.TASKS'];
            return (settingsTMP && settingsTMP === tmpDir &&
                    settingsTasks['RNAScope'] === false);
        }, 'SSR Task settings to change');
    });
});
