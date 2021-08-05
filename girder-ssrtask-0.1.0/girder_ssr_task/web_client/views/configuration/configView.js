import $ from 'jquery';

import View from '@girder/core/views/View';

import PluginConfigBreadcrumbWidget from
    '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import { restRequest } from '@girder/core/rest';
import events from '@girder/core/events';

import ConfigViewTemplate from '../../templates/configuration/configView.pug';
import '../../stylesheets/configuration/configView.styl';

import 'bootstrap-switch'; // /dist/js/bootstrap-switch.js',
import 'bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.css';

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
        ConfigView.getSettings((settings) => {
            this.settings = settings;
            this.render();
        });
    },

    render: function () {
        this.$el.html(ConfigViewTemplate({
            settings: this.settings
        }));

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'SSR Task',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        // this.$('.g-SSR-task-switch').bootstrapSwitch()
        //     .off('switchChange.bootstrapSwitch')
        //     .on('switchChange.bootstrapSwitch', (event, state) => {
        //         var plugin = $(event.currentTarget).attr('key');

        //     });
        return this;
    },

    _saveSettings: function (settings) {
        /* Now save the settings */
        return restRequest({
            type: 'PUT',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(() => {
            /* Clear the settings that may have been loaded. */
            ConfigView.clearSettings();
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-SSR-task-settinsge-error-message').text(
                resp.responseJSON.message
            );
        });
    }
}, {
    /**
     * Get settings if we haven't yet done so.  Either way, call a callback
     * when we have settings.
     *
     * @param {function} callback a function to call after the settings are
     *      fetched.  If the settings are already present, this is called
     *      without any delay.
     */
    getSettings: function (callback) {
        if (!ConfigView.settings) {
            restRequest({
                type: 'GET',
                url: 'SSR_task/settings'
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
    },

    /**
     * Clear the settings so that getSettings will refetch them.
     */
    clearSettings: function () {
        delete ConfigView.settings;
    }
});

export default ConfigView;
