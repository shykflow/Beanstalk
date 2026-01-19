from api.enums import ActivityType
from api.utils.mentioning import MentionUtils

class ActivityUtils:

    @staticmethod
    def get_activity_message(activity, item_count: int = 1) -> str:
        '''In most cases use the 'message' property on Activity or AggregateActivity'''

        and_people = ''
        if item_count is not None:
            if item_count == 2:
                and_people = f" and someone else"
            elif item_count > 2:
                and_people = f" and {activity.numItems} people"

        match ActivityType(int(activity.type)):
            case ActivityType.RECEIVED_MESSAGE:
                return f"{activity.related_user.username}{and_people} sent you a message"

            case ActivityType.MENTIONED_EXPERIENCE:
                return f"{activity.related_user.username}{and_people} mentioned you in an experience"
            case ActivityType.MENTIONED_PLAYLIST:
                return f"{activity.related_user.username}{and_people} mentioned you in a list"
            case ActivityType.MENTIONED_EXPERIENCE_STACK:
                return f"{activity.related_user.username}{and_people} mentioned you in an experience stack"
            case ActivityType.MENTIONED_POST:
                return f"{activity.related_user.username}{and_people} mentioned you in a post"
            case ActivityType.MENTIONED_COMMENT:
                return f"{activity.related_user.username}{and_people} mentioned you in a comment"

            case ActivityType.LIKED_EXPERIENCE:
                return f"{activity.related_user.username}{and_people} liked your experience"
            case ActivityType.LIKED_PLAYLIST:
                return f"{activity.related_user.username}{and_people} liked your list"
            case ActivityType.LIKED_EXPERIENCE_STACK:
                return f"{activity.related_user.username}{and_people} liked your experience stack"
            case ActivityType.LIKED_POST:
                return f"{activity.related_user.username}{and_people} liked your post"
            case ActivityType.LIKED_COMMENT:
                return f"{activity.related_user.username}{and_people} liked your comment"

            case ActivityType.COMMENTED_EXPERIENCE:
                return f"{activity.related_user.username}{and_people} commented {ActivityUtils.related_comment_text(activity)} on your experience"
            case ActivityType.COMMENTED_PLAYLIST:
                return f"{activity.related_user.username}{and_people} commented {ActivityUtils.related_comment_text(activity)} on your list"
            case ActivityType.COMMENTED_EXPERIENCE_STACK:
                return f"{activity.related_user.username}{and_people} commented {ActivityUtils.related_comment_text(activity)} on your experience stack"
            case ActivityType.COMMENTED_POST:
                return f"{activity.related_user.username}{and_people} commented {ActivityUtils.related_comment_text(activity)} on your post"
            case ActivityType.COMMENTED_COMMENT:
                return f"{activity.related_user.username}{and_people} commented {ActivityUtils.related_comment_text(activity)} on your comment"

            case ActivityType.ACCEPTED_EXPERIENCE:
                return f"{activity.related_user.username}{and_people} accepted one of your experiences"
            case ActivityType.COMPLETED_EXPERIENCE:
                return f"{activity.related_user.username}{and_people} reviewed one of your experiences"
            case ActivityType.ACCEPTED_PLAYLIST:
                return f"{activity.related_user.username}{and_people} accepted one of your lists"
            case ActivityType.COMPLETED_PLAYLIST:
                return f"{activity.related_user.username}{and_people} completed one of your lists"

            case ActivityType.FOLLOW_NEW:
                return f"{activity.related_user.username}{and_people} started following you"
            case ActivityType.FOLLOW_ACCEPTED:
                return f"{activity.related_user.username}{and_people} accepted your follow request"
            case ActivityType.FOLLOW_REQUEST:
                return f"{activity.related_user.username}{and_people} sent you a follow request"

            case ActivityType.ADDED_TO_YOUR_PLAYLIST:
                return f"{activity.related_user.username}{and_people} added an experience to your list"
            case ActivityType.REMOVED_FROM_PLAYLIST:
                return f"{activity.related_user.username}{and_people} removed an experience to your list"
            case ActivityType.ADDED_YOUR_EXPERIENCE_TO_PLAYLIST:
                return f"{activity.related_user.username}{and_people} added your experience to their list"

    @staticmethod
    def related_comment_text(activity, replace_mention_ids = False) -> str | None:
        if activity.related_comment is None:
            return None
        refined_comment = activity.related_comment.text
        if refined_comment is not None:
            refined_comment = " ".join(refined_comment.split())
            if replace_mention_ids:
                refined_comment = MentionUtils.text_with_usernames(refined_comment)
            if len(refined_comment) > 20:
                return f' "{refined_comment[:20]}..."'
            else:
                return refined_comment

    @staticmethod
    def comment_type(activity) -> bool:
        return activity.type in (
            ActivityType.COMMENTED_PLAYLIST,
            ActivityType.COMMENTED_EXPERIENCE,
            ActivityType.COMMENTED_EXPERIENCE_STACK,
            ActivityType.COMMENTED_COMMENT,
            ActivityType.COMMENTED_POST,
            ActivityType.MENTIONED_COMMENT,
        )
