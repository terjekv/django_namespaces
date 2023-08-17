# Django Namespaces

A collection-oriented object permission model for Django.

Namespaces fills the niche when you want to grant groups or users privileges to collections of objects, rather than being concerned about permissions for each individual object.

## What is a namespace?

- A namespace contains a collection of objects.
- Every object belongs to one and only one namespace.
- Users and/or groups may be granted permissions to namespace.
- Permissions to create into, read, update, and delete objects within a namespace are delegated to users and/or groups.
- A users permissions to a namespace are the set of permissons granted to the user directly, as well as the permissions granted to groups the user is a member of.
- There is a clear distinction between permissions to the namespace itself and the objects within, allowing for a clear distinction between administration of the namespace and administration of the objects within.
- A specific permission (delegate) can be granted to a user or group to a namespace, they can then grant object permissions to other users and groups.
