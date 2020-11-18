import './routes';

import { registerPluginNamespace } from '@girder/core/pluginUtils';

import * as SSRTasks from './index';

registerPluginNamespace('SSR_Tasks', SSRTasks);
