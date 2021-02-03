import Model from '@girder/core/models/Model';

import JobModel from '@girder/jobs/models/JobModel';

import { restRequest } from '@girder/core/rest';

var cd4plusModel = Model.extend({
    resourceName: 'SSR_task/cd4_plus',
    itemIds: null,
    overlayIds: null,
    annotationIds: null,
    mean: null,
    stdDev: null,

    createJob: function () {
        return restRequest({
            url: `${this.resourceName}`,
            method: 'POST',
            data: {
                'itemIds': JSON.stringify(this.get('itemIds')),
                'overlayIds': JSON.stringify(this.get('overlayIds')),
                'annotationIds': JSON.stringify(this.get('annotationIds')),
                'mean': JSON.stringify(this.get('mean')),
                'stdDev': JSON.stringify(this.get('stdDev'))
            }
        }).then((resp) => {
            return new JobModel(resp);
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    }
});

export default cd4plusModel;
