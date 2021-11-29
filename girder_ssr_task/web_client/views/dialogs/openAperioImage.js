import $ from 'jquery';
import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';
import events from '@girder/histomicsui/events';
import router from '@girder/histomicsui/router';

import template from '../../templates/dialogs/openAperioImage.pug';

let dialog;
const OpenAnnotatedImage = View.extend({
    events: {
        'click .query-image-aperio': 'query',
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

    initialize() {
        this.auth_url = 'SSR_task/aperio_img';
    },

    render() {
        this.$el.html(template({
            title: 'Open image from Aperio by image id'
        })).girderModal(this);
        return this;
    },

    query() {
        if (!this.validate()) {
            this.$('.g-validation-failed-message').html('Username/password or no WSI folder selected.');
            return;
        }
        let username = $('#h-db-username').val(),
            password = $('#h-db-password').val();
        console.log(this.$('.g-validation-failed-message'))
        this.$('.g-validation-failed-message').html('Fatching from Aperio archive...');
        restRequest({
            url: this.auth_url,
            method: 'POST',
            data: {
                username: username,
                password: password,
                inputId: JSON.stringify(this.$('#aperio-image-id').val() || this.$('#aperio-request-id').val()),
                inputType: this.$('#aperio-image-id').val() === '' ? 'requestId' : 'imageId'
            }
        }).done((model) => {
            // annotation refresh
            // Need a better way
            router.setQuery('bounds', null, { trigger: false });
            // router.setQuery('folder', folderId, { trigger: false });
            router.setQuery('image', model._id, {trigger: true});
            $('.modal').girderModal('close');
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
        if ((this.$('#aperio-request-id').val() === '' && this.$('#aperio-image-id').val() === '') || this.$('#h-db-username').val() === '' || this.$('#h-db-username').val() === '') {
            return false;
        }
        return true;
    }
});

function createDialog() {
    return new OpenAnnotatedImage({
        parentView: null
    });
}

events.on('h:openAperioImageUi', function () {
    if (!dialog) {
        dialog = createDialog();
    }
    dialog.setElement($('#g-dialog-container')).render();
});

export default createDialog;
