class CLIError(Exception):
    def __init__(self, message, code, *, status_code=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def format_cli_error(error):
    return f"Error: {error.message}\nCode: {error.code}"