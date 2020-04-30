import _ from 'underscore';

import View from 'girder/views/View';
import Backbone from 'backbone';
import { restRequest } from 'girder/rest';
import events from 'girder/events';
import { splitRoute, parseQueryString } from 'girder/misc';
import { getCurrentUser } from 'girder/auth';
import CollectionModel from 'girder/models/CollectionModel';

import ArchiveView from 'girder_plugins/Archive/views/body/ArchiveView';

import MainPageViewTemplate from '../../templates/layouts/main.pug';
import TaskNavTemplate from '../../templates/layouts/taskNav.pug';
import DataNavTemplate from '../../templates/layouts/dataNav.pug';
import '../../stylesheets/layouts/main.styl';
import '../../stylesheets/layouts/navTask.styl';

import DicomSplit from '../tasks/dicomsplit/main';
import Link from '../tasks/link/main';
import router from '../../router';

import UserView from '../widgets/UserViewWidget';
import CollectionView from '../widgets/CollectionViewWidget';

var Layout = View.extend({
    events: {
        // 'change input[type=radio][name=modality]': function (e) {
        //     events.trigger('SSR_taskView', 'DicomSplit');
        // },
        'click .enabledTask': function (e) {
            let curRoute = Backbone.history.fragment,
                routeParts = splitRoute(curRoute),
                queryString = parseQueryString(routeParts.name);
            let unparsedQueryString = $.param(queryString);
            if (unparsedQueryString.length > 0) {
                unparsedQueryString = '?' + unparsedQueryString;
            }
            router.navigate('apps/' + e.currentTarget.id + unparsedQueryString, {trigger: true});
        },
        'click .s-nav-siderBar': '_collaspeSideBar',
        'click .qc-User': function (event) {
            let link = $(event.currentTarget);
            let curRoute = Backbone.history.fragment,
                routeParts = splitRoute(curRoute),
                queryString = parseQueryString(routeParts.name);
            let unparsedQueryString = $.param(queryString);
            if (unparsedQueryString.length > 0) {
                unparsedQueryString = '?' + unparsedQueryString;
            }

            // router.navigate('apps/user/' + link.attr('g-id') + unparsedQueryString, {trigger: true});
            this.girderArchive = new UserView({
                parentView: this,
                viewName: 'appsUserView',
                el: '#appsUSERArch',
                id: link.attr('g-id')
            });
        },
        'click .qc-Collection': function (event) {
            let link = $(event.currentTarget);
            let curRoute = Backbone.history.fragment,
                routeParts = splitRoute(curRoute),
                queryString = parseQueryString(routeParts.name);
            let unparsedQueryString = $.param(queryString);
            if (unparsedQueryString.length > 0) {
                unparsedQueryString = '?' + unparsedQueryString;
            }

            this.girderArchive = new CollectionView({
                parentView: this,
                viewName: 'appsCollectionView',
                el: '#appsCollectionArch',
                id: link.attr('g-id')
            });
        },
        'click .qc-SAIP': function (event) {
            let link = $(event.currentTarget);
            let curRoute = Backbone.history.fragment,
                routeParts = splitRoute(curRoute),
                queryString = parseQueryString(routeParts.name);
            let unparsedQueryString = $.param(queryString);
            if (unparsedQueryString.length > 0) {
                unparsedQueryString = '?' + unparsedQueryString;
            }
            this.saipArchive = new ArchiveView({
                parentView: this,
                el: '#appsSAIPArch',
                id: link.attr('g-id')
            });
        }
    },
    initialize(settings) {
        Object.filter = (obj, predicate) =>
            Object.keys(obj).filter((key) => predicate(obj[key]));
        Layout.getSettings(null, (settings) => {
            this.settings = settings;
            this.renderTaskNav();
            this.renderDataNav();
        });

        this.$el.html(MainPageViewTemplate());

        let curRoute = Backbone.history.fragment,
            routeParts = splitRoute(curRoute),
            queryString = parseQueryString(routeParts.name);
        this.unparsedQueryString = $.param(queryString);
        if (this.unparsedQueryString.length > 0) {
            this.unparsedQueryString = '?' + this.unparsedQueryString;
        }
        this.listenTo(events, 'SSR_navView', this.renderTaskNav);
        this.listenTo(events, 'SSR_taskView', this.renderTask);
    },
    renderTaskNav(e) {
        let availableTasks = Object.filter(Layout.settings['SSR_task.TASKS'], (enable) => enable === true);

        this.$('#taskNav').html(TaskNavTemplate({
            tasks: availableTasks,
            currentTask: e
        }));

        // this.navTask = new navTask({
        //     el: $('.g-global-nav-main'),
        //     parentView: this,
        //     availableTasks: availableTasks
        // })
    },
    renderDataNav(e) {
        this.SSR_ProjectCollection = new CollectionModel();
        restRequest({
            url: 'collection',
            data: {'text': 'SSR Project'}
        }).then(_.bind((res) => {
            this.SSR_ProjectCollection = this.SSR_ProjectCollection.set(res[0]);
            this.$('#appsNav').html(DataNavTemplate({
                SSR_Project: this.SSR_ProjectCollection,
                user: getCurrentUser()
            }));
        }, this));
    },
    renderTask(e) {
        if (this.tasks) {
            this.tasks.destroy();
        }
        if (e === 'Link') {
            this.tasks = new Link({
                el: $('.task-container'),
                parentView: this
            });
        }
        if (e === 'DicomSplit') {
            this.tasks = new DicomSplit({
                el: $('.task-container'),
                parentView: this
            });
        }
    },
    _collaspeSideBar(e) {
        $(e.target).children()[0].classList.toggle('collapsein');
        if ($(e.target).children().hasClass('collapsein')) {
            this.$('.g-analysis-nav-container').css('left', 'calc(-40vw + 20px)');
            this.$('.g-analysis-nav-container').css('marginLeft', '0vw');
            this.$('.task-container').css('width', 'calc(100vw - 20px)');
            this.$('.task-container').css('marginLeft', '0');
        } else {
            this.$('.g-analysis-nav-container').css('left', '0vw');
            this.$('.g-analysis-nav-container').css('marginLeft', '0vw');
            this.$('.task-container').css('width', '60vw');
            this.$('.task-container').css('marginLeft', '0');
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
