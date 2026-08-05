"""Configuration Layer稳定异常。"""


class ConfigurationError(Exception):
    """配置加载或校验失败。"""


class ConfigurationFileError(ConfigurationError):
    """配置文件无法安全读取。"""


class MissingConfigurationError(ConfigurationError):
    """必需配置缺失。"""


class InvalidConfigurationError(ConfigurationError):
    """配置值不符合契约。"""
