
class Plugin:
    name = "base"
    version = "0.8.0"
    permissions = []
    def build(self, request):
        raise NotImplementedError
