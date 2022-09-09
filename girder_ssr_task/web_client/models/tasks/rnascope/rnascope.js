import Model from '@girder/core/models/Model';

import JobModel from '@girder/jobs/models/JobModel';

import { restRequest } from '@girder/core/rest';

var rnascopeModel = Model.extend({
    resourceName: 'SSR_task/rnascope',
    itemIds: null,
    name: '',
    // overlayItemIds: null,
    includeAnnotationIds: null,
    excludeAnnotationIds: null,
    // mean: null,
    // stdDev: null,
    roundnessThresholds: null,
    pixelThresholds: null,
    pixelsPerVirions: null,

    createJob: function () {
        return restRequest({
            url: `${this.resourceName}`,
            method: 'POST',
            data: {
                'name': JSON.stringify(this.get('name')),
                'itemIds': JSON.stringify(this.get('itemIds')),
                // 'overlayItemIds': JSON.stringify(this.get('overlayItemIds')),
                'includeAnnotationIds': JSON.stringify(this.get('includeAnnotationIds')),
                'excludeAnnotationIds': JSON.stringify(this.get('excludeAnnotationIds')),
                'roundnessThresholds': JSON.stringify(this.get('roundnessThresholds')),
                'pixelThresholds': JSON.stringify(this.get('pixelThresholds')),
                'pixelsPerVirions': JSON.stringify(this.get('pixelsPerVirions'))
            }
        }).then((resp) => {
            return new JobModel(resp);
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    }
});

export default rnascopeModel;
