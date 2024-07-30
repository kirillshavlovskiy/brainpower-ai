from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from channels.db import database_sync_to_async
from django.conf import settings

# Defer getting the User model
UserModel = None


class UserIDAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        global UserModel
        if UserModel is None:
            UserModel = get_user_model()

        close_old_connections()

        # Get the user ID from the query string
        query_string = scope.get('query_string', b'').decode()
        query_params = dict(qp.split('=') for qp in query_string.split('&') if qp)
        user_id = query_params.get('user_id')

        if user_id:
            try:
                user = await self.get_user(int(user_id))
                scope['user'] = user
            except UserModel.DoesNotExist:
                scope['user'] = None
        else:
            scope['user'] = None

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        return UserModel.objects.get(id=user_id)