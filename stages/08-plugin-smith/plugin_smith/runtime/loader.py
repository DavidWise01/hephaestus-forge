
class PluginLoader:
    def validate(self, plugin):
        return hasattr(plugin, "build")
    def load(self, plugin):
        return self.validate(plugin)
