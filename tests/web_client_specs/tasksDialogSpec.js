girderTest.importPlugin('jobs', 'worker', 'large_image', 'large_image_annotation', 'slicer_cli_web', 'histomicsui', 'archive', 'ssrtask', 'rnascope');
girderTest.addScript('/static/built/plugins/ssrtask/SSRTaskTest.js');


girderTest.promise.done(function () {
    SSRTaskTest.startApp();

    describe('Task dialog tests', function () {
        beforeEach(function() {
                spyOn(window, 'confirm').andReturn(true);
            });
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
        describe('Aperio dialog', function () {
            runs(function () {
                $('.workflow-list[data-name="Aperio"]').click();
            });
            girderTest.waitForDialog();
            runs(function () {
                expect($('.modal-title').text()).toBe('Aperio Database annotation fetching');
                $('.h-task-aperio-select').click();
            });
            waitsFor(function() {
                return $('#h-task-aperio-container').is(":visible");
            }, 'Select a root shows up');

            runs(function () {
                $('#g-root-selector').val(
                    girder.auth.getCurrentUser().id
                ).trigger('change');
            });

            waitsFor(function () {
                return $('#g-dialog-container .g-folder-list-link').length > 0;
            }, 'Hierarchy widget to render');

            runs(function () {
                $('.g-folder-list-link:contains("Public")').click();
            });

            waitsFor(function () {
                return $('.g-folder-list-link:contains("WSI")').length > 0;
            }, 'WSI folder to load');

            runs(function () {
                $('.g-folder-list-link:contains("WSI")').click();
            });

            waitsFor(function () {
                return $('.g-item-list-link').length > 0;
            }, 'WSI item to load');

            runs(function () {
                $('.g-select-folder').click();
            });

            waitsFor(function () {
                return $('.wsi-item').length > 0;
            }, 'thumbnails shows up');

            runs(function () {
                $('.query-batch-aperio').click();
                expect($('.g-validation-failed-message')[0].innerText).toBe('Username/password or no WSI folder selected.');
                $('#h-db-username').val('test');
                $('#h-db-password').val('test');
                $('.query-batch-aperio').click();
            });
            waitsFor(function () {
                return  $('.alert:contains("username or password is invalid.")').length > 0
                    || $('.alert:contains("Image record not found in database.")').length > 0;
            }, 'authentication fails or no image found in database');
        });
        describe('Halo dialog', function () {
            runs(function () {
                $('.workflow-list[data-name="Halo"]').click();
            });
            girderTest.waitForDialog();
            runs(function () {
                expect($('.modal-title').text()).toBe('Halo Database annotation fetching');
                $('.h-task-halo-select').click();
            });
            waitsFor(function() {
                return $('#h-task-halo-container').is(":visible");
            }, 'Select a root shows up');

            runs(function () {
                $('#g-root-selector').val(
                    girder.auth.getCurrentUser().id
                ).trigger('change');
            });

            waitsFor(function () {
                return $('#g-dialog-container .g-folder-list-link').length > 0;
            }, 'Hierarchy widget to render');

            runs(function () {
                $('.g-folder-list-link:contains("Public")').click();
            });

            waitsFor(function () {
                return $('.g-folder-list-link:contains("WSI")').length > 0;
            }, 'WSI folder to load');

            runs(function () {
                $('.g-folder-list-link:contains("WSI")').click();
            });

            waitsFor(function () {
                return $('.g-item-list-link').length > 0;
            }, 'WSI item to load');

            runs(function () {
                $('.g-select-folder').click();
            });

            waitsFor(function () {
                return $('.wsi-item').length > 0;
            }, 'thumbnails shows up');

            runs(function () {
                $('.query-batch-halo').click();
                expect($('.g-validation-failed-message')[0].innerText).toBe('Username/password or no WSI folder selected.');
                $('#h-db-username').val('test');
                $('#h-db-password').val('test');
                $('.query-batch-halo').click();
            });
            waitsFor(function () {
                return  $('.alert:contains("username or password is invalid.")').length > 0;
            }, 'authentication fails');
        });
        describe('RNAScope dialog', function () {
            runs(function () {
                $('.workflow-list[data-name="RNAScope"]').click();
            });
            girderTest.waitForDialog();
            runs(function () {
                expect($('.modal-title').text()).toBe('RNAscope');
                $('.h-task-rnascope-select').click();
            });
            waitsFor(function() {
                return $('#h-task-rnascope-container').is(":visible");
            }, 'Select a root shows up');

            runs(function () {
                $('#g-root-selector').val(
                    girder.auth.getCurrentUser().id
                ).trigger('change');
            });

            waitsFor(function () {
                return $('#g-dialog-container .g-folder-list-link').length > 0;
            }, 'Hierarchy widget to render');

            runs(function () {
                $('.g-folder-list-link:contains("Public")').click();
            });

            waitsFor(function () {
                return $('.g-folder-list-link:contains("WSI")').length > 0;
            }, 'WSI folder to load');

            runs(function () {
                $('.g-folder-list-link:contains("WSI")').click();
            });

            waitsFor(function () {
                return $('.g-item-list-link').length > 0;
            }, 'WSI item to load');

            runs(function () {
                $('.g-select-folder').click();
            });

            waitsFor(function () {
                return $('.wsi-list').length == 2 && $($('.wsi-list .pixelsPerVirion')[1]).val() == '25';
            }, 'list shows up');

            runs(function () {
                var headers = $('.rnascope-header [class$=Header]');
                var headers = headers.map(function (idx, panel) {
                    return $(panel).text();
                });
                expect(headers.toArray()).toEqual(['WSI', 'Inclusion layer', 'Exclusion layer', 'Round.', 'Infect.', 'Virion.']);
                $($('.wsi-list .roundnessThreshold')[0]).val('0.9');
                $($('.wsi-list .pixelThreshold')[0]).val('300');
                $($('.wsi-list .pixelsPerVirion')[0]).val('10');
                $($('.wsi-list .icon-arrows-cw')[0]).click();
                expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to sync this parameters?');
            });
            runs(function () {
                expect($($('.wsi-list .roundnessThreshold')[1]).val()).toBe('0.9');
                expect($($('.wsi-list .pixelThreshold')[1]).val()).toBe('300');
                expect($($('.wsi-list .pixelsPerVirion')[1]).val()).toBe('10');
            });
            runs(function () {
                $('.save-batch-rnascope').click();
            });
            waitsFor(function () {
                return  $('.alert:contains("Your Job task is successfully submit, you will receive an email when it is finished.")').length > 0;
            }, 'submit task to worker');
        });

        // describe('Overlays dialog', function () {
        //     runs(function () {
        //         $('.workflow-list[data-name="Overlays"]').click();
        //     });
        //     girderTest.waitForDialog();
        //     runs(function () {
        //         expect($('.modal-title').text()).toBe('Overlays batch of WSIs with Masks');
        //         $('#h-WSIs-select').click();
        //     });
        //     waitsFor(function() {
        //         return $('#h-task-overlays-container').is(":visible");
        //     }, 'Select a root shows up');
        //     runs(function () {
        //         $('#g-root-selector').val(
        //             girder.auth.getCurrentUser().id
        //         ).trigger('change');
        //     });

        //     waitsFor(function () {
        //         return $('#g-dialog-container .g-folder-list-link').length > 0;
        //     }, 'Hierarchy widget to render');

        //     runs(function () {
        //         $('.g-folder-list-link:contains("Public")').click();
        //     });

        //     waitsFor(function () {
        //         return $('.g-folder-list-link:contains("WSI")').length > 0;
        //     }, 'WSI folder to load');

        //     runs(function () {
        //         $('.g-folder-list-link:contains("WSI")').click();
        //     });

        //     waitsFor(function () {
        //         return $('.g-item-list-link').length > 0;
        //     }, 'WSI item to load');

        //     runs(function () {
        //         $('.g-select-folder').click();
        //     });
        //     waitsFor(function () {
        //         return $('.wsis .g-item-list-entry').length == 2;
        //     }, 'WSI list shows up');

        //     runs(function () {
        //         $('#h-Masks-select').click();
        //     });
        //     waitsFor(function() {
        //         return $('#h-task-overlays-container').is(":visible");
        //     }, 'Select a root shows up');
        //     runs(function () {
        //         $('#g-root-selector').val(
        //             girder.auth.getCurrentUser().id
        //         ).trigger('change');
        //     });

        //     waitsFor(function () {
        //         return $('#g-dialog-container .g-folder-list-link').length > 0;
        //     }, 'Hierarchy widget to render');

        //     runs(function () {
        //         $('.g-folder-list-link:contains("Public")').click();
        //     });

        //     waitsFor(function () {
        //         return $('.g-folder-list-link:contains("MSK")').length > 0;
        //     }, 'MSK folder to load');

        //     runs(function () {
        //         $('.g-folder-list-link:contains("MSK")').click();
        //     });

        //     waitsFor(function () {
        //         return $('.g-item-list-link').length > 0;
        //     }, 'MSK item to load');

        //     runs(function () {
        //         $('.g-select-folder').click();
        //     });
        //     waitsFor(function () {
        //         return $('.masks .g-item-list-entry').length == 2;
        //     }, 'MSK list shows up');
        //     runs(function () {
        //         $('#h-overlays-name').val('overlayTest');
        //     });
        // });

        // ON GOING DO WE ALWAYS INSTALL OVERLAYS
        describe('CD4+ dialog', function () {
            runs(function () {
                $('.workflow-list[data-name="CD4+"]').click();
            });
            girderTest.waitForDialog();
            runs(function () {
                expect($('.modal-title').text()).toBe('CD4+ annotation cell counting');
                $('.h-task-cd4plus-select').click();
            });
            waitsFor(function() {
                return $('#h-task-cd4plus-container').is(":visible");
            }, 'Select a root shows up');

            runs(function () {
                $('#g-root-selector').val(
                    girder.auth.getCurrentUser().id
                ).trigger('change');
            });

            waitsFor(function () {
                return $('#g-dialog-container .g-folder-list-link').length > 0;
            }, 'Hierarchy widget to render');

            runs(function () {
                $('.g-folder-list-link:contains("Public")').click();
            });

            waitsFor(function () {
                return $('.g-folder-list-link:contains("WSI")').length > 0;
            }, 'WSI folder to load');

            runs(function () {
                $('.g-folder-list-link:contains("WSI")').click();
            });

            waitsFor(function () {
                return $('.g-item-list-link').length > 0;
            }, 'WSI item to load');

            runs(function () {
                $('.g-select-folder').click();
            });

            waitsFor(function () {
                // return $('.wsi-list').length == 2 && $($('.wsi-list .selectMask')[0]).val() == undefined;
                return $('.cd4plus-header [class$=Header]').length == 4;
            }, 'Now just render the header (later: list shows up but without overlay mask)');

            runs(function () {
                var headers = $('.cd4plus-header [class$=Header]');
                var headers = headers.map(function (idx, panel) {
                    return $(panel).text();
                });
                expect(headers.toArray()).toEqual(['WSI', 'Masks', 'Inclusion layer', 'Exclusion layer']);
                expect($('#h-cd4plus-mean').val()).toBe('498');
                expect($('#h-cd4plus-stdDev').val()).toBe('151');
            });
            // runs(function () {
            //     $('.save-batch-cd4plus').click();
            // });
            // waitsFor(function () {
            //     return  $('.alert:contains("Your Job task is successfully submit, you will receive an email when it is finished.")').length > 0;
            // }, 'submit task to worker');
        });
        describe('workflow download dialog', function () {
            runs(function () {
                $('.workflow-list[data-name="Download_Statistic"]').click();
            });
            girderTest.waitForDialog();
            waitsFor(function () {
                return $('.g-item-list-entry').length == 2 && $('#g-workflow-selector option').length == 3;
            }, 'workflow items show up');
            runs(function () {
                expect($('.modal-title').text()).toBe('Download statistics');
                expect($('.g-item-list-entry:contains("17138051.svs") .g-list-checkbox').is(':checked')).toBe(true);
                var workflowList = $('#g-workflow-selector option');
                var workflowNames = workflowList.map(function (idx, option) {
                    return option.value;
                });
                expect(workflowNames.toArray()).toEqual(['', 'cd4+', 'rnascope']);
                $('.g-submit-button').click();
                expect($('.g-validation-failed-message')[0].innerText).toBe('You need to select at least one image and workflow.');
                $('#g-workflow-selector option').val('rnascope').change();
            });
            waitsFor(function () {
                return $('.g-item-list-entry:visible').length == 1 && $($('.g-item-list-entry .g-item-list-link')[0]).text() == '117138051.svs';
            }, 'filter out items of particular workflow');
            runs(function () {
                expect($('.g-item-list-entry:contains("17138051.svs") .g-list-checkbox').is(':checked')).toBe(false);
                $('.g-submit-button').click();
                expect($('.g-validation-failed-message')[0].innerText).toBe('You need to select at least one image and workflow.');
            });
            runs(function () {
                $('.g-item-list-entry:contains("17138051.svs") .g-list-checkbox').prop('checked', true);
                $('.g-submit-button').click();
            });
        });
    });
});