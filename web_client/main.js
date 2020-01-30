import './routes';

import { registerPluginNamespace } from 'girder/pluginUtils';

import * as SSRTasks from './index';

registerPluginNamespace('SSR_Tasks', SSRTasks);
