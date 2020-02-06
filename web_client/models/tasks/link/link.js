import Model from 'girder/models/Model';

var linkModel = Model.extend({
    resourceName: 'SSR_task/link',
    originalId: null,
    segmentationId: null,
    segType: null
});

export default linkModel;
