import json
from data import User
import logging


class UserApi:
    @staticmethod
    def fetch_user(token):
        try:
            user = User.get(token)
            response = {
                'uid': user.user_id,
                'name': user.name,
                'status': user.status,
                'email': user.email,
            }
            success = True
        except Exception as e:
            success = False
            response = {'error': str(e)}
            logging.error(str(e))
        return response, (200 if success else 500)
