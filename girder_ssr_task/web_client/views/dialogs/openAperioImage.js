import $ from 'jquery';
import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';
import events from '@girder/histomicsui/events';
import router from '@girder/histomicsui/router';

import template from '../../templates/dialogs/openAperioImage.pug';

let dialog;
const OpenAnnotatedImage = View.extend({
    events: {
        'click .query-image-aperio': 'query'
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
        let requestId = $('#aperio-request-id').val();

        restRequest({
            url: this.auth_url,
            method: 'POST',
            data: {
                username: username,
                password: password,
                requestId: JSON.stringify(requestId)
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
        if (this.$('#aperio-request-id').val() === '' || this.$('#h-db-username').val() === '' || this.$('#h-db-username').val() === '') {
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
