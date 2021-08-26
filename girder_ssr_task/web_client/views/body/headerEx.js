import HeaderView from '@girder/histomicsui/views/layout/HeaderImageView';
import { wrap } from '@girder/core/utilities/PluginUtils';

import WorkflowsHeader from './workflowsHeader';
import OpenAperioImageHeader from './openAperioImageHeader';

wrap(HeaderView, 'render', function (render) {
    render.call(this);
    if (!this.workflowsHeader) {
        this.workflowsHeader = new WorkflowsHeader({
            el: this.$('.h-open-annotated-image').parent(),
            parentView: this
        });
    }
    if (!this.openAperioImageHeader) {
        this.openAperioImageHeader = new OpenAperioImageHeader({
            el: this.$('.h-open-annotated-image').parent(),
            parentView: this
        });
    }
    this.openAperioImageHeader.renderOpenAperioImageHeader();
    this.workflowsHeader.renderWorkflowHeader();
    return this;
});
