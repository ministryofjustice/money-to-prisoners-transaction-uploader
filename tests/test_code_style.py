import os
from mtp_common.test_utils.code_style import CodeStyleTestCase  # noqa

CodeStyleTestCase.root_path = os.path.join(os.path.dirname(__file__), os.path.pardir)
