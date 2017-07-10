"""AIOComments Router."""
from .views.comments_rest import CommentAPIView
from .views.comments_tree import get_comments_list, get_comments_tree, \
    get_comments_branch, stream_comments_tree, stream_user_comments
from .views.user_requests import get_user_dlrequests, download


ROUTES = (
    ('PUT', '/api/comment/', CommentAPIView),
    ('*', '/api/comment/{id:\d+}/', CommentAPIView),
    ('GET', '/api/comments/list/{i_id:\d+}/{itype_id:\d+}/', get_comments_list),
    ('GET', '/api/comments/list/{i_id:\d+}/{itype_id:\d+}/{limit:\d+}/', get_comments_list),
    ('GET', '/api/comments/list/{i_id:\d+}/{itype_id:\d+}/{limit:\d+}/{last_id:\d+}/', get_comments_list),

    ('GET', '/api/comments/tree/{i_id:\d+}/', get_comments_tree),
    ('GET', '/api/comments/tree/{i_id:\d+}/{itype_id:\d+}/', get_comments_tree),
    ('GET', '/api/comments/stream/tree/{i_id:\d+}/', stream_comments_tree),
    ('GET', '/api/comments/stream/tree/{i_id:\d+}/{itype_id:\d+}/', stream_comments_tree),

    ('GET', '/api/comments/branch/{i_id:\d+}/', get_comments_branch),
    ('GET', '/api/comments/branch/{i_id:\d+}/{itype_id:\d+}/', get_comments_branch),

    ('GET', '/api/comments/stream/user/{user_id:\d+}/', stream_user_comments),

    ('GET', '/api/comments/download/', download),
    ('GET', '/api/comments/download/{format:\w{1,4}}/', download),
    ('GET', '/api/comments/download/requests/{user_id:\d}/', get_user_dlrequests),
)
