import Model from '@girder/core/models/Model';

var linkModel = Model.extend({
    resourceName: 'SSR_task/link',
    linkName: null,
    originalId: null,
    segmentationId: null,
    segType: null
});

export default linkModel;
