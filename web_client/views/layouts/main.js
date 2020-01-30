import View from 'girder/views/View';
import Backbone from 'backbone';
import { restRequest } from 'girder/rest';
import events from 'girder/events';
import { splitRoute, parseQueryString } from 'girder/misc';
import { getCurrentUser } from 'girder/auth';

import MainPageViewTemplate from '../../templates/layouts/main.pug';
import '../../stylesheets/layouts/main.styl';

import DicomSplit from '../tasks/dicomsplit/main';
import router from '../../router';

var Layout = View.extend({
    events: {
        'click .enabledTask': function (e) {
            router.navigate('analysis/' + e.currentTarget.id + this.unparsedQueryString, {trigger: true});
        },
        'click #dataManagement': function () {
            let user = getCurrentUser();
            router.navigate('qc/user/' + user.id + this.unparsedQueryString, {trigger: true});
        }
    },
    initialize(settings) {
        Object.filter = (obj, predicate) =>
            Object.keys(obj).filter((key) => predicate(obj[key]));
        Layout.getSettings(null, (settings) => {
            this.settings = settings;
            this.renderNav();
        });

        let curRoute = Backbone.history.fragment,
            routeParts = splitRoute(curRoute),
            queryString = parseQueryString(routeParts.name);
        this.unparsedQueryString = $.param(queryString);
        if (this.unparsedQueryString.length > 0) {
            this.unparsedQueryString = '?' + this.unparsedQueryString;
        }
        this.listenTo(events, 'SSR_navView', this.renderNav);
        this.listenTo(events, 'SSR_taskView', this.renderTask);
    },
    renderNav(e) {
        let availableTasks = Object.filter(Layout.settings['SSR_task.TASKS'], (enable) => enable === true);

        this.$el.html(MainPageViewTemplate({
            tasks: availableTasks,
            currentTask: e
        }));
        // this.navTask = new navTask({
        //     el: $('.g-global-nav-main'),
        //     parentView: this,
        //     availableTasks: availableTasks
        // })
    },
    renderTask(e) {
        if (this.tasks) {
            this.tasks.destroy();
        }
        if (e === 'DicomSplit') {
            this.tasks = new DicomSplit({
                el: $('.task-container'),
                parentView: this
            });
        }
    }
}, {
    getSettings: function (task, callback) {
        if (!Layout.settings) {
            restRequest({
                type: 'GET',
                url: 'SSR_task/settings'
            }).done((resp) => {
                Layout.settings = resp;
                events.trigger('SSR_navView', task);
                events.trigger('SSR_taskView', task);
                if (callback) {
                    callback(Layout.settings);
                }
            });
        } else {
            events.trigger('SSR_navView', task);
            events.trigger('SSR_taskView', task);
            if (callback) {
                callback(Layout.settings);
            }
        }
    }
});

export default Layout;
