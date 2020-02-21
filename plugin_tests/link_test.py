from tests import base
from girder.models.user import User


def setUpModule():
    base.enabledPlugins.append('SSR_task')
    base.startServer()


def tearDownModule():
    base.stopServer()


class LinkTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.users = [
            User().createUser(
                'user%d' % n,
                'testpassword',
                'Test',
                'User',
                'user%d@example.com' % n
            ) for n in [0, 1]
        ]
