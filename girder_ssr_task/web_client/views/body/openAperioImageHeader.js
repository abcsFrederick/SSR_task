import View from '@girder/core/views/View';
import events from '@girder/histomicsui/events';
import { restRequest } from '@girder/core/rest';

import OpenAperioImageTemplate from '../../templates/body/OpenAperioImageTemplate.pug';

var OpenAperioImageHeader = View.extend({
    events: {
        'click .h-open-aperio-image': function (evt) {
            events.trigger('h:openAperioImageUi');
        }
    },
    initialize(settings) {
        restRequest({
            type: 'GET',
            url: 'SSR_task/settings'
        }).done((resp) => {
            this.settings = resp;
            if (this.settings['SSR_task.TASKS']['Aperio']) {

            }
        });
    },
    renderOpenAperioImageHeader() {
        this.$('.h-open-annotated-image').before(OpenAperioImageTemplate());
        return this;
    }
});

export default OpenAperioImageHeader;
