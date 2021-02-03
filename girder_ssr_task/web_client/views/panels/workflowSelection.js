import _ from 'underscore';
import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';
import events from '@girder/core/events';
import eventStream from '@girder/core/utilities/EventStream';

import CD4plusModel from '../../models/tasks/cd4plus/cd4plus';

import workflowSelectionTemplate from '../../templates/panels/workflowSelectionTemplate.pug';
import elementsTemplate from '../../templates/panels/elements.pug';
import versionTemplate from '../../templates/panels/versionControl.pug';
import headerTemplate from '../../templates/panels/headerTemplate.pug';
import '../../stylesheets/panels/workflowSelection.styl';

var workflowSelection = View.extend({
    events: {
        'change .workflowOptions': 'pickWorkflow',
        'change .overlayOptions': 'pickOverlay',
        'change .versionOptions': 'pickVersion',
        'click .icon-download': 'downloadStatistic',
        'click .icon-play': 'save'
    },
    initialize: function (settings) {
        this.overlays = settings.overlays;
        this.elements = settings.elements;

        this.workflowList = [];
        this.overlays.filter(model => { 
            if (model.get('workflow')) {
                Object.keys(model.get('workflow')).forEach(workflow => {
                    if (this.workflowList.indexOf(workflow) === -1) {
                        this.workflowList.push(workflow)
                    }
                })
            }
        });
        if (this.workflowList.length) {
            this.render();
        }
    },
    render() {
        if (this.elements.length === 0) {
            this.$('#workflowsResultSelection').empty();
        } else {
            if (!this.$('#workflowsResultSelection').length) {
                this.$el.prepend(workflowSelectionTemplate({
                    workflows: this.workflowList,
                    overlays: this.overlays.toJSON()
                }));
            }
        }
        return this;
    },
    pickWorkflow(evt) {
        console.log('jige1')
        $('.overlayOptions .overlays').addClass('hidden');
        $('.overlayOptions').val(0);
        this.selectedWorkflow = $(evt.currentTarget).val();
        this.overlays.filter((model) => {
            if (model.get('workflow')) {
                if (Object.keys(model.get('workflow')).indexOf(this.selectedWorkflow) !== -1) {
                    $('.overlayOptions [value=' + model.get('_id') + ']').removeClass('hidden');
                }
            }
        });
        this.$('.result').remove();
        this.refreshElement();
    },
    pickOverlay(evt) {
        if ($(evt.currentTarget).val() != 0) {
            let model = this.overlays.get($(evt.currentTarget).val());
            if (this.selectedWorkflow === undefined) {
                this.selectedWorkflow = this.$('.workflowOptions').val();
            }
            this.verisonControl = model.get('workflow')[this.selectedWorkflow];
            if (this.verisonControl.length) {
                if (this.$('.result')) {$('.result').empty()}

                $('#workflowsResultSelection').append(versionTemplate({
                    results: this.verisonControl
                }));
            }
        } else {
            this.$('.result').remove();
            this.refreshElement();
        }
    },
    pickVersion(evt) {
        this.refreshElement();
        if ($(evt.currentTarget).val() != 0) {
            if ( !this.hasHeader ) {
                this.$('#workflowsResultSelection').after(headerTemplate());
            }
            if (this.verisonControl === undefined) {
                let model = this.overlays.get(this.$('.overlayOptions').val());
                this.verisonControl = model.get('workflow')[this.$('.workflowOptions').val()];
            }
            let version = this.verisonControl.filter(v => { if (v.version === parseInt($(evt.currentTarget).val())) return v });
            version[0]['result'].forEach((annotation) => {
                let element = this.elements.filter((element) => { 
                    if (element.get('id') === annotation['elementId']) {
                        return element
                    }
                });
                if (element[0] != undefined) {
                    $('.h-element[data-id=' + annotation['elementId'] + ']').html(elementsTemplate({
                        highlighted: this.parentView._highlighted,
                        element: element[0],
                        Num_of_Cell: annotation['Num_of_Cell']
                    }));
                }
                
            });
            this.hasHeader = true;
        }
    },
    refreshElement() {
        $('#annotationsHeader').empty();
        this.hasHeader = false;
        this.elements.forEach((element) => {
            $('.h-element[data-id=' + element.get('id') + ']').html(elementsTemplate({
                highlighted: this.parentView._highlighted,
                element: element
            }));
        })
    },
    downloadStatistic() {
        console.log('download');
    },
    save() {
        let overlays = [this.$('.overlayOptions').val()];
        let annotations = [this.parentView.annotation.get('_id')];
        let items = [this.parentView.image.get('_id')];
        let mean = this.$('.versionOptions').find(':selected').data('mean');
        let stdDev = this.$('.versionOptions').find(':selected').data('stddev');

        this.cd4plus = new CD4plusModel();
        this.cd4plus.set({
            itemIds: items,
            overlayIds: overlays,
            annotationIds: annotations,
            mean: mean,
            stdDev: stdDev
        });
        this.cd4plus.createJob().done((job) => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Your Job task is successfully submit, you will receive an email when it is finished.',
                type: 'success',
                timeout: 4000
            });
        });
    }
});

export default workflowSelection;
