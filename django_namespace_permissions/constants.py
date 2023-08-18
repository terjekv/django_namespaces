"""Types and constants for the django_namespace_permissions package."""

import enum


# ObjectActions are actions one can perform on objects within a given namespace.
#
# has_create allows one to create objects within the namespace.
# has_read allows one to read an objects within the namespace.
# has_update allows one to update objects within the namespace.
# has_delete allows one to delete objects within the namespace.
class ObjectActions(enum.Enum):
    """ObjectActions are actions one can perform on objects within a given namespace.

    has_create: Allows one to create objects within the namespace.
    has_read: Allows one to read an objects within the namespace.
    has_update: Allows one to update objects within the namespace.
    has_delete: Allows one to delete objects within the namespace.
    """

    CREATE = "has_create"
    READ = "has_read"
    UPDATE = "has_update"
    PARTIAL_UPDATE = "has_update"
    DELETE = "has_delete"


class NamespaceActions(enum.Enum):
    """NamespaceActions are actions one can perform on a namespace itself.

    has_read: Allows one to read the namespace (ie, see details about the namespace)
        this does *not* bestow the permission to read objects within the namespace.
    has_update: Allows one to update the namespace (ie, change details about the namespace)
    has_delete: Allows one to delete the namespace (ie, delete the namespace and
        all objects within it)
    has_delegate: Allows one to delegate permissions to other users on the namespace.
    has_create: Currently not used, but may be used in the future to allow users to
        create sub-namespaces.
    """

    CREATE = "has_create"
    READ = "has_read"
    UPDATE = "has_update"
    PARTIAL_UPDATE = "has_update"
    DELETE = "has_delete"
    DELEGATE = "has_delegate"


HTTP_METHOD_TO_OBJECTACTION_MAP = {
    "GET": ObjectActions.READ.value,
    "POST": ObjectActions.CREATE.value,
    "PUT": ObjectActions.UPDATE.value,
    "PATCH": ObjectActions.PARTIAL_UPDATE.value,
    "DELETE": ObjectActions.DELETE.value,
}
