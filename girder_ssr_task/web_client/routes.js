import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

import router from './router';
import ConfigView from './views/configuration/configView';
import TasksLayout from './views/layouts/main';

exposePluginConfig('ssrtask', 'plugins/ssrtask/config');
router.route('plugins/ssrtask/config', 'ssrtaskConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});

router.route('apps/:task', 'SSR_taskView', function (task) {
    events.trigger('HeaderView:navigateTo', 'Apps');
    events.trigger('panelContent:navigateTo', 'Apps');
    TasksLayout.getSettings(task);
});
