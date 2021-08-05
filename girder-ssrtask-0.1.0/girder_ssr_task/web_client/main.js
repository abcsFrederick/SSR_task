import './routes';

import { registerPluginNamespace } from '@girder/core/pluginUtils';

import * as SSRTask from './index';

registerPluginNamespace('ssrtask', SSRTask);
