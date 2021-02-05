import logging
from data import User, Usage
from utils import to_int


class KeyApi:
    @staticmethod
    def get_key(body):
        try:
            product_id = to_int(body.get('product_id'))
            instance_code = body.get('instance_code')
            instance_type = to_int(body.get('instance_type'))
            auth_code = body.get('auth_code')
            auth_type = to_int(body.get('auth_type'))
            response = None
            if product_id and instance_code and instance_type and auth_code and auth_type:
                response = Usage.find(
                    product_id, instance_code, instance_type, auth_code, auth_type)
                if response:
                    return_code = 200
                else:
                    return_code = 401
            else:
                return_code = 400
        except Exception as e:
            return_code = 500
            logging.error(str(e))
        return response, return_code

    def validate_key(body):
        try:
            token = body.get('token')
            signature = body.get('signature')
            response = None
            if token and signature:
                response = Usage.validate(token, signature)
                if response:
                    return_code = 200
                else:
                    return_code = 401
            else:
                return_code = 400
        except Exception as e:
            return_code = 500
            logging.error(str(e))
        return response, return_code
