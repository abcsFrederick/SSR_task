import $ from 'jquery';

import View from '@girder/core/views/View';
import events from '@girder/core/events';
import eventStream from '@girder/core/utilities/EventStream';

import { restRequest } from '@girder/core/rest';

import NNModelTemplate from '../../../templates/tasks/nnmodel/dialog.pug';


var ConfigView = View.extend({
    events: {
        'submit #g-SSR-task-settings-form': function (event) {
            event.preventDefault();
            this.$('#g-SSR-task-settings-error-message').empty();
            this._saveSettings([{
                key: 'SSR_task.GIRDER_WORKER_TMP',
                value: this.$('#g-SSR-task-settings-TMP').val()
            }]);
        },
        'change .g-SSR-task-switch': function (event) {
            this.settings['SSR_task.TASKS'][$(event.currentTarget).attr('task')] =
                $(event.currentTarget).is(':checked');

            event.preventDefault();
            this.$('#g-SSR-task-settings-error-message').empty();
            this._saveSettings([{
                key: 'SSR_task.TASKS',
                value: this.settings['SSR_task.TASKS']
            }]);
        },
        'click .g-SSR-task-list'(evt) {
            var $el = $(evt.currentTarget);
            $el.find('input').click();
        },
        'click .g-SSR-task-list a,input'(evt) {
            evt.stopPropagation();
        }
    },

    initialize: function () {
        ConfigView.getSettings((nnmodels) => {
            this.nnmodels = nnmodels;
            this.render();
        });
    },

    render: function () {
        this.$el.html(NNModelTemplate({
            title: 'NNModel Inference',
            nnmodels: this.nnmodels
        })).girderModal(this);

        return this;
    }
}, {
    getSettings: function (callback) {
        if (!ConfigView.settings) {
            restRequest({
                type: 'GET',
                url: 'nnmodel'
            }).done((resp) => {
                ConfigView.settings = resp;
                if (callback) {
                    callback(ConfigView.settings);
                }
            });
        } else {
            if (callback) {
                callback(ConfigView.settings);
            }
        }
    }
});