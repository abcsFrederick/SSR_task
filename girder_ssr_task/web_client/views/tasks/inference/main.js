import $ from 'jquery';

import View from '@girder/core/views/View';
import events from '@girder/core/events';
import eventStream from '@girder/core/utilities/EventStream';

import { restRequest } from '@girder/core/rest';

import inferenceTemplate from '../../../templates/tasks/inference/dialog.pug';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a register modal dialog.
 */
var InferenceView = View.extend({
    events: {
        'click .run-batch-infer': 'infer',
        'input .query-id': function() {
            this.$('#aperio-request-id').prop('disabled', false);
            this.$('#aperio-image-id').prop('disabled', false);
            if (this.$('#aperio-image-id').val() !== '') {
                this.$('#aperio-request-id').prop('disabled', true);
            }
            if (this.$('#aperio-request-id').val() !== '') {
                this.$('#aperio-image-id').prop('disabled', true);
            }
        }
    },
    initialize(settings) {
        this.infer_url = 'SSR_task/aiara_infer';
        this.listenTo(eventStream, 'g:event.copy_to_cluster', _.bind(function (event) {
            events.trigger('g:alert', {
                icon: 'ok',
                text: event.data,
                type: 'success',
                timeout: 4000
            });
        }, this));
    },
    render: function () {
        this.$el.html(inferenceTemplate({
            title: 'WSI Inference'
        })).girderModal(this);

        return this;
    },
    infer() {
        if (!this.validate()) {
            this.$('.g-validation-failed-message').html('Username/password or no WSI folder selected.');
            return;
        }
        let username = $('#h-db-username').val(),
            password = $('#h-db-password').val();

        restRequest({
            url: this.infer_url,
            method: 'POST',
            data: {
                workflow: this.$('input[name="inferOption"]:checked').val(),
                username: username,
                password: password,
                inputId: JSON.stringify(this.$('#aperio-image-id').val() || this.$('#aperio-request-id').val()),
                inputType: this.$('#aperio-image-id').val() === '' ? 'requestId' : 'imageId'
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
        if ((this.$('#aperio-request-id').val() === '' && this.$('#aperio-image-id').val() === '') ||
            this.$('#h-db-username').val() === '' || this.$('#h-db-username').val() === '' ||
            this.$('input[name="inferOption"]:checked').val() === undefined) {
            return false;
        }
        return true;
    }
});

export default InferenceView;
