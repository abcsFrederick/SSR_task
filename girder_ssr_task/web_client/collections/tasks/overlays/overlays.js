import Collection from '@girder/core/collections/Collection';

import overlaysModel from '../../../models/tasks/overlays/overlays';

var overlaysCollection = Collection.extend({
    resourceName: 'SSR_task/overlays',
    model: overlaysModel,
    pageLimit: 100
});

export default overlaysCollection;
