import $ from 'jquery';

// import ItemCollection from '@girder/core/collections/ItemCollection';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
// import eventStream from '@girder/core/utilities/EventStream';

import { restRequest } from '@girder/core/rest';

import BrowserWidget from './browserWidget';
import inferenceTemplate from '../../../templates/tasks/inference/dialog.pug';

// import BrowserWidget from './browserWidget';

// import prepareHeaderTemplate from '../../../templates/tasks/cd4plus/Header.pug';
// import ItemListTemplate from '../../../templates/tasks/halo/itemList.pug';

// import '../../../stylesheets/tasks/authentication/authentication.styl';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a register modal dialog.
 */
var InferenceView = View.extend({
    events: {
        'click #infer-WSIs-select': function (evt) {
            this.$('.h-task-infer-select').attr('disabled', true);
            this.$('#h-task-infer-container').removeClass('hidden');
            this.elementId = evt.currentTarget.id;
        },
        'click .run-batch-infer': 'infer'
    },
    initialize(settings) {
        this.infer_url = 'SSR_task/cd4_plus_infer';
        // this.listenTo(eventStream, 'g:event.job_email_sent', _.bind(function (event) {
        //     events.trigger('g:alert', {
        //         icon: 'ok',
        //         text: 'Finish counting CD4+, please go ahead to check.',
        //         type: 'success',
        //         timeout: 4000
        //     });
        // }, this));
    },
    render: function () {
        this.$el.html(inferenceTemplate({
            title: 'WSI Inference'
        })).girderModal(this);

        if (this._browserWidget) {
            this._browserWidget.destroy();
        }
        this._browserWidget = new BrowserWidget({
            parentView: this,
            titleText: 'Select a folder...',
            submitText: 'Open',
            showItems: true,
            selectFolder: true,
            showPreview: false,
            helpText: 'Click on a folder.',
            rootSelectorSettings: {
                pageLimit: 50
            },
            root: this.overlayRoot
        }).setElement($('#h-task-infer-container')).render();
        this.listenTo(this._browserWidget, 'g:selected', this._selectFolder);
        return this;
    },
    _selectFolder(folder) {
        this.outputId = folder.get('_id');
        this.$('#' + this.elementId).text('');
        if (folder) {
            this.$('#' + this.elementId).text(folder.get('name'));
        }
        this.$('#h-task-infer-container').addClass('hidden');
        this.$('.h-task-infer-select').attr('disabled', false);
    },
    infer() {
        if (!this.validate()) {
            this.$('.g-validation-failed-message').html('Username/password or no WSI folder selected.');
            return;
        }
        let username = $('#h-db-username').val(),
            password = $('#h-db-password').val();
        // let items = [];
        // for (let i = 0; i < this.WSIs.length; i++) {
        //     items.push(this.WSIs[i].get('_id'));
        // }

        restRequest({
            url: this.infer_url,
            method: 'POST',
            data: {
                workflow: this.$('input[name="inferOption"]:checked').val(),
                username: username,
                password: password,
                imageId: this.$('#aperio-image-id').val(),
                outputId: this.outputId
            }
        }).done(() => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Inference task submitted. You will be emailed when it finished',
                type: 'success',
                timeout: 4000
            });
        }).fail((error) => {
            events.trigger('g:alert', {
                icon: 'cancel',
                text: error.responseJSON.message,
                type: 'danger',
                timeout: 4000
            });
        });
        // this.$el.modal('hide');
    },
    validate() {
        if ((this.WSIs === undefined && this.$('#aperio-image-id').val() === '') ||
            this.$('#h-db-username').val() === '' || this.$('#h-db-username').val() === '' ||
            this.$('input[name="inferOption"]:checked').val() === undefined) {
            return false;
        }
        return true;
    }
});

export default InferenceView;
