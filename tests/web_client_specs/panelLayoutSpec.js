girderTest.importPlugin('jobs', 'worker', 'large_image', 'large_image_annotation', 'slicer_cli_web', 'histomicsui', 'archive', 'ssrtask', 'rnascope');
girderTest.addScript('/static/built/plugins/ssrtask/SSRTaskTest.js');


girderTest.promise.done(function () {
    SSRTaskTest.startApp();

    describe('Panel layout tests', function () {
        describe('setup', function () {
            it('login regular user', function () {
                SSRTaskTest.login();
            });
            it('open 17138051.svs', function () {
                SSRTaskTest.openImage('17138051.svs');
            });
        });

        describe('Check panel', function () {
            it('check shows up and has reports', function () {
                runs(function () {
                    var workflowPanel = $('.h-panel-group-right .h-workflow-selector');
                    expect(workflowPanel.length).toBe(1);
                    var workflowOptions = $('.workflowOptions option');
                    var workflowNames = workflowOptions.map(function (idx, option) {
                        return option.value;
                    });
                    expect(workflowNames.toArray()).toEqual(['0', 'cd4+', 'rnascope']);
                });
            });
        });

        describe('Select workflow', function () {
            it('select workflow from lists', function () {
                runs(function () {
                    $(".workflowOptions option").val('rnascope').change();
                    expect($('.version-group').length).toBe(1);
                    expect($('.version-group .version-group-name')[0].innerText).toBe('I.: 100 V.: 101 R.: 102');
                });
                runs(function () {
                    $(".workflowOptions option").val('cd4+').change();
                    expect($('.version-group').length).toBe(1);
                    expect($('.version-group .version-group-name')[0].innerText).toBe('Mean: 100 StdDev: 101');
                });
            });
            it('open record', function () {
                runs(function () {
                    $($('.version-group-name')[0]).click();
                });
                waitsFor(function () {
                    return $('.version-annotations').length > 0;
                }, 'record load');
            });
        });
    });
});