(function (global) {
    global.SSRTaskTest = {};

    var app;
    var currentImageId;

    function waitsForPromise(promise, description) {
        var done;

        promise.done(function () {
            done = true;
        }).catch(function (err) {
            if (description) {
                console.error(description);
            }
            throw err;
        });
        waitsFor(function () {
            return done;
        }, description || 'Promise to resolve');

        return promise;
    }

    function startApp() {
        girderTest.promise = girderTest.promise.then(function () {
            $('body').css('overflow', 'hidden');
            girder.router.enabled(false);
            girder.events.trigger('g:appload.before');
            girder.plugins.histomicsui.panels.DrawWidget.throttleAutosave = false;

            app = new girder.plugins.histomicsui.App({
                el: 'body',
                parentView: null
            });
            app.bindRoutes();
            girder.events.trigger('g:appload.after');
            global.SSRTaskTest.app = app;
            return app;
        });
    }

    function openImage(name) {
        var imageId;
        var deferred = $.Deferred();

        runs(function () {
            app.bodyView.once('h:viewerWidgetCreated', function (viewerWidget) {
                viewerWidget.once('g:beforeFirstRender', function () {
                    window.geo.util.mockWebglRenderer();
                });
            });
            $('.h-open-image').click();
        });

        girderTest.waitForDialog();

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
            var $item = $('.g-item-list-link:contains("' + name + '")');
            imageId = $item.next().attr('href').match(/\/item\/([a-f0-9]+)\/download/)[1];
            expect($item.length).toBe(1);
            $item.click();
        });
        waitsFor(function () {
            return $('#g-selected-model').val();
        }, 'selection to be set');

        girderTest.waitForDialog();
        runs(function () {
            $('.g-submit-button').click();
        });

        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.geojs-layer.active').length > 0;
        }, 'image to load');
        girderTest.waitForLoad();
        runs(function () {
            expect(girder.plugins.histomicsui.router.getQuery('image')).toBe(imageId);
            currentImageId = imageId;
            deferred.resolve(imageId);
        });

        return deferred.promise();
    }

    function geojsMap() {
        return app.bodyView.viewer;
    }

    function imageId() {
        return currentImageId;
    }

    function login(user, password) {
        girderTest.waitForLoad('login wait 1');
        runs(function () {
            $('.g-login').click();
        });

        girderTest.waitForDialog('login wait 2');
        runs(function () {
            $('#g-login').val(user || 'user');
            $('#g-password').val(password || 'password');
            $('#g-login-button').click();
        });

        waitsFor(function () {
            return $('.h-user-dropdown-link').length > 0;
        }, 'user to be logged in');
        girderTest.waitForLoad('login wait 3');
    }

    // global.SSRTaskTest.waitsForPromise = waitsForPromise;
    global.SSRTaskTest.startApp = startApp;
    global.SSRTaskTest.openImage = openImage;
    // global.SSRTaskTest.geojsMap = geojsMap;
    // global.SSRTaskTest.imageId = imageId;
    global.SSRTaskTest.login = login;
}(window));