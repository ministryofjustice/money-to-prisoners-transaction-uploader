from mtp_common.build_tasks.executor import Context, Tasks
from mtp_common.build_tasks import tasks as shared_tasks
from mtp_common.build_tasks.paths import paths_for_shell

tasks = shared_tasks.tasks = Tasks()  # unregister all existing tasks
tasks.register(hidden=True)(shared_tasks.python_dependencies.func)
tasks.register(hidden=True)(shared_tasks.precompile_python_code.func)


@tasks.register('python_dependencies', 'precompile_python_code', default=True)
def build(_: Context):
    """
    Builds all necessary assets
    """


@tasks.register('build')
def test(context: Context, functional_tests=False):
    """
    Tests the app
    """
    environment = {'IGNORE_LOCAL_SETTINGS': 'True'}
    if functional_tests:
        environment.update({
            'RUN_FUNCTIONAL_TESTS': '1',
            'OAUTHLIB_INSECURE_TRANSPORT': '1',
        })
    return context.shell('pytest', '--capture', 'no', '--verbose', '--junit-xml', 'junit.xml', environment=environment)


@tasks.register()
def clean(context: Context, delete_dependencies: bool = False):
    """
    Deletes build outputs
    """
    paths = ['junit.xml']
    context.shell('rm -rf %s' % paths_for_shell(paths))
    context.shell('find %s -name "*.pyc" -or -name __pycache__ -delete' % context.app.django_app_name)

    if delete_dependencies:
        context.info('Cleaning app %s dependencies' % context.app.name)
        paths = ['venv']
        context.shell('rm -rf %s' % paths_for_shell(paths))
