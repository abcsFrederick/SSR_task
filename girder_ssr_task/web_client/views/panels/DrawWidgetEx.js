import DrawWidgetEx from '@girder/configuration/panels/DrawWidgetEx';
import { wrap } from '@girder/core/utilities/PluginUtils';

import workflowSelection from './workflowSelection';
import OverlayCollection from '@girder/overlays/collections/OverlayCollection';
import drawWidget from '@girder/histomicsui/templates/panels/drawWidget.pug';


wrap(DrawWidgetEx, 'render', function (render) {
    render.call(this);
    let overlays = this.parentView.overlays;

    // if (this.workflowSelection) need to improve to remove duplicate view
    if (this._skipRenderHTML) {
        delete this._skipRenderHTML;
    } else {
      this.workflowSelection = new workflowSelection({
          el: this.$('.h-elements-container'),
          overlays: overlays,
          elements: this.collection.models,
          parentView: this
      });
    }
    return this;
});
