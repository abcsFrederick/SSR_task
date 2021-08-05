girderTest.importPlugin('jobs', 'worker', 'large_image', 'large_image_annotation', 'slicer_cli_web', 'histomicsui', 'archive', 'ssrtask', 'rnascope');
girderTest.addScript('/static/built/plugins/ssrtask/SSRTaskTest.js');


girderTest.promise.done(function () {
    SSRTaskTest.startApp();

    describe('Overview panel tests', function () {
        describe('setup', function () {
            it('login regular user', function () {
                SSRTaskTest.login();
            });
            it('open 17138051.svs', function () {
                SSRTaskTest.openImage('17138051.svs');
            });
            waitsFor(function() {
                return $('.h-workflow-dropdown-link').length === 1;
            }, 'workflow drop list shows up');
        });
        describe('workflow drop list functions', function () {
            runs(function () {
                $('.h-workflow-dropdown-link').click();
                expect($('.dropdown-workflow').length).toBe(8);
            });
        });
    });
});