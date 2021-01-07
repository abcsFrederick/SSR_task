import View from '@girder/core/views/View';
import events from '@girder/histomicsui/events';

import WorkflowsTemplate from '../../templates/body/WorkflowsTemplate.pug';

var WorkflowsView = View.extend({
    events: {
        // 'click .h-open-labeled-image': function (evt) {
        //     events.trigger('h:openLabeledImageUi');
        // }
    },
    initialize: function (settings) {
        this.$el.append(WorkflowsTemplate);
        this.$('.h-open-labeled-image').insertAfter('.h-open-annotated-image');
    },
    render() {
        return this;
    }
});

export default WorkflowsView;
