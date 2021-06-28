girderTest.importPlugin('jobs', 'worker', 'large_image', 'large_image_annotation', 'slicer_cli_web', 'histomicsui', 'archive', 'ssrtask');

girderTest.startApp();

describe('Test on SSR Task', function () {
    var brandName = 'TestBrandName';
    it('login', function () {
        expect(1).toBe(1);
    });
});
