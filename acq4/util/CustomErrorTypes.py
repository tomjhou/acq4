

class ModuleReusedError(Exception):
    """ Module already used. """
    def __init__(self, *args, **kwargs): # real signature unknown
        pass

    def __str__(self, *args, **kwargs): # real signature unknown
        """ Return str(self). """
        pass

    name = property(lambda self: object(), lambda self, v: None, lambda self: None)  # default
    """module_reused"""