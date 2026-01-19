import re

from django.db.models import QuerySet, Q


class MentionUtils:

    @staticmethod
    def verified_users_mentioned_in_text(text: str) -> QuerySet:
        """
        Returns the list of unique Users who were
        <@userid> tagged in the text.

        Example:
        ```python
        text = "I think <@1234> gave a gift to <@9876>"
        users = MentionUtils.verified_users_mentioned_in_text(text)
        ```
        users == QuerySet<User>([User("thomas"), User("tanner4")])
        """
        # Avoiding circular imports
        from api.models import User
        tags = re.findall(r'<@[0-9]+>', text)
        # Convert tags from "<@1234>" to 1234
        user_ids: list[int] = [int(tag[2:-1]) for tag in tags]
        return User.objects \
            .filter(id__in=user_ids) \
            .filter(email_verified=True) \
            .distinct() \
            .order_by('id')

    @staticmethod
    def text_with_usernames(text: str) -> str:
        """
        Returns list with <@123> replaced with @userABC
        """
        # TODO use cached usernames
        users = MentionUtils.verified_users_mentioned_in_text(text)
        for user in users:
            text = text.replace(f'<@{user.id}>', f'@{user.username}')
        return text
