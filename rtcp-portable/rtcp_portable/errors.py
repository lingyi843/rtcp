class RTCPError(ValueError):
    """Invalid input, unsupported operation, or failed safety precondition."""


class ConfigurationError(RTCPError):
    pass


class LimitError(RTCPError):
    pass


class StateError(RTCPError):
    pass
