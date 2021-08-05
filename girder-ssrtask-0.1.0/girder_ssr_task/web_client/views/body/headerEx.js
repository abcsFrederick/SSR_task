import HeaderView from '@girder/histomicsui/views/layout/HeaderImageView';
import { wrap } from '@girder/core/utilities/PluginUtils';

import WorkflowsHeader from './workflowsHeader';

wrap(HeaderView, 'render', function (render) {
    render.call(this);
    if (!this.workflowsHeader) {
        this.workflowsHeader = new WorkflowsHeader({
            el: this.$('.h-open-annotated-image').parent(),
            parentView: this
        });
    }
    this.workflowsHeader.renderWorkflowHeader();
    return this;
});
