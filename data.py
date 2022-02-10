from simplendb.ndb import Model, ndb
from enum import Enum
import logging
from datetime import datetime
import rsa
import json
from base64 import b64encode, b64decode


class User(Model):

    class Status(Enum):
        L0 = 0
        L1 = 1
        L2 = 2
        L3 = 3
        L4 = 4

    def schema(self):
        super().schema()
        self.Property("user_id", ndb.StringProperty)
        self.Property('email', ndb.StringProperty)
        self.Property('name', ndb.StringProperty)

    @classmethod
    def find(cls, fire_user):
        """
        Verify the token against the Firebase Auth API and fetch the user details from the database

        """
        if not fire_user.get('uid'):
            return None
        _user = cls.query(
            filters = [("cls.user_id", "==", fire_user.get('uid'))]).get()
        if not _user:
            _user = User(user_id = fire_user.get('uid'), email = fire_user.get(
                'email'))
            _user.put()
        if _user.email != fire_user.get('email'):
            _user.email = fire_user.get('email')
            _user.put()
        _user.name = fire_user.get('name')
        return _user

class Customer(Model):

    def schema(self):
        super().schema()
        self.Property('name', ndb.StringProperty)
        self.Property('role', ndb.EnumProperty,
                      enum = User.Status, default = User.Status.L0, repeated = True)


class Organization(Model):
    """
    Entity that represents the ISV
    """

    def schema(self):
        super().schema()
        self.Property('name', ndb.StringProperty)
        self.Property('owner', ndb.KeyProperty, kind = User)
        self.Property('private', ndb.PickleProperty)
        self.Property('public', ndb.PickleProperty)

    def generate_keys(self):
        """
        Generate a new set of RSA keys.
        """
        (public_key, private_key) = rsa.newkeys(1024)
        self.public = public_key.save_pkcs1()
        self.private = private_key.save_pkcs1()


class Product(Model):
    """
    Entitiy that represents the Product.
    """

    def schema(self):
        super().schema()
        self.Property('name', ndb.StringProperty)
        self.Property('organization', ndb.KeyProperty, kind = Organization)
        # Is this product a freemium product
        self.Property('allows_free', ndb.BooleanProperty)


class Licence(Model):
    """
    Entity that represents that grant of a licence to access the Product.
    """

    def schema(self):
        super().schema()
        # product for which this is a licence key
        self.Property('product', ndb.KeyProperty, kind = Product)
        # Integer showing the licence type
        self.Property('access_level', ndb.IntegerProperty)
        # Id for the entity that owns the license
        self.Property('auth_code', ndb.StringProperty)
        # Type of the auth code
        self.Property('auth_type', ndb.IntegerProperty)
        
    def __init__(self, product, *args, **kwargs):
        super(Licence, self).__init__(*args, **kwargs)
        self.product = product.get_key()


class Usage(Model):
    """
    Entity that represents one usage of a licence
    """

    def schema(self):
        super().schema()
        # the key that this is a usage of
        self.Property('licence', ndb.KeyProperty, kind = Licence)
        # local copy of the key access_level
        self.Property('access_level', ndb.IntegerProperty, default = 0)
        # localcopy of the key product
        self.Property('product', ndb.KeyProperty, kind = Product)
        # The Identify for the entiity this Usage is authorised for
        self.Property('instance_code', ndb.StringProperty)
        # The type of the instance_code
        self.Property('instance_type', ndb.IntegerProperty)
        # local copy of the applicable private key
        self.Property('private', ndb.PickleProperty)
        # local copy of publci key
        self.Property('public', ndb.PickleProperty)

    def __init__(self, licence, *args, **kwargs):
        super(Usage, self).__init__(*args, **kwargs)
        self.licence = licence.get_key()
        if licence.access_level:
            self.access_level = licence.access_level
        if licence.product:
            self.product = licence.product
            org = licence.product.get().organization.get()
            self.private = org.private
            self.public = org.public

    def token(self) -> str:
        """
        Get the key token that will be passed to the client
        """
        return json.dumps({
            "product_id": self.product.id,
            "access_level": self.access_level,
            "licence_key": self.licence.id,
            "usage_id": self.key.id,
            "instance_code": self.instance_code,
            "instance_type": self.instance_type,
            "time_stamp": datetime.utcnow().isoformat(),
        })

    @classmethod
    def find(cls, product_id, instance_code, instance_type, auth_code, auth_type):
        """
        Find a Usage instance based on the info passed from the client
        """
        _key = Licence.query(filters = [
            ("product", "=", Product.Key(product_id)),
            ("auth_code", "=", auth_code),
            ("auth_type", "=", auth_type)
        ]
        ).get()
        if _key:
            _use = Usage.query(filters = [
            ("licence", "=", _key.get_key()),
            ("instance_code", "=", instance_code),
            ("instance_type", "=", instance_type)
        ]
        ).get()
            if _use:
                return _use.sign()            
            _use = Usage(
                _key,
                instance_code = instance_code,
                instance_type = instance_type
            )
            _use.put()
            return _use.sign()
        _product: Product = Product.get_by_id(product_id)
        if _product.allows_free:
            _key = Licence(
                product = _product,
                auth_code = auth_code,
                auth_type = auth_type
            )
            _key.put()
            _use = Usage(
                _key,
                instance_code = instance_code,
                instance_type = instance_type
            )
            _use.put()
            return _use.sign()
        return None

    @classmethod
    def validate(cls, key, signature):
        """
        Check tht a token represeting one usage that has been granted to a client is still valid
        """
        token = json.loads(key)
        _use = Usage.get_by_id(token.get('usage_id'))
        if _use and _use.verify(key, signature):
            return _use.sign()
        return None

    def sign(self) -> str:
        token = self.token()
        signature = rsa.sign(
            token.encode(), rsa.PrivateKey.load_pkcs1(self.private), 'SHA-1')
        response = {
            "signature": b64encode(signature).decode('utf-8'),
            "token": token
        }
        return response

    def verify(self, token, signature) -> bool:
        try:
            s1 = signature.encode()
            s2 = b64decode(s1)
            rsa.verify(token.encode(), s2,
                       rsa.PublicKey.load_pkcs1(self.public))
            return True
        except rsa.VerificationError:
            return False
