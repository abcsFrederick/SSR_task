import View from '@girder/core/views/View';
import events from '@girder/histomicsui/events';
import { restRequest } from '@girder/core/rest';

import overlaysWorkflowView from '../tasks/overlays/main';
import cd4plusWorkflowView from '../tasks/cd4plus/main';
import aperioWorkflowView from '../tasks/aperio/main';

import WorkflowsTemplate from '../../templates/body/WorkflowsHeader.pug';

var WorkflowsHeader = View.extend({
    events: {
        'click .workflow-list': function (evt) {
            let taskName = $(evt.currentTarget).attr('data-name').toLowerCase();
            // dialog task

            if (this.workflowView) {
                this.workflowView.destroy();
            }
            if (taskName === 'overlays') {
                this.workflowView = new overlaysWorkflowView({
                    el: $('#g-dialog-container'),
                    parentView: this,
                    workflow: $(evt.currentTarget).attr('data-name')
                });
            }
            if (taskName === 'cd4+') {
                this.workflowView = new cd4plusWorkflowView({
                    el: $('#g-dialog-container'),
                    parentView: this,
                    workflow: $(evt.currentTarget).attr('data-name')
                });
            }
            if (taskName === 'aperio') {
                this.workflowView = new aperioWorkflowView({
                    el: $('#g-dialog-container'),
                    parentView: this,
                    workflow: $(evt.currentTarget).attr('data-name')
                });
            }
            this.workflowView.render();
        }
    },
    initialize: function (settings) {
        Object.filter = (obj, predicate) =>
            Object.keys(obj).filter((key) => predicate(obj[key]));
        restRequest({
            type: 'GET',
            url: 'SSR_task/settings'
        }).done((resp) => {
            this.settings = resp;
            this.renderWorkflowHeader();
            // test workflow template
            // this.renderTest()
        });
        // this.$('.h-workflow-dropdown-link').insertBefore('.h-open-labeled-image');
    },
    renderWorkflowHeader() {
        if (!this.$('.h-workflow-dropdown-link').length && this.settings) {
            this.availableTasks = Object.filter(this.settings['SSR_task.TASKS'], (enable) => enable === true);

            this.$el.append(WorkflowsTemplate({
                workflows: this.availableTasks
            }));
        }
        return this;
    },
    // test workflow template
    renderTest() {
        this.workflowView = new cd4plusWorkflowView({
            el: $('.h-image-view-container'),
            parentView: this,
            workflow: 'cd4+'
        });
        this.workflowView.render();
    }
});

export default WorkflowsHeader;
