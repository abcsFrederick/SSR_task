import DrawWidgetEx from '@girder/configuration/panels/DrawWidgetEx';
import { wrap } from '@girder/core/utilities/PluginUtils';

import workflowSelection from './workflowSelection';
import OverlayCollection from '@girder/overlays/collections/OverlayCollection';
import drawWidget from '@girder/histomicsui/templates/panels/drawWidget.pug';


wrap(DrawWidgetEx, 'render', function (render) {
    render.call(this);
    let overlays = this.parentView.overlays;

    // if (this.workflowSelection) FIX: Needs to remove duplicate view
    if (this.workflowSelection) {
        this.workflowSelection.undelegateEvents();
        this.workflowSelection.stopListening();
        this.workflowSelection.off();
    }
    this.workflowSelection = new workflowSelection({
        el: this.$('.h-elements-container'),
        overlays: overlays,
        elements: this.collection.models,
        parentView: this
    });

    return this;
});
