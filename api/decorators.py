
class static_property(staticmethod):
    """
    Like @property but for a class
    ```
    class Foo:

        @static_property
        def bar() -> str:
            return 'asdf'
    ```

    foobar = Foo.bar
    """
    def __get__(self, *_):
        return self.__func__()
