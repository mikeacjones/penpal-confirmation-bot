class Redditor:
    def __init__(self, id, fullname=None):
        self.id = id
        self.fullname = fullname if fullname else id

    def __str__(self) -> str:
        return self.fullname

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return other.lower() == str(self).lower()
        return (
            isinstance(other, self.__class__)
            and str(self).lower() == str(other).lower()
        )
