from util.conf import JIRA_SETTINGS, CONFLUENCE_SETTINGS, BITBUCKET_SETTINGS, JSM_SETTINGS
from util.api.jira_clients import JiraRestClient
from util.api.confluence_clients import ConfluenceRestClient
from util.api.bitbucket_clients import BitbucketRestClient
from lxml import etree
import json

JIRA = 'jira'
CONFLUENCE = 'confluence'
BITBUCKET = 'bitbucket'
JSM = 'jsm'
DEFAULT_ACTIONS = 'util/default_test_actions.json'


def read_json_file(file_path):
    with open(file_path) as json_file:
        data = json.load(json_file)
        return data


class BaseApplication:
    type = None
    version = None
    nodes_count = None
    dataset_information = None

    def __init__(self, api_client, config_yml):
        self.client = api_client(host=config_yml.server_url,
                                 user=config_yml.admin_login, password=config_yml.admin_password)
        self.config = config_yml

    def get_default_actions(self):
        actions_json = read_json_file(DEFAULT_ACTIONS)
        return actions_json[self.type]

    @property
    def jmeter_default_actions(self):
        return self.get_default_actions()['jmeter']

    @property
    def selenium_default_actions(self):
        return self.get_default_actions()['selenium']

    @property
    def locust_default_actions(self):
        return self.get_default_actions()['locust']


class Jira(BaseApplication):
    type = JIRA

    @property
    def version(self):
        jira_server_info = self.client.get_server_info()
        jira_server_version = jira_server_info.get('version', '')
        return jira_server_version

    @property
    def nodes_count(self):
        return self.client.get_cluster_nodes_count(jira_version=self.version)

    def __issues_count(self):
        return self.client.get_total_issues_count()

    @property
    def dataset_information(self):
        return f"{self.__issues_count()} issues"


class Confluence(BaseApplication):
    type = CONFLUENCE

    @property
    def version(self):
        return self.client.get_confluence_version()

    @property
    def nodes_count(self):
        return self.client.get_confluence_nodes_count()

    @property
    def dataset_information(self):
        return f"{self.client.get_total_pages_count()} pages"


class Bitbucket(BaseApplication):
    type = BITBUCKET
    bitbucket_repos_selector = "#content-bitbucket\.atst\.repositories-0>.field-group>.field-value"  # noqa W605

    @property
    def version(self):
        return self.client.get_bitbucket_version()

    @property
    def nodes_count(self):
        return self.client.get_bitbucket_nodes_count()

    @property
    def dataset_information(self):
        system_page_html = self.client.get_bitbucket_system_page()
        if 'Repositories' in system_page_html:
            dom = etree.HTML(system_page_html)
            repos_count = dom.cssselect(self.bitbucket_repos_selector)[0].text
            return f'{repos_count} repositories'
        else:
            return 'Could not parse number of Bitbucket repositories'


class Jsm(BaseApplication):
    type = JSM

    @property
    def version(self):
        jsm_server_info = self.client.get_service_desk_info()
        return jsm_server_info.get('version', '')

    @property
    def nodes_count(self):
        jira_server_info = self.client.get_server_info()
        jira_server_version = jira_server_info.get('version', '')
        return self.client.get_cluster_nodes_count(jira_version=jira_server_version)

    def __issues_count(self):
        return self.client.get_total_issues_count()

    @property
    def dataset_information(self):
        return f"{self.__issues_count()} issues"


class ApplicationSelector:
    APP_TYPE_MSG = ('ERROR: Please run util/analytics.py with application type as argument. '
                    'E.g. python util/analytics.py jira/confluence/bitbucket/jsm')

    def __init__(self, app_name):
        self.application_type = self.__get_application_type(app_name)

    def __get_application_type(self, app_name):
        if app_name.lower() not in [JIRA, CONFLUENCE, BITBUCKET, JSM]:
            raise SystemExit(self.APP_TYPE_MSG)
        return app_name.lower()

    @property
    def application(self):
        if self.application_type == JIRA:
            return Jira(api_client=JiraRestClient, config_yml=JIRA_SETTINGS)
        if self.application_type == CONFLUENCE:
            return Confluence(api_client=ConfluenceRestClient, config_yml=CONFLUENCE_SETTINGS)
        if self.application_type == BITBUCKET:
            return Bitbucket(api_client=BitbucketRestClient, config_yml=BITBUCKET_SETTINGS)
        if self.application_type == JSM:
            return Jsm(api_client=JiraRestClient, config_yml=JSM_SETTINGS)
