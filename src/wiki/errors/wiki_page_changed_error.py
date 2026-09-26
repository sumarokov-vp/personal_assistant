from src.wiki.errors.wiki_error import WikiError


class WikiPageChangedError(WikiError):
    def __init__(self) -> None:
        super().__init__(
            "Страница изменилась, пока я её правил: правка не записана, повтори"
        )
