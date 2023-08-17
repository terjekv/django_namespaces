# Working with namespaces

Assuming you have installed the namespaces endpoints to the `/namespaces/` path, you can now work with namespaces as follows. Note that all these views require authentication, but the examples ignore this for brevity.

!!! note
    For all operations where you would use the id of the namespace, you can also use the name of the namespace.

## Endpoints for namespaces themselves

These endpoints are named `namespace-list-list` (for the list view) and `namespace-list-detail` (for the detail view).

### List namespaces (list view)

```bash
curl http://localhost:8000/namespaces/
```

### Create a namespace (detail view)

```bash
curl -X POST -H "Content-Type: application/json" -d '{"name": "test", "description": "A test namespace"}' http://localhost:8000/namespaces/
```

### Read a namespace (detail view)

```bash
curl http://localhost:8000/namespaces/1/
```

This will also show all user and groups that have permissions to the namespace, as well as their permission settings. Note that this will not expand users from groups, so users listed here are only those that have been granted permissions directly to the namespace. A user may be a member of a group and thus have permissions to the namespace, but will not be listed here.

### Update a namespace (detail view)

```bash
curl -X PATCH -H "Content-Type: application/json" -d '{"description": "A test namespace, updated"}' http://localhost:8000/namespaces/1/
```

### Delete a namespace (detail view)

```bash
curl -X DELETE http://localhost:8000/namespaces/1/
```

## Working with permissions

The permissions to namespaces or their objects are manipulated through the following endpoint:
`/<namespaceid>/(namespace|objects)/(user|group)/<user_or_groupid>`.

### Granting permissions to namespaces

This endpoint is named `namespace-grant-grant-permission`.

A few examples:

```bash
curl -X POST http://localhost:8000/namespaces/1/namespace/user/1/ -d '{"has_read": true}'
```

This grants the user with id 1 read permissions to the namespace with id 1. This will allow only this user to read the namespace itself, but not the objects within.

```bash
curl -X POST http://localhost:8000/namespaces/1/objects/group/1/ -d '{"has_read": true}'
```

This grants the group with id 1 read permissions to the objects within the namespace with id 1. Anyone in the group with id 1 will be able to read the objects within the namespace with id 1, but not the namespace itself.

The permissions available to be granted are:

#### For the namespaces themselves

- `has_read`: Allows a user to see the user and groups and their permissions to the namespace, as well as its name and description.
- `has_update`: Allows a user to change the name and description of the namespace.
- `has_delegate`: Allows a to delegate permissions to the namespace.
- `has_delete`: Allows a user to delete the namespace.

!!! warning
    Deleting a namespace also deletes all objects within the namespace.

#### For the objects within the namespace

- `has_create`: Allows a user to create objects within the namespace.
- `has_read`: Allows a user to read objects within the namespace.
- `has_update`: Allows a user to update existing objects within the namespace.
- `has_delete`: Allows a user to delete objects within the namespace.

Note that for `has_update` and `has_delete`, the requestor also needs `has_read` to the object or namespace they want to manipulate. Often, these permissions are provided by different groups, so one user may be a member of two  groups, one that grants `has_read` to the namespace, and another group that grants `has_update` to the namespace. These permissions then combine to allow the user to update the object, while allowing members of the `has_read` group to only read the object or namespace without being able to manipulate it.

### Revoking all permissions to namespace

This endpoint is named `namespace-grant-revoke-permission`.

```bash
curl -X DELETE http://localhost:8000/namespaces/1/namespace/user/1/
```

This revokes the user with id 1 all permissions from the namespace with id 1. Note that this does not revoke permissions from groups the user is a member of, nor does it remove permissions to the objects within the namespace.

```bash
curl -X DELETE http://localhost:8000/namespaces/1/objects/user/1/
```

### Patching permissions to namespaces

This endpoint is named `namespace-grant-modify-permissions`.

```bash
curl -X PATCH http://localhost:8000/namespaces/1/objects/group/1/ -d '{"has_update": true}'
```

This removes all permissions *except has_update* from the group with id 1 to update objects within the namespace with id 1. Note that this is a patch, so you need to specify all permissions you want to keep.

### Listing permissions to namespaces

The name of this endpoint is `namespace-grant-list-permission`.

```bash
curl http://localhost:8000/namespaces/1/namespace/user/1/
```

This lists all permissions the user with id 1 has to the namespace with id 1. Note that this expands from groups, so if the user is a member of a group that has permissions to the namespace, this will be listed here.

```bash
curl http://localhost:8000/namespaces/1/objects/group/1/
```

List the given groups permissions to the objects within the namespace with id 1.
