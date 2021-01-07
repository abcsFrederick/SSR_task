import HeaderView from '@girder/histomicsui/views/layout/HeaderImageView';
import { wrap } from '@girder/core/utilities/PluginUtils';

import WorkflowsView from './workflowsView';

wrap(HeaderView, 'render', function (render) {
    render.call(this);
    new WorkflowsView({
        el: this.$('.h-open-annotated-image').parent(),
        parentView: this
    }).render();
    return this;
});
