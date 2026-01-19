class LifeFrameUser:
    def __init__(self, data):
        self.id = data['id']

    def __str__(self):
        return(self.id)


class Category:
    def __init__(self, data: dict):
        self.id: int = int(data['id'])
        self.name: str = data['name']
        self.parent_id: int | None = data['parent_id']
        self.parent_name: str | None = data.get('parent_name')
        self.has_children: bool | None = data.get('has_children')
        self.relevant_weight: float | None = data.get('relevant_weight')
        self.search_similarity: float | None = data.get('search_similarity')
        self.archived: bool = data.get('archived', False)
        self.forwarded_to: int | None = data.get('forwarded_to')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'parent_name': self.parent_name,
            'search_similarity': self.search_similarity,
            'has_children': self.has_children,
            'relevant_weight': self.relevant_weight,
            'archived': self.archived,
            'forwarded_to': self.forwarded_to,
        }


class CategoryGroup:
    def __init__(self, data: dict):
        self.name = data['name']
        self.categories: list[int] = data['categories']

    def to_dict(self):
        return {
            'name': self.name,
            'categories': self.categories,
        }
