import events from 'girder/events';
import router from './router';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

import ConfigView from './views/configuration/configView';
import TasksLayout from './views/layouts/main';

exposePluginConfig('SSR_task', 'plugins/SSR_task/config');
router.route('plugins/SSR_task/config', 'SSR_taskConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});

router.route('apps/:task', 'SSR_taskView', function (task) {
    events.trigger('HeaderView:navigateTo', 'Apps');
    events.trigger('panelContent:navigateTo', 'Apps');
    TasksLayout.getSettings(task);
});
